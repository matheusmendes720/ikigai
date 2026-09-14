#!/usr/bin/env python3
"""Interactive chat REPL for the IKIGAI agent layer.

Features:
  - Loads active soul (default ikigai-planner) into system prompt via
    ``src.ikigai.src.agents.v2.system_prompt.assemble``.
  - User types messages; agent responds deterministically (prints the active
    soul summary + a heuristic response — no real LLM call in this shell).
  - ``/profile X`` command switches soul mid-REPL and re-renders the system
    prompt. Profile switches are logged via ``profile_switch.log_switch``.
  - Each user/agent message is persisted to
    ``vault/ikigai/runtime/chat/{thread_id}/chat.md`` via
    ``src.ikigai.src.chat.writer.write_entry``.
  - Each session emits SSE events via ``AgentSSEPublisher`` (using
    ``FakeGateway`` in dev mode for offline use).
  - Type ``exit`` (or send EOF / Ctrl+C / Ctrl+D) to quit gracefully — emits
    a ``thread.closed`` event on the way out.

Usage:
  python scripts/chat_repl.py --vault /tmp/repl-smoke --thread demo-repl

Env:
  IKIGAI_DEV_MODE=1   bind FakeGateway to the SSE publisher (default: same).
"""
from __future__ import annotations

import argparse
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Ensure repo root is on sys.path so ``from src.ikigai...`` resolves both when
# invoked directly and when piped through a shell.
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from src.ikigai.src.agents.v2.profile_switch import (  # noqa: E402
    log_switch,
    parse_profile_command,
)
from src.ikigai.src.agents.v2.sse_publisher import AgentSSEPublisher  # noqa: E402
from src.ikigai.src.agents.v2.system_prompt import assemble  # noqa: E402
from src.ikigai.src.agents.v2.tests.fixtures.fake_mcp_server import (  # noqa: E402
    FakeMcpServer,
)
from src.ikigai.src.chat.writer import write_entry  # noqa: E402
from src.ikigai.souls.loader import known_profiles, load_soul  # noqa: E402

DEFAULT_PROFILE = "ikigai-planner"
DEFAULT_CAPABILITIES = (
    "Read vault notes",
    "Persist chat entries to vault/ikigai/runtime/chat/{thread_id}/",
    "Switch active soul via /profile <name>",
)
DEFAULT_SCOPE = (
    "planner-only: NO PAV math, NO policy engine, NO scoring execution. "
    "Heuristic response is sufficient for shell demo."
)


# ---------------------------------------------------------------------------
# Fake SSE gateway — mirrors the shape of the test fixture but lives here
# so the script has zero deps on the v2 graph runtime path.
# ---------------------------------------------------------------------------
class FakeGateway:
    """Records every SSE publish call. Used in dev/offline mode."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    def publish_event(self, event: str, payload: dict) -> None:
        self.calls.append((event, dict(payload)))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _resolve_profile_or_die(name: str) -> str:
    """Return profile if it exists, else raise FileNotFoundError."""
    available = known_profiles()
    if name not in available:
        raise FileNotFoundError(
            f"unknown soul profile: {name!r}. Known: {sorted(available)}"
        )
    return name


def _build_system_prompt(profile: str) -> str:
    return assemble(profile, DEFAULT_CAPABILITIES, DEFAULT_SCOPE)


def _heuristic_respond(profile: str, user_message: str) -> str:
    """Deterministic offline response — no LLM call, prints the active soul
    summary plus a one-line heuristic reply."""
    soul = load_soul(profile)
    first_line = soul.strip().splitlines()[0] if soul.strip() else "(empty soul)"
    snippet = user_message.strip().splitlines()[0] if user_message.strip() else ""
    return (
        f"[{profile}] {first_line}\n"
        f"  echo: {snippet[:200]}"
    )


def _print_banner(profile: str, thread_id: str) -> None:
    bar = "=" * 64
    print(bar)
    print(f"  IKIGAI chat REPL — profile={profile}  thread={thread_id}")
    print("  commands: /profile <name> | exit | quit")
    print(bar)


# ---------------------------------------------------------------------------
# REPL
# ---------------------------------------------------------------------------
def run(
    vault_root: Path,
    thread_id: str,
    initial_profile: str,
    publisher: AgentSSEPublisher,
) -> int:
    profile = _resolve_profile_or_die(initial_profile)
    system_prompt = _build_system_prompt(profile)
    print()
    print(system_prompt)
    _print_banner(profile, thread_id)
    print()

    # Emit thread.created on startup
    publisher.publish_thread_created(
        thread_id=thread_id,
        profile_active=profile,
        soul_path=f"src/ikigai/souls/{profile}.md",
    )

    entry_seq = 0

    def _next_entry_id() -> str:
        nonlocal entry_seq
        entry_seq += 1
        return f"e-{thread_id[:8]}-{entry_seq:04d}"

    try:
        while True:
            try:
                raw = input(f"[{profile}] > ")
            except EOFError:
                print()
                break
            except KeyboardInterrupt:
                print()
                break

            text = raw.strip()
            if not text:
                continue
            if text.lower() in {"exit", "quit", ":q"}:
                break

            # /profile switch — handles both forms "/profile X" and bare "/profile"
            requested = parse_profile_command(text)
            if requested is not None:
                target = _resolve_profile_or_die(requested)
                if target == profile:
                    print(f"  (already on profile {target!r})")
                    continue
                prev = profile
                profile = target
                system_prompt = _build_system_prompt(profile)
                log_switch(
                    vault_root,
                    thread_id,
                    from_profile=prev,
                    to_profile=profile,
                    reason="user command",
                )
                publisher.publish_profile_switched(
                    from_profile=prev,
                    to_profile=profile,
                    reason="user command",
                )
                print(f"  switched: {prev} -> {profile}")
                print()
                print(system_prompt)
                print()
                continue

            # /profile with no arg or unknown profile — emit help
            if text.startswith("/profile"):
                available = sorted(known_profiles())
                print(f"  usage: /profile <name>. known: {available}")
                continue

            # Plain message → persist user entry, publish, then respond.
            ts_user = _now_iso()
            user_entry_id = _next_entry_id()
            write_entry(
                vault_root,
                thread_id,
                {"ts": ts_user, "actor": "user", "content": text},
            )
            publisher.publish_entry_message(
                entry_id=user_entry_id,
                actor="user",
                ts=ts_user,
                content=text,
            )

            response = _heuristic_respond(profile, text)
            print()
            print(response)
            print()

            ts_agent = _now_iso()
            agent_entry_id = _next_entry_id()
            write_entry(
                vault_root,
                thread_id,
                {"ts": ts_agent, "actor": "agent", "content": response},
            )
            publisher.publish_entry_message(
                entry_id=agent_entry_id,
                actor="agent",
                ts=ts_agent,
                content=response,
            )
    finally:
        publisher.publish_thread_closed(
            thread_id=thread_id,
            closed_at=_now_iso(),
            summary_path=f"vault/ikigai/runtime/chat/{thread_id}/chat.md",
        )

    print("bye.")
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="IKIGAI interactive chat REPL")
    p.add_argument(
        "--vault",
        type=Path,
        required=True,
        help="Vault root (will be created if missing).",
    )
    p.add_argument(
        "--thread",
        type=str,
        default=None,
        help="Thread id (uuid). Auto-generated if omitted.",
    )
    p.add_argument(
        "--profile",
        type=str,
        default=DEFAULT_PROFILE,
        help=f"Initial soul profile (default: {DEFAULT_PROFILE}).",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])
    vault_root: Path = args.vault.expanduser().resolve()
    vault_root.mkdir(parents=True, exist_ok=True)

    thread_id = args.thread or str(uuid.uuid4())
    if thread_id and not thread_id.strip():
        thread_id = str(uuid.uuid4())

    # Dev-mode SSE gateway: FakeGateway unless the env says otherwise. The
    # local FakeGateway keeps the script offline-friendly.
    publisher = AgentSSEPublisher(gateway=FakeGateway())

    try:
        return run(vault_root, thread_id, args.profile, publisher)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())

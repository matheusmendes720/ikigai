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
import re
import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List

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

# Cap response bullet count per the soul's # Constraints convention.
MAX_RESPONSE_BULLETS = 5


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
@dataclass(frozen=True)
class SoulView:
    """Parsed view of an IKIGAI soul markdown file.

    Cached once per (profile, switch) so we never load the same soul twice
    and never re-parse the same markdown twice.
    """

    profile: str
    markdown: str
    title: str
    voice_signature: str
    constraints: List[str] = field(default_factory=list)


_SECTION_RE = re.compile(r"^##\s+(?P<name>[^\n]+?)\s*$", re.MULTILINE)
_PARENS_RE = re.compile(r"\s*\([^)]*\)\s*$")


def _normalize_section_name(name: str) -> str:
    """Strip trailing parentheticals so ``Voice`` and ``Voice (foo)`` collide."""
    return _PARENS_RE.sub("", name.strip().lower()).strip()


def _split_sections(markdown: str) -> dict[str, str]:
    """Return ``{section_name_lower: body}`` for every ``## Heading`` block.

    Section names are normalized via :func:`_normalize_section_name` so that
    ``## Constraints (7 never-do rules)`` and ``## Constraints`` map to the
    same lookup key.
    """
    matches = list(_SECTION_RE.finditer(markdown))
    sections: dict[str, str] = {}
    for i, m in enumerate(matches):
        name = _normalize_section_name(m.group("name"))
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(markdown)
        sections[name] = markdown[start:end].strip()
    return sections


def _first_line_or_bullet(text: str) -> str:
    """Return the first bullet or first non-empty paragraph line of ``text``."""
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        # Strip leading bullet markers like "- " or "* " or "1. "
        cleaned = re.sub(r"^([-*]|\d+\.)\s+", "", line)
        return cleaned
    return ""


def _extract_bullets(text: str) -> List[str]:
    """Return the never-do rules (or any bullet lines) from a section body."""
    bullets: List[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        m = re.match(r"^([-*]|\d+\.)\s+(.*)$", line)
        if m:
            cleaned = m.group(2).strip()
            # Skip section-level headers like "Constraints (7 never-do rules)"
            if cleaned and not cleaned.endswith(":"):
                bullets.append(cleaned)
    return bullets


def _parse_soul(profile: str) -> SoulView:
    """Load + parse a soul into a reusable SoulView."""
    markdown = load_soul(profile)
    sections = _split_sections(markdown)
    title_match = re.search(r"^#\s+(?P<title>[^\n]+)$", markdown, re.MULTILINE)
    title = title_match.group("title").strip() if title_match else profile
    voice = _first_line_or_bullet(sections.get("voice", ""))
    constraints = _extract_bullets(sections.get("constraints", ""))
    return SoulView(
        profile=profile,
        markdown=markdown,
        title=title,
        voice_signature=voice,
        constraints=constraints,
    )


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


def _build_system_prompt(soul: SoulView) -> str:
    """Render the system prompt from a parsed SoulView (single soul load)."""
    return assemble(
        soul.profile,
        DEFAULT_CAPABILITIES,
        DEFAULT_SCOPE,
        soul_content=soul.markdown,
    )


def _voice_excerpt(soul: SoulView, max_chars: int = 90) -> str:
    """Trim a voice signature to a single display line."""
    sig = soul.voice_signature
    if len(sig) <= max_chars:
        return sig
    return sig[: max_chars - 1].rstrip() + "…"


def _truncate_to_bullet_cap(text: str, cap: int) -> str:
    """Enforce the soul's # Constraints bullet cap (default 5).

    Keeps non-bullet lines intact, then keeps the first ``cap`` bullet lines
    (across ``-`` / ``*`` / numbered lists). Trailing bullet lines are dropped.
    """
    if cap <= 0:
        return text
    kept: List[str] = []
    bullet_count = 0
    for line in text.splitlines():
        if bullet_count >= cap and re.match(r"^\s*([-*]|\d+\.)\s+", line):
            continue
        if re.match(r"^\s*([-*]|\d+\.)\s+", line):
            bullet_count += 1
        kept.append(line)
    return "\n".join(kept)


def _agent_respond(soul: SoulView, user_message: str) -> str:
    """Soul-aware heuristic response — no LLM call.

    Output shape::

        [<profile>] <voice signature excerpt>...
          <response to user message>

    Heuristic:
      * ``plan`` keyword  →  propose a 5-step Q-by-Q sketch
      * contains ``?``     →  ask exactly one clarifying question
      * default            →  reflect back in 1-2 sentences

    The response is capped at ``MAX_RESPONSE_BULLETS`` bullets per the
    soul's # Constraints convention (enforced via ``_truncate_to_bullet_cap``).
    """
    msg = user_message.strip()
    msg_lower = msg.lower()
    tokens = re.findall(r"[a-z0-9]+", msg_lower)
    first_word = tokens[0] if tokens else ""
    contains_question = "?" in msg

    if first_word == "plan" or "plan" in tokens[:3]:
        response_body = (
            "Q-by-Q sketch:\n"
            f"  - Q3 close: audit the last 2 shipped waves, log blockers.\n"
            f"  - Q4 open: pick 2-3 active projects, defer the rest.\n"
            f"  - Decision: which one to sequence first, and why?\n"
            f"  - Risk: 1 failure mode the user hasn't named yet.\n"
            f"  - Next checkpoint: by end of this week."
        )
    elif contains_question:
        response_body = (
            "One clarifying question before I respond: "
            "what would success look like for you in the next 7 days?"
        )
    else:
        response_body = (
            f"Reflecting back: I heard the signal in your message. "
            f"Two threads worth surfacing — the immediate ask and the underlying "
            f"intent. Tell me which one to dig into first."
        )

    response_body = _truncate_to_bullet_cap(response_body, MAX_RESPONSE_BULLETS)
    excerpt = _voice_excerpt(soul)
    return f"[{soul.profile}] {excerpt}\n  {response_body}"


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
    # Load + parse the soul exactly once. Reuse for system prompt AND for
    # every subsequent response (no double-load via load_soul()).
    soul = _parse_soul(profile)
    system_prompt = _build_system_prompt(soul)
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
                soul = _parse_soul(profile)  # ONE load per switch
                system_prompt = _build_system_prompt(soul)
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

            response = _agent_respond(soul, text)
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

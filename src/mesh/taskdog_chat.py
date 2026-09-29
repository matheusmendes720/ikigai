"""td chat REPL — interface CLI do v2 graph.

Stream events from v2 graph as they're produced. NO auto-execute.
Always emit Proposal and wait for --approve.

Usage:
    td chat [--thread-id ID] [--model NAME]

The REPL keeps a single thread_id across turns. Approval state is
persisted in the v2 graph checkpointer (SQLite) so resume works.
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


# ANSI color codes (works on Windows Terminal / PowerShell with VT100)
class C:
    R = "\033[31m"  # red
    G = "\033[32m"  # green
    Y = "\033[33m"  # yellow
    B = "\033[34m"  # blue
    M = "\033[35m"  # magenta
    C = "\033[36m"  # cyan
    DIM = "\033[2m"  # dim
    BOLD = "\033[1m"  # bold
    RESET = "\033[0m"


def _ensure_ikigai_path() -> None:
    """Add src/ikigai/src to sys.path if not already there."""
    repo_root = Path(__file__).resolve().parents[2]  # .../life-oss/life
    ikigai_src = repo_root / "src" / "ikigai" / "src"
    if str(ikigai_src) not in sys.path:
        sys.path.insert(0, str(ikigai_src))


def _summarize_event(node_name: str, node_output: dict[str, Any]) -> str:
    """Make a one-line summary of a node's output for streaming display."""
    # Pick a key piece of info depending on the node
    if node_name == "recall":
        ctx = node_output.get("context", {})
        n_vault = len(ctx.get("vault_today", "").splitlines())
        n_taskdog = len(ctx.get("taskdog_active", []))
        return f"read vault ({n_vault} lines), taskdog ({n_taskdog} tasks), memory (k={len(ctx.get('memory', []))})"
    if node_name == "observe":
        return f"observed: {node_output.get('raw_query', '?')[:60]}"
    if node_name == "reason":
        return f"reasoned: {len(node_output.get('intentions', []))} intentions"
    if node_name == "plan":
        plan = node_output.get("plan", {})
        return f"plan: {len(plan) if isinstance(plan, list) else 1} step(s)"
    if node_name == "reflect":
        reflection = node_output.get("reflection", "")
        return f"reflected: {str(reflection)[:80]}"
    if node_name == "commit":
        summary = node_output.get("commit_summary", "")
        return f"COMMIT: {summary[:100]}"
    if node_name == "error":
        return f"ERROR: {node_output.get('error', '?')}"
    if node_name == "surface_intentions":
        suggs = node_output.get("user_suggestions", [])
        if suggs:
            # show count + first full suggestion
            return f"{len(suggs)} suggestions: " + " | ".join(suggs)[:200]
        err = node_output.get("suggestions_error", "")
        if err:
            return f"no suggestions ({err[:80]})"
        return "0 suggestions"
    # Default: show first value
    if node_output:
        first_key = next(iter(node_output))
        first_val = node_output[first_key]
        return f"{first_key}={str(first_val)[:60]}"
    return "(no output)"


def _print_event(node_name: str, node_output: dict[str, Any]) -> None:
    color = {
        "recall": C.C,
        "observe": C.DIM,
        "reason": C.B,
        "plan": C.M,
        "reflect": C.Y,
        "commit": C.G,
        "error": C.R,
    }.get(node_name, C.DIM)
    summary = _summarize_event(node_name, node_output)
    print(f"{color}[{node_name}]{C.RESET}    {summary}", flush=True)


def _apply_proposal(proposal: Any) -> None:
    """Apply a Proposal's changes via the mesh review queue.

    Each change is enqueued as a TaskChange; the mesh propagator will
    dispatch to all forks. Until M148-write tools are wired in, this is
    a dry-run print (changes are shown but not queued).
    """
    try:
        from src.mesh.queue import enqueue
        from src.contracts.task_change import TaskChange, TaskAction
    except Exception as e:  # noqa: BLE001
        print(f"{C.Y}[commit] queue import failed: {e} — dry-run only{C.RESET}")
        return

    for i, change in enumerate(proposal.changes):
        try:
            action_str = change.get("action", "CREATE")
            # Normalize to lowercase for TaskAction enum
            action_str = action_str.lower() if isinstance(action_str, str) else "create"

            # Sanitize UEID — some test data has malformed ueids; if so, generate a fallback
            ueid = change.get("ueid", "")
            try:
                from src.contracts.common import UEID as _UEID
                _UEID(ueid)  # validates
            except Exception:
                import hashlib as _hl
                h = _hl.sha256(ueid.encode("utf-8")).hexdigest()
                ueid = f"tsk:triage:{h[:8]}:{h[8:16]}:{h[16:24]}"

            tc = TaskChange(
                event_id=__import__("uuid").uuid4().hex,
                ueid=ueid,
                action=TaskAction(action_str),
                fields=change.get("fields", {}),
                source_fork=f"td_chat:{proposal.skill}",
                timestamp=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
            )
            event_id = enqueue(tc)
            print(f"  {C.G}[ok] queued change #{i}: {tc.action.value} {tc.ueid} (event={event_id}){C.RESET}")
        except Exception as e:  # noqa: BLE001
            print(
                f"  {C.R}[fail] change #{i}: {type(e).__name__}: {e}{C.RESET}"
            )


def _print_proposal(result_state: dict[str, Any]) -> None:
    """Print a proposal block, if the agent emitted one."""
    proposal = result_state.get("commit_summary") or ""
    if not proposal:
        return
    print(f"\n{C.BOLD}{C.Y}PROPOSAL:{C.RESET} {proposal}")
    # Surface user-facing suggestions if any (M158e)
    suggestions = result_state.get("user_suggestions", [])
    if suggestions:
        print(f"\n{C.BOLD}{C.G}LLM Suggestions ({len(suggestions)}):{C.RESET}")
        for i, s in enumerate(suggestions, 1):
            print(f"  {C.C}{i}.{C.RESET} {s}")
    # Surface errors
    err = result_state.get("suggestions_error") or result_state.get("error")
    if err:
        print(f"\n{C.R}error: {err}{C.RESET}")
    changes = result_state.get("pending_changes", [])
    if changes:
        print(f"{C.DIM}  {len(changes)} pending change(s). Reply with:{C.RESET}")
        print(f"  {C.G}--approve{C.RESET}            apply all")
        print(f"  {C.R}--reject{C.RESET}             discard all")
        print(f"  {C.Y}--reject <idx>{C.RESET}        discard change #idx")
        print(f"  {C.C}--edit <idx> <field>=<val>{C.RESET}  edit before approve")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="ikigai-taskdog chat",
        description="REPL interface for the v2 deep agent graph.",
    )
    parser.add_argument(
        "--thread-id",
        default=None,
        help="Thread ID for the conversation (default: auto-generated).",
    )
    parser.add_argument(
        "--model",
        default="minimax-m3",
        help="Model name (cosmetic; the v2 graph uses env vars).",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable ANSI colors in output.",
    )
    args = parser.parse_args(argv)

    if args.no_color:
        # Disable all colors
        for attr in dir(C):
            if not attr.startswith("_"):
                setattr(C, attr, "")

    _ensure_ikigai_path()
    # Force FAKE_LLM off unless user already set it; let the v2 graph decide.
    os.environ.setdefault("IKIGAI_FAKE_LLM", "0")

    thread_id = args.thread_id or f"chat-{datetime.now().isoformat()}"
    config: dict[str, Any] = {"configurable": {"thread_id": thread_id}}

    # Lazy import so --help works without the v2 deps
    try:
        from agents.v2.graph import graph as v2_graph_factory  # type: ignore

        v2_graph = v2_graph_factory()
    except Exception as e:  # noqa: BLE001
        print(f"{C.R}error: cannot import v2 graph: {e}{C.RESET}", file=sys.stderr)
        return 2

    print(f"{C.BOLD}ikigai-chat{C.RESET}  thread_id={thread_id}  model={args.model}")
    try:
        from agents.v2.skills import list_skills as _list_skills

        skills_line = ", ".join(_list_skills())
    except Exception:  # noqa: BLE001
        skills_line = "taskdog-triage, vault-intent-extract"
    print(
        f"{C.DIM}  skills: {skills_line}, meta_plan{C.RESET}"
    )
    print(
        f"{C.DIM}  shortcuts: /triage (run taskdog-triage), "
        f"/extract (run vault-intent-extract){C.RESET}"
    )
    print(
        f"{C.DIM}  type your request, or /skill <name> <args>, or /quit to exit{C.RESET}"
    )

    prompt = f"\n{C.BOLD}{C.G}> {C.RESET}"
    approval_prompt = f"\n{C.BOLD}{C.G}> {C.RESET}"

    # Pending proposal awaiting --approve/--reject (set by /triage, /extract shortcuts)
    pending_proposal: Any = None

    while True:
        try:
            raw = input(prompt)
        except (EOFError, KeyboardInterrupt):
            print(f"\n{C.DIM}[ikigai-chat] thread closed{C.RESET}")
            return 0

        request = raw.strip()
        if not request:
            continue

        # Direct approval of pending proposal (set by /triage, /extract, etc)
        if pending_proposal is not None and request in ("--approve", "--reject"):
            if request == "--approve":
                print(f"{C.G}[commit] approved (changes would be queued via review_queue){C.RESET}")
                _apply_proposal(pending_proposal)
            else:
                print(f"{C.R}[commit] rejected (no changes applied){C.RESET}")
            pending_proposal = None
            continue

        if request in ("/quit", "/exit", ":q"):
            print(f"{C.DIM}[ikigai-chat] thread closed{C.RESET}")
            return 0
        if request == "/help":
            print("Commands:")
            print("  /skill <name>    invoke a named skill (e.g. /skill daily)")
            print("  /thread          show current thread_id")
            print("  /reset           start a new thread")
            print("  /quit            exit the REPL")
            continue
        if request == "/thread":
            print(f"thread_id = {thread_id}")
            continue
        if request == "/reset":
            thread_id = f"chat-{datetime.now().isoformat()}"
            config = {"configurable": {"thread_id": thread_id}}
            print(f"{C.DIM}new thread_id = {thread_id}{C.RESET}")
            continue

        # Optional skill prefix
        skill_name: str | None = None
        if request.startswith("/skill "):
            parts = request[len("/skill ") :].split(maxsplit=1)
            skill_name = parts[0]
            request = parts[1] if len(parts) > 1 else ""
        elif request == "/triage":
            # M161 shortcut: run taskdog-triage on current taskdog state
            try:
                from src.mesh.adapters.taskdog import TaskdogAdapter

                adapter = TaskdogAdapter()
                tasks = adapter.list_all()
                from agents.v2.skills.taskdog_triage import propose

                proposal = propose(tasks)
                pending_proposal = proposal
                print(
                    f"\n{C.BOLD}{C.Y}PROPOSAL from taskdog-triage:{C.RESET}"
                )
                print(proposal.to_json())
                print(
                    f"\n{C.DIM}{len(proposal.changes)} change(s) proposed. "
                    f"Reply with --approve to apply, --reject to discard.{C.RESET}"
                )
                continue
            except Exception as e:  # noqa: BLE001
                print(f"{C.R}error running triage: {e}{C.RESET}")
                continue
        elif request == "/extract":
            # M161 shortcut: run vault-intent-extract on today's note
            try:
                from datetime import date as _date

                from agents.v2.skills.vault_intent_extract import (
                    propose_from_file,
                )

                today_iso = _date.today().isoformat()
                note_paths = [
                    f"vault/daily/{today_iso}.md",
                    f"vault/{today_iso}.md",
                ]
                for p in note_paths:
                    if Path(p).exists():
                        proposal = propose_from_file(p)
                        pending_proposal = proposal
                        print(
                            f"\n{C.BOLD}{C.Y}PROPOSAL from vault-intent-extract:{C.RESET}"
                        )
                        print(proposal.to_json())
                        print(
                            f"\n{C.DIM}{len(proposal.changes)} change(s) proposed. "
                            f"Reply with --approve to apply, --reject to discard.{C.RESET}"
                        )
                        break
                else:
                    print(
                        f"{C.DIM}no vault note for today ({today_iso}). "
                        f"Create vault/daily/{today_iso}.md to enable extraction.{C.RESET}"
                    )
                continue
            except Exception as e:  # noqa: BLE001
                print(f"{C.R}error running extract: {e}{C.RESET}")
                continue

        # Invoke v2 graph with streaming
        try:
            payload: dict[str, Any] = {"raw_query": request}
            if skill_name:
                payload["skill"] = skill_name
            # graph.stream yields dict per node
            for event in v2_graph.stream(payload, config=config):
                if not isinstance(event, dict):
                    continue
                for node_name, node_output in event.items():
                    if isinstance(node_output, dict):
                        _print_event(node_name, node_output)
                    else:
                        print(f"{C.DIM}[{node_name}]{C.RESET}    (non-dict output)")

            # After streaming, get final state for proposal display
            final_state = v2_graph.get_state(config)
            values = getattr(final_state, "values", {}) or {}
            _print_proposal(values)

        except Exception as e:  # noqa: BLE001
            print(f"{C.R}error: {type(e).__name__}: {e}{C.RESET}")
            continue

        # Approval prompt
        try:
            approval = input(approval_prompt).strip()
        except (EOFError, KeyboardInterrupt):
            print(f"\n{C.DIM}[ikigai-chat] thread closed{C.RESET}")
            return 0

        if not approval:
            continue
        if approval == "--approve":
            print(f"{C.G}[commit] approved (changes would be queued){C.RESET}")
        elif approval == "--reject":
            print(f"{C.R}[commit] rejected (no changes applied){C.RESET}")
        elif approval.startswith("--reject "):
            print(f"{C.R}[commit] partial reject: {approval}{C.RESET}")
        elif approval.startswith("--edit "):
            print(f"{C.C}[commit] edit: {approval}{C.RESET}")
        else:
            print(
                f"{C.DIM}(unrecognized approval command, treating as new request){C.RESET}"
            )


if __name__ == "__main__":
    raise SystemExit(main())

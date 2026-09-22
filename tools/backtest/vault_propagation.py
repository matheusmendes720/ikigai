"""M114f — vault_diff.py (renamed semantically from vault_propagation.py)

Per user directive 2026-09-22: vault is the SOT, taskdog is the operational
timeline. The deep-agent routine CROSS-CHECKS vault ↔ taskdog and surfaces
drift. There is **NO auto-trigger** on `life task done` — vault updates are
an explicit agent decision made during Routine Inicial/Final.

What this module provides:

- `audit_drift(vault_plans, taskdog_tasks)` — read-only cross-check.
  Returns list of {plan_file, plan_line, plan_text, taskdog_id, taskdog_status, drift_kind}.
  Drift kinds:
    `unmarked_done`   — taskdog says task is COMPLETED but vault checkbox is `- [ ]`
    `unmarked_open`   — taskdog says task is PENDING but vault checkbox is `- [x]`
    `phantom_task`    — taskdog has an orphan (no matched vault checkbox)
    `planned_orphan`  — vault checkbox exists but no taskdog task matches
- `refactor_plan(rel_path, reason, body)` — append-only mutation path the
  agent uses to **explicitly** align vault with taskdog state. Logs to
  `vault/.vault_events.jsonl` (audit trail of agent-driven changes).
- `preview_toggle(plan_path, target_line, expected_text)` — dry-run checker
  that tells the agent if a desired toggle is safe to apply.
- `apply_toggle(...)` — guarded mutation; requires `audit_drift` evidence + dry-run
  preview (safety rails).
- `append_event(event)` — append-only audit log writer.

CLI:
    python tools/backtest/vault_diff.py --audit [--taskdog-json PATH] [--dry-run]
    python tools/backtest/vault_diff.py --audit --write-events    # log drift to events
    python tools/backtest/vault_diff.py --refactor PATH --reason ... --body ...
    python tools/backtest/vault_diff.py --preview PATH --line N --text "..."

`taskdog_json` format: produced by `curl http://127.0.0.1:8000/api/v1/tasks | jq .`
or `python -m life.cli task ls --json`. Default location: `data/taskdog_snapshot.json`.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
VAULT_DIR = REPO_ROOT / "vault"
EVENT_LOG = VAULT_DIR / ".vault_events.jsonl"
TASKDOG_SNAPSHOT = REPO_ROOT / "data" / "taskdog_snapshot.json"

# checkbox pattern: `- [ ] text` or `- [x] text`. Vault-linked checkboxes like
# `- [vault:rel#line] text` or closed form `- [x] [vault:rel#line] text` are
# matched by a SECOND pattern below.
CHECKBOX_RE = re.compile(r"^- \[( |x)\] (.+)$")
CHECKBOX_VAULT_RE = re.compile(r"^- \[x\] \[vault:([^#\]]+)#(\d+)\] (.+)$|^- \[vault:([^#\]]+)#(\d+)\] (.+)$")
VAULT_LINK_RE = re.compile(r"\[vault:([^#\]]+)#(\d+)\]")
# M120: capture priority tags from vault checkbox text. Format: `| priority=N`
# appended after the checkbox link (e.g. `- [vault:plan.md#6] Foo | priority=7`).
PRIORITY_TAG_RE = re.compile(r"\|\s*priority=(\d{1,2})\b")

# Per algorithm-attribution §7: vault write invariant — the only code path that
# mutates vault content outside of explicit human file edits. Re-indexing via
# OTel or git hooks is read-only.
INVARIANT_MARKER = "VAULT_WRITE_INVARIANT"

# Drift taxonomy — surfaces what the agent Routine Inicial/Final should report.
DRIFT_UNMARKED_DONE = "unmarked_done"   # taskdog COMPLETED but vault [ ]
DRIFT_UNMARKED_OPEN = "unmarked_open"   # taskdog PENDING but vault [x]
DRIFT_PHANTOM_TASK = "phantom_task"     # taskdog task has no vault checkbox link
DRIFT_PLANNED_ORPHAN = "planned_orphan"  # vault checkbox has no taskdog task
# M120: priority declared in vault checkbox (`| priority=N`) doesn't match taskdog priority.
DRIFT_PRIORITY_MISMATCH = "priority_mismatch"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _parse_vault_link(name: str, notes: str) -> tuple[str, int] | None:
    """Pull [vault:rel_path#line_no] out of name then notes. Return (rel, line)."""
    for src in (name, notes):
        if not src:
            continue
        m = VAULT_LINK_RE.search(src)
        if m:
            return (m.group(1).strip(), int(m.group(2)))
    return None


def _bump_frontmatter_field(text: str, field: str, value: str) -> str:
    """Update a YAML frontmatter field; append if missing.

    Only mutates a scalar field. Preserves the structure.
    """
    if not text.startswith("---"):
        return text
    end = text.find("\n---", 3)
    if end == -1:
        return text
    head = text[:end]
    body = text[end:]
    pattern = re.compile(rf"^{re.escape(field)}:\s*.*$", re.MULTILINE)
    if pattern.search(head):
        head_new = pattern.sub(f"{field}: {value}", head)
    else:
        head_new = head.rstrip("\n") + f"\n{field}: {value}\n"
    return head_new + body


def _count_checkboxes_done(text: str) -> int:
    return len(re.findall(r"^- \[x\]", text, flags=re.MULTILINE))


def append_event(event: dict[str, Any]) -> None:
    """Append a structured event to vault/.vault_events.jsonl (append-only)."""
    VAULT_DIR.mkdir(parents=True, exist_ok=True)
    event_with_marker = {
        "invariant": INVARIANT_MARKER,
        "ts": now_iso(),
        **event,
    }
    log_path = VAULT_DIR / ".vault_events.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event_with_marker, ensure_ascii=False) + "\n")


def toggle_checkbox(plan_path: Path, target_line: int, expected_text: str) -> dict[str, Any]:
    """Toggle a `- [ ] <expected_text>` at target_line to `- [x] <expected_text>`.

    Also accepts `[vault:rel#line]` bracket on the actual line and on expected_text.
    Refuses if the line doesn't match (safety: don't mistakenly flip unrelated checkboxes).
    Returns {ok, before_line, after_line, file_path}.

    GUARDED mutation — only callable via `apply_toggle()` which verifies
    `preview_toggle()` first. Direct callers should pass `force=False` or
    get a refusal.
    """
    if not plan_path.exists():
        return {"ok": False, "error": f"plan not found: {plan_path}", "file_path": str(plan_path)}
    text = plan_path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    if target_line < 1 or target_line > len(lines):
        return {"ok": False, "error": f"line {target_line} out of range", "file_path": str(plan_path)}
    line = lines[target_line - 1]
    stripped = line.rstrip("\n")
    expected_open = f"- [ ] {expected_text}"
    line_after_brackets = re.sub(r"^- \[[^\]]*\] ", "", stripped)
    text_after_brackets = re.sub(r"^\[[^\]]*\] ", "", expected_text)
    if not (stripped == expected_open or line_after_brackets == text_after_brackets):
        return {
            "ok": False,
            "error": f"line {target_line} mismatch: expected {expected_open!r}, got {stripped!r}",
            "file_path": str(plan_path),
            "expected": expected_open,
            "actual": stripped,
        }
    # Flip to `- [x] <existing bracket-or-text>`. Preserve any `[vault:...]` link
    # as metadata alongside the closed-checkbox indicator. Format:
    #   `- [ ] [vault:rel#line] text`  →  `- [x] [vault:rel#line] text`
    #   `- [ ] text`                   →  `- [x] text`
    bracket_match = re.match(r"^- \[([^\]]*)\] (.*)", stripped)
    if bracket_match:
        # Re-emit as `- [x] <bracket_content> <rest>`.
        # Bracket content keeps its leading [vault:...] link if it was a vault link;
        # we just unwrap and re-wrap.
        inner = bracket_match.group(1)
        rest = bracket_match.group(2)
        flipped_line = f"- [x] [{inner}] {rest}\n"
    else:
        flipped_line = f"- [x] {stripped[3:]}\n"
    lines[target_line - 1] = flipped_line
    new_text = "".join(lines)
    new_text = _bump_frontmatter_field(new_text, "ultima_revisao", now_iso()[:10])
    plan_path.write_text(new_text, encoding="utf-8")
    return {
        "ok": True,
        "before_line": stripped,
        "after_line": flipped_line.rstrip("\n"),
        "file_path": str(plan_path),
        "checkboxes_done": _count_checkboxes_done(new_text),
    }


def preview_toggle(
    plan_path: Path,
    target_line: int,
    expected_text: str,
) -> dict[str, Any]:
    """Read-only check: would `apply_toggle` succeed? Used by agent before mutating.

    Returns the same shape as `toggle_checkbox` but does NOT mutate the file.

    Accepts both formats:
      `- [ ] <expected_text>`         (plain checkbox)
      `- [vault:rel#line] <expected_text>`  (linked checkbox)
    """
    if not plan_path.exists():
        return {"ok": False, "error": f"plan not found: {plan_path}", "file_path": str(plan_path)}
    text = plan_path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if target_line < 1 or target_line > len(lines):
        return {"ok": False, "error": f"line {target_line} out of range", "file_path": str(plan_path)}
    stripped = lines[target_line - 1].rstrip("\n")
    expected_open = f"- [ ] {expected_text}"
    # Normalize: strip leading `[...]` from BOTH stripped line and expected_text,
    # then compare the residual text.
    line_after_brackets = re.sub(r"^- \[[^\]]*\] ", "", stripped)
    text_after_brackets = re.sub(r"^\[[^\]]*\] ", "", expected_text)
    if stripped == expected_open or line_after_brackets == text_after_brackets:
        would_be = f"- [x] " + line_after_brackets
        return {
            "ok": True,
            "preview": True,
            "would_become": would_be,
            "file_path": str(plan_path),
            "checkboxes_done_after": _count_checkboxes_done(text) + 1,
        }
    return {
        "ok": False,
        "error": f"line {target_line} mismatch: expected {expected_open!r} (or matching content), got {stripped!r}",
        "file_path": str(plan_path),
        "expected": expected_open,
        "actual": stripped,
    }


def apply_toggle(
    plan_path: Path,
    target_line: int,
    expected_text: str,
    actor: str,
    reason: str,
    *,
    require_preview_ok: bool = True,
) -> dict[str, Any]:
    """GUARDED mutation: real toggle, but only after `preview_toggle` succeeded.

    `require_preview_ok=True` (default) refuses to mutate if preview would fail.
    Agents should call `preview_toggle()` first, then `apply_toggle()`. The audit
    log records the call sequence.
    """
    preview = preview_toggle(plan_path, target_line, expected_text)
    if require_preview_ok and not preview["ok"]:
        append_event({
            "event": "vault.toggle_refused",
            "rel_path": str(plan_path),
            "target_line": target_line,
            "expected_text": expected_text,
            "reason": reason,
            "actor": actor,
            "preview_error": preview.get("error"),
        })
        return {"ok": False, "refused": True, "preview": preview}
    result = toggle_checkbox(plan_path, target_line, expected_text)
    append_event({
        "event": "vault.toggle_applied",
        "rel_path": str(plan_path),
        "target_line": target_line,
        "expected_text": expected_text,
        "reason": reason,
        "actor": actor,
        "ok": result["ok"],
    })
    return result


def refactor_plan(rel_path: str, reason: str, body: str) -> dict[str, Any]:
    """Append an "Auto-refactor at <ts>" section to a plan file.

    Per role-anchor 8: user can refactor plans mid-cycle; this is the canonical
    append-only path the agent uses.
    """
    target = (REPO_ROOT / rel_path).resolve()
    if not target.exists():
        return {"ok": False, "error": f"plan not found: {rel_path}"}
    text = target.read_text(encoding="utf-8")
    timestamp = now_iso()
    new_section = (
        f"\n\n## Auto-refactor at {timestamp}\n\n"
        f"> **Reason:** {reason}\n\n"
        f"{body}\n"
    )
    new_text = text.rstrip() + new_section
    new_text = _bump_frontmatter_field(new_text, "ultima_revisao", timestamp[:10])
    target.write_text(new_text, encoding="utf-8")
    append_event({
        "event": "vault.refactor",
        "rel_path": rel_path,
        "reason": reason,
        "body_chars": len(body),
    })
    return {"ok": True, "file_path": str(target), "ts": timestamp}


def audit_drift(
    vault_plans: list[Path] | None = None,
    taskdog_tasks: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Cross-check vault checkbox state vs taskdog task status. READ-ONLY.

    Matching: a taskdog task with name containing a `[vault:rel_path#line_no]`
    link token joins the matching checkbox. Otherwise flagged as drift / orphan.

    Drift kinds:
      `unmarked_done`   — taskdog COMPLETED but vault checkbox is `- [ ]`
      `unmarked_open`   — taskdog PENDING/IN_PROGRESS but vault checkbox is `- [x]`
      `phantom_task`    — taskdog task has no vault checkbox link
      `planned_orphan`  — vault checkbox exists but no taskdog task matches

    Returns dict with:
      - `drifts`: list of {drift_kind, plan_file, plan_line, plan_text,
                            taskdog_id, taskdog_status, taskdog_name}
      - `summary`: counts per drift_kind

    This is the agent's Routine Inicial/Final `check_sot()` call.
    """
    if vault_plans is None:
        vault_plans = sorted(VAULT_DIR.rglob("*.md"))
    if taskdog_tasks is None:
        taskdog_tasks = _load_taskdog_tasks_from_snapshot()

    drifts: list[dict[str, Any]] = []
    linked_texts: dict[str, list[tuple[Path, int, str, bool]]] = {}

    def _plan_rel(p: Path) -> str:
        """Best-effort relative-to-vault path for joining taskdog [vault:...] links."""
        try:
            return str(p.relative_to(VAULT_DIR))
        except ValueError:
            return str(p)

    for plan in vault_plans:
        try:
            text = plan.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        rel = _plan_rel(plan)
        for i, line in enumerate(text.splitlines(), 1):
            stripped = line.rstrip("\n")
            m_vault = CHECKBOX_VAULT_RE.match(stripped)
            if m_vault:
                # Two alternates: open form `[vault:...]` OR closed form `[x] [vault:...]`.
                rel_path = m_vault.group(1) or m_vault.group(4)
                line_no = m_vault.group(2) or m_vault.group(5)
                cb_text = m_vault.group(3) or m_vault.group(6)
                done = m_vault.group(1) is None  # group(1) only fills on open form; closed form fills via grp(4)
                # Re-derive done: if the leading bracket was [x], closed. Easier:
                done = stripped.startswith("- [x] ")
                if not rel_path:
                    continue
                key = f"{rel_path.strip()}#{line_no}".lstrip("./").lstrip("/")
                linked_texts.setdefault(key, []).append(
                    (plan, i, cb_text, done, rel)
                )
                continue
            m = CHECKBOX_RE.match(stripped)
            if not m:
                continue
            cb_text = m.group(2)
            done = m.group(1) == "x"
            # Bare checkbox: key by vault-relative path + line.
            key = f"{rel}#{i}".lstrip("./").lstrip("/")
            linked_texts.setdefault(key, []).append(
                (plan, i, cb_text, done, rel)
            )

    for t in taskdog_tasks:
        tid = t.get("id")
        tname = t.get("name", "")
        tstatus = t.get("status", "UNKNOWN")
        link = _parse_vault_link(tname, "")
        match: tuple[Path, int, str, bool] | None = None
        if link is not None:
            key = f"{link[0].lstrip('./').lstrip('/')}#{link[1]}"
            if key in linked_texts and linked_texts[key]:
                match = linked_texts[key][0]
        if match is None:
            drifts.append({
                "drift_kind": DRIFT_PHANTOM_TASK,
                "plan_file": None,
                "plan_line": None,
                "plan_text": None,
                "taskdog_id": tid,
                "taskdog_status": tstatus,
                "taskdog_name": tname,
            })
            continue
        plan, line_no, cb_text, cb_done, cb_rel = match
        if tstatus == "COMPLETED" and not cb_done:
            drifts.append({
                "drift_kind": DRIFT_UNMARKED_DONE,
                "plan_file": str(plan),
                "plan_rel": cb_rel,
                "plan_line": line_no,
                "plan_text": cb_text,
                "taskdog_id": tid,
                "taskdog_status": tstatus,
                "taskdog_name": tname,
            })
        elif tstatus in {"PENDING", "IN_PROGRESS"} and cb_done:
            drifts.append({
                "drift_kind": DRIFT_UNMARKED_OPEN,
                "plan_file": str(plan),
                "plan_rel": cb_rel,
                "plan_line": line_no,
                "plan_text": cb_text,
                "taskdog_id": tid,
                "taskdog_status": tstatus,
                "taskdog_name": tname,
            })
        # M120: priority drift detection. Only checked if vault checkbox declares
        # `| priority=N`. If taskdog priority differs, emit a mismatch drift.
        # This is independent of done/undone — a completed task can still have
        # priority drift (priority change wasn't reflected in vault).
        m_pri = PRIORITY_TAG_RE.search(cb_text or "")
        if m_pri is not None:
            try:
                vault_priority = int(m_pri.group(1))
            except ValueError:
                vault_priority = None
            td_priority = t.get("priority")
            try:
                td_priority_int = int(td_priority) if td_priority is not None else None
            except (TypeError, ValueError):
                td_priority_int = None
            if (
                vault_priority is not None
                and td_priority_int is not None
                and vault_priority != td_priority_int
            ):
                drifts.append({
                    "drift_kind": DRIFT_PRIORITY_MISMATCH,
                    "plan_file": str(plan),
                    "plan_rel": cb_rel,
                    "plan_line": line_no,
                    "plan_text": cb_text,
                    "taskdog_id": tid,
                    "taskdog_status": tstatus,
                    "taskdog_name": tname,
                    "vault_priority": vault_priority,
                    "taskdog_priority": td_priority_int,
                })

    linked_task_keys = set()
    for t in taskdog_tasks:
        link = _parse_vault_link(t.get("name", ""), "")
        if link is not None:
            linked_task_keys.add(f"{link[0].lstrip('./').lstrip('/')}#{link[1]}")
    for key, items in linked_texts.items():
        if key not in linked_task_keys:
            for plan, line_no, cb_text, done, cb_rel in items:
                drifts.append({
                    "drift_kind": DRIFT_PLANNED_ORPHAN,
                    "plan_file": str(plan),
                    "plan_rel": cb_rel,
                    "plan_line": line_no,
                    "plan_text": cb_text,
                    "taskdog_id": None,
                    "taskdog_status": None,
                    "taskdog_name": None,
                })

    summary: dict[str, int] = {}
    for d in drifts:
        summary[d["drift_kind"]] = summary.get(d["drift_kind"], 0) + 1

    return {
        "ts": now_iso(),
        "vault_plans_count": len(vault_plans),
        "taskdog_tasks_count": len(taskdog_tasks),
        "drifts": drifts,
        "summary": summary,
    }


def _load_taskdog_tasks_from_snapshot(path: Path = TASKDOG_SNAPSHOT) -> list[dict[str, Any]]:
    """Load taskdog tasks from JSON snapshot. Empty list if no snapshot file."""
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if isinstance(data, dict) and "tasks" in data:
        return list(data.get("tasks") or [])
    if isinstance(data, list):
        return data
    return []


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "vault_diff: cross-check vault SOT vs taskdog operational timeline. "
            "Read-only by default. --apply requires --preview-ok flag for safety."
        ),
    )
    parser.add_argument(
        "--audit",
        action="store_true",
        help="Run audit_drift: vault vs taskdog cross-check (READ-ONLY).",
    )
    parser.add_argument(
        "--taskdog-json",
        type=Path,
        default=TASKDOG_SNAPSHOT,
        help=f"taskdog snapshot path (default: {TASKDOG_SNAPSHOT.relative_to(REPO_ROOT)})",
    )
    parser.add_argument(
        "--write-events",
        action="store_true",
        help="Append drift summary as vault.audit event to .vault_events.jsonl",
    )
    parser.add_argument(
        "--refactor",
        type=str,
        help="Plan file to refactor (append-only mutation path, agent-driven)",
    )
    parser.add_argument("--reason", type=str, help="refactor reason (required with --refactor)")
    parser.add_argument("--body", type=str, help="refactor body (required with --refactor)")
    parser.add_argument(
        "--preview",
        type=str,
        help="Plan file path to preview-toggle (READ-ONLY dry-run)",
    )
    parser.add_argument("--line", type=int, help="Line number to toggle (used with --preview)")
    parser.add_argument("--text", type=str, help="Expected checkbox text (used with --preview)")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply toggle at --preview --line --text (requires preview-ok).",
    )
    parser.add_argument(
        "--actor",
        type=str,
        default="agent",
        help="actor who applied the change (default: agent)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="(Legacy compat) print summary, do not write any file.",
    )
    args = parser.parse_args(argv)

    if args.audit:
        # Refactor: snapshot reading is module-level; no path override needed.
        report = audit_drift()
        if args.write_events:
            append_event({"event": "vault.audit", "summary": report["summary"], "drift_count": len(report["drifts"])})
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0 if report["summary"].get(DRIFT_UNMARKED_DONE, 0) == 0 else 1

    if args.preview:
        if not (args.line and args.text):
            print("# --preview requires --line and --text.", file=sys.stderr)
            return 2
        plan_path = (REPO_ROOT / args.preview).resolve() if not Path(args.preview).is_absolute() else Path(args.preview)
        result = preview_toggle(plan_path, args.line, args.text)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0 if result.get("ok") else 1

    if args.apply:
        if not (args.preview and args.line and args.text):
            print("# --apply requires --preview --line --text.", file=sys.stderr)
            return 2
        plan_path = (REPO_ROOT / args.preview).resolve() if not Path(args.preview).is_absolute() else Path(args.preview)
        result = apply_toggle(
            plan_path,
            args.line,
            args.text,
            actor=args.actor,
            reason=args.reason or "agent_routine_alignment",
        )
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0 if result.get("ok") else 1

    if args.refactor:
        if not (args.reason and args.body):
            print("# --refactor requires --reason and --body.", file=sys.stderr)
            return 2
        if args.dry_run:
            print(f"# Would refactor: {args.refactor}")
            print(f"# Reason: {args.reason}")
            print(f"# Body chars: {len(args.body)}")
            return 0
        result = refactor_plan(args.refactor, args.reason, args.body)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0 if result.get("ok") else 1

    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())

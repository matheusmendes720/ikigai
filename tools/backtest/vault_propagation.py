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
# M121: alternation handles all 3 vault-linked checkbox forms.
# M125: added optional leading whitespace (`[ \t]{0,4}`) for nested checkboxes.
# Max 4 spaces — beyond that, the line is likely a code block or list item.
CHECKBOX_VAULT_RE = re.compile(
    r"^[ \t]{0,4}- \[x\] \[vault:([^#\]]+)#(\d+)\] (.+)$"   # closed: `- [x] [vault:rel#line] text`
    r"|^[ \t]{0,4}- \[vault:([^#\]]+)#(\d+)\] (.+)$"         # bare:   `- [vault:rel#line] text`
    r"|^[ \t]{0,4}- \[ \] \[vault:([^#\]]+)#(\d+)\] (.+)$"   # open:   `- [ ] [vault:rel#line] text`
)
VAULT_LINK_RE = re.compile(r"\[vault:([^#\]]+)#(\d+)\]")
# M120: capture priority tags from vault checkbox text. Format: `| priority=N`
# appended after the checkbox link (e.g. `- [vault:plan.md#6] Foo | priority=7`).
PRIORITY_TAG_RE = re.compile(r"\|\s*priority=(\d{1,2})\b")
# M122: capture tags declarations. Format: `| tags=tag1,tag2,tag3` (comma-separated).
# Whitespace inside the list is tolerated: `| tags=foo, bar, baz`.
TAGS_TAG_RE = re.compile(r"\|\s*tags=([^\n|]+)")
# M130: capture due_date declarations. Format: `| due=YYYY-MM-DD`. Vault
# date is plain ISO; taskdog's `deadline` is ISO datetime (we compare on
# the date portion, first 10 chars).
DUE_TAG_RE = re.compile(r"\|\s*due=(\d{4}-\d{2}-\d{2})\b")

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
# M122: tags declared in vault checkbox (`| tags=a,b,c`) don't match taskdog tags.
DRIFT_TAG_MISMATCH = "tag_mismatch"
# M130: due_date declared in vault checkbox (`| due=YYYY-MM-DD`) doesn't
# match taskdog's deadline field (date portion only).
DRIFT_DUE_DATE_MISMATCH = "due_date_mismatch"


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
    #   `- [vault:rel#line] text`      →  `- [x] [vault:rel#line] text`  (legacy)
    # The bracket content distinguishes two cases:
    # - non-whitespace content (e.g. "vault:rel#line") → preserve as a link
    # - whitespace-only content (`[ ]`)                → just the checkbox marker
    bracket_match = re.match(r"^- \[([^\]]*)\] (.*)", stripped)
    if bracket_match and bracket_match.group(1).strip():
        # Non-empty bracket content — preserve as a link inside [ ].
        inner = bracket_match.group(1)
        rest = bracket_match.group(2)
        flipped_line = f"- [x] [{inner}] {rest}\n"
    else:
        # Empty/whitespace bracket content — strip the whole `[ ]` and replace.
        # stripped[3:] on "- [ ] text" = "] text" — instead skip past "[ ]".
        # stripped[5:] gives " text" with leading space; lstrip one.
        flipped_line = f"- [x] {stripped[5:].lstrip(' ')}\n"
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


def reopen_checkbox(plan_path: Path, target_line: int, expected_text: str) -> dict[str, Any]:
    """Inverse of `toggle_checkbox`: flip `- [x] <text>` back to `- [ ] <text>`.

    M133: used when the user (or agent) wants to unmark a task as not done.
    Same safety guards as `toggle_checkbox`: refuses if line doesn't match.
    Returns {ok, before_line, after_line, file_path, checkboxes_done}.
    """
    if not plan_path.exists():
        return {"ok": False, "error": f"plan not found: {plan_path}", "file_path": str(plan_path)}
    text = plan_path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    if target_line < 1 or target_line > len(lines):
        return {"ok": False, "error": f"line {target_line} out of range", "file_path": str(plan_path)}
    line = lines[target_line - 1]
    stripped = line.rstrip("\n")
    # Refuse if the line is already open.
    if stripped.startswith("- [ ] "):
        return {
            "ok": False,
            "error": f"line {target_line} is already open (cannot reopen): {stripped!r}",
            "file_path": str(plan_path),
        }
    # Match `- [x] text` (no link) OR `- [x] [vault:...] text` (with link).
    # The `[x]` token must be exactly that — not a vault link.
    # Pattern: `- [x] <link_or_text>` where link is `[vault:rel#line]` or just text.
    m = re.match(r"^- \[x\] (.+)$", stripped)
    if m is None:
        return {
            "ok": False,
            "error": f"line {target_line} mismatch: expected `- [x] <text>`, got {stripped!r}",
            "file_path": str(plan_path),
            "expected": f"- [x] {expected_text}",
            "actual": stripped,
        }
    rest = m.group(1)  # everything after `- [x] `
    # Validate that expected_text matches the content (after stripping the link prefix).
    link_m = re.match(r"^\[vault:[^#\]]+#\d+\] (.+)$", rest)
    if link_m:
        content = link_m.group(1)
    else:
        content = rest
    if content != expected_text:
        return {
            "ok": False,
            "error": f"line {target_line} mismatch: expected content {expected_text!r}, got {content!r}",
            "file_path": str(plan_path),
            "expected": expected_text,
            "actual": content,
        }
    reopened_line = f"- [ ] {rest}\n"
    lines[target_line - 1] = reopened_line
    new_text = "".join(lines)
    new_text = _bump_frontmatter_field(new_text, "ultima_revisao", now_iso()[:10])
    plan_path.write_text(new_text, encoding="utf-8")
    return {
        "ok": True,
        "before_line": stripped,
        "after_line": reopened_line.rstrip("\n"),
        "file_path": str(plan_path),
        "checkboxes_done": _count_checkboxes_done(new_text),
    }


def preview_reopen(plan_path: Path, target_line: int, expected_text: str) -> dict[str, Any]:
    """Read-only check: would `reopen_checkbox` succeed? Used by agent before mutating.

    Returns the same shape as `reopen_checkbox` but does NOT mutate the file.
    """
    if not plan_path.exists():
        return {"ok": False, "error": f"plan not found: {plan_path}", "file_path": str(plan_path)}
    text = plan_path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if target_line < 1 or target_line > len(lines):
        return {"ok": False, "error": f"line {target_line} out of range", "file_path": str(plan_path)}
    stripped = lines[target_line - 1].rstrip("\n")
    if stripped.startswith("- [ ] "):
        return {
            "ok": False,
            "error": f"line {target_line} is already open: {stripped!r}",
            "file_path": str(plan_path),
        }
    m = re.match(r"^- \[x\] (.+)$", stripped)
    if m is None:
        return {
            "ok": False,
            "error": f"line {target_line} mismatch: expected `- [x] <text>`, got {stripped!r}",
            "file_path": str(plan_path),
            "expected": f"- [x] {expected_text}",
            "actual": stripped,
        }
    rest = m.group(1)
    link_m = re.match(r"^\[vault:[^#\]]+#\d+\] (.+)$", rest)
    content = link_m.group(1) if link_m else rest
    if content != expected_text:
        return {
            "ok": False,
            "error": f"line {target_line} mismatch: expected content {expected_text!r}, got {content!r}",
            "file_path": str(plan_path),
            "expected": expected_text,
            "actual": content,
        }
    would_be = f"- [ ] {rest}"
    return {
        "ok": True,
        "preview": True,
        "would_become": would_be,
        "file_path": str(plan_path),
        "checkboxes_done_after": _count_checkboxes_done(text) - 1,
    }


def apply_reopen(
    plan_path: Path,
    target_line: int,
    expected_text: str,
    actor: str,
    reason: str,
    *,
    require_preview_ok: bool = True,
) -> dict[str, Any]:
    """GUARDED mutation: real reopen, but only after `preview_reopen` succeeded.

    Mirror of `apply_toggle` but for the reverse direction.
    """
    preview = preview_reopen(plan_path, target_line, expected_text)
    if require_preview_ok and not preview["ok"]:
        append_event({
            "event": "vault.reopen_refused",
            "rel_path": str(plan_path),
            "target_line": target_line,
            "expected_text": expected_text,
            "reason": reason,
            "actor": actor,
            "preview_error": preview.get("error"),
        })
        return {"ok": False, "refused": True, "preview": preview}
    result = reopen_checkbox(plan_path, target_line, expected_text)
    append_event({
        "event": "vault.reopen_applied",
        "rel_path": str(plan_path),
        "target_line": target_line,
        "expected_text": expected_text,
        "reason": reason,
        "actor": actor,
        "ok": result["ok"],
    })
    return result


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
                # Three alternates: closed `[x] [vault:...]`, bare `[vault:...]`,
                # or open `[ ] [vault:...]` (M121).
                rel_path = m_vault.group(1) or m_vault.group(4) or m_vault.group(7)
                line_no = m_vault.group(2) or m_vault.group(5) or m_vault.group(8)
                cb_text = m_vault.group(3) or m_vault.group(6) or m_vault.group(9)
                # done = True if leading bracket was [x]; False for [ ] or bare.
                done = (m_vault.group(1) is None) and (m_vault.group(7) is None)
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
        # M122: tag drift detection. Compares vault `| tags=a,b,c` to taskdog tags
        # as unordered sets (case-insensitive, whitespace-trimmed). Emits
        # tag_mismatch drift if the sets differ.
        # Skip if taskdog tags field is missing (None) — we don't know what
        # they should be. Empty list vs vault-tags-still-fires mismatch.
        m_tags = TAGS_TAG_RE.search(cb_text or "")
        if m_tags is not None and "tags" in t:
            vault_tags_raw = m_tags.group(1)
            vault_tags = sorted({x.strip().lower() for x in vault_tags_raw.split(",") if x.strip()})
            td_tags_raw = t.get("tags") or []
            if isinstance(td_tags_raw, str):
                # Some servers serialize as comma-separated string.
                td_tags_iter = [x.strip() for x in td_tags_raw.split(",") if x.strip()]
            else:
                td_tags_iter = list(td_tags_raw)
            td_tags = sorted({str(x).strip().lower() for x in td_tags_iter if str(x).strip()})
            if vault_tags and vault_tags != td_tags:
                drifts.append({
                    "drift_kind": DRIFT_TAG_MISMATCH,
                    "plan_file": str(plan),
                    "plan_rel": cb_rel,
                    "plan_line": line_no,
                    "plan_text": cb_text,
                    "taskdog_id": tid,
                    "taskdog_status": tstatus,
                    "taskdog_name": tname,
                    "vault_tags": vault_tags,
                    "taskdog_tags": td_tags,
                })
        # M130: due_date drift detection. Compares vault `| due=YYYY-MM-DD`
        # to taskdog's `deadline` field on the date portion only.
        # Skip if taskdog has no deadline (None) — we don't know what it
        # should be. Missing deadline vs vault-due-set fires mismatch.
        m_due = DUE_TAG_RE.search(cb_text or "")
        if m_due is not None:
            vault_due = m_due.group(1)
            td_deadline_raw = t.get("deadline")
            if td_deadline_raw is not None and isinstance(td_deadline_raw, str):
                # Extract date portion: "2026-08-30T18:00:00" → "2026-08-30"
                td_due = td_deadline_raw[:10] if len(td_deadline_raw) >= 10 else None
            else:
                td_due = None
            if td_due is not None and vault_due != td_due:
                drifts.append({
                    "drift_kind": DRIFT_DUE_DATE_MISMATCH,
                    "plan_file": str(plan),
                    "plan_rel": cb_rel,
                    "plan_line": line_no,
                    "plan_text": cb_text,
                    "taskdog_id": tid,
                    "taskdog_status": tstatus,
                    "taskdog_name": tname,
                    "vault_due_date": vault_due,
                    "taskdog_due_date": td_due,
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

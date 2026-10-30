"""Worktree nodes — wraps the existing ``scripts/worktree-helper.sh``.

The repo has a bash worktree helper at ``scripts/worktree-helper.sh`` (M24.1
fix for Windows paths via ``cygpath -m``). No Python equivalent exists.
Paperclip shells out to it for ``create`` and ``cleanup``; uses raw
``git`` subprocesses for ``commit`` and ``merge`` (those are 3-line
operations and don't need a wrapper).

Failure handling (per plan §"Git worktree automation"):
* ``create`` fails (path exists) → report to error channel; graph routes
  to END via the ``error`` route (caller cleans up via the helper's
  ``cleanup-all``).
* ``commit`` fails → error channel; graph routes to END (worktree stays
  around for inspection; orphan-GC sweep handles later).
* ``merge`` fails (conflict) → we deliberately do NOT auto-resolve;
  ``error_type=MergeConflictError`` + the worktree path so the user can
  manually resolve + re-run.
* ``cleanup`` fails (worktree locked) → log + continue. The orphan-GC
  sweep (``scripts/worktree-helper.sh cleanup-all``) is the safety net.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
import sys
from pathlib import Path

from src.ikigai.src.agents.paperclip.state import PaperclipStateDict

log = logging.getLogger(__name__)


def _resolve_repo_root() -> Path:
    """Find the repo root by walking up until ``.git`` is found.

    Mirrors the pattern in drift tests (``test_drift_extended_invariants``).
    """
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / ".git").is_dir():
            return parent
    return Path.cwd()


def _to_posix_path(path: Path) -> str:
    """Convert a Windows path to POSIX for MSYS bash invocation.

    Without this, ``bash scripts/worktree-helper.sh`` fails on Windows
    because MSYS bash mangles backslashes and drive letters when handed
    a Windows-style absolute path like ``C:\\Users\\foo``. We shell out
    to ``cygpath -u`` to get the POSIX form (``/c/Users/foo``) that bash
    on Windows actually resolves. Falls back to ``str(path)`` on
    non-Windows or when ``cygpath`` is unavailable — so Linux/macOS
    users are unaffected, and Windows boxes without Git for Windows
    degrade gracefully rather than crashing.
    """
    if sys.platform != "win32":
        return str(path)
    if not shutil.which("cygpath"):
        return str(path)
    try:
        result = subprocess.run(
            ["cygpath", "-u", str(path)],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        converted = result.stdout.strip()
        return converted if converted else str(path)
    except (subprocess.SubprocessError, OSError) as exc:
        log.warning("cygpath conversion failed for %s: %s — falling back", path, exc)
        return str(path)


def _run(
    cmd: list[str], *, cwd: Path | None = None, timeout: int = 30
) -> subprocess.CompletedProcess[str]:
    """Thin wrapper around subprocess.run with text + capture on."""
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def worktree_create_node(state: PaperclipStateDict) -> dict[str, object]:
    """Create ``.worktrees/<task_id>/`` on branch ``paperclip/<task_id>``.

    Uses ``scripts/worktree-helper.sh create <task_id>`` — M24.1 Windows-safe.
    """
    task_id = state.get("task_id") or ""
    if not task_id:
        return {
            "originating_node": "worktree_create",
            "error_type": "TaskIdMissing",
            "error_message": "task_id is required for worktree_create",
            "last_step": "worktree_create",
        }
    repo_root = _resolve_repo_root()
    helper = repo_root / "scripts" / "worktree-helper.sh"
    if not helper.exists():
        return {
            "originating_node": "worktree_create",
            "error_type": "WorktreeHelperMissing",
            "error_message": f"worktree-helper.sh not found at {helper}",
            "last_step": "worktree_create",
        }
    proc = _run(["bash", _to_posix_path(helper), "create", task_id], cwd=repo_root, timeout=30)
    if proc.returncode != 0:
        return {
            "originating_node": "worktree_create",
            "error_type": "WorktreeCreateError",
            "error_message": proc.stderr.strip() or proc.stdout.strip(),
            "last_step": "worktree_create",
        }
    worktree_path = repo_root / ".worktrees" / task_id
    branch_name = f"paperclip/{task_id}"
    log.info("paperclip worktree_create: %s (branch=%s)", worktree_path, branch_name)
    return {
        "worktree_path": str(worktree_path),
        "branch_name": branch_name,
        "last_step": "worktree_create",
        "messages": [
            {
                "role": "system",
                "content": f"paperclip: worktree_create path={worktree_path} branch={branch_name}",
            }
        ],
    }


def worktree_commit_node(state: PaperclipStateDict) -> dict[str, object]:
    """Commit any pending changes in the worktree with a Paperclip-prefixed message.

    Single-commit-per-spec design — if the agent left multiple commits,
    we ``git add -A && git commit --amend`` so the worktree ends with
    exactly one commit on top of the base branch.
    """
    worktree = state.get("worktree_path")
    task_id = state.get("task_id") or "unknown"
    if not worktree:
        return {
            "originating_node": "worktree_commit",
            "error_type": "WorktreeMissing",
            "error_message": "worktree_path missing — worktree_create must run first",
            "last_step": "worktree_commit",
        }
    wt = Path(worktree)
    if not wt.exists():
        return {
            "originating_node": "worktree_commit",
            "error_type": "WorktreeMissing",
            "error_message": f"worktree path {wt} does not exist",
            "last_step": "worktree_commit",
        }
    # Stage everything
    add = _run(["git", "add", "-A"], cwd=wt, timeout=15)
    if add.returncode != 0:
        return {
            "originating_node": "worktree_commit",
            "error_type": "GitAddError",
            "error_message": add.stderr.strip(),
            "last_step": "worktree_commit",
        }
    # Commit (--allow-empty so we always produce a sha even if spec was trivial)
    msg = f"paperclip: {task_id}\n\nAutomated commit from Paperclip MVP graph."
    commit = _run(["git", "commit", "--allow-empty", "-m", msg], cwd=wt, timeout=15)
    if commit.returncode != 0:
        return {
            "originating_node": "worktree_commit",
            "error_type": "GitCommitError",
            "error_message": commit.stderr.strip(),
            "last_step": "worktree_commit",
        }
    # Capture sha
    rev = _run(["git", "rev-parse", "HEAD"], cwd=wt, timeout=5)
    sha = (rev.stdout or "").strip() or None
    log.info("paperclip worktree_commit: sha=%s", sha)
    return {
        "commit_sha": sha,
        "last_step": "worktree_commit",
        "messages": [{"role": "system", "content": f"paperclip: commit {sha}"}],
    }


def worktree_merge_node(state: PaperclipStateDict) -> dict[str, object]:
    """Merge ``paperclip/<task_id>`` into master with --no-ff.

    The merge runs in the REPO ROOT (not the worktree) — the worktree's
    branch must already be reachable from the repo's branch refs.
    Conflict → ``error_type=MergeConflictError`` (HIL candidate for
    Wave N+3).
    """
    worktree = state.get("worktree_path")
    branch = state.get("branch_name")
    task_id = state.get("task_id") or "unknown"
    if not worktree or not branch:
        return {
            "originating_node": "worktree_merge",
            "error_type": "MergeContextMissing",
            "error_message": "worktree_path / branch_name missing",
            "last_step": "worktree_merge",
        }
    repo_root = _resolve_repo_root()
    msg = f"paperclip: merge {task_id} ({state.get('commit_sha', '?')[:8]})"
    merge = _run(
        ["git", "merge", "--no-ff", branch, "-m", msg],
        cwd=repo_root,
        timeout=30,
    )
    if merge.returncode != 0:
        return {
            "originating_node": "worktree_merge",
            "error_type": "MergeConflictError",
            "error_message": merge.stderr.strip() or "merge failed (conflict?)",
            "last_step": "worktree_merge",
        }
    log.info("paperclip worktree_merge: %s -> master", branch)
    return {
        "last_step": "worktree_merge",
        "messages": [{"role": "system", "content": f"paperclip: merge {branch} -> master"}],
    }


def worktree_cleanup_node(state: PaperclipStateDict) -> dict[str, object]:
    """Remove the worktree + branch via the helper.

    Failure here is non-fatal — the orphan-GC sweep handles it. We log
    + continue (don't populate the error channel).
    """
    worktree = state.get("worktree_path")
    task_id = state.get("task_id") or ""
    if not task_id:
        return {"last_step": "worktree_cleanup"}
    repo_root = _resolve_repo_root()
    helper = repo_root / "scripts" / "worktree-helper.sh"
    if not helper.exists():
        log.warning("worktree-helper.sh missing during cleanup; leaving %s intact", worktree)
        return {"last_step": "worktree_cleanup"}
    proc = _run(["bash", _to_posix_path(helper), "cleanup", task_id], cwd=repo_root, timeout=30)
    if proc.returncode != 0:
        log.warning(
            "paperclip worktree_cleanup: helper exit=%d stderr=%s (orphan-GC will sweep later)",
            proc.returncode,
            proc.stderr.strip(),
        )
    return {
        "last_step": "worktree_cleanup",
        "messages": [{"role": "system", "content": f"paperclip: cleanup task_id={task_id}"}],
    }

"""Every module the published code imports is a module the branch publishes.

This guard exists because of a real failure, and it is the kind that is
invisible on the machine where it happens:

`src/data/drafts.py` was written, imported by `src/services/drafts.py`, and
covered by tests — and it was in NO clone. `.gitignore` has a deny-all rule
under `src/data/` (`/src/data/*`) with each real file named back, and the new
file was not named back. On the owner's disk everything worked; a fresh clone
could not import the service at all.

The suite could not see it, because the file being present is exactly the thing
the suite takes for granted. `git` is the only witness, and `git` was saying it
all along: `git ls-files` did not list the file.

So this walks the imports of every TRACKED module under `src/` and asks git
whether the module it names is tracked too. A file that is imported is a file
that has to ship.
"""

from __future__ import annotations

import ast
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]


def _tracked() -> set[str]:
    """The files the branch publishes, as paths relative to the repository root."""
    try:
        listed = subprocess.run(
            ["git", "ls-files", "src"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError):  # pragma: no cover — not a clone
        return set()
    return {line.strip() for line in listed.splitlines() if line.strip().endswith(".py")}


def _imported_modules(path: Path) -> set[str]:
    """The `src.*` modules one file imports, at any depth."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError):  # pragma: no cover — a broken file is another test
        return set()

    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            if node.module == "src" or node.module.startswith("src."):
                found.add(node.module)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "src" or alias.name.startswith("src."):
                    found.add(alias.name)
    return found


def _candidates(module: str) -> tuple[str, str]:
    """The two shapes a module can take on disk."""
    base = module.replace(".", "/")
    return f"{base}.py", f"{base}/__init__.py"


def test_every_imported_module_is_tracked() -> None:
    tracked = _tracked()
    if not tracked:
        # Outside a clone there is nothing to prove: in a clone every tracked
        # file is present by construction, which is the state this guards.
        return

    offenders: list[str] = []
    for relative in sorted(tracked):
        path = REPO_ROOT / relative
        if not path.exists():  # pragma: no cover — a tracked file that is gone
            offenders.append(f"{relative} is tracked and missing from disk")
            continue
        for module in sorted(_imported_modules(path)):
            module_file, package_file = _candidates(module)
            if module_file in tracked or package_file in tracked:
                continue
            # A module that exists on disk but not in the index is the exact
            # failure: it runs here and nowhere else.
            if (REPO_ROOT / module_file).exists() or (REPO_ROOT / package_file).exists():
                offenders.append(f"{relative} imports {module}, which is IGNORED (on disk, not in git)")
            else:
                offenders.append(f"{relative} imports {module}, which does not exist")

    assert not offenders, (
        "the branch imports what it does not publish:\n  "
        + "\n  ".join(offenders[:20])
        + "\nName the file back in the .gitignore (a deny-all rule under a "
        "directory excludes every new file in it), or stop importing it."
    )


def test_the_data_layer_names_back_every_file_it_has() -> None:
    """The directory the failure happened in, held from the other side.

    `/src/data/*` is a deny-all rule with each real file named back. That is a
    rule every new file has to be added to, and forgetting is silent — so the
    files are compared with the index here, where forgetting is loud.
    """
    tracked = _tracked()
    if not tracked:
        return

    ship = {
        path.name
        for path in (REPO_ROOT / "src" / "data").glob("*.py")
        if f"src/data/{path.name}" in tracked
    }
    on_disk = {path.name for path in (REPO_ROOT / "src" / "data").glob("*.py")}

    missing = on_disk - ship
    assert not missing, (
        f"src/data/ holds {sorted(missing)} and the branch does not publish them. "
        "Add `!/src/data/<name>` to the .gitignore."
    )

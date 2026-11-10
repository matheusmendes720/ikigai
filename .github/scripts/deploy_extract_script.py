"""Extract the deploy's remote script from the workflow.

The deploy's remote script is the thing that actually ships to the box, and
it is carried inside the workflow as a heredoc. This pulls it OUT, so it can
be diffed against the version that ran before, or run on a box on its own.

    python .github/scripts/deploy_extract_script.py OUT.sh

The script is read OUT of the workflow and not copied here: a copy is a
second version, and the day the two drift this tool proves nothing.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml


def _repo_root() -> Path:
    """The directory that holds `.github/workflows/deploy.yml`.

    Found by walking UP, because a script that assumes a fixed depth is a
    script that breaks the day it moves.
    """
    for candidate in Path(__file__).resolve().parents:
        if (candidate / ".github" / "workflows" / "deploy.yml").exists():
            return candidate
    raise SystemExit("deploy.yml not found above this script")


def remote_script() -> str:
    """The script the remote receives."""
    workflow = yaml.safe_load(
        (_repo_root() / ".github" / "workflows" / "deploy.yml").read_text(encoding="utf-8")
    )
    step = next(
        s for s in workflow["jobs"]["deploy"]["steps"] if s.get("name") == "Deploy over SSH"
    )
    match = re.search(r"<<'DEPLOY_SCRIPT'\n(.*?)\nDEPLOY_SCRIPT\n", step["run"], re.DOTALL)
    if match is None:
        raise SystemExit(
            "the deploy script is not carried by a heredoc, or the terminator "
            "is not alone on its line — the remote would receive nothing"
        )
    return match.group(1)


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit(f"usage: {sys.argv[0]} OUT.sh")
    out = Path(sys.argv[1])
    script = remote_script()
    out.write_text(script + "\n", encoding="utf-8", newline="\n")
    lines = script.splitlines()
    print(f"extracted {len(script)} bytes to {out}")
    print("first line:", lines[0] if lines else "(empty)")
    print("last line:", lines[-1] if lines else "(empty)")


if __name__ == "__main__":
    main()

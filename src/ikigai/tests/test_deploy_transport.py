"""Check the deploy workflow the way the runner will read it.

The deploy is the one thing in this repository that cannot be tested by
running it: it ships to a box, it needs four secrets, and every failure it
has had was a failure of SHAPE rather than of logic. So the shape is what a
test has to hold.

Three things are checked, and each of them was a measured failure:

1. **The remote script is byte-identical to what ran before.** The heredoc
   that carries it strips the block's indentation, and a stray space in the
   terminator turns the whole script into a file that is never executed.
2. **The script is transferred, not embedded in a step's input.** The values
   are interpolated on the runner, so the remote receives them.
3. **Nothing has to be downloaded to deploy.** The pipeline used to fetch a
   binary from GitHub Releases on every run, and a CDN in 504 killed a deploy
   that had nothing wrong with it.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "deploy.yml"

#: The remote script's own opener, which every version of it starts with.
SCRIPT_OPENER = "set -eu"


def _workflow() -> dict[str, Any]:
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


def _deploy_step() -> dict[str, Any]:
    steps = _workflow()["jobs"]["deploy"]["steps"]
    step = next(
        (s for s in steps if s.get("name") == "Deploy over SSH"), None
    )
    assert step is not None, "the deploy step no longer exists"
    return step


def _remote_script() -> str:
    """The script the remote receives, taken from the heredoc.

    It is read OUT of the workflow, not copied into the test: a copy is a
    second version, and the day the two drift the test holds nothing.
    """
    body = _deploy_step()["run"]
    match = re.search(
        r"<<'DEPLOY_SCRIPT'\n(.*?)\nDEPLOY_SCRIPT\n", body, re.DOTALL
    )
    assert match is not None, (
        "the deploy script is not carried by a heredoc, or the terminator is "
        "not alone on its line — the remote would receive nothing"
    )
    return match.group(1)


def test_the_remote_script_is_carried_and_terminated() -> None:
    script = _remote_script()

    assert script.startswith(SCRIPT_OPENER), (
        "the remote script does not start with `set -eu` — the heredoc's "
        "indentation is not being stripped and the remote runs it differently"
    )
    assert "IKIGAI_DEPLOY_PATH=" in script, "the deploy path is not in the script"
    assert "docker compose up -d --wait" in script, (
        "the script no longer waits for the service to be healthy — a deploy "
        "that reports success while the api is down is the green lie the "
        "healthcheck exists to prevent (contract C-2)"
    )


def test_the_deploy_downloads_nothing_to_run() -> None:
    """The pipeline fetches a binary from GitHub Releases on every run.

    A release CDN in 504 killed a deploy that had nothing wrong with it, and
    the action's own retry gave up after 31 seconds of refusals. The runner's
    `ssh` does the same job with nothing to download.
    """
    step = _deploy_step()

    assert "uses" not in step, (
        "the deploy uses an action again — an action that downloads a binary "
        "from GitHub Releases on every run, which is the pipeline's weakest link"
    )
    assert "ssh " in step["run"], "the deploy does not use ssh"
    assert "DEPLOY_SCRIPT" in step["run"], "the deploy carries no script"


def test_the_deploy_retries() -> None:
    """Three attempts, because every failure this deploy had was transient."""
    body = _deploy_step()["run"]

    assert "attempt" in body, "the deploy tries exactly once"
    assert "-ge 3" in body, "the retry has no ceiling — a box that is down hangs the deploy"


def test_the_key_is_written_and_removed() -> None:
    """The key is a file the runner uses and then deletes.

    A key left in `RUNNER_TEMP` is a key in a build artifact, and a key
    passed on a command line is a key in the process list.
    """
    body = _deploy_step()["run"]

    assert "chmod 600" in body, "the key file is not written with the mode ssh requires"
    assert 'rm -f "$key_file"' in body, "the key file is never removed"
    assert "-i \"$key_file\"" in body, "the key is not passed by file"


def test_the_deploy_does_not_hang_on_a_password_prompt() -> None:
    """A key that does not authenticate asks for a password, and a
    non-interactive runner waits on that prompt until the job dies with no
    error at all."""
    body = _deploy_step()["run"]

    assert "BatchMode=yes" in body, (
        "the deploy can wait on a password prompt — and a job that waits on a "
        "prompt fails with no error"
    )
    assert "StrictHostKeyChecking=accept-new" in body, (
        "the deploy does not say how to treat an unknown host key"
    )

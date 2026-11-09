"""The bot's socket has to outlive the harness's run.

**Why this is a test and not a comment.** A routine that asks the owner WAITS
for the answer: the agent is suspended on the question (ADR-041, `owner.mjs`),
and the question's ceiling is 15 minutes. The bot's HTTP client therefore has
to be willing to wait longer than the harness's run — otherwise the bot gives
up, tells the owner "a rotina falhou", and the agent goes on working with
nobody listening.

**Measured on the box (2026-11-09).** The ceilings lived in three places and
nothing connected them: the run's ceiling was 10 minutes, the bot's client
waited 10 minutes and 30 seconds, and the question's ceiling was 15 minutes.
So NO routine that asked the owner could ever finish, on any of the three
paths. The order is the contract, and this file pins it:

    the bot's socket  >  the harness's run  >  the owner's question

The numbers are read from the compose (the deployment's own map) and from the
bot's constants (the code that waits), and compared against each other — so a
change in one place that breaks the order fails here.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from src.bot.harness_client import DEFAULT_TIMEOUT_S, TIMEOUT_MARGIN_S

#: The repository root. This file lives in ``tests/transport/``, so the root
#: is four parents up.
REPO_ROOT = Path(__file__).resolve().parents[4]
COMPOSE = REPO_ROOT / "deploy" / "compose.yml"


def _default(raw: Any) -> int:
    """The default of a compose value: ``${NAME:-1200000}`` -> ``1200000``."""
    text = str(raw or "")
    assert ":-" in text, f"{text!r} declares no default"
    return int(text.split(":-", 1)[1].rstrip("}"))


def _environment(service: str) -> dict[str, Any]:
    document = yaml.safe_load(COMPOSE.read_text(encoding="utf-8"))
    services = document.get("services") or {}
    assert service in services, f"the compose declares no {service!r} service"
    return (services[service].get("environment") or {})


def test_the_bot_outlives_the_harness() -> None:
    """The bot's socket waits longer than the harness's run.

    The bot's client is the one that carries the answer of a routine. If it
    gives up first, the owner is told the routine failed while the agent is
    still working on it — the silence that looks like a failure.
    """
    run_ms = _default(_environment("harness").get("HARNESS_TIMEOUT_MS"))
    bot_s = _default(_environment("bot").get("IKIGAI_HARNESS_TIMEOUT_S"))

    assert bot_s * 1000 >= run_ms, (
        f"the bot's ceiling ({bot_s} s) is shorter than the harness's run "
        f"({run_ms} ms): the bot gives up before the harness answers, and the "
        "owner is told the routine failed while the agent is still working"
    )


def test_the_bots_own_default_is_the_deployments_default() -> None:
    """The bot's default and the compose's default must be the same number.

    Two defaults that disagree are two contracts: the deployment says one
    thing and the code says another, and the one that loses is the one the
    owner meets.
    """
    bot_s = _default(_environment("bot").get("IKIGAI_HARNESS_TIMEOUT_S"))
    assert DEFAULT_TIMEOUT_S == float(bot_s), (
        f"the bot's own default ({DEFAULT_TIMEOUT_S} s) is not the one the "
        f"deployment declares ({bot_s} s)"
    )


def test_the_bot_outlives_the_question() -> None:
    """The bot's socket has to outlive the QUESTION the routine asks.

    This is the assertion that catches the defect the product had. A routine
    that asks the owner waits for the answer — the agent is suspended on the
    question — and the question's ceiling is 15 minutes. The bot's client was
    willing to wait 10 minutes and 30 seconds, so it gave up while the owner
    was still reading, and told the owner the routine had failed.

    Falsifiable by construction: against the old numbers (run 600 s, question
    900 s, bot 630 s) this fails.
    """
    owner_ms = _default(_environment("harness").get("HARNESS_OWNER_TIMEOUT_MS"))
    bot_s = _default(_environment("bot").get("IKIGAI_HARNESS_TIMEOUT_S"))

    assert DEFAULT_TIMEOUT_S + TIMEOUT_MARGIN_S > owner_ms / 1000, (
        "the bot's client timeout does not outlive the question's ceiling: a "
        "routine that asks the owner waits for the answer, and the bot would "
        "give up before the harness heard it"
    )
    assert bot_s * 1000 >= owner_ms, (
        f"the bot's ceiling ({bot_s} s) is shorter than the question's "
        f"({owner_ms} ms): the bot gives up while the owner is still reading"
    )


def test_the_bots_margin_covers_the_harnesss() -> None:
    """The bot's margin has to outlast the harness's own margin.

    The harness declares a patience that outlives its run by a minute; the
    bot's client has to wait at least that much longer, or the bot's socket
    gives up while the harness is still preparing its answer.
    """
    run_ms = _default(_environment("harness").get("HARNESS_TIMEOUT_MS"))
    bot_s = _default(_environment("bot").get("IKIGAI_HARNESS_TIMEOUT_S"))

    assert DEFAULT_TIMEOUT_S + TIMEOUT_MARGIN_S > bot_s, (
        "the bot's client timeout is not longer than the ceiling it was "
        "given — the margin is what makes the wait survivable"
    )
    assert DEFAULT_TIMEOUT_S + TIMEOUT_MARGIN_S > run_ms / 1000, (
        "the bot's client timeout is shorter than the harness's run: the bot "
        "would give up before the harness answered"
    )

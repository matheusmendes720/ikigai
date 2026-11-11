"""The published surface: the route the repository declares, and its gate.

The Mini App is the only door of this product that the internet can knock on.
Everything that decides where that door is — its address, its credential model,
whether it is published at all — used to live in the box's `.env`, which means
it was reviewed by nobody and changed by hand.

ADR-045 moves it into the repository (`deploy/surfaces.json`) and gives the
surface a gate of its own. This module is that gate's contract: it holds the
table to the deployment, the deployment to the table, and the applier to the
shapes that were measured to be dangerous on this box.

The failures it refuses are not hypothetical. Each guard below names a shape
that was MEASURED on the box, not a style preference:

* `tailscale funnel --bg <port>` without `--https` takes the **443** host and
  REPLACES that host's `/` — measured: the MCP api's route went down (443 `/`
  was `127.0.0.1:8000` and became `127.0.0.1:10000`) with `AllowFunnel` left
  on 443.
* `tailscale funnel reset` wipes the WHOLE serve config — measured: the 443,
  the 8443 and the 8444 of another deployment went with it.
* A surface declared on the 443 host publishes the api, the agent's harness
  and three routes of another project along with the panel.

So the guards are about the EFFECT: the table must agree with the deployment,
the consumer must fail closed, and the applier must never be able to take a
host that belongs to someone else.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
TABLE = REPO_ROOT / "deploy" / "surfaces.json"
APPLIER = REPO_ROOT / "deploy" / "apply-surfaces.sh"
COMPOSE = REPO_ROOT / "deploy" / "compose.yml"
CI_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"
DEPLOY_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "deploy.yml"

#: The port of the Mini App inside the deployment. The compose publishes it on
#: the loopback, and the route points at it — a table that names a different
#: port publishes a route to nothing.
MINIAPP_PORT = 8003


def _table() -> dict[str, Any]:
    return json.loads(TABLE.read_text(encoding="utf-8"))


def _surfaces() -> dict[str, dict[str, Any]]:
    return dict(_table().get("surfaces") or {})


def _compose_services() -> dict[str, Any]:
    import yaml

    document = yaml.safe_load(COMPOSE.read_text(encoding="utf-8"))
    return dict(document.get("services") or {})


def _workflow(path: Path) -> dict[str, Any]:
    import yaml

    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    return dict(document.get("jobs") or {})


def _deploy_script() -> str:
    """The script the deploy sends to the box.

    It is the `run:` of the SSH step — the remote script is written to a file
    there and piped over stdin (`bash -s`), so the step's own body IS the
    script that lands on the box.
    """
    jobs = _workflow(DEPLOY_WORKFLOW)
    steps = jobs["deploy"].get("steps") or []
    for step in steps:
        if str(step.get("name") or "") == "Deploy over SSH":
            return str(step.get("run") or "")
    raise AssertionError("the deploy workflow has no 'Deploy over SSH' step")


def _applier_body() -> str:
    """The applier's CODE, without its comments.

    The header of the script CITES the very shapes the guards forbid —
    `funnel reset`, the 443, the 8443 — because that is where they are
    explained. A guard that read the comments would find the forbidden shape
    in the explanation of why it is forbidden.
    """
    script = APPLIER.read_text(encoding="utf-8")
    lines = []
    for line in script.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        lines.append(line.split(" #", 1)[0])
    return "\n".join(lines)


# ── The table ────────────────────────────────────────────────────────────────
def test_the_table_of_published_surfaces_exists_and_parses() -> None:
    """The table is a FILE in the repository, not a string in an environment.

    A table that lives in the box's `.env` is a table nobody reviews, and a
    route that nobody reviews is a route that drifts from the code that serves
    it. This is the same argument as ADR-042's routing table, one layer up:
    the table of the deployment travels with the deployment.
    """
    assert TABLE.exists(), (
        f"{TABLE} is missing — the published surface has no declared route, "
        "and the address falls back to the environment nobody reviews"
    )
    assert _surfaces(), "the table declares no surface"


def test_every_surface_declares_a_credential_model_we_implement() -> None:
    """The data door of a surface is the Telegram signature — or nothing.

    A surface that declares an unknown credential model is refused by the
    consumer (no address at all), which is the honest outcome: a published
    surface with an open data door is worse than no surface.
    """
    from src.bot.surfaces import ALLOWED_AUTH

    for name, surface in _surfaces().items():
        assert str(surface.get("auth") or "") in ALLOWED_AUTH, (
            f"the surface {name!r} declares the credential model "
            f"{surface.get('auth')!r}, which this code does not implement: "
            f"{sorted(ALLOWED_AUTH)}"
        )


def test_every_surface_declares_a_state_and_a_mode_we_know() -> None:
    """Two states, two modes — and the state is the OWNER's word.

    `pending` is declared but not published; `published` is on the internet.
    Neither is a fact the code can derive: the funnel being granted in the
    tailnet's admin is not the same thing as the route being published, and
    the repository is where the second one is said.
    """
    from src.bot.surfaces import ALLOWED_MODES, ALLOWED_STATES

    for name, surface in _surfaces().items():
        assert str(surface.get("state") or "") in ALLOWED_STATES, (
            f"the surface {name!r} declares the unknown state "
            f"{surface.get('state')!r}: {sorted(ALLOWED_STATES)}"
        )
        assert str(surface.get("mode") or "") in ALLOWED_MODES, (
            f"the surface {name!r} declares the unknown mode "
            f"{surface.get('mode')!r}: {sorted(ALLOWED_MODES)}"
        )


def test_a_published_surface_declares_the_funnel_mode() -> None:
    """`published` with a mode that cannot publish is a contradiction.

    The applier refuses it on the box, but the refusal happens in production,
    after a deploy — this guard catches it in the pull request.
    """
    from src.bot.surfaces import MODE_FUNNEL, STATE_PUBLISHED

    for name, surface in _surfaces().items():
        if str(surface.get("state") or "") == STATE_PUBLISHED:
            assert str(surface.get("mode") or "") == MODE_FUNNEL, (
                f"the surface {name!r} is declared published but its mode is "
                f"{surface.get('mode')!r}: a surface that does not know how to "
                "be published stays unpublished"
            )


def test_a_surface_never_declares_the_shared_https_host() -> None:
    """The 443 host of this box carries more than the panel.

    Measured on the box:

        vps-hetzner.tail78a4a0.ts.net:443 -> {
          "/":       http://127.0.0.1:8000,   # the MCP api
          "/athena": http://127.0.0.1:27210,  # another session
          "/harness": http://127.0.0.1:8002,  # the agent
          "/hefesto": http://127.0.0.1:27213, # another session
          "/telegram": http://127.0.0.1:27212 # another session
        }

    A surface published from that host publishes all of them. The panel has
    its own host — a host that carries nothing but the panel.
    """
    for name, surface in _surfaces().items():
        assert int(surface.get("https_port") or 0) != 443, (
            f"the surface {name!r} declares the 443 host: that host carries the "
            "MCP api, the agent's harness and three routes of another project"
        )


def test_the_table_points_at_the_service_the_deployment_publishes() -> None:
    """The route's target is the port the compose actually serves.

    The route points at a service. If the deployment moves the panel's port
    and the table does not follow, the route points at a closed door — and the
    page answers 502 from the internet while everything inside the tailnet
    still looks healthy.
    """
    for name, surface in _surfaces().items():
        target = str(surface.get("target") or "")
        assert target.startswith("http://127.0.0.1:"), (
            f"the surface {name!r} points at {target!r}: the route is applied "
            "on the box, and only the loopback is the box's own service"
        )
        port = int(target.rsplit(":", 1)[1])
        assert port == MINIAPP_PORT, (
            f"the surface {name!r} points at the port {port}, and the deployment "
            f"serves the panel on {MINIAPP_PORT}: the route would answer 502"
        )


def test_the_miniapp_surface_is_declared() -> None:
    """The panel is a surface of the table, with a name the bot looks up."""
    surfaces = _surfaces()
    assert "miniapp" in surfaces, f"the table declares no miniapp: {sorted(surfaces)}"


# ── The consumer ─────────────────────────────────────────────────────────────
@pytest.mark.parametrize(
    "mutation",
    [
        {"auth": "none"},
        {"auth": ""},
        {"state": "public"},
        {"state": ""},
        {"mode": "public-internet"},
        {"mode": ""},
        {"host": ""},
        {"https_port": 0},
        {"https_port": 70000},
        {"https_port": "not-a-port"},
    ],
)
def test_the_consumer_refuses_a_surface_it_does_not_implement(
    tmp_path: Path, mutation: dict[str, Any]
) -> None:
    """No address at all — and that is the POINT.

    The consumer is fail-closed: a surface it cannot vouch for produces no
    URL, so the bot behaves exactly as it did before the panel existed (the
    chat keeps working, the panel button is simply not sent). A surface with
    an open data door would be worse than no surface.
    """
    from src.bot.surfaces import surface, surface_url

    declared = {
        "host": "vps-hetzner.tail78a4a0.ts.net",
        "https_port": 8443,
        "path": "/",
        "target": "http://127.0.0.1:8003",
        "mode": "funnel",
        "auth": "telegram-initdata",
        "state": "pending",
    }
    declared.update(mutation)
    path = tmp_path / "surfaces.json"
    path.write_text(json.dumps({"surfaces": {"miniapp": declared}}), encoding="utf-8")

    assert surface("miniapp", path) is None, (
        f"the consumer accepted a surface it does not implement: {mutation!r}"
    )
    assert surface_url("miniapp", path) == "", (
        f"the consumer produced an address for a surface it does not implement: {mutation!r}"
    )


def test_a_missing_table_produces_no_address(tmp_path: Path) -> None:
    """A table that cannot be read is a table that does not exist.

    The surfaces are then the ones from before, which is none of them.
    """
    from src.bot.surfaces import miniapp_url, surface

    assert surface("miniapp", tmp_path / "absent.json") is None
    assert miniapp_url(tmp_path / "absent.json") == ""


def test_a_malformed_table_produces_no_address(tmp_path: Path) -> None:
    """A table that is not JSON, or not a table, is refused the same way."""
    from src.bot.surfaces import miniapp_url

    for payload in ("{not json", "[]", '{"surfaces": "nope"}', "{}"):
        path = tmp_path / "surfaces.json"
        path.write_text(payload, encoding="utf-8")
        assert miniapp_url(path) == "", f"the consumer accepted the payload {payload!r}"


def test_the_address_does_not_change_with_the_state() -> None:
    """`pending` and `published` are the SAME address.

    The funnel does not move the panel — it removes the tailnet-only
    restriction from it. An address that changed with the state would mean the
    button in the Telegram pointed somewhere else after the flip, and the
    owner would have to re-open the panel by hand.
    """
    from src.bot.surfaces import surface_url

    base = {
        "host": "vps-hetzner.tail78a4a0.ts.net",
        "https_port": 8443,
        "path": "/",
        "target": "http://127.0.0.1:8003",
        "mode": "funnel",
        "auth": "telegram-initdata",
    }
    paths = []
    for state in ("pending", "published"):
        path = Path(f"/tmp/surface-{state}.json")
        path.write_text(
            json.dumps({"surfaces": {"miniapp": {**base, "state": state}}}),
            encoding="utf-8",
        )
        paths.append(surface_url("miniapp", path))

    assert paths[0] == paths[1], (
        f"the address changed with the state: {paths[0]!r} vs {paths[1]!r}"
    )
    assert paths[0] == "https://vps-hetzner.tail78a4a0.ts.net:8443/"


def test_the_bot_reads_the_table_before_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """The table is the truth; the environment is the fallback.

    A box that carries the address in its `.env` has two truths, and a second
    truth is one nobody reviews. The order matters: the table first, the
    environment only when there is no table to read.
    """
    import src.bot.main as main

    monkeypatch.setenv("IKIGAI_SURFACES_FILE", str(TABLE))
    monkeypatch.setenv("IKIGAI_MINIAPP_URL", "https://elsewhere.invalid/panel")

    url = main._miniapp_url()
    assert url == "https://vps-hetzner.tail78a4a0.ts.net:8443/", (
        "the bot did not read the declared table — the environment won over "
        "the repository"
    )


# ── The deployment ───────────────────────────────────────────────────────────
def test_the_compose_mounts_the_table_read_only() -> None:
    """The table reaches the container, and it cannot be written from there.

    Two details are load-bearing, and both were measured elsewhere in this
    repository:

    * the path is `./surfaces.json`, relative to the **project directory**
      (`deploy/`) — `../surfaces.json` would be the wrong file;
    * the mount is a FILE that exists. A mount of a file IN MISSING makes
      docker create a DIRECTORY, and the bot would read no table while
      looking perfectly healthy.
    """
    compose = COMPOSE.read_text(encoding="utf-8")
    assert "./surfaces.json:/etc/ikigai/surfaces.json:ro" in compose, (
        "the table is not mounted read-only at /etc/ikigai/surfaces.json"
    )


def test_the_compose_names_the_table_for_the_bot() -> None:
    """The bot has to be told WHERE the table is — the mount is not enough.

    The value is the INTERPOLATION form (`${IKIGAI_SURFACES_FILE:-/etc/…}`),
    because the variable can still point somewhere else: what changes is the
    DEFAULT, not the capability (ADR-042 D2). The default has to be the
    mount's path, or the bot reads a table that is not the one the
    deployment carries.
    """
    bot = _compose_services()["bot"]
    environment = bot.get("environment") or {}
    value = str(environment.get("IKIGAI_SURFACES_FILE") or "")
    assert value, "the bot is not told where the table is"
    assert "/etc/ikigai/surfaces.json" in value, (
        f"the default of the table's path is {value!r}, and the mount is at "
        "/etc/ikigai/surfaces.json"
    )


def test_the_mounted_table_is_the_one_the_repository_publishes() -> None:
    """The file on disk is the file the repository publishes.

    A table that exists on the owner's disk and not in the commit is a table
    that a clone does not have — and the bot then reads nothing while the
    container reports healthy.
    """
    assert (COMPOSE.parent / "surfaces.json").exists(), (
        "the compose mounts ./surfaces.json, and that file does not exist in "
        "deploy/ — docker would create a directory there"
    )


# ── The applier ──────────────────────────────────────────────────────────────
def test_the_applier_exists() -> None:
    assert APPLIER.exists(), f"{APPLIER} is missing — the declared route would not be applied"


def test_the_applier_never_resets_the_box_config() -> None:
    """`tailscale funnel reset` is FORBIDDEN, and it is not a style rule.

    Measured: it wipes the WHOLE serve config. The 443 (the MCP api, the
    agent's harness and three routes of another project), the 8443 and the
    8444 went with it — and the repair had to be re-applied by hand, route by
    route, from a photograph taken beforehand.

    The applier applies ONE declared host:port and path. It never resets.
    """
    script = _applier_body()
    offenders = [line for line in script.splitlines() if "funnel reset" in line]
    assert not offenders, (
        "the applier resets the box's whole serve config — measured, that "
        f"takes every other surface with it: {offenders}"
    )


def test_the_applier_always_names_the_host_and_the_path() -> None:
    """Every `tailscale` command carries `--https` AND `--set-path`.

    Measured: `tailscale funnel --bg 10000` WITHOUT `--https` assumes the
    **443** host and replaces that host's `/` handler — the MCP api's route
    went down (443 `/` was `127.0.0.1:8000`, became `127.0.0.1:10000`) and
    `AllowFunnel` was left on 443.
    """
    script = _applier_body()
    commands = [
        command
        for command in re.findall(
            r"sudo(?:\s+-n)?\s+tailscale\s+(?:funnel|serve)\b[^\n]*", script
        )
        # `serve status` only READS the config; it changes nothing.
        if " status" not in command
    ]
    assert commands, "the applier runs no tailscale command at all"

    for command in commands:
        assert "--https=" in command, (
            f"the command does not name the host: {command!r} — without "
            "--https the funnel takes the 443 host"
        )
        assert "--set-path=" in command, (
            f"the command does not name the path: {command!r} — without "
            "--set-path it replaces that host's '/'"
        )


def test_the_applier_hardcodes_no_host_and_no_port() -> None:
    """The applier reads the route from the TABLE, not from itself.

    A port written into the script is a second truth about the route — and
    the second truth is the one that does not move when the table moves.
    """
    script = _applier_body()
    assert not re.search(r"\b\d{4,5}\b", script), (
        "the applier hardcodes a port: the route's port belongs to the table"
    )
    assert "tail78a4a0" not in script, (
        "the applier hardcodes a host: the route's host belongs to the table"
    )


def test_the_applier_fails_closed_on_an_unknown_state() -> None:
    """A state the applier does not know is a refusal, not a default.

    The default of an unknown state must be the closed door: a script that
    published an unknown surface would put a door on the internet that nobody
    decided to open.
    """
    script = _applier_body()
    assert "published)" in script and "pending)" in script, (
        "the applier does not branch on the state"
    )
    assert "unknown state" in script, (
        "the applier does not refuse an unknown state — it must fail closed"
    )


# ── The gates ────────────────────────────────────────────────────────────────
def test_the_ci_gates_the_surface_with_a_job_of_its_own() -> None:
    """The surface is PUBLISHED code, and published code has a gate.

    The `src-bot` entry gates the page's JavaScript and the `ikigai` entry
    gates the bot's Python — but nothing gated the SURFACE: not the table,
    not the mount, not the applier. A route declared in one place and applied
    from another drifts the first time one of them is edited.
    """
    jobs = _workflow(CI_WORKFLOW)
    assert "published-surface" in jobs, (
        f"the CI has no job of its own for the surface: {sorted(jobs)}"
    )
    steps = jobs["published-surface"].get("steps") or []
    runs = " ".join(str(step.get("run") or "") for step in steps)
    assert "test_published_surface.py" in runs, (
        "the surface's own job does not run the surface's own guards"
    )


def test_the_ci_gate_publishes_nothing() -> None:
    """The contract gate is a CONTRACT gate: it touches no box and no route.

    A gate that could publish would publish by accident, in a pull request,
    on somebody's laptop.
    """
    jobs = _workflow(CI_WORKFLOW)
    steps = jobs["published-surface"].get("steps") or []
    body = json.dumps(steps)
    assert "tailscale" not in body, "the CI gate reaches for the tailscale binary"
    assert "ssh" not in body.lower(), "the CI gate reaches for a machine"


def test_the_deploy_applies_the_table_after_the_services_are_up() -> None:
    """The route is applied AFTER the services answer.

    The route points at a service. A route that points at a service that is
    not up yet is a route that answers 502 — and the deploy would report
    success, because the compose wait had already passed.
    """
    script = _deploy_script()
    assert "apply-surfaces.sh" in script, (
        "the deploy does not apply the declared surfaces"
    )
    up = script.find("docker compose up")
    apply = script.find("apply-surfaces.sh")
    assert up != -1 and apply != -1, "the deploy does not bring the services up"
    assert up < apply, (
        "the route is applied BEFORE the services are up — a route applied "
        "first answers 502 until the container is there"
    )


def test_the_deploy_probes_the_effect_from_outside_the_tailnet() -> None:
    """The effect gate runs on a runner that is not in the tailnet.

    A probe from inside the tailnet answers even with the funnel off, and
    would prove nothing about publication. The gate is a separate job that
    needs the deploy, so it cannot race it.
    """
    jobs = _workflow(DEPLOY_WORKFLOW)
    assert "published-surface" in jobs, (
        f"the deploy has no effect gate: {sorted(jobs)}"
    )
    job = jobs["published-surface"]
    assert "deploy" in (job.get("needs") or []), (
        "the effect gate does not wait for the deploy — it would measure the "
        "previous deployment"
    )
    assert str(job.get("runs-on") or "") == "ubuntu-latest", (
        "the effect gate does not run on the runner"
    )

    body = json.dumps(job.get("steps") or [])
    assert "tailscale" not in body, "the effect gate reaches for the tailscale binary"
    assert "/api/session" in body, (
        "the effect gate does not probe the data door — a published page with "
        "an open door is not a published surface"
    )


def test_the_effect_gate_only_asks_when_the_surface_is_published() -> None:
    """A surface that is declared but not published is not a failure.

    It is a decision that has not been taken yet (ADR-045 D3). The gate asks
    the table first, and only probes when the table says `published`.
    """
    jobs = _workflow(DEPLOY_WORKFLOW)
    steps = jobs["published-surface"].get("steps") or []
    guarded = [
        step
        for step in steps
        if str(step.get("if") or "").find("published") != -1
    ]
    assert guarded, (
        "the effect gate probes unconditionally — a surface that is declared "
        "but not published is a decision, not a failure"
    )
    body = json.dumps(steps)
    assert "state" in body, "the effect gate does not read the declared state"


def test_the_surface_and_its_gate_are_one_change() -> None:
    """The table, the consumer, the applier and the gates travel together.

    A route without a gate is a door that nobody watches; a gate without a
    route is a test of nothing. They are one decision, and the guard is that
    the decision is taken whole.
    """
    for path in (
        TABLE,
        APPLIER,
        REPO_ROOT / "src" / "bot" / "surfaces.py",
        REPO_ROOT / "src" / "ikigai" / "tests" / "test_published_surface.py",
    ):
        assert path.exists(), f"{path} is missing — the surface is half a decision"

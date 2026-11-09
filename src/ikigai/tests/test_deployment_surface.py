"""The deployment surface: the compose file, the ingestion and the channel.

Three things have to hold together, and none of them is visible in the code:

1. **The vault is a volume.** The prose is the persistent memory, and a
   container that only sees the copy baked into its image answers from the
   memory of the commit it was built from — while the vault says otherwise.
2. **The ingestion has a command.** The `vault-sync` skill says "run the
   ingestion", and a routine that names no command is a routine nobody can
   run.
3. **The change channel is named in BOTH places.** The migration raises it
   and the code listens for it; a channel that does not match is a listener
   that waits forever, and the symptom is a sync that never syncs.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
COMPOSE = REPO_ROOT / "deploy" / "compose.yml"
MIGRATIONS = REPO_ROOT / "src" / "contracts" / "migrations"


def _compose() -> str:
    return COMPOSE.read_text(encoding="utf-8")


def _deploy_workflow() -> str:
    return (REPO_ROOT / ".github" / "workflows" / "deploy.yml").read_text(encoding="utf-8")


def _service_block(name: str) -> str:
    """The block of ONE service, by the two-space indentation compose uses.

    The services are at two spaces and their keys at four, so the next
    service header is the next line that starts with EXACTLY two spaces and
    a non-space after them. That is enough to read one service without a
    YAML parser — and the suite must not depend on a package the image does
    not carry.
    """
    compose = _compose()
    header = f"\n  {name}:\n"
    assert header in compose, f"the compose has no {name!r} service"
    rest = compose.split(header, 1)[1]
    end = re.search(r"\n  \S", rest)
    return rest if end is None else rest[: end.start()]


def test_the_compose_file_exists() -> None:
    assert COMPOSE.exists(), f"{COMPOSE} is missing"


def test_the_vault_is_a_volume_and_not_only_a_copy() -> None:
    """The prose is mounted, so the ingestion reads what is there NOW."""
    compose = _compose()
    assert "./vault:/app/vault:ro" in compose, (
        "the vault is not mounted as a volume — the ingestion would read the "
        "copy baked into the image, which is the prose of the build, not of now"
    )


def test_the_compose_runs_the_ingestion() -> None:
    compose = _compose()
    assert "src.services.sync" in compose, "nothing runs the vault ingestion"
    assert "IKIGAI_VAULT_ROOTS" in compose, "the ingestion is not told where the prose is"


def test_the_zones_tree_is_mounted_for_the_ingestion() -> None:
    """The knowledge zones reach the ingestion as a VOLUME.

    They are synced onto the Cloud Volume by Syncthing and they are the
    owner's own markdown — the same argument as the vault above: a container
    that only sees the copy baked into its image answers from the prose of the
    commit it was built from.
    """
    compose = _compose()
    assert "/app/zonas:ro" in compose, (
        "the zones are not mounted — the ingestion would read the copy baked "
        "into the image, which is the prose of the build, not of now"
    )


def test_the_deployment_names_the_zones_layout() -> None:
    """The layout the zones are read with is named in the deployment."""
    compose = _compose()
    assert "=zones" in compose, (
        "the zones layout is not named in the deployment — the ingestion would "
        "read the zones with the layout of another tree"
    )


def test_the_compose_runs_the_websocket() -> None:
    compose = _compose()
    assert "src.transport.ws_server" in compose, "the websocket is not deployed"
    assert "IKIGAI_WS_TOKEN" in compose, (
        "the websocket is a write channel and it is deployed without a token"
    )


def test_the_bot_speaks_the_websocket_scheme() -> None:
    """The bot's change stream names a WEBSOCKET, and the scheme is the protocol.

    The websocket answers on 8001 and so would an HTTP server: the port says
    nothing about the protocol. The compose said `http://ws:8001/sync` — the
    right host, the right port, the wrong protocol — so the bot's whole store
    leg (search, read, write, the change stream) was refused before a socket
    opened, while the container reported healthy. Measured on the box: 591 ms
    to fail on `http://`, 99 ms to answer a real call on `ws://`.

    Nothing measured this, which is why it survived; the guard is the
    measurement.
    """
    services = _compose_services()
    environment = services["bot"].get("environment") or {}
    url = str(environment.get("IKIGAI_WS_URL") or "")

    assert url, (
        "the bot has no websocket: it would only ever learn about its own writes, "
        "and every write made by the ingestion would stay invisible"
    )
    assert url.startswith(("ws://", "wss://")), (
        f"the bot's websocket URL is {url!r}: an http:// URL is a different "
        "protocol that happens to share the port, and the call fails even when "
        "the service is healthy"
    )


def _compose_services() -> dict[str, Any]:
    """The compose, parsed.

    The file is YAML, so the guards read it as YAML: a service that holds a
    DSN is a fact about the compose, not a string that happens to be near it.
    """
    import yaml

    document = yaml.safe_load(_compose())
    services = document.get("services") or {}
    assert services, "the compose declares no services"
    return services


def test_the_compose_gives_the_bot_the_agent_door() -> None:
    """The bot reaches the agent, and the agent is deployed.

    Without the door the bot still writes, searches and reads — but the
    routines ARE the cadences the product runs, and a compose that deploys
    the agent without wiring it to anything is a product that ships an
    expensive process and never asks it for anything.
    """
    services = _compose_services()
    assert "harness" in services, "the agent is not deployed"

    bot = services["bot"]
    url = str((bot.get("environment") or {}).get("IKIGAI_HARNESS_URL") or "")
    assert "http://harness:8002" in url, (
        f"the bot's door does not point at the agent's service: {url!r}"
    )
    assert "harness" in (bot.get("depends_on") or {}), "the bot starts before the agent it talks to"


def test_the_compose_fires_the_cadence() -> None:
    """The cadence is the only trigger with no input, and the clock is HERE.

    A bot image that is told no time runs exactly as it did before the cadence
    existed, so the deployment is where the clock is set. The offset is
    asserted separately and on purpose: a cadence with no clock fires at the
    CONTAINER's hour — UTC — and the report lands three hours before the day
    it reports on has ended.
    """
    bot = _compose_services()["bot"]
    environment = bot.get("environment") or {}

    assert "IKIGAI_CADENCE_AT" in environment, "the deployment never asks for a cadence"
    assert environment["IKIGAI_CADENCE_AT"], (
        "the cadence time is empty; `IKIGAI_CADENCE_AT=off` is how to say no"
    )
    assert "IKIGAI_CADENCE_UTC_OFFSET" in environment, (
        "the cadence has no clock, so it fires at the container's UTC hour"
    )


def test_the_provider_key_is_a_file_and_not_an_environment_variable() -> None:
    """The agent's key must not travel in the environment.

    An `environment:` entry is not a secret store. The engine keeps it in the
    container's `Config.Env` — so `docker inspect` prints the key — and in
    `/proc/1/environ` inside the container, where every process the agent
    spawns inherits it. Measured on the box before this guard existed: the
    125-character key was one `docker inspect` away from anyone allowed to run
    `docker` there.

    A file secret is mounted at `/run/secrets/<name>` and exists only inside
    the container that declares it, so the two assertions are one contract:
    the variable is gone AND the file is there. Keeping only the first would
    pass for a compose that forgot to mount the key at all, and the agent
    would fail at the first request with a message about authentication.
    """
    services = _compose_services()
    environment = services["harness"].get("environment") or {}

    assert "HARNESS_PROVIDER_API_KEY" not in environment, (
        "the provider's key is in the container's environment: `docker inspect` "
        "prints Config.Env, and every child process inherits it"
    )

    mounted = services["harness"].get("secrets") or []
    names = {
        entry if isinstance(entry, str) else str((entry or {}).get("source")) for entry in mounted
    }
    assert "harness_provider_key" in names, (
        f"the harness mounts no provider-key secret: {sorted(names)}"
    )

    import yaml

    document = yaml.safe_load(_compose())
    declaration = (document.get("secrets") or {}).get("harness_provider_key") or {}
    assert str(declaration.get("file") or "").endswith("harness_provider_key"), (
        "the secret is not backed by a file: the key would come from somewhere "
        f"the operator cannot protect: {declaration!r}"
    )

    # The third half of the contract, and the one that catches a change that
    # went only half way: the agent must be told the FILE. A compose without
    # the variable AND an entrypoint still resolving `$HARNESS_PROVIDER_API_KEY`
    # would start, find nothing, and fail at the first request with "invalid
    # api key" — a message that names the credential and not the wiring.
    entrypoint = (REPO_ROOT / "deploy" / "harness" / "entrypoint.sh").read_text(encoding="utf-8")
    assert "/run/secrets/harness_provider_key" in entrypoint, (
        "the entrypoint never names the secret mount: the agent would read the key "
        "from an environment variable that is no longer set"
    )
    assert '"$HARNESS_PROVIDER_API_KEY"' not in entrypoint, (
        "the entrypoint still resolves the key from the environment"
    )


def test_the_fallback_provider_is_declared_and_mounted() -> None:
    """A refusal from the primary provider must not become an empty answer.

    Measured on the box with a quota-exhausted key: the turn ended with
    `stopReason: "error"` on the assistant message and an empty text, and the
    routine answered `ok: true` with zero bytes — the owner asked for the day's
    report and got nothing, with a green status.

    The retry needs three things wired together, and a missing one is silent:
    the trigger list (what is worth retrying), the fallback provider/model the
    harness passes to `pi`, and a key it can read. The key is a FILE for the
    same reason as the primary's: `docker inspect` prints the environment.
    """
    services = _compose_services()
    environment = services["harness"].get("environment") or {}

    assert str(environment.get("HARNESS_FALLBACK_PROVIDER") or ""), (
        "no fallback provider is declared: a refused routine would come back empty"
    )
    assert str(environment.get("HARNESS_FALLBACK_MODEL") or ""), (
        "the fallback provider has no model: pi would have to guess one"
    )
    triggers = str(environment.get("HARNESS_FALLBACK_ON") or "")
    assert "429" in triggers, (
        f"the trigger list does not include 429, the meter that started all this: {triggers!r}"
    )
    assert "401" not in triggers, (
        "401 is in the trigger list: a wrong key is not a transient refusal, and "
        "retrying it hides the cause behind a second provider's answer"
    )

    mounted = services["harness"].get("secrets") or []
    names = {
        entry if isinstance(entry, str) else str((entry or {}).get("source")) for entry in mounted
    }
    assert "deepseek_api_key" in names, f"the fallback key is not mounted: {sorted(names)}"

    import yaml

    document = yaml.safe_load(_compose())
    declaration = (document.get("secrets") or {}).get("deepseek_api_key") or {}
    assert str(declaration.get("file") or "").endswith("deepseek_api_key"), (
        f"the fallback key is not a file secret: {declaration!r}"
    )


def test_the_agent_does_not_hold_a_dsn() -> None:
    """The agent is a client of the api, like every other client.

    A DSN in the agent's container would be a second writer of one store
    waiting to happen (ADR-037 D5) — and the agent has no need of one: it
    reaches the DOM through the api's MCP.
    """
    services = _compose_services()
    environment = services["harness"].get("environment") or {}
    assert "IKIGAI_STORE_DSN" not in environment, (
        "the agent holds a DSN — it is a second writer of the store"
    )


def test_the_bot_does_not_hold_a_dsn() -> None:
    """The bot gained a second door, and it did not gain a store.

    A door to the agent is a door to a CLIENT of the api, not to the
    database. A DSN in the bot would be a fallback to the database — a
    second writer waiting to happen (ADR-037 D5, D6).
    """
    services = _compose_services()
    environment = services["bot"].get("environment") or {}
    assert "IKIGAI_STORE_DSN" not in environment, (
        "the bot holds a DSN — it is a second writer of the store"
    )


def test_the_ingestion_has_a_command() -> None:
    """`python -m src.services.sync` is what the routine means."""
    from src.services.sync import main

    assert callable(main)


def test_the_sync_reads_the_trees_the_environment_names(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A container mounts the vault where the deployment says, not where the
    repository happens to keep it."""
    from src.services.sync import VAULT_ROOTS_ENV, default_sources

    monkeypatch.setenv(VAULT_ROOTS_ENV, "/app/vault/ikigai/closing-2026=closing")
    sources = default_sources()

    assert len(sources) == 1
    # Compared as PATHS, not as strings: the path separator is the platform's,
    # and a container's path is a POSIX one whatever the host is.
    assert sources[0].root == Path("/app/vault/ikigai/closing-2026")
    assert sources[0].layout == "closing"


def test_a_malformed_tree_listing_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    from src.services.sync import VAULT_ROOTS_ENV, default_sources

    monkeypatch.setenv(VAULT_ROOTS_ENV, "/app/vault")

    with pytest.raises(ValueError, match=VAULT_ROOTS_ENV):
        default_sources()


def test_the_change_channel_is_named_in_both_places() -> None:
    """The migration raises it; the code listens for it."""
    from src.data.repository import ARTIFACT_EVENTS_CHANNEL

    migration = MIGRATIONS / "0004_artifact_events.sql"
    assert migration.exists(), f"{migration.name} is missing"

    assert ARTIFACT_EVENTS_CHANNEL in migration.read_text(encoding="utf-8"), (
        f"the migration does not raise {ARTIFACT_EVENTS_CHANNEL!r} — the code would "
        "listen for a channel nobody announces on"
    )


def test_the_change_migration_has_a_reverse_script() -> None:
    reverse = MIGRATIONS / "0004_artifact_events.down.sql"
    assert reverse.exists(), f"{reverse.name} is missing"
    assert reverse.read_text(encoding="utf-8").strip(), f"{reverse.name} is empty"


def test_the_vault_is_mounted_from_the_repository_root() -> None:
    """The volume path is resolved against the PROJECT DIRECTORY — the
    directory that holds the compose file, which is `deploy/`. The vault is
    tracked at the repository root, one level up, so the mount has to say
    `../vault`.

    The assertion above (`./vault:/app/vault:ro`) cannot catch this: that
    string is a SUBSTRING of `../vault:/app/vault:ro`, so it passes for both
    the right path and the wrong one. The vault is at the root of the
    repository, and `deploy/vault` does not exist — docker would create it
    empty, and the ingestion would read nothing while looking healthy.
    """
    compose = _compose()
    assert "../vault:/app/vault:ro" in compose, (
        "the vault is not mounted from the repository root — the ingestion would "
        "read a directory that is not in the repository"
    )


def test_the_ingestion_declares_a_healthcheck_it_can_pass() -> None:
    """The image's healthcheck measures the MCP transport on 8000.

    The ingestion serves no surface: it writes the vault into the store and
    serves nothing. Inheriting the image's check would leave it reporting
    unhealthy forever — a lie in the other direction, and a deploy that waits
    for health would never finish. What the ingestion depends on is the
    STORE, so that is what its check measures.
    """
    block = _service_block("sync")
    assert "healthcheck:" in block, (
        "the ingestion inherits the image's healthcheck, which dials the MCP "
        "transport — a surface the ingestion never opens"
    )
    assert "--store-only" in block, (
        "the ingestion's healthcheck must measure the store, the only thing it actually depends on"
    )


def test_the_deploy_path_reaches_the_remote_script() -> None:
    """The remote script must RECEIVE the deploy path — by one of two ways.

    Written after three deploys died on the same line with every secret set:

        bash: line 3: IKIGAI_DEPLOY_PATH: the deploy path is not set

    `appleboy/ssh-action` forwards NAMES from `envs` and takes the values from
    the step's `env:`. The old step used `envs: IKIGAI_DEPLOY_PATH=${{ … }}`,
    which forwards nothing, so the guard fired before anything was deployed.
    The log made it worse by showing `IKIGAI_DEPLOY_PATH=***`, which reads like
    the value arrived — GitHub masks secrets.

    There are two ways that work, and the guard accepts both because the
    choice belongs to the workflow:

    (a) `envs` lists NAMES and every name is declared in `env:`;
    (b) the value is interpolated into `script:` with `${{ }}`, so Actions
        substitutes it on the runner and there is no forwarding to get wrong.

    What it rejects is the third form — `KEY=VALUE` inside `envs` — for
    `IKIGAI_DEPLOY_PATH`, and any name listed without a value.
    """
    import yaml

    document = yaml.safe_load(_deploy_workflow())
    steps = [
        step for job in (document.get("jobs") or {}).values() for step in (job.get("steps") or [])
    ]
    ssh = [step for step in steps if step.get("name") == "Deploy over SSH"]
    assert ssh, "the deploy step is not in the deploy workflow"

    step = ssh[0]
    script = _remote_script()
    envs = str((step.get("with") or {}).get("envs") or "")
    names = [name.strip() for name in envs.split(",") if name.strip()]

    offenders = [name for name in names if "=" in name]
    assert not offenders, (
        f"envs contains 'KEY=VALUE' ({offenders}). The action forwards names only, "
        "so these arrive empty on the remote and the deploy dies at its first guard"
    )

    declared = set((step.get("env") or {}).keys())
    forwarded = bool(names) and all(name in declared for name in names)
    interpolated = "secrets.IKIGAI_DEPLOY_PATH" in script

    assert forwarded or interpolated, (
        "the deploy path reaches the remote script by neither mechanism: "
        f"envs={names!r} (declared: {sorted(declared)}) and the script does not "
        "interpolate secrets.IKIGAI_DEPLOY_PATH"
    )


def test_the_deploy_runs_compose_from_the_directory_that_holds_it() -> None:
    """`docker compose` with no `-f` looks for a compose file in the CURRENT
    directory, and the repository root has none: the compose file is
    `deploy/compose.yml`.

    A deploy that runs it from the root deploys NOTHING, and says so in a way
    that has nothing to do with the secrets: "no configuration file provided".
    """
    workflow = _deploy_workflow()
    assert "cd deploy" in workflow, (
        "the deploy runs 'docker compose' from the repository root, where there is no compose file"
    )


def test_the_deploy_pulls_the_tag_the_pipeline_pushed() -> None:
    """The publisher and the deployer must NAME the image the same way.

    The metadata action pushes `sha-<commit>`; the deploy pulls
    `:<commit>`. Both look right and neither is wrong on its own — and the
    deploy stops on a manifest that does not exist.
    """
    workflow = _deploy_workflow()
    assert "type=sha,format=long" in workflow, (
        "the published tag no longer follows the scheme the deploy looks for"
    )
    assert ":sha-${{ github.sha }}" in workflow, (
        "the deploy no longer pulls the tag the pipeline pushes"
    )


def test_the_deploy_publishes_every_image_the_compose_names() -> None:
    """`docker compose pull` pulls EVERY image the compose names.

    The compose has two images — the canonical service and the agent — and
    the agent's image is not in the canonical service's build (ADR-037 D7).
    A pipeline that publishes only the first one leaves the deploy with an
    image that cannot be pulled.
    """
    workflow = _deploy_workflow()
    assert "deploy/Dockerfile" in workflow, "the canonical image is not published"
    assert "deploy/harness/Dockerfile" in workflow, (
        "the agent's image is not published, and the deploy pulls every image the compose names"
    )


def test_the_container_names_the_agent_directory_the_agent_reads() -> None:
    """The agent reads its directory from `PI_CODING_AGENT_DIR` — measured.

    The image used to declare `PI_AGENT_DIR`, which the agent does NOT read.
    The two only coincided because HOME was /root and the default is
    `~/.pi/agent`, so the container worked BY LUCK: an operator who moved
    `PI_AGENT_DIR` moved the provider catalogue away from the agent, and
    every routine then failed with "Unknown provider" — a container that is
    healthy, answers, and cannot run a single routine.

    The name is the guard. A container that names the directory with the
    variable the agent reads cannot drift from it.
    """
    dockerfile = (REPO_ROOT / "deploy" / "harness" / "Dockerfile").read_text(encoding="utf-8")
    assert "PI_CODING_AGENT_DIR=" in dockerfile, (
        "the image does not name the agent's directory with the variable the agent reads"
    )
    assert "PI_AGENT_DIR=" not in dockerfile, (
        "the image declares PI_AGENT_DIR, which the agent does not read — the provider "
        "catalogue would land where the agent never looks"
    )

    entrypoint = (REPO_ROOT / "deploy" / "harness" / "entrypoint.sh").read_text(encoding="utf-8")
    assert "PI_CODING_AGENT_DIR" in entrypoint, (
        "the boot does not write the provider catalogue where the agent reads it"
    )


def test_the_pipeline_publishes_only_tags_that_name_the_commit() -> None:
    """A floating tag is a second truth about what a build is.

    The metadata action published `latest` on the default branch beside
    `sha-<commit>`. Nothing consumed it — the deploy pulls the sha tag by
    name — and the registry therefore held two answers to "what is the
    current build": the commit CI tested, and "the newest main", which is
    something else the moment `main` moves. Measured on the box: the running
    containers were on `sha-77ebb161…` while `latest` was three commits
    behind, and a human pulling `latest` by habit would have deployed
    older code than the one the deploy had just verified.

    The rule is not "no `latest` by name" — it is "every published tag
    names the commit". A branch tag (`type=ref`) floats in exactly the same
    way, so the guard reads the metadata steps and requires every tag they
    publish to be a sha.
    """
    document = yaml.safe_load(_deploy_workflow())
    steps = [
        step for job in (document.get("jobs") or {}).values() for step in (job.get("steps") or [])
    ]
    metadata = [step for step in steps if "metadata-action" in str(step.get("uses") or "")]
    assert metadata, "the pipeline publishes no image at all"

    for step in metadata:
        tags = str((step.get("with") or {}).get("tags") or "")
        published = [line.strip() for line in tags.splitlines() if line.strip()]
        assert published, "a metadata step publishes no tag"
        for tag in published:
            assert tag.startswith("type=sha"), (
                f"the pipeline publishes the tag {tag!r}, which does not name the "
                "commit: it floats, and the registry then holds two truths about "
                "what the current build is"
            )


def test_the_compose_never_falls_back_to_a_tag_that_can_float() -> None:
    """The compose's default image must be a LOCAL name.

    The default was the repository's own registry path with a `latest` tag,
    so a stack started without `IKIGAI_IMAGE` ran whatever the registry
    held at that moment. The variable that names the tag is the only thing
    that pins a deployment, and the default quietly removed it.

    The default is now `ikigai:local`: a name with no registry in it, which
    a fresh clone builds for itself and which nothing can pull by accident.
    The guard therefore checks two things — no `:latest` anywhere, and no
    registry path in the fallback — because a default that names a registry
    is a default that can be pulled from somewhere else than the deploy.
    """
    services = _compose_services()
    for name, service in services.items():
        image = str(service.get("image") or "")
        assert ":latest" not in image, (
            f"the {name} service names a floating tag: {image!r}. The deploy "
            "pulls a tag that names the commit, and the fallback must not "
            "contradict it"
        )

        fallback = re.search(r"\$\{IKIGAI(?:_HARNESS)?_IMAGE:-([^}]+)\}", image)
        if fallback is None:
            continue
        default = fallback.group(1)
        assert "/" not in default, (
            f"the {name} service falls back to a REGISTRY image ({default!r}): "
            "a default that names a registry can be pulled from somewhere else "
            "than the deploy that tested it"
        )


# ─── the deploy's three arms ────────────────────────────────────────────────
#
# Six deploys ran red with every secret set, and each failure named something
# that was not the cause. The fix is in the workflow; this is the guard,
# because a pipeline that has failed six times in a row is a pipeline whose
# shape has to be held by something stronger than a comment.


def _deploy_step() -> dict[str, Any]:
    """The one step that ships to the box, read as data instead of as text."""
    workflow = yaml.safe_load(_deploy_workflow())
    steps = workflow["jobs"]["deploy"]["steps"]
    step = next(
        (candidate for candidate in steps if candidate.get("name") == "Deploy over SSH"),
        None,
    )
    assert step is not None, "the deploy step is gone"
    return step


def _remote_script() -> str:
    """The script the remote receives, wherever it is carried.

    The transport changed twice: an action's `with.script`, and now a heredoc
    in a `run:` block. The guard follows the script, not the transport — the
    assertions below are about WHAT the remote runs, and they must not have
    to be rewritten every time the way of sending it changes.
    """
    step = _deploy_step()
    with_script = str((step.get("with") or {}).get("script") or "")
    if with_script:
        return with_script
    match = re.search(
        r"<<'DEPLOY_SCRIPT'\n(.*?)\nDEPLOY_SCRIPT\n", str(step.get("run") or ""), re.DOTALL
    )
    assert match is not None, (
        "the deploy carries no remote script — neither in the step's input nor "
        "in a heredoc, so the box would run nothing"
    )
    return match.group(1)


def _deploy_script() -> str:
    return _remote_script()


def _script_commands() -> list[str]:
    """The script's EXECUTABLE lines.

    The comments name the failures ("`docker compose pull` is NOT used"), so a
    plain substring search over the whole script reads the explanation as the
    defect.
    """
    return [line for line in _deploy_script().splitlines() if not line.lstrip().startswith("#")]


def test_the_deploy_carries_its_values_in_the_script_and_not_through_envs() -> None:
    """`envs:` delivered NONE of the values to the remote script.

    Measured twice: the step above ("The deploy is configured") read the same
    secrets and passed, the SSH connection succeeded, and the remote died on
    `bash: line 3: IKIGAI_DEPLOY_PATH: the deploy path is not set`.

    The values are assigned in the script instead, with the form Actions
    substitutes on the RUNNER before the script is sent — so there is no
    forwarding left to get wrong.
    """
    deploy = _deploy_step()
    assert "envs" not in (deploy.get("with") or {}), (
        "the deploy carries its values through `envs:` again — that is the arm "
        "that delivered nothing to the remote, twice, with every secret set"
    )

    script = _deploy_script()
    for name in ("IKIGAI_DEPLOY_PATH", "IKIGAI_IMAGE", "IKIGAI_HARNESS_IMAGE"):
        assignment = script.find(f"{name}='")
        guard = script.find(f': "${{{name}:?')
        assert assignment != -1, f"the deploy never assigns {name} to a value"
        assert guard != -1, f"the deploy never asserts that {name} is set"
        assert assignment < guard, (
            f"{name} is asserted before it is assigned, so the guard reads whatever "
            "the remote shell happened to have"
        )

    # The ceiling on the remote command. An ssh action had `command_timeout`;
    # the plain ssh does not, so the ceiling is the runner's own job timeout
    # and the script's `--wait` has to fit inside it.
    assert "--wait-timeout 240" in script, (
        "the remote script no longer bounds its own wait for the services"
    )


def test_the_deploy_repairs_the_clone_refspec_before_it_fetches() -> None:
    """A clone with a NARROW refspec never sees `main`.

    The box was configured with `+refs/heads/feat/harness-container:...`, so
    `git fetch --all` brought that one branch, `checkout main` landed on a
    stale local branch, and `pull --ff-only` refused. The deploy had every
    secret and a working connection, and still could not reach the commit it
    had just built: it would have run one commit while reporting another.

    The repair is in the pipeline, so a clone configured by hand cannot make
    the deploy lie again.
    """
    commands = "\n".join(_script_commands())
    refspec = "+refs/heads/*:refs/remotes/origin/*"
    assert refspec in commands, (
        "the deploy no longer widens the clone's refspec, so a narrow clone "
        "fetches every branch except the one it deploys"
    )
    assert commands.index(refspec) < commands.index("git fetch"), (
        "the refspec is repaired AFTER the fetch, which is one deploy too late"
    )
    assert "checkout -q -B main origin/main" in commands, (
        "the deploy checks out a LOCAL main, which may be the stale branch the "
        "narrow refspec was hiding"
    )
    assert "reset --hard origin/main" in commands, (
        "the deploy does not reset the tree it is about to run, so drift on the "
        "box changes what gets deployed"
    )


def test_the_deploy_pulls_the_two_images_by_name_and_retries() -> None:
    """`docker compose pull` HEADs every manifest, and that is what GHCR denies.

    Measured twice: `denied` on the manifest while the same tag came down by
    name minutes later. The images are named explicitly instead, a tag already
    on the host is not pulled at all, and a refused pull is retried with a
    growing wait before the deploy gives up.
    """
    commands = "\n".join(_script_commands())
    assert "docker compose pull" not in commands, (
        "the deploy runs `docker compose pull` again: it HEADs every manifest, "
        "and that is the request the registry refuses"
    )
    assert 'docker pull "$image"' in commands, "the deploy pulls no image by name"
    assert "docker image inspect" in commands, (
        "the deploy pulls a tag that is already on the host, so a redeploy of the "
        "same commit can fail on the registry for no reason"
    )
    assert "attempt" in commands, (
        "a refused pull is no longer retried, so one flaky anonymous pull ends the deploy"
    )
    assert "-ge 5" in commands, (
        "the pull retry has no ceiling, so a registry that keeps refusing hangs the deploy"
    )

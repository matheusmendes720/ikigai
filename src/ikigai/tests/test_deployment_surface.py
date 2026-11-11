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


# ─── the readiness probe measures the provider the routines use ──────────────
#
# Measured on the box (2026-11-09): the probe spawned the agent WITHOUT the
# provider flags, so pi fell back to its own default — the SECOND provider in
# the catalogue — and the harness reported `provider: deepseek` while every
# routine ran on `harness`/MiniMax. The container's HEALTHCHECK reads that
# probe, so the container was healthy on the strength of the provider of
# reserve, and the healthcheck said nothing about the primary.


def _js_function(source: str, name: str) -> str:
    """The body of one top-level JS function, by its closing brace at column 0.

    The functions of the harness are written with the closing brace of the
    function at column 0 and the nested braces indented, so the first line
    that is exactly `}` ends the function.
    """
    marker = f"function {name}("
    assert marker in source, f"the harness has no function {name}"
    start = source.index(marker)
    end = source.index("\n}\n", start)
    return source[start:end]


def _js_code(source: str) -> str:
    """The code WITHOUT the comments.

    A comment that names a thing reads as that thing to a substring search —
    the same trap the deploy script has with `docker compose pull`. The
    comment in `acquire` says "`providerArgs()`", and a guard that reads the
    comment as the code would call the fixed code broken.
    """
    out: list[str] = []
    in_block = False
    for line in source.splitlines():
        stripped = line.strip()
        if in_block:
            if "*/" in stripped:
                in_block = False
            continue
        if stripped.startswith("/*"):
            if "*/" not in stripped:
                in_block = True
            continue
        if stripped.startswith("//"):
            continue
        out.append(line)
    return "\n".join(out)


def _harness_server() -> str:
    return (REPO_ROOT / "deploy" / "harness" / "server.mjs").read_text(encoding="utf-8")


def test_the_readiness_probe_measures_the_provider_the_routines_use() -> None:
    """The probe and the routines must agree on WHICH provider the agent uses.

    The guard is the SHARED HELPER: one place owns the provider flags, and
    both callers use it. A probe that carries its own list can drift from the
    routines again — and it did, silently: nothing failed, the container said
    "healthy", and the model it named was not the one any routine would use.

    Falsifiable by construction: against the old server.mjs the first
    assertion fails, because the helper did not exist.
    """
    server = _harness_server()
    code = _js_code(server)

    helper = _js_function(code, "providerArgs")
    assert '"--model"' in helper, (
        "the shared helper does not carry the model flag, so the probe and the "
        "routines can still name different models"
    )
    assert '"--provider"' in helper, (
        "the shared helper does not carry the provider flag, so the probe and "
        "the routines can still name different providers"
    )
    assert "registry.default" in helper, (
        "the shared helper does not resolve the DEFAULT RUNTIME of the routing "
        "table, so the probe measures the environment while the routines "
        "measure the table — the same drift, one level up"
    )

    assert "providerArgs(" in _js_function(code, "piArgs"), (
        "the routines do not use the shared provider flags — the two paths can "
        "drift apart again"
    )
    acquire = _js_function(code, "acquire")
    assert "runtime?.provider" in acquire, (
        "the session pool does not hand the ROUTED runtime's provider to the "
        "shared chain — the routine and the probe resolve it differently"
    )
    assert "|| PI_PROVIDER" not in acquire, (
        "the session pool short-circuits the resolution with the environment "
        "before the routing table is consulted"
    )
    assert "providerArgs(" in _js_function(code, "ready"), (
        "the readiness probe spawns the agent without the provider flags: it "
        "measures pi's own default (the fallback) instead of the provider the "
        "routines use, and the healthcheck inherits the lie"
    )


def test_the_readiness_probe_does_not_spend_tokens() -> None:
    """The probe asks the agent for its STATE — it does not make it answer.

    The owner's decision (2026-11-09): the probe certifies the primary, the
    same way the routines are configured, and it must not cost a token per
    check. So it asks for the state and stops there.
    """
    ready = _js_function(_harness_server(), "ready")
    assert "getState()" in ready, "the probe no longer reads the agent's state"
    assert "promptAndWait" not in ready, (
        "the probe now makes the model answer — that spends tokens on every "
        "healthcheck, which is a cost decision and not a technical one"
    )


# ─── the ceilings agree with each other ─────────────────────────────────────
#
# Measured on the box (2026-11-09): the monthly review died at 302 s with the
# container UP (58 min of uptime, no deploy) and the agent still writing. The
# caller saw "fetch failed" — and the agent kept working, so the work landed in
# the store with nobody told.
#
# The isolation (three cases, the same handler, the same 310 s delay, on the
# box's own Node 24):
#
#   A · server with the default `requestTimeout` + a client with no timeout
#       -> OK at 310.1 s      (the server's default does NOT cut the response)
#   B · server with `requestTimeout = 0`       + a client with no timeout
#       -> OK at 310.1 s
#   C · server with `requestTimeout = 0`       + `fetch` (undici's default
#       headersTimeout is 300 s)
#       -> FAILED at 301.0 s, `UND_ERR_HEADERS_TIMEOUT`
#
# So the 300 s that killed the run came from the CLIENT, not from the server —
# and the client's ceiling was never the product's to set. What the product
# DOES own is the order of its own ceilings, and that order was wrong: the
# run's ceiling (10 min) was SHORTER than the question's (15 min), so a
# routine that asked the owner could never finish, and the bot's socket (630 s)
# was 30 s from the run's ceiling.


def test_the_server_patience_outlives_the_run() -> None:
    """The server must not be able to cut a run that its own ceiling allows.

    Node's `requestTimeout` (300 s by default) governs the RECEIVING of the
    request, not the sending of the response — the isolation above shows the
    response arriving at 310 s against a server with the default. So this is
    not a claim about what killed the run; it is a claim about the order of the
    product's own ceilings: the server declares a patience derived from the
    run's, so no future change to Node's defaults can cut a run that the
    harness itself allowed.

    Falsifiable by construction: against the old server.mjs the first
    assertion fails, because the server never declared its patience.
    """
    code = _js_code(_harness_server())
    assert "server.requestTimeout" in code, (
        "the harness does not declare the server's patience — Node's default "
        "is 300 s, and nothing ties the server to the run it is allowed to take"
    )
    assert "RUN_TIMEOUT_MS + REQUEST_MARGIN_MS" in code, (
        "the server's patience is not derived from the run's ceiling, so the "
        "two can drift apart again — and the server is the one that dies"
    )


def test_a_run_outlives_the_question_it_asks() -> None:
    """A routine that asks the owner waits for the answer — so the run's
    ceiling has to be LONGER than the question's.

    The agent is suspended on the question (ADR-041, `owner.mjs`): the call
    blocks until the owner answers or the question's deadline passes. A run
    whose ceiling is shorter than the question's dies with the owner still
    reading, and no routine that asks anything can ever finish.

    Measured on the box (2026-11-09): the run's ceiling was 10 min and the
    question's 15 min — no routine that asked a question could complete.
    """
    code = _js_code(_harness_server())
    run_line = next(
        (line for line in code.splitlines() if "const RUN_TIMEOUT_MS" in line),
        "",
    )
    assert run_line, "the harness has no ceiling of one routine"
    assert "OWNER_TIMEOUT_MS" in run_line, (
        "the routine's ceiling is not derived from the question's ceiling, so a "
        "routine that asks the owner can die while the owner is still reading"
    )


def test_the_declared_ceilings_agree_with_each_other() -> None:
    """The three ceilings — the question's, the run's, the bot's — must agree.

    They live in three places (the harness's code, the compose, the bot's
    client), and nothing in the code connected them: the compose declared a
    10-minute run, a 15-minute question and a 10-minute bot, while Node
    killed the socket at 5. A routine that asked the owner could not finish
    on any of the three paths.

    The order is the contract: the bot's socket waits longer than the
    harness's socket, which waits longer than the run, which waits longer
    than the question.
    """
    services = _compose_services()
    harness_env = (services.get("harness") or {}).get("environment") or {}
    bot_env = (services.get("bot") or {}).get("environment") or {}

    def declared(raw: Any) -> int:
        """The default of a compose value: `${NAME:-1200000}` -> 1200000."""
        text = str(raw or "")
        assert ":-" in text, f"{text!r} declares no default"
        return int(text.split(":-", 1)[1].rstrip("}"))

    run_ms = declared(harness_env.get("HARNESS_TIMEOUT_MS"))
    owner_ms = declared(harness_env.get("HARNESS_OWNER_TIMEOUT_MS"))
    bot_s = declared(bot_env.get("IKIGAI_HARNESS_TIMEOUT_S"))

    assert run_ms > owner_ms, (
        f"the run's ceiling ({run_ms} ms) is not longer than the question's "
        f"({owner_ms} ms): a routine that asks the owner dies while the owner "
        "is still reading"
    )
    assert run_ms >= owner_ms + 10 * 60 * 1000, (
        f"the run's ceiling ({run_ms} ms) leaves the agent less than 10 minutes "
        f"to work after the question expires ({owner_ms} ms + 10 min): "
        "measured on the box (2026-11-09), a 5-minute margin was not enough — "
        "the monthly review's questions expired at 21:41:53Z and the run was "
        "cut at 21:47:21Z, with the agent still working"
    )
    assert bot_s * 1000 >= run_ms, (
        f"the bot's ceiling ({bot_s} s) is shorter than the harness's run "
        f"({run_ms} ms): the bot gives up before the harness answers, and the "
        "owner is told the routine failed while the agent is still working"
    )


def test_a_refused_request_cannot_release_a_running_turn() -> None:
    """A refusal must not release the turn that is running.

    Measured on the box (2026-11-09): the quarterly-plan's request was REFUSED
    — *"Agent is already processing"*, a correct refusal — and its `finally`
    put `busy = false` on the monthly-review's turn, which was still running.
    The reaper then saw an idle session and **killed the agent mid-write**, at
    20:41:59Z; the agent was writing at 20:41:53Z. The routine's work was
    lost, and nobody was told.

    So the session COUNTS its turns in flight, and everything that might
    release a session — the reaper, the eviction — looks at the count.

    Falsifiable by construction: against the old server.mjs the first
    assertion fails, because the flag was there instead of the count.
    """
    code = _js_code(_harness_server())

    routine = _js_function(code, "runRoutine")
    assert "entry.busy = false" not in routine, (
        "a refused request still releases the mark of the turn that is running"
    )
    assert "entry.turns" in routine, (
        "the session does not count its turns in flight, so a refusal can "
        "release a live one"
    )

    reap = _js_function(code, "reapIdle")
    assert "turns" in reap, (
        "the reaper does not look at the turns in flight — it can kill a live "
        "agent that is in the middle of a routine"
    )

    acquire = _js_function(code, "acquire")
    assert "s.turns > 0" in acquire, (
        "the eviction does not skip the sessions with a turn in flight"
    )



# ---------------------------------------------------------------------------
# The write-back (ADR-043)
# ---------------------------------------------------------------------------


def test_the_write_back_is_deployed_as_a_service_of_its_own() -> None:
    """Writing is not a request: it has its own cadence, and its own mounts.

    A writer that shared the ingestion's container would share its mounts —
    and the ingestion's mounts are the owner's prose, read-only on purpose.
    """
    services = _compose_services()
    assert "write" in services, "the write-back is not deployed"

    command = " ".join(str(part) for part in (services["write"].get("command") or []))
    assert "src.services.vault_write" in command, (
        f"the write container runs something else: {command!r}"
    )


def test_the_owners_trees_are_read_only_in_every_container() -> None:
    """PASS 2: the `vault/` and the `/app/zonas` stay read-only, everywhere.

    The owner edits those two trees by hand. A machine that can write there
    is a machine that can eat the owner's prose, and the read-only mount is
    the only thing that says no.
    """
    services = _compose_services()
    for name, service in services.items():
        for volume in service.get("volumes") or []:
            text = str(volume)
            if not text.endswith(":rw"):
                continue
            target = text.split(":")[-2]
            assert target not in ("/app/vault", "/app/zonas"), (
                f"the {name} container mounts {target} read-write: the owner's "
                "prose is not a machine's to overwrite"
            )


def test_the_write_back_writes_in_a_tree_of_its_own() -> None:
    """PASS 1: the tree is not the clone the deploy discards.

    The deploy does `git reset --hard origin/main` over the repository's
    `vault/`: a file written there is a file that does not exist after the
    next deploy, and a commit made there is a commit the next deploy undoes.
    """
    services = _compose_services()
    writable = [
        str(volume)
        for volume in (services["write"].get("volumes") or [])
        if str(volume).endswith(":rw")
    ]
    assert len(writable) == 1, (
        f"the write-back has {len(writable)} writable mounts: {writable}"
    )
    assert "vault-escrita" in writable[0], (
        f"the write-back does not write in its own tree: {writable[0]!r}"
    )
    assert "IKIGAI_VAULT_PATH" not in writable[0], (
        "the write-back writes in the repository's own vault: the deploy "
        "discards that directory with `git reset --hard`"
    )


def test_the_write_back_is_told_where_to_write() -> None:
    """The tree comes from the environment, as the ingestion's does.

    Without it the writer has nowhere to write, and it writes nothing —
    which is the right answer for a writer with no tree, but not a
    deployment.
    """
    environment = _compose_services()["write"].get("environment") or {}
    roots = str(environment.get("IKIGAI_VAULT_WRITE_ROOTS") or "")
    assert roots, "the write-back is not told where to write"
    assert "vault-escrita" in roots, f"the write-back writes in {roots!r}"


def test_the_write_back_never_pushes() -> None:
    """PASS 9: no push, and no credential to push with.

    The tree is delivered by the Syncthing, which needs no token and no
    branch. A writer that pushed would make the VPS a writer of the
    repository — a credential the deploy's token does not have, and one it
    must not be given.
    """
    write = _compose_services()["write"]
    environment = write.get("environment") or {}
    for name in environment:
        upper = name.upper()
        assert "TOKEN" not in upper and "GITHUB" not in upper, (
            f"the write-back holds {name}: a credential to push with"
        )

    command = " ".join(str(part) for part in (write.get("command") or []))
    assert "push" not in command, f"the write container pushes: {command!r}"

    source = (REPO_ROOT / "src" / "services" / "vault_write.py").read_text(encoding="utf-8")
    assert '"push"' not in source, "the writer calls a push"
    assert "git push" not in source, "the writer calls a push"


def test_the_ingestion_reads_the_tree_the_write_back_writes() -> None:
    """The cycle closes because the ingestion reads what the writer wrote.

    The write-back's tree is mounted read-only into the ingestion, and the
    `escrita` layout is named in the deployment. Without the second half the
    files the writer produces would sit on the volume and never come back to
    the store — and the owner's hand on them would be lost.
    """
    sync = _compose_services()["sync"]
    volumes = " ".join(str(volume) for volume in (sync.get("volumes") or []))
    assert "/app/vault-escrita:ro" in volumes, (
        "the ingestion does not read the tree the write-back writes: the "
        "cycle would not close"
    )
    environment = sync.get("environment") or {}
    assert "=escrita" in str(environment.get("IKIGAI_VAULT_ROOTS") or ""), (
        "the ingestion does not read the write-back's tree with the `escrita` layout"
    )


def test_the_write_back_runs_as_the_user_that_owns_the_tree() -> None:
    """The writer is not root, and the reason is the Syncthing.

    The Syncthing applies an incoming change by writing a temporary file
    INSIDE the directory and renaming it over the target — so it needs to be
    able to write in the directories the writer creates. A writer that runs as
    root creates directories the Syncthing cannot write in, and the owner's
    hand on those files stops coming back to the store. Silently: the file is
    there, it looks right, and it never changes again.
    """
    write = _compose_services()["write"]
    user = str(write.get("user") or "")

    assert user, "the write-back declares no user: it would run as root"
    assert not user.startswith("0:") and user != "root", (
        f"the write-back runs as {user!r}: the Syncthing cannot update what it creates"
    )

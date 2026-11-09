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

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

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

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
COMPOSE = REPO_ROOT / "deploy" / "compose.yml"
MIGRATIONS = REPO_ROOT / "src" / "contracts" / "migrations"


def _compose() -> str:
    return COMPOSE.read_text(encoding="utf-8")


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

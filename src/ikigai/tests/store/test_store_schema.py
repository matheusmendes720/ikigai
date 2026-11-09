"""The contract-versus-SQL drift test (SPEC-02 T2.5).

These tests read the migration files as text and compare them against the
Pydantic contracts. They need no database and must always run: the schema is
the part of the system that everything else assumes, so a drift here has to be
visible in CI rather than at the first deploy.

The regex comparison derives one side from the contract. A copy of the pattern
inside the test would pass forever, which is exactly the failure this file
exists to prevent.
"""

from __future__ import annotations

import re
from pathlib import Path

from src.contracts.common import _UEID_PATTERN
from src.contracts.dom import ArtifactKind
from src.contracts.store import EMBEDDING_DIM, KIND_TABLES, RLS_CLIENT_CLAIM

MIGRATIONS = Path(__file__).resolve().parents[3] / "contracts" / "migrations"

_NON_KIND_TABLES = {"artifact_revisions", "artifact_relations"}


def _read(name: str) -> str:
    return (MIGRATIONS / name).read_text(encoding="utf-8")


def _table_block(sql: str, table: str) -> str:
    match = re.search(rf"create table ikig\.{table} \((.*?)\n\);", sql, re.DOTALL)
    assert match is not None, f"table ikig.{table} not found in the schema"
    return match.group(1)


def test_migration_files_exist() -> None:
    for name in (
        "0001_init.sql",
        "0002_indexes.sql",
        "0003_rls.sql",
        "0004_artifact_events.sql",
        "0001_init.down.sql",
        "0002_indexes.down.sql",
        "0003_rls.down.sql",
        "0004_artifact_events.down.sql",
    ):
        path = MIGRATIONS / name
        assert path.exists(), f"{name} is missing"
        assert path.read_text(encoding="utf-8").strip(), f"{name} is empty"


def test_every_migration_has_a_reverse_script() -> None:
    """A migration without a reverse script cannot be rolled back.

    The runner refuses to roll back the last applied migration when its
    reverse script is missing — and it refuses at rollback time, on a live
    database, with the data at stake. The gap between "applied" and "rolled
    back" is exactly where a schema stops matching its contract, so the
    script has to exist before the migration is applied, not after.
    """
    for path in sorted(MIGRATIONS.glob("*.sql")):
        if path.name.endswith(".down.sql"):
            continue
        reverse = path.with_name(path.name.replace(".sql", ".down.sql"))
        assert reverse.exists(), f"{path.name} has no reverse script ({reverse.name})"
        assert reverse.read_text(encoding="utf-8").strip(), f"{reverse.name} is empty"


def _statements(sql: str) -> str:
    """The statements of a migration, without its commentary.

    A comment that quotes the expression it is about ("the index calls
    to_tsvector('portuguese', …)") is documentation, not a dependency — and a
    test that reads it as one makes the documentation load-bearing.
    """
    return "\n".join(line for line in sql.splitlines() if not line.lstrip().startswith("--"))


def test_the_full_text_configuration_precedes_the_index_that_needs_it() -> None:
    """A GIN index over `to_tsvector('portuguese', …)` needs that configuration.

    Postgres creates only `english` and `simple` on a fresh database; every
    other language has to be created explicitly, by a migration that runs
    FIRST. When it does not, the migration that builds the index aborts and
    the schema is never built at all — a failure that only shows on a real
    database, after the whole store was supposed to exist.
    """
    migrations = sorted(
        (p for p in MIGRATIONS.glob("*.sql") if not p.name.endswith(".down.sql")),
        key=lambda p: p.name,
    )

    created: dict[str, int] = {}
    for index, path in enumerate(migrations):
        sql = _statements(path.read_text(encoding="utf-8"))
        for config in re.findall(r"create text search configuration (\w+)", sql):
            created.setdefault(config, index)

    for index, path in enumerate(migrations):
        sql = _statements(path.read_text(encoding="utf-8"))
        for config in set(re.findall(r"to_tsvector\('([^']+)'", sql)):
            assert config in created, (
                f"{path.name} indexes on the '{config}' configuration and no "
                "migration creates it — Postgres ships only 'english' and "
                "'simple', so this migration would abort"
            )
            assert created[config] < index, (
                f"{path.name} uses the '{config}' configuration but the "
                "migration that creates it runs after it"
            )


def test_every_kind_has_a_column_check() -> None:
    sql = _read("0001_init.sql")
    match = re.search(r"constraint artifacts_kind_known check \(kind in \(([^)]*)\)\)", sql)
    assert match is not None, "the artifacts_kind_known check is missing"
    declared = set(re.findall(r"'([^']+)'", match.group(1)))
    expected = {kind.value for kind in ArtifactKind}
    assert declared == expected, f"kinds in the SQL check differ: {declared ^ expected}"


def test_uid_check_matches_contract_pattern() -> None:
    sql = _read("0001_init.sql")
    match = re.search(r"constraint artifacts_uid_format check \(uid ~ '([^']+)'\)", sql)
    assert match is not None, "the artifacts_uid_format check is missing"
    sql_pattern = match.group(1)
    contract_pattern = _UEID_PATTERN.pattern

    assert _alternatives(sql_pattern) == _alternatives(contract_pattern), (
        "the UID pattern in the SQL no longer matches the contract pattern"
    )


def _alternatives(pattern: str) -> list[str]:
    """The top-level alternatives of a `^(?:a|b|c)$` pattern, whitespace removed."""
    body = pattern.strip()
    body = re.sub(r"^\^\(\?:", "", body)
    body = re.sub(r"\)\$$", "", body)
    return [part.replace(" ", "") for part in body.split("|")]


def test_extension_tables_cover_typed_kinds() -> None:
    sql = _read("0001_init.sql")
    tables = set(re.findall(r"create table ikig\.(artifact_\w+)", sql))
    registered = {name for name in KIND_TABLES.values() if name}
    unregistered = tables - registered - _NON_KIND_TABLES
    assert not unregistered, f"tables with no kind behind them: {unregistered}"
    for kind, table in KIND_TABLES.items():
        if table is None:
            continue
        assert f"create table ikig.{table} (" in sql, f"{kind} declares {table}, absent from the SQL"


def test_no_physical_delete_path() -> None:
    sql = _read("0001_init.sql")
    revisions = _table_block(sql, "artifact_revisions")
    assert "references ikig.artifacts" not in revisions, (
        "the revision history must not be tied to the artifact's lifetime"
    )
    assert "on delete cascade" not in revisions
    artifacts = _table_block(sql, "artifacts")
    assert "deleted_at" in artifacts, "soft delete needs a deleted_at column"
    assert "on delete cascade" not in artifacts


def test_revision_starts_at_one() -> None:
    sql = _read("0001_init.sql")
    artifacts = _table_block(sql, "artifacts")
    assert "revision" in artifacts
    assert re.search(r"revision\s+integer\s+not null default 1", artifacts)
    assert "revision >= 1" in artifacts


def test_artifacts_carry_the_client_column() -> None:
    """The RLS policies filter on client_id, so the column has to exist."""
    sql = _read("0001_init.sql")
    artifacts = _table_block(sql, "artifacts")
    assert "client_id" in artifacts


def test_embedding_dimension_matches_contract() -> None:
    sql = _read("0002_indexes.sql")
    match = re.search(r"embedding vector\((\d+)\)", sql)
    assert match is not None, "no vector column found in the indexes migration"
    assert int(match.group(1)) == EMBEDDING_DIM


def test_every_rls_enabled_table_has_a_policy() -> None:
    rls = _read("0003_rls.sql")
    enabled = set(re.findall(r"alter table ikig\.(\w+) enable row level security", rls))
    assert enabled, "no table has row level security enabled"
    for table in enabled:
        assert f"on ikig.{table}" in rls, f"ikig.{table} has RLS enabled but no policy"


def test_rls_filters_on_the_client_claim() -> None:
    rls = _read("0003_rls.sql")
    # The name comes from the constant, not from a copy of it: a copy in
    # this test would pass forever, even after the policies and the service
    # started disagreeing about the same fact.
    assert RLS_CLIENT_CLAIM in rls, (
        f"the policies do not filter on {RLS_CLIENT_CLAIM!r} — the constant and "
        "the migration disagree about the same name"
    )
    assert "auth.uid()" not in rls, "the client is one person with several devices, not a user"


def test_the_provenance_column_is_in_the_schema() -> None:
    """The column that says where the prose came from has to exist.

    It carries the ZONE (the first segment of the path) and the FILE. Without
    it the store holds the content of a vault note and forgets the note.
    """
    sql = _statements(_read("0005_vault_path.sql"))
    assert re.search(r"alter table ikig\.artifacts add column vault_path text", sql), (
        "the migration does not add the vault_path column"
    )


def test_every_spine_field_is_read_by_the_repository() -> None:
    """The SELECT list and the spine must agree, and the spine is the side that is derived.

    A copy of the field list inside this test would pass forever, which is the
    failure this file exists to prevent. The list is read from the model.
    """
    from src.contracts.dom import Artifact
    from src.data.repository import _ARTIFACT_COLUMNS

    columns = {column.strip() for column in _ARTIFACT_COLUMNS.split(",")}
    missing = set(Artifact.model_fields) - columns
    assert not missing, f"the spine has fields the repository never reads: {sorted(missing)}"


def test_the_provenance_column_is_indexed_for_the_prefix_match() -> None:
    """The zone filter is a prefix match, so the index has to be a prefix index."""
    sql = _statements(_read("0005_vault_path.sql"))
    assert "text_pattern_ops" in sql, (
        "the zone filter is a LIKE prefix and a plain b-tree index does not serve it"
    )


def test_the_revision_history_records_when_the_revision_was_written() -> None:
    """What the row gives up on its dates, the history keeps.

    The row holds the dates the artifact states, because the model makes both
    of them required and the store cannot know better. The moment of the
    WRITE is not lost with them: it is the `created_at` of the revision the
    write appends, and it is the clock's.
    """
    revisions = _table_block(_read("0001_init.sql"), "artifact_revisions")
    assert re.search(r"created_at\s+timestamptz\s+not null default now\(\)", revisions), (
        "the revision history does not record when the revision was written"
    )

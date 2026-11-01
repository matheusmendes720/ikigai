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
from src.contracts.store import EMBEDDING_DIM, KIND_TABLES

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
        "0001_init.down.sql",
        "0002_indexes.down.sql",
        "0003_rls.down.sql",
    ):
        path = MIGRATIONS / name
        assert path.exists(), f"{name} is missing"
        assert path.read_text(encoding="utf-8").strip(), f"{name} is empty"


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
    assert "request.jwt.claim.client_id" in rls
    assert "auth.uid()" not in rls, "the client is one person with several devices, not a user"

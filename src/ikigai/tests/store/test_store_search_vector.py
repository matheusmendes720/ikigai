"""The search vector is a COLUMN, and the query reads the column.

Migration `0009_materialized_search_vector` moved the full-text expression
out of the query and into a generated column. The reason was measured, not
guessed:

* the GIN index was on the exact expression the query used, and when the
  planner picked it the query took **6 ms**;
* when the planner refused it, the query recomputed ``to_tsvector()`` — the
  Portuguese **stemmer** — over the whole body of every row it visited:
  **1 500 ms** for the query, and **20 069 ms** to stem 1 990 bodies once
  (against 60 ms for the titles alone);
* the planner refuses the index for COMMON terms, because it cannot estimate
  how many rows a computed expression matches, and ``ANALYZE`` does not fix
  that estimate.

So the query must read the COLUMN. If it goes back to the expression, the
store is slow again — and the failure is invisible: a green suite, a healthy
container, and a search that takes a second and a half.

These guards read the SQL and the repository as text. They need no database
and must always run.
"""

from __future__ import annotations

import re
from pathlib import Path

MIGRATIONS = Path(__file__).resolve().parents[3] / "contracts" / "migrations"
REPOSITORY = Path(__file__).resolve().parents[3] / "data" / "repository.py"

MIGRATION = "0009_materialized_search_vector.sql"


def _read(name: str) -> str:
    return (MIGRATIONS / name).read_text(encoding="utf-8")


def _statements(sql: str) -> str:
    """The statements of a migration, without its commentary.

    A comment that quotes the expression it is about is documentation, not a
    dependency — and a test that reads it as one makes the documentation
    load-bearing.
    """
    return "\n".join(line for line in sql.splitlines() if not line.lstrip().startswith("--"))


def test_the_migration_materializes_the_vector() -> None:
    """The column exists, and it is GENERATED — so it cannot drift.

    A column maintained by a trigger is a column that somebody can stop
    updating. A generated column is computed by the database on every write,
    and the only way for it to disagree with the body is for the write not
    to have happened.
    """
    sql = _statements(_read(MIGRATION))
    assert "add column search_vector tsvector" in sql, (
        "the migration does not add the search_vector column"
    )
    assert re.search(r"generated always as", sql, re.IGNORECASE), (
        "the search_vector column is not GENERATED — a column that somebody "
        "has to maintain is a column that ages in silence"
    )
    assert "stored" in sql.lower(), (
        "the search_vector column must be STORED: a virtual column would "
        "compute the stemmer at query time, which is the cost this migration exists to remove"
    )


def test_the_column_carries_the_same_expression_the_index_used() -> None:
    """The semantics must not change: same configuration, same stemming.

    The old index was on ``to_tsvector('portuguese', coalesce(title,'') ||
    ' ' || coalesce(body,''))``. A column that stemmed something else would
    answer a different question — and the difference would be a search that
    quietly finds less.
    """
    sql = _statements(_read(MIGRATION))
    assert "to_tsvector('portuguese'" in sql, (
        "the materialized column does not use the 'portuguese' configuration"
    )
    assert re.search(
        r"coalesce\(title,\s*''\)\s*\|\|\s*' '\s*\|\|\s*coalesce\(body,\s*''\)", sql
    ), (
        "the materialized column does not stem the title AND the body — a "
        "column that stems only one of them answers a different question"
    )


def test_the_index_is_on_the_column() -> None:
    """A GIN index over the COLUMN, not over the expression.

    This is the whole point of the migration: an index on a computed
    expression is the one the planner cannot estimate the use of.
    """
    sql = _statements(_read(MIGRATION))
    index = re.search(r"create index \w+\s+on ikig\.artifacts using gin \(([^)]*)\)", sql, re.I)
    assert index is not None, "the migration does not build a GIN index on the column"
    assert "search_vector" in index.group(1), (
        f"the GIN index is not on the column: {index.group(1)!r}"
    )
    assert "to_tsvector" not in index.group(1), (
        "the GIN index is still on the expression — that is the index the "
        "planner refuses for common terms"
    )


def test_the_old_expression_index_is_gone() -> None:
    """Two indexes over the same text cost write time and buy nothing.

    The expression index served the same query by the same path the column
    now serves. Leaving it means every write maintains two indexes, and the
    second one is the one the planner sometimes picks — and refuses.
    """
    sql = _statements(_read(MIGRATION))
    assert re.search(r"drop index if exists ikig\.ix_artifacts_body_fts", sql), (
        "the expression index is not dropped — the store maintains two "
        "indexes over the same prose, and the slow one is still there"
    )


def test_the_query_reads_the_column_and_not_the_expression() -> None:
    """The query is the other half of the fix, and it is the half that drifts.

    The migration can be perfect and the query can still ask for the
    expression: the plan is then the old plan, and the store is slow again
    with a green suite.
    """
    source = REPOSITORY.read_text(encoding="utf-8")

    # The predicate that the search builds, read from the code itself.
    predicates = re.findall(r'clauses\.append\(\s*"([^"]+)"', source)
    text_predicates = [p for p in predicates if "plainto_tsquery" in p]
    assert text_predicates, (
        "the repository no longer builds a full-text predicate — the search "
        "silently stopped matching text"
    )
    for predicate in text_predicates:
        assert "search_vector" in predicate, (
            f"the search still asks for the expression, not the column: {predicate!r}"
        )
        assert "to_tsvector" not in predicate, (
            f"the search still computes the stemmer at query time: {predicate!r}"
        )


def test_the_migration_has_a_reverse_script_that_restores_the_index() -> None:
    """The `down` restores the state the `up` found.

    The `up` drops the expression index, so the `down` has to bring it
    back: a rollback that leaves the schema without the index it had is a
    rollback that changes the design rather than reversing it.
    """
    reverse = MIGRATIONS / MIGRATION.replace(".sql", ".down.sql")
    assert reverse.exists(), f"{reverse.name} is missing"
    sql = _statements(reverse.read_text(encoding="utf-8"))
    assert "drop column if exists search_vector" in sql, (
        "the reverse script does not drop the column"
    )
    assert "ix_artifacts_body_fts" in sql, (
        "the reverse script does not restore the expression index the migration dropped"
    )

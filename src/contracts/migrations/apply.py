"""The migration runner for the store.

One runner, one lock, one ledger. Applying twice is a no-op, and a migration
that changed after it was applied is an error rather than a silent re-run —
re-running an altered migration is how a schema stops matching its contract.

Usage:
    python -m src.contracts.migrations.apply            # apply pending
    python -m src.contracts.migrations.apply status
    python -m src.contracts.migrations.apply down --yes # roll back the last one
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sys
from pathlib import Path

from ..store import STORE_DSN_ENV

MIGRATIONS_DIR = Path(__file__).parent
LOCK_KEY = "ikig_schema_migrations"

BOOTSTRAP_SQL = """
create schema if not exists ikig;
create table if not exists ikig.schema_migrations (
    name       text primary key,
    checksum   text        not null,
    applied_at timestamptz not null default now()
);
"""


class MigrationError(RuntimeError):
    """A migration could not be applied. Raised instead of a raw driver error."""


def _dsn() -> str:
    dsn = os.environ.get(STORE_DSN_ENV)
    if not dsn:
        raise MigrationError(
            f"{STORE_DSN_ENV} is not set. The store connection string comes from the "
            "environment; it is never stored in the repository."
        )
    return dsn


def _connect(dsn: str):  # noqa: ANN202 — psycopg is an optional runtime dependency
    try:
        import psycopg
    except ImportError as exc:
        raise MigrationError(
            'psycopg is required to apply migrations. '
            'Install it with: pip install "psycopg[binary]"'
        ) from exc
    return psycopg.connect(dsn)


def _migration_files() -> list[Path]:
    files = [p for p in MIGRATIONS_DIR.glob("*.sql") if not p.name.endswith(".down.sql")]
    return sorted(files, key=lambda p: p.name)


def _checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _applied(conn) -> dict[str, str]:  # noqa: ANN001 — psycopg connection
    rows = conn.execute("select name, checksum from ikig.schema_migrations").fetchall()
    return {name: checksum for name, checksum in rows}


def apply_pending(conn) -> list[str]:  # noqa: ANN001 — psycopg connection
    applied: list[str] = []
    recorded = _applied(conn)
    for path in _migration_files():
        checksum = _checksum(path)
        if path.name in recorded:
            if recorded[path.name] != checksum:
                raise MigrationError(
                    f"{path.name} changed after it was applied. Roll it back with "
                    "'down' before editing an applied migration."
                )
            continue
        with conn.transaction():
            conn.execute(path.read_text(encoding="utf-8"))
            conn.execute(
                "insert into ikig.schema_migrations(name, checksum) values (%s, %s)",
                (path.name, checksum),
            )
        applied.append(path.name)
    return applied


def rollback_last(conn) -> str | None:  # noqa: ANN001 — psycopg connection
    row = conn.execute(
        "select name from ikig.schema_migrations order by applied_at desc, name desc limit 1"
    ).fetchone()
    if row is None:
        return None
    name = row[0]
    down_script = MIGRATIONS_DIR / name.replace(".sql", ".down.sql")
    if not down_script.exists():
        raise MigrationError(f"{name} has no reverse script ({down_script.name} is missing).")
    with conn.transaction():
        conn.execute(down_script.read_text(encoding="utf-8"))
        conn.execute("delete from ikig.schema_migrations where name = %s", (name,))
    return name


def status(conn) -> list[tuple[str, str, str]]:  # noqa: ANN001 — psycopg connection
    rows = conn.execute(
        "select name, checksum, applied_at from ikig.schema_migrations order by name"
    ).fetchall()
    return [(name, checksum, str(applied_at)) for name, checksum, applied_at in rows]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m src.contracts.migrations.apply")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("up", help="apply pending migrations")
    sub.add_parser("status", help="list applied migrations")
    down = sub.add_parser("down", help="roll back the most recently applied migration")
    down.add_argument(
        "--yes",
        action="store_true",
        help="required: rolling back can destroy data",
    )
    args = parser.parse_args(argv)
    command = args.command or "up"

    if command == "down" and not args.yes:
        print(
            "Refusing to roll back without --yes: a down migration can destroy data.",
            file=sys.stderr,
        )
        return 2

    try:
        dsn = _dsn()
        conn = _connect(dsn)
    except MigrationError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    try:
        conn.execute(BOOTSTRAP_SQL)
        conn.commit()
        conn.execute("select pg_advisory_lock(hashtext(%s))", (LOCK_KEY,))
        conn.commit()
        try:
            if command == "up":
                applied = apply_pending(conn)
                if applied:
                    for name in applied:
                        print(f"applied {name}")
                else:
                    print("no pending migrations")
            elif command == "status":
                rows = status(conn)
                if not rows:
                    print("no migrations applied")
                for name, checksum, applied_at in rows:
                    print(f"{name} {checksum[:12]} {applied_at}")
            else:
                rolled = rollback_last(conn)
                if rolled is None:
                    print("nothing to roll back")
                else:
                    print(f"rolled back {rolled}")
        finally:
            # A failed statement leaves the transaction aborted, so the unlock
            # needs a clean transaction to run in.
            conn.rollback()
            conn.execute("select pg_advisory_unlock(hashtext(%s))", (LOCK_KEY,))
            conn.commit()
    except MigrationError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

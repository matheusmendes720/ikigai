"""The row-level security policies, proved against a role they bind (SPEC-02 T2.4).

The spec's verification is: "com ``client_id=A``, ``select`` de ``B`` → 0 linhas;
com RLS off → linhas". Two things make that proof easy to fake, and both are
avoided here.

The first: the role that owns the tables **bypasses** row-level security, so
a proof run as the owner proves nothing — it would see every row with or
without the policies. The proof here runs as a role that does NOT own them,
which is also the role a managed Postgres may hand the service.

The second: the service does not set ``request.jwt.claim.client_id``, so the
policies only bind a role that does not own the tables. That is a real
property of the system, and it is why the deploy README states the
dependency: the service's role must own the DOM's tables, or the store is
unusable. The last test here is the mutation check for that — the
healthcheck's write probe must fail under a bound role, so the container
cannot report healthy while every write is refused.
"""

from __future__ import annotations

import importlib.util
import shutil

import pytest

_HAS_DRIVER = importlib.util.find_spec("psycopg") is not None
_HAS_CONTAINERS = importlib.util.find_spec("testcontainers") is not None
_HAS_DOCKER = shutil.which("docker") is not None

requires_store = pytest.mark.skipif(
    not (_HAS_DRIVER and _HAS_CONTAINERS and _HAS_DOCKER),
    reason="needs psycopg, testcontainers and Docker to reach a real Postgres",
)

ROLE = "ikigai_rls_client"
PASSWORD = "rls_client"
CLIENT_A = "cliente-a"
CLIENT_B = "cliente-b"

UID_A = "kpi:rls-a:0000000a:00000000"
UID_B = "kpi:rls-b:0000000b:00000000"


@pytest.fixture(scope="module")
def store_dsn() -> str:
    from testcontainers.postgres import PostgresContainer

    from src.data.client import with_connect_timeout

    with PostgresContainer("pgvector/pgvector:pg16") as postgres:
        dsn = postgres.get_connection_url().replace("postgresql+psycopg2://", "postgresql://")
        # The container publishes on IPv4, and 'localhost' resolves to IPv6
        # FIRST — an address nothing listens on, which the driver waits out
        # for the whole OS connect timeout before it tries the next one.
        dsn = dsn.replace("localhost", "127.0.0.1")
        dsn = with_connect_timeout(dsn)
        _prepare(dsn)
        yield dsn


@pytest.fixture(scope="module")
def bound_dsn(store_dsn: str) -> str:
    """A DSN for a role the policies actually bind."""
    import psycopg
    from psycopg.conninfo import make_conninfo

    with psycopg.connect(store_dsn) as conn:
        conn.execute(f"drop role if exists {ROLE}")
        conn.execute(f"create role {ROLE} login password '{PASSWORD}'")
        conn.execute(f"grant usage on schema ikig to {ROLE}")
        conn.execute(
            f"grant select, insert, update, delete on all tables in schema ikig to {ROLE}"
        )
        conn.commit()
    return make_conninfo(store_dsn, user=ROLE, password=PASSWORD)


def _prepare(dsn: str) -> None:
    import psycopg

    from src.contracts.migrations.apply import BOOTSTRAP_SQL, apply_pending

    with psycopg.connect(dsn) as conn:
        conn.execute(BOOTSTRAP_SQL)
        apply_pending(conn)
        conn.execute(
            "insert into ikig.artifacts (uid, kind, title, client_id) values "
            f"('{UID_A}', 'kpi', 'da cliente a', '{CLIENT_A}'), "
            f"('{UID_B}', 'kpi', 'da cliente b', '{CLIENT_B}')"
        )


def _visible_clients(dsn: str, claim: str | None) -> set[str]:
    """The client_ids a session can see, with the claim set (or not)."""
    import psycopg

    from src.contracts.store import RLS_CLIENT_CLAIM

    with psycopg.connect(dsn) as conn:
        if claim is not None:
            # Session scope: the claim has to survive the statements that
            # follow it, which is how a request-scoped claim would behave.
            # The setting's name comes from the constant the policies read.
            conn.execute(f"select set_config('{RLS_CLIENT_CLAIM}', %s, false)", (claim,))
        rows = conn.execute("select client_id from ikig.artifacts").fetchall()
    return {str(row[0]) for row in rows}


@requires_store
def test_the_policies_isolate_clients(store_dsn: str, bound_dsn: str) -> None:
    """A claim for client A sees A's rows and not B's."""
    assert _visible_clients(bound_dsn, CLIENT_A) == {CLIENT_A}
    assert _visible_clients(bound_dsn, CLIENT_B) == {CLIENT_B}


@requires_store
def test_the_owner_role_sees_everything(store_dsn: str) -> None:
    """The role that owns the tables bypasses the policies — and that is why
    the deploy depends on it. The proof above is meaningless without this
    one: if the owner saw nothing either, the policies would be untested."""
    assert _visible_clients(store_dsn, None) == {CLIENT_A, CLIENT_B}


@requires_store
def test_without_the_claim_a_bound_role_sees_nothing(bound_dsn: str) -> None:
    """The deploy trap, pinned.

    A role the policies bind, with no claim, sees nothing: the comparison is
    against NULL, and NULL is not true. This is why the service's role must
    own the tables, and why the healthcheck's probe writes a row instead of
    running ``select 1``.
    """
    assert _visible_clients(bound_dsn, None) == set()


@requires_store
def test_the_healthcheck_probe_writes_as_the_owner(store_dsn: str) -> None:
    """The probe succeeds where the service actually runs."""
    from src.transport.healthcheck import _check_store

    _check_store(store_dsn)


@requires_store
def test_the_healthcheck_probe_is_refused_by_a_bound_role(bound_dsn: str) -> None:
    """The mutation check: the probe must FAIL where the store is unusable.

    Without this, a probe that only ever ran as the owner would be a health
    check that cannot fail — the container would report healthy while every
    write was refused by the policy.
    """
    from src.transport.healthcheck import _check_store

    with pytest.raises(Exception):
        _check_store(bound_dsn)


@requires_store
def test_the_probe_leaves_nothing_behind(store_dsn: str) -> None:
    """The probe writes a row and throws it away: no row, no ledger entry."""
    import psycopg

    from src.transport.healthcheck import _check_store

    _check_store(store_dsn)
    with psycopg.connect(store_dsn) as conn:
        rows = conn.execute(
            "select count(*) from ikig.artifacts where uid = 'kpi:healthcheck:00000000:00000000'"
        ).fetchone()
        keys = conn.execute(
            "select count(*) from ikig.idempotency_keys where key like 'healthcheck%'"
        ).fetchone()
    assert int(rows[0]) == 0, "the healthcheck left a row in the store"
    assert int(keys[0]) == 0, "the healthcheck left an entry in the ledger"

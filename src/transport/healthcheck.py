"""A healthcheck that measures the DATA PLANE, not the surface (contract C-2).

``curl http://localhost:8000/healthz`` would prove that a socket answers and
nothing else. A green answer on the wrong path is worse than no answer at
all — that is contract C-2, written down because the repo had already been
burned by it ("``405`` em ``GET /mcp`` = sinal de vida, não de erro").

Two things actually matter for the container to count as up:

1. **the store can be WRITTEN** — the data plane, measured by the only query
   that proves it: an insert the check immediately discards;
2. **a client can reach the transport** — the address the bot and the harness
   dial, not the loopback the server happens to bind.

The first one is subtler than it looks, and it was wrong here. The probe used
to be ``select 1`` — a query against no table at all. It proves the socket
carries bytes, which is what C-2 forbids. It is also blind to the store's
row-level security: the DOM's policies filter on
``request.jwt.claim.client_id``, and the service does not set that claim, so
the policies only bind a role that does not own the tables. A ``select 1``
answers fine under such a role — RLS does not apply to it — while EVERY
write is refused by the policy's ``with check``. The container would have
reported healthy while the store was unusable: the green lie, wearing a
different hat.

So the probe writes a row and throws it away. Under a role the policies
bind, the insert is refused and the check reports the refusal. Under the
owner role it succeeds and is rolled back, and nothing is stored — the probe
leaves no row, no sequence and no ledger entry behind.

The second one is the other subtle half. A server bound to 127.0.0.1 also
answers a connection to 0.0.0.0, because the kernel resolves 0.0.0.0 to the
loopback — so a check against the bind host passes on a service that no other
container in the network can reach. That is the green lie C-2 warns about,
and it is why the check below dials the address a CLIENT uses.

Exit code 0 means both. Anything else exits non-zero, so the container
orchestrator sees the failure rather than a green lie.

This is the API's healthcheck: it measures the store, and the api is the
only process that holds a DSN. The bot runs the SAME image and has no store
at all — it is a client of the api — so the compose file overrides its
healthcheck with the one thing the bot actually depends on: the api's MCP
endpoint being reachable.

The third role is the WORKER: the ingestion holds a DSN and serves no surface
at all. It cannot inherit the image's healthcheck either — that one dials the
MCP transport on 8000, which the ingestion never opens, so it would report
unhealthy forever. A container that reports unhealthy forever is a lie in the
other direction, and a deploy that waits for health would never finish. So
``--store-only`` measures the half the worker actually depends on: the store
can be written.

Run::

    python -m src.transport.healthcheck
    python -m src.transport.healthcheck --store-only
"""

from __future__ import annotations

import argparse
import os
import socket
import sys

from src.contracts.store import STORE_DSN_ENV
from src.transport.mcp_server import transport_host, transport_port

_WILDCARD_HOSTS = ("0.0.0.0", "::", "")

# The probe's own row. The uid is a valid one and is never stored: the
# transaction is rolled back, so the probe leaves nothing behind.
_PROBE_UID = "kpi:healthcheck:00000000:00000000"
_PROBE_INSERT = (
    "insert into ikig.artifacts (uid, kind, title, client_id) "
    f"values ('{_PROBE_UID}', 'kpi', 'healthcheck', 'healthcheck')"
)


def _check_store(dsn: str) -> None:
    """Prove the store can be written, by writing and discarding a row.

    The insert is rolled back, so the probe leaves no row and no ledger entry
    behind. What it does leave is the answer to the question that matters: can
    the service's own role write to the DOM? If the store's policies bind
    that role, the insert is refused and the check says so.
    """
    import psycopg

    conn = psycopg.connect(dsn, connect_timeout=5)
    try:
        conn.execute(_PROBE_INSERT)
        conn.rollback()
    finally:
        conn.close()


def _client_address(bind_host: str) -> str:
    """The address a client on the network uses to reach this process.

    When the transport binds one specific address, that address is the one.
    When it binds every interface, the address that proves reachability is
    this host's own — the one the bot resolves the api to.
    """
    if bind_host not in _WILDCARD_HOSTS:
        return bind_host
    hostname = socket.gethostname()
    try:
        candidates = socket.getaddrinfo(hostname, None, socket.AF_INET)
    except OSError as exc:
        raise RuntimeError(f"cannot resolve the address of {hostname}: {exc}") from exc
    for info in candidates:
        address = str(info[4][0])
        if not address.startswith("127."):
            return address
    raise RuntimeError(
        f"the transport binds every interface but {hostname} has no address a client can reach"
    )


def check_reachable(host: str, port: int) -> None:
    """Prove that a client can reach an address.

    The address is the one a CLIENT uses — not the bind address — because a
    server bound to every interface also answers the loopback, and a check
    against the loopback passes on a service no other container can reach.
    """
    address = _client_address(host)
    with socket.create_connection((address, port), timeout=5):
        return


def probe(dsn: str, host: str, port: int) -> None:
    """Both halves of the data plane, for a transport that is not the MCP one.

    The websocket server has the same obligation as the api: the container
    must not report healthy while the store is unreachable or while the
    surface nobody can dial is the only thing that answers. It raises on
    failure; the caller decides what to do with that.
    """
    _check_store(dsn)
    check_reachable(host, port)


def main(argv: list[str] | None = None) -> int:
    """The probe, for the transport this process serves.

    ``--host`` and ``--port`` name the surface to measure. Without them it is
    the MCP transport's address — the api is what the image's HEALTHCHECK
    runs. The websocket server passes its own, because it is a different
    surface on a different port and a probe that measures the wrong one
    reports a green lie.
    """
    parser = argparse.ArgumentParser(prog="python -m src.transport.healthcheck")
    parser.add_argument("--host", default=None, help="the address to dial")
    parser.add_argument("--port", type=int, default=None, help="the port to dial")
    parser.add_argument(
        "--store-only",
        action="store_true",
        help="measure only the store — for the workers that hold a DSN and serve no surface",
    )
    args = parser.parse_args(argv)

    dsn = os.environ.get(STORE_DSN_ENV)
    if not dsn:
        print(f"{STORE_DSN_ENV} is not set", file=sys.stderr)
        return 1

    try:
        if args.store_only:
            # A worker: it writes, and it serves nothing. The surface half of
            # the probe would measure a port this process never opens.
            _check_store(dsn)
        else:
            host = args.host if args.host is not None else transport_host()
            port = args.port if args.port is not None else transport_port()
            probe(dsn, host, port)
    except Exception as exc:  # a healthcheck reports, it does not raise
        print(f"unhealthy: {exc}", file=sys.stderr)
        return 1

    print("healthy")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

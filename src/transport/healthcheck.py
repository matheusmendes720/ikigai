"""A healthcheck that measures the DATA PLANE, not the surface (contract C-2).

``curl http://localhost:8000/healthz`` would prove that a socket answers and
nothing else. A green answer on the wrong path is worse than no answer at
all — that is contract C-2, written down because the repo had already been
burned by it ("``405`` em ``GET /mcp`` = sinal de vida, não de erro").

Two things actually matter for the container to count as up:

1. **the store answers** — a trivial query, against the DSN the service
   layer itself uses;
2. **a client can reach the transport** — the address the bot and the harness
   dial, not the loopback the server happens to bind.

The second one is the subtle half. A server bound to 127.0.0.1 also answers
a connection to 0.0.0.0, because the kernel resolves 0.0.0.0 to the
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

Run::

    python -m src.transport.healthcheck
"""

from __future__ import annotations

import os
import socket
import sys

from src.contracts.store import STORE_DSN_ENV
from src.transport.mcp_server import transport_host, transport_port

_WILDCARD_HOSTS = ("0.0.0.0", "::", "")


def _check_store(dsn: str) -> None:
    import psycopg

    with psycopg.connect(dsn, connect_timeout=5) as conn:
        with conn.cursor() as cur:
            cur.execute("select 1")
            row = cur.fetchone()
    if row is None or row[0] != 1:
        raise RuntimeError("the store did not answer `select 1`")


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
        f"the transport binds every interface but {hostname} has no address a "
        "client can reach"
    )


def _check_transport() -> None:
    address = _client_address(transport_host())
    port = transport_port()
    with socket.create_connection((address, port), timeout=5):
        return


def main() -> None:
    dsn = os.environ.get(STORE_DSN_ENV)
    if not dsn:
        print(f"{STORE_DSN_ENV} is not set", file=sys.stderr)
        raise SystemExit(1)

    try:
        _check_store(dsn)
        _check_transport()
    except Exception as exc:  # noqa: BLE001 — a healthcheck reports, it does not raise
        print(f"unhealthy: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    print("healthy")


if __name__ == "__main__":
    main()

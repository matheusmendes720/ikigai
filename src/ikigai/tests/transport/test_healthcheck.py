"""The healthcheck: the probe that measures the data plane.

There are two roles and two probes, and mixing them is how a container ends
up lying:

- the api (and the websocket) SERVE a surface, so their probe measures the
  store AND the address a client dials — the second half is what catches a
  server bound to a loopback nobody else can reach;
- the ingestion serves NOTHING. It writes the vault into the store and
  serves no surface at all, so the surface half would measure a port the
  process never opens — and the container would report unhealthy forever.

`--store-only` is the flag that says which role the caller is, and it is the
difference between a container that reports what it is and one that reports
the opposite of the truth.
"""

from __future__ import annotations

import pytest
from src.transport import healthcheck

_DSN = "postgresql://ikigai:secret@db:5432/ikigai"


def test_the_store_only_probe_measures_the_store_and_nothing_else(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A worker has no surface to dial."""
    monkeypatch.setenv(healthcheck.STORE_DSN_ENV, _DSN)
    stores: list[str] = []

    monkeypatch.setattr(healthcheck, "_check_store", stores.append)
    monkeypatch.setattr(
        healthcheck,
        "check_reachable",
        lambda host, port: pytest.fail("the store-only probe must not dial a surface"),
    )

    assert healthcheck.main(["--store-only"]) == 0
    assert stores == [_DSN]


def test_the_transport_probe_measures_both_halves(monkeypatch: pytest.MonkeyPatch) -> None:
    """The api's probe is the whole data plane: the store AND the address a
    client uses to reach the surface."""
    monkeypatch.setenv(healthcheck.STORE_DSN_ENV, _DSN)
    stores: list[str] = []
    surfaces: list[tuple[str, int]] = []

    monkeypatch.setattr(healthcheck, "_check_store", stores.append)
    monkeypatch.setattr(
        healthcheck,
        "check_reachable",
        lambda host, port: surfaces.append((host, port)),
    )

    assert healthcheck.main(["--host", "0.0.0.0", "--port", "8001"]) == 0
    assert stores == [_DSN]
    assert surfaces == [("0.0.0.0", 8001)]


def test_without_a_dsn_the_probe_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    """No DSN is not a reason to report healthy."""
    monkeypatch.delenv(healthcheck.STORE_DSN_ENV, raising=False)

    assert healthcheck.main(["--store-only"]) == 1


def test_a_store_that_refuses_the_write_is_unhealthy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The probe writes a row and throws it away. A store that refuses the
    write is a store the service cannot use, and the check has to say so."""
    monkeypatch.setenv(healthcheck.STORE_DSN_ENV, _DSN)

    def refuse(dsn: str) -> None:
        raise RuntimeError("the store refused the write")

    monkeypatch.setattr(healthcheck, "_check_store", refuse)

    assert healthcheck.main(["--store-only"]) == 1

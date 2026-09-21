"""ikigai serve — single-process orchestrator.

Bootstraps a UnifiedMCPGateway (with all registered mesh adapters) and a
minimal HTTP server in a daemon thread on the configured port (default
8765). Designed to be invoked by `ikigai.bat serve` / `ikigai-serve.sh`
or any supervisor that wants a single, well-behaved process entry point.

Graceful shutdown is wired to SIGINT and SIGTERM: both signals cancel the
serve loop and join the gateway before exiting with a zero status.

Falls back gracefully when `sys_ikigai` is not importable (e.g. in a
fresh checkout before `uv sync`): a stub gateway and stub HTTP server
are used so the orchestrator can still respond to lifecycle signals.
"""

from __future__ import annotations

import argparse
import logging
import signal
import sys
import threading
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

LOG = logging.getLogger("ikigai.serve")

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
DEFAULT_LOG_LEVEL = "INFO"

__all__ = (
    "DEFAULT_HOST",
    "DEFAULT_LOG_LEVEL",
    "DEFAULT_PORT",
    "ServeOptions",
    "ServeRuntime",
    "main",
    "register_mesh_adapters",
    "serve",
)

# ---------------------------------------------------------------------------
# Options / Runtime containers
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ServeOptions:
    """Resolved CLI options for the orchestrator.

    Default host is ``"127.0.0.1"`` (dev-mode safe bind; not ``0.0.0.0``).
    Default port is ``8765`` per the rebuild plan (default-playbook port).
    """

    host: str = "127.0.0.1"
    port: int = 8765
    with_cli: bool = True
    with_tui: bool = False
    log_level: str = DEFAULT_LOG_LEVEL


@dataclass
class ServeRuntime:
    """Live handles for the running orchestrator; mutated as services come up."""

    options: ServeOptions
    gateway: Any | None = None
    httpd: ThreadingHTTPServer | None = None
    http_thread: threading.Thread | None = None
    stop_event: threading.Event = field(default_factory=threading.Event)
    registered_adapters: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Adapter registration
# ---------------------------------------------------------------------------


def register_mesh_adapters(gateway: Any) -> list[str]:
    """Register every available mesh fork adapter against ``gateway``.

    Returns the list of adapter names that were successfully attached.
    Failures are logged at WARNING but do not abort startup — the
    orchestrator is expected to keep running in a degraded state rather
    than refuse to boot when an optional fork is unavailable.
    """

    attached: list[str] = []

    candidate_paths: list[tuple[str, str]] = [
        (
            "cli",
            "sys_ikigai.gateway.adapters.cli_adapter:CliAdapter",
        ),
        (
            "taskdog",
            "sys_ikigai.gateway.adapters.taskdog_adapter:TaskdogAdapter",
        ),
        (
            "solverforge_calendar",
            "sys_ikigai.gateway.adapters.solverforge_calendar_adapter:SolverforgeCalendarAdapter",
        ),
        (
            "tuiboard",
            "sys_ikigai.gateway.adapters.tuiboard_adapter:TuiboardAdapter",
        ),
    ]

    for name, dotted in candidate_paths:
        try:
            module_path, _, attr = dotted.partition(":")
            module = __import__(module_path, fromlist=[attr])
            cls = getattr(module, attr)
        except Exception as exc:  # pragma: no cover — adapter wiring best-effort
            LOG.warning("mesh adapter '%s' unavailable: %s", name, exc)
            continue

        register: Callable[[Any, Any], Any] | None = getattr(gateway, "register_adapter", None)
        if register is None:  # stub gateway — best effort
            LOG.debug("gateway has no register_adapter; recording '%s' only", name)
            attached.append(name)
            continue

        try:
            register(gateway, cls())
        except Exception as exc:  # pragma: no cover — adapter wiring best-effort
            LOG.warning("mesh adapter '%s' registration failed: %s", name, exc)
            continue

        attached.append(name)
        LOG.info("mesh adapter attached: %s", name)

    return attached


# ---------------------------------------------------------------------------
# HTTP server (liveness + discovery)
# ---------------------------------------------------------------------------


def _build_handler(runtime: ServeRuntime) -> type[BaseHTTPRequestHandler]:
    """Return an HTTP handler bound to ``runtime`` for /health and /info."""

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
            LOG.debug("http: " + format, *args)

        def _json(self, status: int, payload: dict[str, Any]) -> None:
            body = __import__("json").dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:
            if self.path in ("/", "/health"):
                self._json(
                    200,
                    {
                        "status": "ok",
                        "adapters": runtime.registered_adapters,
                    },
                )
            elif self.path == "/info":
                self._json(
                    200,
                    {
                        "host": runtime.options.host,
                        "port": runtime.options.port,
                        "log_level": runtime.options.log_level,
                        "with_cli": runtime.options.with_cli,
                        "with_tui": runtime.options.with_tui,
                        "adapters": runtime.registered_adapters,
                    },
                )
            else:
                self._json(404, {"error": "not_found", "path": self.path})

    return Handler


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------


def _install_signal_handlers(runtime: ServeRuntime) -> None:
    """Install SIGINT/SIGTERM handlers that flip the stop event."""

    def _handle(signum: int, frame: Any) -> None:
        LOG.info("signal %s received; requesting shutdown", signum)
        runtime.stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            signal.signal(sig, _handle)
        except (ValueError, OSError):  # pragma: no cover — non-main thread
            LOG.debug("could not install handler for %s", sig)


def _build_gateway() -> Any:
    """Construct a UnifiedMCPGateway or a stub when sys_ikigai is missing."""

    try:
        from sys_ikigai.gateway.gateway import (  # type: ignore[import-not-found]
            GatewayConfig,
            UnifiedMCPGateway,
        )
    except Exception as exc:  # pragma: no cover — import fallback
        LOG.warning("sys_ikigai gateway not importable; using stub gateway (%s)", exc)

        class _StubGateway:
            def __init__(self) -> None:
                self.adapters: list[str] = []

            def register_adapter(self, _gateway: Any, adapter: Any) -> None:
                self.adapters.append(getattr(adapter, "name", adapter.__class__.__name__))

        return _StubGateway()

    config = GatewayConfig()
    return UnifiedMCPGateway(config=config)


def _shutdown(runtime: ServeRuntime) -> None:
    """Stop the HTTP loop and close the gateway; idempotent."""

    if runtime.httpd is not None:
        LOG.info("stopping http server on %s:%s", runtime.options.host, runtime.options.port)
        try:
            runtime.httpd.shutdown()
            runtime.httpd.server_close()
        except Exception as exc:  # pragma: no cover — best-effort shutdown
            LOG.warning("http shutdown error: %s", exc)
        runtime.httpd = None

    if runtime.http_thread is not None and runtime.http_thread.is_alive():
        runtime.http_thread.join(timeout=2.0)

    close = getattr(runtime.gateway, "close", None)
    if callable(close):
        try:
            close()
        except Exception as exc:  # pragma: no cover — best-effort shutdown
            LOG.warning("gateway close error: %s", exc)


def serve(runtime: ServeRuntime) -> int:
    """Run the orchestrator until SIGINT/SIGTERM; returns the exit code."""

    logging.basicConfig(
        level=getattr(logging, runtime.options.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    )

    runtime.gateway = _build_gateway()
    runtime.registered_adapters = register_mesh_adapters(runtime.gateway)
    LOG.info(
        "ikigai serve: %d mesh adapter(s) attached (%s)",
        len(runtime.registered_adapters),
        ", ".join(runtime.registered_adapters) or "<none>",
    )

    handler_cls = _build_handler(runtime)
    runtime.httpd = ThreadingHTTPServer((runtime.options.host, runtime.options.port), handler_cls)
    runtime.http_thread = threading.Thread(
        target=runtime.httpd.serve_forever,
        name="ikigai-serve-http",
        daemon=True,
    )
    runtime.http_thread.start()
    LOG.info(
        "ikigai serve: http listening on http://%s:%s",
        runtime.options.host,
        runtime.options.port,
    )

    _install_signal_handlers(runtime)
    try:
        while not runtime.stop_event.is_set():
            runtime.stop_event.wait(timeout=1.0)
    finally:
        _shutdown(runtime)

    LOG.info("ikigai serve: shutdown complete")
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_argv(argv: Iterable[str]) -> ServeOptions:
    parser = argparse.ArgumentParser(
        prog="ikigai-serve",
        description="ikigai serve — single-process orchestrator.",
    )
    parser.add_argument("--host", default=DEFAULT_HOST, help="HTTP bind host")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="HTTP bind port")
    parser.add_argument(
        "--with-cli",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Also expose the CLI entry point (default: enabled).",
    )
    parser.add_argument(
        "--with-tui",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Also spawn the operator TUI in-process (default: disabled).",
    )
    parser.add_argument(
        "--log-level",
        default=DEFAULT_LOG_LEVEL,
        choices=("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"),
        help="Logging verbosity (default: INFO).",
    )

    ns = parser.parse_args(list(argv))
    return ServeOptions(
        host=ns.host,
        port=ns.port,
        with_cli=ns.with_cli,
        with_tui=ns.with_tui,
        log_level=ns.log_level,
    )


def main(argv: list[str] | None = None) -> int:
    options = _parse_argv(sys.argv[1:] if argv is None else argv)
    runtime = ServeRuntime(options=options)
    return serve(runtime)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

"""Reliability layer for external MCP calls — retry, circuit breaker, cache invalidation.

This module provides decorators for:
- Exponential backoff with jitter
- Circuit breaker pattern
- Session cache invalidation on connection failures
- OTel span emission for every retry attempt
"""
from __future__ import annotations

import functools
import logging
import random
import time
import traceback
from dataclasses import dataclass
from typing import Any, Callable, TypeVar

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

T = TypeVar("T")
_log = logging.getLogger("ikigai.reliability")

# Per-server circuit-breaker state (in-memory; reset on process restart).
_circuit_state: dict[str, _CircuitBreaker] = {}

# Module-level reference to _MCP_SESSION_CACHE for invalidation
_mcp_session_cache_ref: dict[str, bool] | None = None


def _set_cache_ref(cache: dict[str, bool]) -> None:
    """Set the module-level reference to the session cache."""
    global _mcp_session_cache_ref
    _mcp_session_cache_ref = cache


@dataclass
class RetryConfig:
    max_attempts: int = 3
    initial_backoff_s: float = 0.5
    max_backoff_s: float = 8.0
    backoff_multiplier: float = 2.0
    jitter: bool = True


@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 5  # open after N consecutive failures
    reset_timeout_s: float = 30.0  # half-open after this many seconds


def retry_with_backoff(
    *,
    name: str,
    retryable_exceptions: tuple[type[BaseException], ...] = (ConnectionError, TimeoutError, OSError),
    config: RetryConfig = RetryConfig(),
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator: retry a function with exponential backoff + jitter.

    Emits OTel span `reliability.{name}` with attributes:
    - attempt (int, 1-indexed)
    - attempt.duration_ms (number)
    - attempt.error (string, exception class name)
    - attempt.succeeded (bool)
    """

    def decorator(fn: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            tracer = trace.get_tracer("ikigai.reliability")
            last_exc: BaseException | None = None
            for attempt in range(1, config.max_attempts + 1):
                with tracer.start_as_current_span(
                    f"reliability.{name}.attempt_{attempt}"
                ) as span:
                    span.set_attribute("reliability.attempt", attempt)
                    span.set_attribute("reliability.max_attempts", config.max_attempts)
                    start = time.perf_counter()
                    try:
                        result = fn(*args, **kwargs)
                        span.set_attribute("reliability.succeeded", True)
                        span.set_attribute(
                            "reliability.duration_ms",
                            (time.perf_counter() - start) * 1000,
                        )
                        return result
                    except retryable_exceptions as exc:
                        last_exc = exc
                        span.set_status(Status(StatusCode.ERROR))
                        span.set_attribute("reliability.succeeded", False)
                        span.set_attribute("reliability.error.class", type(exc).__name__)
                        span.set_attribute("reliability.error.message", str(exc)[:500])
                        # Capture stack trace in span attributes (truncated).
                        tb_str = traceback.format_exc(limit=10)
                        span.set_attribute("reliability.error.traceback", tb_str[:2000])
                        if attempt < config.max_attempts:
                            backoff = min(
                                config.initial_backoff_s
                                * (config.backoff_multiplier ** (attempt - 1)),
                                config.max_backoff_s,
                            )
                            if config.jitter:
                                backoff *= random.uniform(0.5, 1.5)
                            _log.warning(
                                "reliability.%s attempt %d/%d failed (%s); backing off %.2fs",
                                name,
                                attempt,
                                config.max_attempts,
                                type(exc).__name__,
                                backoff,
                            )
                            time.sleep(backoff)
            assert last_exc is not None
            raise last_exc

        return wrapper

    return decorator


class _CircuitBreaker:
    def __init__(self, name: str, config: CircuitBreakerConfig) -> None:
        self.name = name
        self.config = config
        self.consecutive_failures = 0
        self.opened_at: float | None = None

    def is_open(self) -> bool:
        if self.opened_at is None:
            return False
        if time.time() - self.opened_at > self.config.reset_timeout_s:
            _log.info("circuit_breaker.%s transitioning to half-open", self.name)
            self.opened_at = None
            return False
        return True

    def record_failure(self) -> None:
        self.consecutive_failures += 1
        if (
            self.consecutive_failures >= self.config.failure_threshold
            and self.opened_at is None
        ):
            _log.warning(
                "circuit_breaker.%s OPENED after %d failures",
                self.name,
                self.consecutive_failures,
            )
            self.opened_at = time.time()

    def record_success(self) -> None:
        if self.consecutive_failures > 0 or self.opened_at is not None:
            _log.info("circuit_breaker.%s CLOSED after success", self.name)
        self.consecutive_failures = 0
        self.opened_at = None


def circuit_breaker(
    name: str, config: CircuitBreakerConfig = CircuitBreakerConfig()
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator: fail fast if circuit is open; auto-recover after reset_timeout_s.

    Raises `CircuitOpenError` immediately if the circuit is open.
    """

    def decorator(fn: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            cb = _circuit_state.setdefault(name, _CircuitBreaker(name, config))
            if cb.is_open():
                raise CircuitOpenError(f"circuit_breaker.{name} is OPEN")
            try:
                result = fn(*args, **kwargs)
            except Exception:
                cb.record_failure()
                raise
            cb.record_success()
            return result

        return wrapper

    return decorator


class CircuitOpenError(RuntimeError):
    """Raised when a circuit breaker is open."""


def invalidate_session_cache(system: str) -> None:
    """Clear the cached 'initialize' handshake result for a system.

    Call this when a call fails with a connection-related error so the next
    attempt re-runs the handshake. Idempotent.
    """
    if _mcp_session_cache_ref is not None and system in _mcp_session_cache_ref:
        _log.info("Invalidating session cache for system: %s", system)
        del _mcp_session_cache_ref[system]

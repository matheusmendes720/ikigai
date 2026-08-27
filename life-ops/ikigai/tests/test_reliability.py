"""Tests for reliability layer — retry, circuit breaker, cache invalidation."""
from __future__ import annotations

import time
from unittest.mock import patch

import pytest

from src.agents.reliability import (
    RetryConfig,
    CircuitBreakerConfig,
    retry_with_backoff,
    circuit_breaker,
    invalidate_session_cache,
    CircuitOpenError,
    _set_cache_ref,
    _circuit_state,
)


# Reset circuit state before each test
@pytest.fixture(autouse=True)
def reset_circuit_state():
    """Reset circuit breaker state before each test."""
    _circuit_state.clear()
    yield
    _circuit_state.clear()


# Test cache reference
@pytest.fixture
def test_cache():
    """Create a test cache and set it as the module reference."""
    cache: dict[str, bool] = {}
    _set_cache_ref(cache)
    yield cache
    _set_cache_ref({})


class TestRetry:
    """Tests for retry_with_backoff decorator."""

    def test_retry_succeeds_after_transient_failure(self):
        """Test that retry succeeds after transient failures."""
        call_count = 0

        @retry_with_backoff(
            name="test_retry",
            retryable_exceptions=(ValueError,),
            config=RetryConfig(max_attempts=3, jitter=False),
        )
        def flaky_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("transient error")
            return "success"

        result = flaky_function()
        assert result == "success"
        assert call_count == 3

    def test_retry_gives_up_after_max_attempts(self):
        """Test that retry gives up after max attempts and re-raises."""
        call_count = 0

        @retry_with_backoff(
            name="test_retry_fail",
            retryable_exceptions=(ValueError,),
            config=RetryConfig(max_attempts=3, jitter=False),
        )
        def always_fails():
            nonlocal call_count
            call_count += 1
            raise ValueError("persistent error")

        with pytest.raises(ValueError, match="persistent error"):
            always_fails()
        assert call_count == 3

    def test_retry_respects_backoff_timing(self):
        """Test that backoff timing is applied between retries."""
        call_times = []

        @retry_with_backoff(
            name="test_timing",
            retryable_exceptions=(ValueError,),
            config=RetryConfig(
                max_attempts=3,
                initial_backoff_s=0.1,
                max_backoff_s=1.0,
                backoff_multiplier=2.0,
                jitter=False,
            ),
        )
        def timed_function():
            call_times.append(time.perf_counter())
            if len(call_times) < 3:
                raise ValueError("error")
            return "success"

        timed_function()

        # Check that backoff occurred (second call should be at least 0.1s after first)
        assert call_times[1] - call_times[0] >= 0.1
        # Third call should be at least 0.2s after second (exponential)
        assert call_times[2] - call_times[1] >= 0.2


class TestCircuitBreaker:
    """Tests for circuit_breaker decorator."""

    def test_circuit_breaker_opens_after_threshold(self):
        """Test that circuit opens after threshold failures."""

        @circuit_breaker("test_cb", CircuitBreakerConfig(failure_threshold=5, reset_timeout_s=30.0))
        def failing_function():
            raise ConnectionError("connection failed")

        # First 5 failures should raise ConnectionError
        for i in range(5):
            with pytest.raises(ConnectionError):
                failing_function()

        # 6th call should raise CircuitOpenError
        with pytest.raises(CircuitOpenError, match="circuit_breaker.test_cb is OPEN"):
            failing_function()

    def test_circuit_breaker_half_opens_after_timeout(self):
        """Test that circuit transitions to half-open after timeout."""

        @circuit_breaker(
            "test_cb_timeout", CircuitBreakerConfig(failure_threshold=3, reset_timeout_s=0.1)
        )
        def failing_function():
            raise ConnectionError("connection failed")

        # Open the circuit
        for i in range(3):
            with pytest.raises(ConnectionError):
                failing_function()

        # Wait for timeout
        time.sleep(0.15)

        # Next call should NOT raise CircuitOpenError (circuit is half-open)
        # It should proceed and raise the actual error from the function
        with pytest.raises(ConnectionError):
            failing_function()

    def test_circuit_breaker_closes_on_success(self):
        """Test that circuit closes after a successful call."""

        call_count = 0

        @circuit_breaker("test_cb_success", CircuitBreakerConfig(failure_threshold=3, reset_timeout_s=30.0))
        def sometimes_failing():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise ConnectionError("error")
            return "success"

        # First two calls fail
        with pytest.raises(ConnectionError):
            sometimes_failing()
        with pytest.raises(ConnectionError):
            sometimes_failing()

        # Third call succeeds, circuit should close (failures < threshold)
        result = sometimes_failing()
        assert result == "success"

        # Fourth call should succeed normally (circuit is closed)
        result = sometimes_failing()
        assert result == "success"


class TestCacheInvalidation:
    """Tests for session cache invalidation."""

    def test_invalidate_session_cache_clears_entry(self, test_cache):
        """Test that invalidate_session_cache clears the cache entry."""
        # Set a cache entry
        test_cache["solverforge"] = True
        test_cache["tuiboard"] = True

        # Invalidate one
        invalidate_session_cache("solverforge")

        assert "solverforge" not in test_cache
        assert test_cache.get("tuiboard") is True

    def test_invalidate_session_cache_idempotent(self, test_cache):
        """Test that invalidation is idempotent (can call multiple times)."""
        test_cache["solverforge"] = True

        # Call multiple times - should not raise
        invalidate_session_cache("solverforge")
        invalidate_session_cache("solverforge")
        invalidate_session_cache("solverforge")

        assert "solverforge" not in test_cache

    def test_invalidate_session_cache_nonexistent(self, test_cache):
        """Test that invalidating nonexistent key is safe."""
        # Should not raise
        invalidate_session_cache("nonexistent")


class TestStackTraceCapture:
    """Tests for stack trace capture in OTel spans."""

    def test_stack_trace_captured_in_span(self):
        """Test that stack trace is captured in span attributes."""
        import traceback as tb

        # Set up a real tracer for this test
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider, SpanProcessor
        from opentelemetry.sdk.resources import Resource, SERVICE_NAME

        # Custom processor to capture spans
        captured_spans = []

        class CaptureProcessor(SpanProcessor):
            def on_end(self, span):
                captured_spans.append(span)

        # Create a minimal tracer provider
        provider = TracerProvider(
            resource=Resource.create({SERVICE_NAME: "ikigai-test"})
        )
        provider.add_span_processor(CaptureProcessor())
        trace.set_tracer_provider(provider)

        @retry_with_backoff(
            name="test_trace",
            retryable_exceptions=(ValueError,),
            config=RetryConfig(max_attempts=1, jitter=False),
        )
        def failing_function():
            raise ValueError("test error")

        with pytest.raises(ValueError):
            failing_function()

        # Verify span was captured
        assert len(captured_spans) >= 1
        span = captured_spans[0]

        # Check span attributes
        attributes = dict(span.attributes)
        assert attributes.get("reliability.succeeded") is False
        assert attributes.get("reliability.error.class") == "ValueError"
        assert "test error" in attributes.get("reliability.error.message", "")
        # Check traceback was captured
        traceback_val = attributes.get("reliability.error.traceback", "")
        assert "failing_function" in traceback_val
        assert "ValueError" in traceback_val
        assert "test error" in traceback_val


def test_circuit_breaker_counts_logical_calls_not_attempts():
    """Verify CB-then-retry stacking: 5 logical calls × 3 attempts each = 5 failures, then open."""
    call_count = 0

    @circuit_breaker("test_logical", CircuitBreakerConfig(failure_threshold=5, reset_timeout_s=999))
    @retry_with_backoff(
        name="test_logical",
        retryable_exceptions=(ValueError,),
        config=RetryConfig(max_attempts=3, initial_backoff_s=0, max_backoff_s=0, jitter=False),
    )
    def always_fails():
        nonlocal call_count
        call_count += 1
        raise ValueError("boom")

    # Each logical call exhausts 3 retries. After 5 logical calls, CB should open.
    for i in range(5):
        with pytest.raises(ValueError):
            always_fails()
    # The 6th logical call should fail-fast with CircuitOpenError.
    with pytest.raises(CircuitOpenError):
        always_fails()
    # Verify f was called 5 × 3 = 15 times (5 logical × 3 attempts each).
    assert call_count == 15, f"expected 15 calls (5 logical × 3 attempts), got {call_count}"

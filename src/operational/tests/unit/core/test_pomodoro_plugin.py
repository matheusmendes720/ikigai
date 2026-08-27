"""Unit tests for the reframed :mod:`operational.core.pomodoro_machine`.

These tests verify the new **plugin contract** architecture
(:class:`PomodoroPlugin`, :class:`InMemoryPomodoroPlugin`,
:class:`PomodoroTracker`, plugin registry).
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

from operational.core.pomodoro_machine import (
    DEFAULT_TRANSITIONS,
    InMemoryPomodoroPlugin,
    PomodoroEvent,
    PomodoroPlugin,
    PomodoroSession,
    PomodoroSessionEvent,
    PomodoroTracker,
    default_transition_table,
    get_default_plugin,
    set_default_plugin,
)
from operational.enums import PomodoroState


# ---------------------------------------------------------------------------
# Protocol conformance
# ---------------------------------------------------------------------------


class TestPomodoroPluginProtocol:
    """The InMemoryPomodoroPlugin must satisfy the PomodoroPlugin protocol."""

    def test_in_memory_satisfies_protocol(self) -> None:
        plugin: PomodoroPlugin = InMemoryPomodoroPlugin()
        assert isinstance(plugin, PomodoroPlugin)

    def test_custom_implementation_satisfies_protocol(self) -> None:
        class CustomPlugin:
            def start_session(self, session_id: str, *, rounds_max: int = 4) -> PomodoroSession:
                return PomodoroSession(session_id=session_id, rounds_max=rounds_max)

            def get_session(self, session_id: str) -> PomodoroSession | None:
                return None

            def list_sessions(self) -> list[PomodoroSession]:
                return []

            def delete_session(self, session_id: str) -> bool:
                return False

            def record_event(self, session_id: str, event: PomodoroSessionEvent) -> None:
                pass

        custom: PomodoroPlugin = CustomPlugin()
        assert isinstance(custom, PomodoroPlugin)


# ---------------------------------------------------------------------------
# InMemoryPomodoroPlugin
# ---------------------------------------------------------------------------


class TestInMemoryPomodoroPlugin:
    """Tests for the default in-memory plugin."""

    def test_create_plugin(self) -> None:
        plugin = InMemoryPomodoroPlugin()
        assert plugin.list_sessions() == []

    def test_start_session(self) -> None:
        plugin = InMemoryPomodoroPlugin()
        session = plugin.start_session("pmo_abc", rounds_max=4)
        assert session.session_id == "pmo_abc"
        assert session.rounds_max == 4
        assert session.state == PomodoroState.IDLE
        assert session.current_round == 0
        assert session.started_at is not None
        assert session.completed_at is None

    def test_start_session_duplicate_raises(self) -> None:
        plugin = InMemoryPomodoroPlugin()
        plugin.start_session("pmo_abc")
        with pytest.raises(ValueError, match="already exists"):
            plugin.start_session("pmo_abc")

    def test_start_session_invalid_rounds_raises(self) -> None:
        plugin = InMemoryPomodoroPlugin()
        with pytest.raises(ValueError, match="rounds_max"):
            plugin.start_session("pmo_abc", rounds_max=0)

    def test_get_session_returns_session(self) -> None:
        plugin = InMemoryPomodoroPlugin()
        plugin.start_session("pmo_abc")
        assert plugin.get_session("pmo_abc") is not None
        assert plugin.get_session("pmo_missing") is None

    def test_list_sessions(self) -> None:
        plugin = InMemoryPomodoroPlugin()
        plugin.start_session("pmo_1")
        plugin.start_session("pmo_2")
        plugin.start_session("pmo_3")
        assert len(plugin.list_sessions()) == 3

    def test_delete_session(self) -> None:
        plugin = InMemoryPomodoroPlugin()
        plugin.start_session("pmo_abc")
        assert plugin.delete_session("pmo_abc") is True
        assert plugin.get_session("pmo_abc") is None

    def test_delete_session_missing_returns_false(self) -> None:
        plugin = InMemoryPomodoroPlugin()
        assert plugin.delete_session("pmo_missing") is False

    def test_record_event_valid_transition(self) -> None:
        plugin = InMemoryPomodoroPlugin()
        plugin.start_session("pmo_abc")
        event = PomodoroSessionEvent(
            session_id="pmo_abc",
            timestamp=datetime.now(UTC),
            state=PomodoroState.WORK,
            round_number=1,
        )
        plugin.record_event("pmo_abc", event)
        session = plugin.get_session("pmo_abc")
        assert session is not None
        assert session.state == PomodoroState.WORK
        assert session.current_round == 1
        assert len(session.events) == 1

    def test_record_event_invalid_transition_raises(self) -> None:
        plugin = InMemoryPomodoroPlugin()
        plugin.start_session("pmo_abc")
        # IDLE → COMPLETE is valid (per DEFAULT_TRANSITIONS)
        # but IDLE → WORK → COMPLETE works; let's try IDLE → BREAK (invalid)
        with pytest.raises(ValueError, match="Invalid transition"):
            plugin.record_event(
                "pmo_abc",
                PomodoroSessionEvent(
                    session_id="pmo_abc",
                    timestamp=datetime.now(UTC),
                    state=PomodoroState.BREAK,
                ),
            )

    def test_record_event_complete_sets_completed_at(self) -> None:
        plugin = InMemoryPomodoroPlugin()
        plugin.start_session("pmo_abc")
        ts = datetime.now(UTC)
        plugin.record_event(
            "pmo_abc",
            PomodoroSessionEvent(
                session_id="pmo_abc",
                timestamp=ts,
                state=PomodoroState.COMPLETE,
            ),
        )
        session = plugin.get_session("pmo_abc")
        assert session is not None
        assert session.completed_at == ts

    def test_record_event_unknown_session_raises(self) -> None:
        plugin = InMemoryPomodoroPlugin()
        with pytest.raises(KeyError, match="not found"):
            plugin.record_event(
                "pmo_missing",
                PomodoroSessionEvent(
                    session_id="pmo_missing",
                    timestamp=datetime.now(UTC),
                    state=PomodoroState.WORK,
                ),
            )


# ---------------------------------------------------------------------------
# PomodoroTracker (reference state machine)
# ---------------------------------------------------------------------------


class TestPomodoroTracker:
    """Tests for the reference state machine implementation."""

    def test_initial_state(self) -> None:
        tracker = PomodoroTracker(session_id="pmo_abc")
        assert tracker.current_state == PomodoroState.IDLE
        assert tracker.current_round == 0
        assert not tracker.is_running
        assert not tracker.is_complete
        assert tracker.events == []

    def test_invalid_rounds_max_raises(self) -> None:
        with pytest.raises(ValueError, match="rounds_max"):
            PomodoroTracker(session_id="pmo_abc", rounds_max=0)

    def test_start_idle_to_work(self) -> None:
        tracker = PomodoroTracker(session_id="pmo_abc")
        event = tracker.start()
        assert event.from_state == PomodoroState.IDLE
        assert event.to_state == PomodoroState.WORK
        assert tracker.current_round == 1
        assert tracker.is_running

    def test_start_from_non_idle_raises(self) -> None:
        tracker = PomodoroTracker(session_id="pmo_abc")
        tracker.start()
        with pytest.raises(RuntimeError, match="Cannot start"):
            tracker.start()

    def test_complete_round_to_break(self) -> None:
        tracker = PomodoroTracker(session_id="pmo_abc", rounds_max=4)
        tracker.start()
        event = tracker.complete_round()
        assert event.to_state == PomodoroState.BREAK
        assert tracker.current_round == 1

    def test_complete_round_to_long_break_at_max(self) -> None:
        tracker = PomodoroTracker(session_id="pmo_abc", rounds_max=1)
        tracker.start()
        event = tracker.complete_round()
        assert event.to_state == PomodoroState.LONG_BREAK

    def test_complete_round_requires_work(self) -> None:
        tracker = PomodoroTracker(session_id="pmo_abc")
        with pytest.raises(RuntimeError, match="WORK"):
            tracker.complete_round()

    def test_complete_break_to_work(self) -> None:
        tracker = PomodoroTracker(session_id="pmo_abc", rounds_max=4)
        tracker.start()
        tracker.complete_round()  # WORK → BREAK
        event = tracker.complete_break()  # BREAK → WORK
        assert event.to_state == PomodoroState.WORK
        assert tracker.current_round == 2

    def test_complete_break_requires_break(self) -> None:
        tracker = PomodoroTracker(session_id="pmo_abc")
        with pytest.raises(RuntimeError, match="BREAK"):
            tracker.complete_break()

    def test_complete_long_break_to_idle(self) -> None:
        tracker = PomodoroTracker(session_id="pmo_abc", rounds_max=1)
        tracker.start()
        tracker.complete_round()  # WORK → LONG_BREAK
        event = tracker.complete_long_break()
        assert event.to_state == PomodoroState.IDLE

    def test_interrupt_work_to_paused(self) -> None:
        tracker = PomodoroTracker(session_id="pmo_abc")
        tracker.start()
        event = tracker.interrupt()
        assert event.to_state == PomodoroState.PAUSED

    def test_resume_paused_to_work(self) -> None:
        tracker = PomodoroTracker(session_id="pmo_abc")
        tracker.start()
        tracker.interrupt()
        event = tracker.resume()
        assert event.to_state == PomodoroState.WORK

    def test_abort_paused_to_idle(self) -> None:
        tracker = PomodoroTracker(session_id="pmo_abc")
        tracker.start()
        tracker.interrupt()
        event = tracker.abort()
        assert event.to_state == PomodoroState.IDLE

    def test_skip_break_emits_two_events(self) -> None:
        tracker = PomodoroTracker(session_id="pmo_abc", rounds_max=4)
        tracker.start()
        tracker.complete_round()  # WORK → BREAK
        tracker.skip_break()  # BREAK → SKIPPED → WORK
        assert tracker.current_state == PomodoroState.WORK
        # Two new events (SKIPPED and WORK)
        assert len(tracker.events) == 4  # start, complete_round, skipped, work

    def test_finish_idle_to_complete(self) -> None:
        tracker = PomodoroTracker(session_id="pmo_abc")
        event = tracker.finish()
        assert event.to_state == PomodoroState.COMPLETE
        assert tracker.is_complete

    def test_finish_requires_idle(self) -> None:
        tracker = PomodoroTracker(session_id="pmo_abc")
        tracker.start()
        with pytest.raises(RuntimeError, match="IDLE"):
            tracker.finish()

    def test_complete_is_terminal(self) -> None:
        tracker = PomodoroTracker(session_id="pmo_abc")
        tracker.finish()
        with pytest.raises(RuntimeError, match="terminal"):
            tracker.transition(PomodoroState.IDLE)

    def test_invalid_transition_raises(self) -> None:
        tracker = PomodoroTracker(session_id="pmo_abc")
        # IDLE → BREAK is not a valid transition per DEFAULT_TRANSITIONS
        with pytest.raises(ValueError, match="Invalid transition"):
            tracker.transition(PomodoroState.BREAK)

    def test_get_state_duration_minutes(self) -> None:
        tracker = PomodoroTracker(
            session_id="pmo_abc",
            work_minutes=50,
            break_minutes=10,
            long_break_minutes=30,
        )
        assert tracker.get_state_duration_minutes(PomodoroState.WORK) == 50
        assert tracker.get_state_duration_minutes(PomodoroState.BREAK) == 10
        assert tracker.get_state_duration_minutes(PomodoroState.LONG_BREAK) == 30
        assert tracker.get_state_duration_minutes(PomodoroState.SKIPPED) == 10
        assert tracker.get_state_duration_minutes(PomodoroState.IDLE) == 0
        assert tracker.get_state_duration_minutes(PomodoroState.COMPLETE) == 0

    def test_full_lifecycle(self) -> None:
        """Full session: IDLE → WORK → BREAK → WORK → BREAK → ... → LONG_BREAK → IDLE → COMPLETE."""
        tracker = PomodoroTracker(session_id="pmo_abc", rounds_max=2)
        tracker.start()
        for _ in range(2):
            tracker.complete_round()  # WORK → BREAK (or LONG_BREAK on last)
            if tracker.current_state == PomodoroState.LONG_BREAK:
                break
            tracker.complete_break()  # BREAK → WORK
        assert tracker.current_state == PomodoroState.LONG_BREAK
        tracker.complete_long_break()  # LONG_BREAK → IDLE
        assert tracker.current_state == PomodoroState.IDLE
        tracker.finish()
        assert tracker.is_complete


# ---------------------------------------------------------------------------
# Plugin registry
# ---------------------------------------------------------------------------


class TestPluginRegistry:
    """Tests for the default plugin registry."""

    def setup_method(self) -> None:
        # Reset registry to clean state for each test
        import operational.core.pomodoro_machine as mod

        mod._DEFAULT_PLUGIN = None

    def teardown_method(self) -> None:
        import operational.core.pomodoro_machine as mod

        mod._DEFAULT_PLUGIN = None

    def test_get_default_plugin_returns_in_memory(self) -> None:
        plugin = get_default_plugin()
        assert isinstance(plugin, InMemoryPomodoroPlugin)

    def test_get_default_plugin_singleton(self) -> None:
        p1 = get_default_plugin()
        p2 = get_default_plugin()
        assert p1 is p2

    def test_set_default_plugin_replaces(self) -> None:
        class CustomPlugin:
            def start_session(self, session_id: str, *, rounds_max: int = 4) -> PomodoroSession:
                return PomodoroSession(session_id=session_id, rounds_max=rounds_max)

            def get_session(self, session_id: str) -> PomodoroSession | None:
                return None

            def list_sessions(self) -> list[PomodoroSession]:
                return []

            def delete_session(self, session_id: str) -> bool:
                return False

            def record_event(self, session_id: str, event: PomodoroSessionEvent) -> None:
                pass

        custom = CustomPlugin()
        set_default_plugin(custom)  # type: ignore[arg-type]
        assert get_default_plugin() is custom


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


class TestModuleHelpers:
    """Tests for default_transition_table()."""

    def test_default_transition_table_returns_copy(self) -> None:
        t1 = default_transition_table()
        t2 = default_transition_table()
        assert t1 == t2
        assert t1 is not t2
        # Mutating copy does not affect original
        t1[PomodoroState.IDLE] = frozenset()
        assert DEFAULT_TRANSITIONS[PomodoroState.IDLE] == frozenset(
            {PomodoroState.WORK, PomodoroState.COMPLETE}
        )

    def test_default_transitions_complete(self) -> None:
        for state in PomodoroState:
            assert state in DEFAULT_TRANSITIONS
        assert DEFAULT_TRANSITIONS[PomodoroState.COMPLETE] == frozenset()
        assert DEFAULT_TRANSITIONS[PomodoroState.IDLE] == frozenset(
            {PomodoroState.WORK, PomodoroState.COMPLETE}
        )

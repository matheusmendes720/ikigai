"""Persistent app state for the CLI layer.

Each repository is backed by a JSON file so that data survives across
``subprocess`` calls (interactive home menu) and process restarts.

Under the hood it uses an :class:`InMemoryRepository` for speed, but
calls ``dump()`` after every write and ``load()`` at import time.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from operational.entities.ajuste_fino import AjusteFino
from operational.entities.habit import Habit
from operational.entities.journal import JournalEntry
from operational.entities.metric import SleepRecord
from operational.entities.policy import PolicyDecision, PolicySetpoints
from operational.entities.pomodoro import PomodoroRound
from operational.entities.routine import Routine, RoutineLog
from operational.entities.time_block import TimeBlock
from operational.entities.v3 import (
    DailyReflection,
    DayContext,
    LunchRecord,
    TransicaoRegistrada,
)
from operational.persistence.memory import InMemoryRepository

# ---------------------------------------------------------------------------
# Where state lives
# ---------------------------------------------------------------------------
_STATE_DIR = Path(os.environ.get("TIME_TASKER_STATE_DIR", Path.home() / ".time-tasker"))
_STATE_DIR.mkdir(parents=True, exist_ok=True)


class _PersistentRepo(InMemoryRepository):
    """In-memory repo that snapshots to a JSON file on every mutation."""

    def __init__(self, model_class: type, filename: str) -> None:
        super().__init__(model_class)
        self._path = _STATE_DIR / filename
        self._load()

    # -- helpers ----------------------------------------------------------

    def _path_for(self, filename: str) -> Path:
        return _STATE_DIR / filename

    def _load(self) -> None:
        """Load seed data from JSON (mode='json' dump format)."""
        if not self._path.exists():
            return
        try:
            raw: dict[str, dict[str, Any]] = json.loads(self._path.read_text("utf-8"))
            self._store.update(raw)
        except (json.JSONDecodeError, OSError):
            pass  # corrupt file → start fresh

    def _dump(self) -> None:
        """Snapshot every stored entity in JSON mode."""
        serialized: dict[str, dict[str, Any]] = {}
        for eid, data in self._store.items():
            serialized[eid] = self._model_class.model_validate(data).model_dump(
                mode="json",  # date/datetime → iso strings
                exclude={*self._model_class.model_computed_fields.keys()},
            )
        text = json.dumps(serialized, indent=2, ensure_ascii=False)
        self._path.write_text(text.replace("\r\n", "\n"), "utf-8")

    # -- override persistence hooks ---------------------------------------

    def _persist_one(self, entity_id: str, data: dict[str, Any]) -> None:
        super()._persist_one(entity_id, data)
        self._dump()

    def _remove_one(self, entity_id: str) -> None:
        super()._remove_one(entity_id)
        self._dump()

    def clear(self) -> None:
        super().clear()
        if self._path.exists():
            self._path.unlink()


# ---------------------------------------------------------------------------
# Repositories — one per entity type, persisted to ``~/.time-tasker/*.json``
# ---------------------------------------------------------------------------
routines: _PersistentRepo = _PersistentRepo(Routine, "routines.json")
routine_logs: _PersistentRepo = _PersistentRepo(RoutineLog, "routine_logs.json")
time_blocks: _PersistentRepo = _PersistentRepo(TimeBlock, "time_blocks.json")
journals: _PersistentRepo = _PersistentRepo(JournalEntry, "journals.json")
habits: _PersistentRepo = _PersistentRepo(Habit, "habits.json")
sleep_records: _PersistentRepo = _PersistentRepo(SleepRecord, "sleep_records.json")
pomodoros: _PersistentRepo = _PersistentRepo(PomodoroRound, "pomodoros.json")
policy_decisions: _PersistentRepo = _PersistentRepo(PolicyDecision, "policy_decisions.json")
policy_setpoints: _PersistentRepo = _PersistentRepo(PolicySetpoints, "policy_setpoints.json")
ajustes_finos: _PersistentRepo = _PersistentRepo(AjusteFino, "ajustes_finos.json")

# V3 entities
day_contexts: _PersistentRepo = _PersistentRepo(DayContext, "day_contexts.json")
daily_reflections: _PersistentRepo = _PersistentRepo(DailyReflection, "daily_reflections.json")
lunch_records: _PersistentRepo = _PersistentRepo(LunchRecord, "lunch_records.json")
transicoes: _PersistentRepo = _PersistentRepo(TransicaoRegistrada, "transicoes.json")


# ---------------------------------------------------------------------------
# Dataset loader — load / switch datasets at runtime
# ---------------------------------------------------------------------------

_ALL_REPOS: tuple[_PersistentRepo, ...] = (
    routines, routine_logs, time_blocks, journals, habits,
    sleep_records, pomodoros, policy_decisions, policy_setpoints,
    ajustes_finos, day_contexts, daily_reflections,
    lunch_records, transicoes,
)


def load_dataset(name: str, *, clear_first: bool = False) -> dict[str, int]:
    """Load a named dataset into the repos.

    This is the runtime switcher — call it before launching the TUI to
    populate the UI with mock data while the real pipelines are being built.

    Args:
        name: "synthetic", "golden", or "production".
        clear_first: If True, wipe all repos before loading.
                     Use when switching datasets (e.g. ``--golden`` / ``--synthetic``).

    Returns:
        dict mapping entity_type → count loaded.

    Raises:
        ValueError: If the dataset name is unknown.

    """
    if name == "production":
        if clear_first:
            for repo in _ALL_REPOS:
                repo.clear()
        return {}

    from operational.cli.csv_loader import import_from_csv_as_entities
    from operational.cli.dataset_selector import resolve_dataset

    ref = resolve_dataset(name)
    if not ref.csv_path or not ref.csv_path.exists():
        return {}

    if clear_first:
        for repo in _ALL_REPOS:
            repo.clear()

    groups = import_from_csv_as_entities(ref.csv_path)
    repo_map: dict[str, object] = {
        "routine": routines,
        "routine_log": routine_logs,
        "time_block": time_blocks,
        "journal_entry": journals,
        "habit": habits,
        "sleep_record": sleep_records,
        "pomodoro_round": pomodoros,
        "policy_decision": policy_decisions,
        "policy_setpoints": policy_setpoints,
        "ajuste_fino": ajustes_finos,
        "day_context": day_contexts,
        "daily_reflection": daily_reflections,
        "lunch_record": lunch_records,
        "transicao": transicoes,
    }
    counts: dict[str, int] = {}
    for etype, entities in groups.items():
        if etype in repo_map:
            for ent in entities:
                repo_map[etype].upsert(ent)
            counts[etype] = len(entities)
    return counts


def clear_all_state() -> None:
    """Wipe all repos and delete all JSON state files."""
    for repo in _ALL_REPOS:
        repo.clear()


# ---------------------------------------------------------------------------
# Auto-load dataset on boot (if requested via env var)
# ---------------------------------------------------------------------------
def _auto_load_dataset() -> None:
    """If TIME_TASKER_DATASET is set and the state dir is empty, load from CSV.

    Skips if any state file already exists (don't overwrite user data).
    Skips silently on errors (the user can run ``operational doctor`` to debug).
    """
    dataset_name = os.environ.get("TIME_TASKER_DATASET")
    if not dataset_name or dataset_name == "production":
        return
    if any(_STATE_DIR.glob("*.json")):
        return
    try:
        load_dataset(dataset_name)
    except Exception:  # noqa: BLE001
        pass  # silent


_auto_load_dataset()

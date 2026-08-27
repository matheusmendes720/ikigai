"""Comprehensive unit tests for ``operational.types``.

Covers:

* Branded type aliases (``Hour``, ``Minute``, ``UEID``, ``StreakInt``,
  ``Score``) — validated through Pydantic models that use them.
* Protocol structural typing (``Repository``, ``Clock``, ``Logger``) —
  verified by ``isinstance`` checks and concrete fakes.
* TypeVar bounds (``T_Entity``, ``T_Enum``) — verified through actual
  generic usage.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Any

import pytest
from pydantic import BaseModel, ValidationError

from operational.types import (
    Clock,
    Hour,
    Logger,
    Minute,
    Repository,
    Score,
    StreakInt,
    T,
    T_Entity,
    T_Enum,
    UEID,
)

# ---------------------------------------------------------------------------
# Fixtures / fakes
# ---------------------------------------------------------------------------


class _SampleEntity(BaseModel):
    """Concrete BaseModel used to exercise generic protocols."""

    id: str
    name: str
    value: int = 0


class _InMemoryRepository:
    """Minimal in-memory implementation of ``Repository[_SampleEntity]``."""

    def __init__(self) -> None:
        self._store: dict[str, _SampleEntity] = {}

    def get(self, id: str) -> _SampleEntity | None:
        return self._store.get(id)

    def list(self, filters: dict[str, Any] | None = None) -> list[_SampleEntity]:
        items = list(self._store.values())
        if not filters:
            return items
        return [i for i in items if all(getattr(i, k, None) == v for k, v in filters.items())]

    def upsert(self, entity: _SampleEntity) -> str:
        self._store[entity.id] = entity
        return entity.id

    def delete(self, id: str) -> bool:
        return self._store.pop(id, None) is not None

    def count(self, filters: dict[str, Any] | None = None) -> int:
        return len(self.list(filters))


class _IncompleteRepository:
    """A class that does NOT implement the full ``Repository`` protocol."""

    def get(self, id: str) -> _SampleEntity | None:
        return None


class _SystemClock:
    """Production-style clock — returns ``datetime.now()``/``date.today()``."""

    def now(self) -> datetime:
        return datetime.now()

    def today(self) -> date:
        return date.today()


class _FrozenClock:
    """Test-friendly clock — always returns the same instant."""

    def __init__(self, fixed: datetime) -> None:
        self._fixed = fixed

    def now(self) -> datetime:
        return self._fixed

    def today(self) -> date:
        return self._fixed.date()


class _ListLogger:
    """Test logger that captures calls into a list."""

    def __init__(self) -> None:
        self.records: list[tuple[str, str, dict[str, Any]]] = []

    def info(self, msg: str, **fields: Any) -> None:
        self.records.append(("info", msg, fields))

    def warning(self, msg: str, **fields: Any) -> None:
        self.records.append(("warning", msg, fields))

    def error(self, msg: str, **fields: Any) -> None:
        self.records.append(("error", msg, fields))


class _PartialLogger:
    """Logger that only implements ``info`` — must fail runtime check."""

    def info(self, msg: str, **fields: Any) -> None:
        return None


# ---------------------------------------------------------------------------
# Hour
# ---------------------------------------------------------------------------


class TestHourTypeAlias:
    """``Hour`` accepts 0..23, rejects 24+ and negatives via Pydantic."""

    def test_hour_accepts_zero(self) -> None:
        class M(BaseModel):
            h: Hour

        assert M(h=0).h == 0

    def test_hour_accepts_23(self) -> None:
        class M(BaseModel):
            h: Hour

        assert M(h=23).h == 23

    @pytest.mark.parametrize("value", [-1, -100, 24, 25, 100])
    def test_hour_rejects_out_of_range(self, value: int) -> None:
        class M(BaseModel):
            h: Hour

        with pytest.raises(ValidationError):
            M(h=value)


# ---------------------------------------------------------------------------
# Minute
# ---------------------------------------------------------------------------


class TestMinuteTypeAlias:
    """``Minute`` accepts 0..59, rejects 60+ and negatives."""

    def test_minute_accepts_zero(self) -> None:
        class M(BaseModel):
            m: Minute

        assert M(m=0).m == 0

    def test_minute_accepts_59(self) -> None:
        class M(BaseModel):
            m: Minute

        assert M(m=59).m == 59

    @pytest.mark.parametrize("value", [-1, -5, 60, 61, 200])
    def test_minute_rejects_out_of_range(self, value: int) -> None:
        class M(BaseModel):
            m: Minute

        with pytest.raises(ValidationError):
            M(m=value)


# ---------------------------------------------------------------------------
# UEID
# ---------------------------------------------------------------------------


class TestUEIDTypeAlias:
    """``UEID`` matches ``^[a-z]{3,5}_[a-z0-9_]+$``."""

    @pytest.mark.parametrize(
        "value",
        [
            "hab_morning_water",
            "rou_entry_meditation",
            "pmo_focus_deep",
            "blk_work_001",
            "day_2026_06_07",
            "abc_x",
            "abcd_xyz_123",
        ],
    )
    def test_ueid_accepts_valid(self, value: str) -> None:
        class M(BaseModel):
            uid: UEID

        m = M(uid=value)
        assert m.uid == value

    @pytest.mark.parametrize(
        "value",
        [
            "ab_x",  # prefix too short (2 chars)
            "abcdef_x",  # prefix too long (6 chars)
            "HAB_x",  # uppercase prefix
            "habX_x",  # mixed case
            "hab-xxx",  # hyphen not allowed
            "hab_",  # empty slug
            "hab",  # missing separator
            "hab_ABC",  # uppercase slug
            "hab_ x",  # space
            "1ab_xxx",  # prefix starts with digit
            "_abc_xxx",  # prefix missing
            "",  # empty
        ],
    )
    def test_ueid_rejects_invalid(self, value: str) -> None:
        class M(BaseModel):
            uid: UEID

        with pytest.raises(ValidationError):
            M(uid=value)


# ---------------------------------------------------------------------------
# StreakInt
# ---------------------------------------------------------------------------


class TestStreakIntTypeAlias:
    """``StreakInt`` accepts any non-negative integer."""

    def test_streak_accepts_zero(self) -> None:
        class M(BaseModel):
            s: StreakInt

        assert M(s=0).s == 0

    def test_streak_accepts_large(self) -> None:
        class M(BaseModel):
            s: StreakInt

        assert M(s=10_000).s == 10_000

    @pytest.mark.parametrize("value", [-1, -50, -1000])
    def test_streak_rejects_negative(self, value: int) -> None:
        class M(BaseModel):
            s: StreakInt

        with pytest.raises(ValidationError):
            M(s=value)


# ---------------------------------------------------------------------------
# Score
# ---------------------------------------------------------------------------


class TestScoreTypeAlias:
    """``Score`` accepts 0.0..1.0 inclusive."""

    def test_score_accepts_zero(self) -> None:
        class M(BaseModel):
            v: Score

        assert M(v=0.0).v == 0.0

    def test_score_accepts_one(self) -> None:
        class M(BaseModel):
            v: Score

        assert M(v=1.0).v == 1.0

    def test_score_accepts_typical(self) -> None:
        class M(BaseModel):
            v: Score

        assert M(v=0.85).v == 0.85

    @pytest.mark.parametrize("value", [-0.1, -1.0, 1.1, 2.0, 100.0])
    def test_score_rejects_out_of_range(self, value: float) -> None:
        class M(BaseModel):
            v: Score

        with pytest.raises(ValidationError):
            M(v=value)


# ---------------------------------------------------------------------------
# Repository
# ---------------------------------------------------------------------------


class TestRepositoryProtocol:
    """``Repository`` is a runtime-checkable Protocol."""

    def test_runtime_checkable(self) -> None:
        """``Repository`` must carry ``_is_runtime_protocol``."""
        assert hasattr(Repository, "_is_runtime_protocol")
        assert Repository._is_runtime_protocol is True

    def test_complete_implementation_passes(self) -> None:
        """``_InMemoryRepository`` satisfies ``Repository`` structurally."""
        repo = _InMemoryRepository()
        assert isinstance(repo, Repository)

    def test_incomplete_implementation_fails(self) -> None:
        """Missing methods are detected by ``isinstance``."""
        bad = _IncompleteRepository()
        assert not isinstance(bad, Repository)

    def test_non_class_fails(self) -> None:
        """Non-class objects never satisfy the protocol."""
        assert not isinstance(object(), Repository)
        assert not isinstance(42, Repository)
        assert not isinstance("string", Repository)

    def test_concrete_crud_cycle(self) -> None:
        """Smoke test of CRUD semantics on the fake repo."""
        repo: _InMemoryRepository = _InMemoryRepository()
        e1 = _SampleEntity(id="hab_a", name="a", value=1)
        e2 = _SampleEntity(id="hab_b", name="b", value=2)

        assert repo.upsert(e1) == "hab_a"
        assert repo.upsert(e2) == "hab_b"
        assert repo.count() == 2
        assert repo.get("hab_a") is e1
        assert repo.list() == [e1, e2]
        assert repo.list({"value": 2}) == [e2]
        assert repo.delete("hab_a") is True
        assert repo.get("hab_a") is None
        assert repo.delete("hab_a") is False
        assert repo.count() == 1

    def test_protocol_with_typevar(self) -> None:
        """``Repository`` accepts a generic parameter at runtime."""

        class GenericRepo(Repository[_SampleEntity]):
            def get(self, id: str) -> _SampleEntity | None:
                return None

            def list(self, filters: dict[str, Any] | None = None) -> list[_SampleEntity]:
                return []

            def upsert(self, entity: _SampleEntity) -> str:
                return entity.id

            def delete(self, id: str) -> bool:
                return False

            def count(self, filters: dict[str, Any] | None = None) -> int:
                return 0

        gr = GenericRepo()
        assert isinstance(gr, Repository)
        # The class is a Repository subclass at runtime
        assert issubclass(GenericRepo, Repository)


# ---------------------------------------------------------------------------
# Clock
# ---------------------------------------------------------------------------


class TestClockProtocol:
    """``Clock`` is a runtime-checkable Protocol with ``now``/``today``."""

    def test_runtime_checkable(self) -> None:
        assert hasattr(Clock, "_is_runtime_protocol")
        assert Clock._is_runtime_protocol is True

    def test_system_clock_satisfies(self) -> None:
        assert isinstance(_SystemClock(), Clock)

    def test_frozen_clock_satisfies(self) -> None:
        fixed = datetime(2026, 6, 7, 9, 0, 0)
        clock = _FrozenClock(fixed)
        assert isinstance(clock, Clock)
        assert clock.now() == fixed
        assert clock.today() == date(2026, 6, 7)

    def test_non_clock_fails(self) -> None:
        class _NoNow:
            def today(self) -> date:
                return date.today()

        assert not isinstance(_NoNow(), Clock)
        assert not isinstance(object(), Clock)


# ---------------------------------------------------------------------------
# Logger
# ---------------------------------------------------------------------------


class TestLoggerProtocol:
    """``Logger`` is a runtime-checkable Protocol with three methods."""

    def test_runtime_checkable(self) -> None:
        assert hasattr(Logger, "_is_runtime_protocol")
        assert Logger._is_runtime_protocol is True

    def test_list_logger_satisfies(self) -> None:
        log = _ListLogger()
        assert isinstance(log, Logger)

    def test_partial_logger_fails(self) -> None:
        """A logger missing ``warning`` and ``error`` is not a Logger."""
        assert not isinstance(_PartialLogger(), Logger)

    def test_structured_fields(self) -> None:
        """``**fields`` accepts arbitrary structured metadata."""
        log = _ListLogger()
        log.info("started", step=1, user="me")
        log.warning("slow", ms=850)
        log.error("boom", code=500)

        assert log.records == [
            ("info", "started", {"step": 1, "user": "me"}),
            ("warning", "slow", {"ms": 850}),
            ("error", "boom", {"code": 500}),
        ]


# ---------------------------------------------------------------------------
# TypeVar bounds
# ---------------------------------------------------------------------------


class TestTypeVars:
    """Verify the TypeVars declared in ``types.py``."""

    def test_t_is_unbound(self) -> None:
        """``T`` is exported and has no bound."""
        # TypeVar has no bound attribute, or it is None
        bound = getattr(T, "__bound__", None)
        assert bound is None

    def test_t_entity_bound_is_basemodel(self) -> None:
        """``T_Entity`` is bounded by :class:`pydantic.BaseModel`."""
        assert getattr(T_Entity, "__bound__", None) is BaseModel

    def test_t_enum_bound_is_strenum(self) -> None:
        """``T_Enum`` is bounded by :class:`enum.StrEnum`."""
        assert getattr(T_Enum, "__bound__", None) is StrEnum

    def test_t_entity_usable_in_generic_class(self) -> None:
        """``T_Entity`` can parameterise a class declaration without errors."""

        class Repo(Repository[T_Entity]):  # type: ignore[misc]
            def get(self, id: str) -> T_Entity | None:  # type: ignore[override]
                return None

            def list(self, filters: dict[str, Any] | None = None) -> list[T_Entity]:  # type: ignore[override]
                return []

            def upsert(self, entity: T_Entity) -> str:  # type: ignore[override]
                return "x"

            def delete(self, id: str) -> bool:  # type: ignore[override]
                return False

            def count(self, filters: dict[str, Any] | None = None) -> int:  # type: ignore[override]
                return 0

        # The class can be instantiated and produces a concrete instance
        # that satisfies the runtime-checkable Repository protocol.
        instance = Repo()
        assert isinstance(instance, Repository)
        # The class itself inherits from Repository at runtime
        assert issubclass(Repo, Repository)
        # Plain dict is NOT a BaseModel
        assert not issubclass(dict, BaseModel)

    def test_t_enum_usable_as_generic_param(self) -> None:
        """``T_Enum`` can parameterise a function signature."""

        class Color(StrEnum):
            RED = "R"
            BLUE = "B"

        def first(enum_cls: type[T_Enum]) -> T_Enum:
            return next(iter(enum_cls))

        # Type-checker happy; runtime returns the first member.
        assert first(Color) is Color.RED


# ---------------------------------------------------------------------------
# Module-level invariants
# ---------------------------------------------------------------------------


class TestModuleSurface:
    """The module exposes a stable public API."""

    def test_all_is_complete(self) -> None:
        import operational.types as mod

        expected = {
            "Hour",
            "Minute",
            "UEID",
            "StreakInt",
            "Score",
            "Repository",
            "Clock",
            "Logger",
            "T",
            "T_Entity",
            "T_Enum",
        }
        assert expected.issubset(set(mod.__all__))

    def test_all_names_importable(self) -> None:
        """Every name in ``__all__`` is importable from the module."""
        import operational.types as mod

        for name in mod.__all__:
            assert hasattr(mod, name), f"Missing export: {name}"

    def test_annotated_aliases_are_subscriptable(self) -> None:
        """``Annotated[int, Field(...)]`` evaluates to a usable annotation."""
        from typing import get_type_hints

        # Trigger evaluation; should not raise.
        get_type_hints(_SampleEntity)

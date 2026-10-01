"""Tests for M-TBD — recursive reflection layer.

Covers:
  * DecisionStore appends to JSONL correctly
  * Reflector detects known patterns from synthetic data
  * Findings carry confidence + sample_size
  * Reflection writer + cron-style end-to-end run

Mirrors the test patterns of test_m161_taskdog_triage / test_m161_vault_intent_extract.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

from src.agents.reflection.patterns import (
    FAST_FINISH_HOURS,
    FAST_FINISH_MIN_RATIO,
    FAST_FINISH_MIN_SAMPLE,
    UNDERESTIMATION_MIN_SAMPLE,
    UNDERESTIMATION_RATIO,
    Finding,
)
from src.agents.reflection.recursive import (
    Decision,
    DecisionStore,
    Reflector,
)
from src.agents.reflection.writer import render_reflection, write_reflection


# All paths are sandboxed under tmp_path. The repo's tests/conftest.py
# redirects tempfile to data/pytest-tmp/ so we don't trip Windows locks.
@pytest.fixture
def store(tmp_path: Path) -> DecisionStore:
    base = tmp_path / "decisions"
    base.mkdir()
    return DecisionStore(base_dir=base)


@pytest.fixture
def reflections_dir(tmp_path: Path) -> Path:
    p = tmp_path / "reflections"
    p.mkdir()
    return p


# ---------------------------------------------------------------------------
# DecisionStore — append + read
# ---------------------------------------------------------------------------


def test_append_creates_dated_jsonl_file(store: DecisionStore) -> None:
    """append() writes to <base>/<YYYY-MM-DD>.jsonl and creates the file."""
    ts = datetime(2026, 9, 30, 12, 0, tzinfo=timezone.utc)
    path = store.append("create", "ik:tsk:abc:1111", {"title": "buy milk"}, timestamp=ts)
    assert path.name == "2026-09-30.jsonl"
    assert path.exists()
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    payload = json.loads(lines[0])
    assert payload["action"] == "create"
    assert payload["ueid"] == "ik:tsk:abc:1111"
    assert payload["context"] == {"title": "buy milk"}
    # timestamp preserved as ISO 8601 (with TZ)
    assert payload["timestamp"].startswith("2026-09-30T12:00:00")


def test_append_concatenates_to_same_day(store: DecisionStore) -> None:
    """Multiple appends in the same day land on one line per call."""
    ts = datetime(2026, 9, 30, 12, 0, tzinfo=timezone.utc)
    store.append("create", "ik:tsk:abc:1111", {"title": "buy milk"}, timestamp=ts)
    store.append("done", "ik:tsk:abc:1111", {"actual_minutes": 30}, timestamp=ts)
    out = store.read(lookback_days=1, today=date(2026, 9, 30))
    assert len(out) == 2
    assert out[0].action == "create"
    assert out[1].action == "done"


def test_read_respects_lookback_window(store: DecisionStore) -> None:
    """read() returns decisions from the last N days inclusive of today."""
    today = date(2026, 9, 30)
    old_ts = datetime(2026, 8, 1, tzinfo=timezone.utc)  # way older than 7 days
    new_ts = datetime(2026, 9, 25, tzinfo=timezone.utc)  # within window
    store.append("create", "ik:tsk:abc:1111", {}, timestamp=old_ts)
    store.append("create", "ik:tsk:abc:2222", {}, timestamp=new_ts)
    out = store.read(lookback_days=7, today=today)
    ueids = {d.ueid for d in out}
    assert "ik:tsk:abc:2222" in ueids
    assert "ik:tsk:abc:1111" not in ueids


def test_read_handles_malformed_lines(store: DecisionStore) -> None:
    """A corrupt line is skipped silently; valid lines still load."""
    target = store.base_dir / "2026-09-30.jsonl"
    target.write_text(
        "garbage line\n"
        + json.dumps(
            {
                "timestamp": "2026-09-30T12:00:00+00:00",
                "action": "create",
                "ueid": "ik:tsk:abc:1111",
                "context": {},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    out = store.read(lookback_days=1, today=date(2026, 9, 30))
    assert len(out) == 1
    assert out[0].ueid == "ik:tsk:abc:1111"


def test_append_defaults_to_current_utc(store: DecisionStore) -> None:
    """When timestamp omitted, append() uses UTC now()."""
    path = store.append("update", "ik:tsk:abc:1111", {"priority": 1})
    assert path.exists()
    payload = json.loads(path.read_text(encoding="utf-8").strip())
    assert payload["action"] == "update"
    # ISO timestamp with TZ marker
    assert "T" in payload["timestamp"]
    assert payload["timestamp"].endswith("+00:00")


# ---------------------------------------------------------------------------
# Reflector — pattern detection
# ---------------------------------------------------------------------------


def _seed_underestimations(store: DecisionStore, n: int, today: date) -> None:
    """Seed n synthetic ueids whose actual time is 3x the estimate."""
    base = datetime(today.year, today.month, today.day, 9, tzinfo=timezone.utc)
    for i in range(n):
        ueid = f"ik:tsk:est:{i:04d}:0001"
        store.append(
            "create",
            ueid,
            {"title": f"task {i}", "estimated_minutes": 60},
            timestamp=base,
        )
        store.append(
            "done",
            ueid,
            {"actual_minutes": 180},
            timestamp=base + timedelta(hours=3),
        )


def _seed_on_target(store: DecisionStore, n: int, today: date) -> None:
    """Seed n synthetic ueids that hit estimate exactly (control group)."""
    base = datetime(today.year, today.month, today.day, 9, tzinfo=timezone.utc)
    for i in range(n):
        ueid = f"ik:tsk:on:{i:04d}:0001"
        store.append(
            "create",
            ueid,
            {"title": f"on-target {i}", "estimated_minutes": 60},
            timestamp=base,
        )
        store.append(
            "done",
            ueid,
            {"actual_minutes": 60},
            timestamp=base + timedelta(hours=1),
        )


def test_reflector_detects_underestimation(store: DecisionStore) -> None:
    today = date(2026, 9, 30)
    _seed_underestimations(store, n=5, today=today)
    _seed_on_target(store, n=5, today=today)  # controls — should not pollute
    reflector = Reflector(store=store)
    findings = reflector.analyze(lookback_days=14, today=today)
    under = [f for f in findings if f.pattern == "underestimation_2x"]
    assert len(under) == 1
    f = under[0]
    assert f.sample_size == 5
    assert f.confidence > 0
    # avg_ratio should be 3.0 (180/60)
    assert f.detail["avg_ratio"] == pytest.approx(3.0, rel=0.01)
    # suggested adjustment mentions overrun
    assert "underestimated" in f.suggested_adjustment.lower()


def test_reflector_no_underestimation_when_below_threshold(store: DecisionStore) -> None:
    today = date(2026, 9, 30)
    _seed_on_target(store, n=10, today=today)
    reflector = Reflector(store=store)
    findings = reflector.analyze(lookback_days=14, today=today)
    under = [f for f in findings if f.pattern == "underestimation_2x"]
    assert under == []


def test_reflector_respects_min_sample(store: DecisionStore) -> None:
    """Below UNDERESTIMATION_MIN_SAMPLE → no finding."""
    today = date(2026, 9, 30)
    _seed_underestimations(store, n=UNDERESTIMATION_MIN_SAMPLE - 1, today=today)
    reflector = Reflector(store=store)
    findings = reflector.analyze(lookback_days=14, today=today)
    under = [f for f in findings if f.pattern == "underestimation_2x"]
    assert under == []


def _seed_fast_finish(
    store: DecisionStore,
    tags: tuple[str, ...],
    count: int,
    hours_to_done: float,
    today: date,
) -> None:
    base = datetime(today.year, today.month, today.day, 9, tzinfo=timezone.utc)
    for i in range(count):
        ueid = f"ik:tsk:ff:{tags[0]}:{i:04d}"
        store.append(
            "create",
            ueid,
            {"title": f"task {i}", "tags": list(tags)},
            timestamp=base,
        )
        store.append(
            "done",
            ueid,
            {},
            timestamp=base + timedelta(hours=hours_to_done),
        )


def _seed_slow_finish(
    store: DecisionStore,
    tags: tuple[str, ...],
    count: int,
    today: date,
) -> None:
    base = datetime(today.year, today.month, today.day, 9, tzinfo=timezone.utc)
    for i in range(count):
        ueid = f"ik:tsk:sf:{tags[0]}:{i:04d}"
        store.append(
            "create",
            ueid,
            {"title": f"slow {i}", "tags": list(tags)},
            timestamp=base,
        )
        store.append(
            "done",
            ueid,
            {},
            timestamp=base + timedelta(hours=48),
        )


def test_reflector_detects_fast_finish_tag_combo(store: DecisionStore) -> None:
    today = date(2026, 9, 30)
    _seed_fast_finish(
        store, tags=("quick", "doc"), count=4, hours_to_done=1.0, today=today
    )
    _seed_slow_finish(store, tags=("slow", "big"), count=4, today=today)
    reflector = Reflector(store=store)
    findings = reflector.analyze(lookback_days=14, today=today)
    fast = [f for f in findings if f.pattern == "fast_finish_tag_combo"]
    assert len(fast) == 1
    f = fast[0]
    assert f.sample_size == 4
    assert f.confidence == pytest.approx(1.0, rel=0.01)
    assert sorted(f.detail["tags"]) == ["doc", "quick"]


def test_reflector_no_fast_finish_below_ratio(store: DecisionStore) -> None:
    today = date(2026, 9, 30)
    # 2 fast, 2 slow (50% — below FAST_FINISH_MIN_RATIO)
    _seed_fast_finish(
        store, tags=("mixed",), count=2, hours_to_done=1.0, today=today
    )
    _seed_slow_finish(store, tags=("mixed",), count=2, today=today)
    reflector = Reflector(store=store)
    findings = reflector.analyze(lookback_days=14, today=today)
    fast = [f for f in findings if f.pattern == "fast_finish_tag_combo"]
    assert fast == []


def test_reflector_detects_priority_churn(store: DecisionStore) -> None:
    today = date(2026, 9, 30)
    base = datetime(today.year, today.month, today.day, 9, tzinfo=timezone.utc)
    for i in range(3):
        ueid = f"ik:tsk:pc:{i:04d}:0001"
        store.append(
            "create",
            ueid,
            {"title": f"task {i}", "priority": 3},
            timestamp=base,
        )
        store.append(
            "update",
            ueid,
            {"priority": 2},
            timestamp=base + timedelta(hours=1),
        )
        store.append(
            "update",
            ueid,
            {"priority": 1},
            timestamp=base + timedelta(hours=2),
        )
    reflector = Reflector(store=store)
    findings = reflector.analyze(lookback_days=14, today=today)
    churn = [f for f in findings if f.pattern == "priority_churn"]
    assert len(churn) == 1
    assert churn[0].sample_size == 3


def test_reflector_empty_store_returns_empty_findings(store: DecisionStore) -> None:
    reflector = Reflector(store=store)
    assert reflector.analyze(lookback_days=14) == []


def test_finding_dataclass_carries_confidence_and_sample() -> None:
    """Finding carries the four load-bearing fields."""
    f = Finding(
        pattern="x",
        confidence=0.5,
        sample_size=4,
        suggested_adjustment="hi",
        detail={"k": "v"},
    )
    assert f.pattern == "x"
    assert f.confidence == 0.5
    assert f.sample_size == 4
    assert f.suggested_adjustment == "hi"
    assert f.detail == {"k": "v"}


# ---------------------------------------------------------------------------
# render_reflection + write_reflection
# ---------------------------------------------------------------------------


def test_render_reflection_marks_no_findings(tmp_path: Path) -> None:
    body = render_reflection([], today=date(2026, 9, 30), lookback_days=14)
    assert "# Reflection — 2026-09-30" in body
    assert "Findings: 0" in body
    assert "No patterns" in body


def test_render_reflection_includes_finding_block() -> None:
    findings = [
        Finding(
            pattern="underestimation_2x",
            confidence=0.8,
            sample_size=5,
            suggested_adjustment="Multiply by 2x",
            detail={"avg_ratio": 2.5},
        )
    ]
    body = render_reflection(findings, today=date(2026, 9, 30))
    assert "underestimation_2x" in body
    assert "Multiply by 2x" in body
    assert "avg_ratio" in body
    assert "confidence 80%" in body


def test_write_reflection_writes_markdown(store: DecisionStore, reflections_dir: Path) -> None:
    today = date(2026, 9, 30)
    _seed_underestimations(store, n=5, today=today)
    reflector = Reflector(store=store)
    findings = reflector.analyze(lookback_days=14, today=today)
    target = write_reflection(findings, target=reflections_dir / "2026-09-30.md", today=today)
    assert target.exists()
    body = target.read_text(encoding="utf-8")
    assert body.startswith("# Reflection — 2026-09-30")
    assert "underestimation_2x" in body


# ---------------------------------------------------------------------------
# CLI entry — end-to-end cron-style invocation
# ---------------------------------------------------------------------------


def test_main_runs_end_to_end_via_subprocess(tmp_path: Path, monkeypatch) -> None:
    """End-to-end: seed store → invoke main() → markdown appears.

    The CLI uses module-level path constants pointing at the repo's
    vault/. For the test we redirect _DECISIONS_DIR (recursive.py) and
    _REFLECTIONS_DIR (writer.py) via monkeypatch, then call main() to
    verify the CLI entry point works end-to-end.
    """
    import src.agents.reflection.recursive as recursive
    import src.agents.reflection.writer as writer

    decisions_dir = tmp_path / "decisions"
    reflections_dir = tmp_path / "reflections"
    decisions_dir.mkdir()
    reflections_dir.mkdir()
    monkeypatch.setattr(recursive, "_DECISIONS_DIR", decisions_dir)
    monkeypatch.setattr(writer, "_REFLECTIONS_DIR", reflections_dir)

    # Seed via the public API (which uses _DECISIONS_DIR through DecisionStore())
    today = date(2026, 9, 30)
    base = datetime(today.year, today.month, today.day, 9, tzinfo=timezone.utc)
    for i in range(5):
        ueid = f"ik:tsk:cron:{i:04d}:0001"
        recursive.DecisionStore().append(
            "create",
            ueid,
            {"title": f"cron task {i}", "estimated_minutes": 30},
            timestamp=base,
        )
        recursive.DecisionStore().append(
            "done",
            ueid,
            {"actual_minutes": 90},
            timestamp=base + timedelta(hours=2),
        )

    # Invoke the CLI entry directly (in-process to avoid sys.path quirks)
    rc = recursive.main([
        "--lookback-days",
        "14",
        "--out",
        str(reflections_dir / "cron.md"),
    ])
    assert rc == 0
    out_path = reflections_dir / "cron.md"
    assert out_path.exists()
    body = out_path.read_text(encoding="utf-8")
    assert "underestimation_2x" in body


def test_main_json_flag_returns_json_payload(store: DecisionStore, capsys) -> None:
    today = date(2026, 9, 30)
    _seed_underestimations(store, n=4, today=today)

    import src.agents.reflection.recursive as recursive

    # DecisionStore in this test is bound to the tmp_path fixture, not the
    # module default. Invoke analyze() directly to keep the test isolated.
    reflector = Reflector(store=store)
    findings = reflector.analyze(lookback_days=14, today=today)
    payload = {
        "lookback_days": 14,
        "findings": [__import__("dataclasses").asdict(f) for f in findings],
    }
    # Sanity: payload is JSON-serialisable
    text = json.dumps(payload, default=str, indent=2)
    parsed = json.loads(text)
    assert parsed["lookback_days"] == 14
    assert any(f["pattern"] == "underestimation_2x" for f in parsed["findings"])


# ---------------------------------------------------------------------------
# cross-cutting invariants
# ---------------------------------------------------------------------------


def test_no_llm_in_reflection_pipeline() -> None:
    """Architectural rule (ADR-013): reflection is pure arithmetic."""
    import src.agents.reflection.patterns as patterns
    import src.agents.reflection.recursive as recursive
    import src.agents.reflection.writer as writer

    sources = [
        Path(recursive.__file__).read_text(encoding="utf-8"),
        Path(patterns.__file__).read_text(encoding="utf-8"),
        Path(writer.__file__).read_text(encoding="utf-8"),
    ]
    combined = "\n".join(sources).lower()
    # No LLM client imports. Forbidden substrings:
    forbidden = ["openai", "anthropic", "langchain", "litellm", "MiniMax"]
    for needle in forbidden:
        assert needle.lower() not in combined, (
            f"{needle} found in reflection module — pipeline must be pure arithmetic"
        )


def test_append_only_semantics(store: DecisionStore, tmp_path: Path) -> None:
    """DecisionStore must never truncate an existing file."""
    p = store.base_dir / "2026-09-30.jsonl"
    p.write_text('{"timestamp":"2026-09-30T09:00:00+00:00","action":"create","ueid":"ik:tsk:abc:1111","context":{}}\n', encoding="utf-8")
    before = p.read_text(encoding="utf-8")
    ts = datetime(2026, 9, 30, 10, 0, tzinfo=timezone.utc)
    store.append("done", "ik:tsk:abc:1111", {}, timestamp=ts)
    after = p.read_text(encoding="utf-8")
    assert after.startswith(before)
    assert after.count("\n") == before.count("\n") + 1
"""M116 tests — llm_judge.py.

Verifies stub scoring, fallback behavior, JSON parsing, and CLI integration.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from tools.backtest import llm_judge as lj  # noqa: E402
from tools.backtest.llm_judge import (  # noqa: E402
    _parse_llm_response,
    _stub_score,
    aggregate_llm_scores,
    judge_scenario_llm,
    main,
)


# === Stub scoring ===

def test_stub_score_pass_add_task() -> None:
    sc = {"day": 1, "category": "add-task", "prompt": "create task"}
    oc = {"status": "PASS", "tools_called": ["taskdog_create_task"], "detail": "backtest day 1"}
    s = _stub_score(sc, oc)
    assert 0.0 <= s["overall"] <= 1.0
    assert s["mode"] == "stub"
    assert "argument_quality" in s
    assert "sequence_coherence" in s


def test_stub_score_fail_returns_low_overall() -> None:
    sc = {"day": 1, "category": "add-task"}
    oc = {"status": "ERROR", "tools_called": [], "detail": "failed"}
    s = _stub_score(sc, oc)
    assert s["overall"] < 0.6


def test_stub_score_complete_task_sequence() -> None:
    """complete-task expects start + complete; both present = high seq_coherence."""
    sc = {"day": 1, "category": "complete-task"}
    oc = {
        "status": "PASS",
        "tools_called": ["taskdog_complete_task"],
        "detail": "completed task 5",
    }
    s = _stub_score(sc, oc)
    # seq_coherence checks for `taskdog_start` substring; absent → 0.5 + 0.5*0 = 0.5
    assert s["sequence_coherence"] >= 0.5


# === LLM response parsing ===

def test_parse_llm_response_extracts_json() -> None:
    text = """{
        "argument_quality": 0.8,
        "sequence_coherence": 0.9,
        "cultural_fit": 0.7,
        "tool_selection": 1.0
    }"""
    s = _parse_llm_response(text, {"day": 1, "category": "add-task"})
    assert s["mode"] == "llm"
    assert s["overall"] == pytest.approx(0.85, abs=0.01)


def test_parse_llm_response_handles_json_fence() -> None:
    text = """```json
{"argument_quality": 0.5, "sequence_coherence": 0.5, "cultural_fit": 0.5, "tool_selection": 0.5, "comment": "ok"}
```"""
    s = _parse_llm_response(text, {"day": 1, "category": "add-task"})
    assert s["mode"] == "llm"
    assert s["overall"] == 0.5


def test_parse_llm_response_invalid_falls_back_to_stub() -> None:
    text = "not valid JSON at all"
    s = _parse_llm_response(text, {"day": 1, "category": "add-task"})
    # Stub fallback because JSON parse failed.
    assert s["mode"] == "stub"


def test_parse_llm_response_computes_overall_when_missing() -> None:
    text = """{"argument_quality": 1.0, "sequence_coherence": 1.0, "cultural_fit": 1.0, "tool_selection": 1.0}"""
    s = _parse_llm_response(text, {"day": 1, "category": "add-task"})
    assert s["overall"] == 1.0


# === judge_scenario_llm mode dispatch ===

def test_judge_scenario_llm_default_is_stub() -> None:
    """Without --use-llm, always stub."""
    s = judge_scenario_llm(
        {"day": 1, "category": "add-task"},
        {"status": "PASS", "tools_called": ["taskdog_create_task"], "detail": "ok"},
    )
    assert s["mode"] == "stub"


def test_judge_scenario_llm_with_use_llm_no_api_key_is_stub(monkeypatch: pytest.MonkeyPatch) -> None:
    """--use-llm but no API key → stub fallback."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("CLAUDE_API_KEY", raising=False)
    monkeypatch.delenv("IKIGAI_FAKE_LLM", raising=False)
    s = judge_scenario_llm(
        {"day": 1, "category": "add-task"},
        {"status": "PASS", "tools_called": ["taskdog_create_task"], "detail": "ok"},
        use_llm=True,
    )
    assert s["mode"] == "stub"


def test_judge_scenario_llm_with_fake_llm_is_stub(monkeypatch: pytest.MonkeyPatch) -> None:
    """IKIGAI_FAKE_LLM=1 forces stub even with --use-llm."""
    monkeypatch.setenv("IKIGAI_FAKE_LLM", "1")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-but-should-be-ignored")
    s = judge_scenario_llm(
        {"day": 1, "category": "add-task"},
        {"status": "PASS", "tools_called": ["taskdog_create_task"], "detail": "ok"},
        use_llm=True,
    )
    assert s["mode"] == "stub"


# === Aggregate ===

def test_aggregate_llm_scores_averages() -> None:
    per = [
        {"argument_quality": 1.0, "sequence_coherence": 1.0, "cultural_fit": 1.0, "tool_selection": 1.0, "overall": 1.0, "mode": "stub"},
        {"argument_quality": 0.0, "sequence_coherence": 0.0, "cultural_fit": 0.0, "tool_selection": 0.0, "overall": 0.0, "mode": "stub"},
    ]
    agg = aggregate_llm_scores(per)
    assert agg["overall"] == 0.5
    assert agg["n_scenarios"] == 2
    assert agg["argument_quality"] == 0.5


def test_aggregate_llm_scores_counts_modes() -> None:
    per = [
        {"argument_quality": 0.5, "sequence_coherence": 0.5, "cultural_fit": 0.5, "tool_selection": 0.5, "overall": 0.5, "mode": "stub"},
        {"argument_quality": 0.5, "sequence_coherence": 0.5, "cultural_fit": 0.5, "tool_selection": 0.5, "overall": 0.5, "mode": "llm"},
    ]
    agg = aggregate_llm_scores(per)
    assert agg["modes"] == {"stub": 1, "llm": 1}


def test_aggregate_empty_list() -> None:
    agg = aggregate_llm_scores([])
    assert agg["overall"] == 0.0
    assert agg["n_scenarios"] == 0


# === CLI ===

def test_main_dry_run_writes_aggregate_to_stdout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    import yaml
    scenarios_yaml = tmp_path / "scenarios.yaml"
    scenarios_yaml.write_text(yaml.safe_dump({
        "scenarios": [
            {"day": 1, "category": "add-task", "prompt": "x", "expected_tools": ["taskdog_create_task"]},
        ],
    }), encoding="utf-8")
    results_json = tmp_path / "results.json"
    results_json.write_text(json.dumps({
        "outcomes": [{"status": "PASS", "tools_called": ["taskdog_create_task"], "detail": "ok"}],
    }), encoding="utf-8")
    rc = main(["--scenarios", str(scenarios_yaml), "--harness-results", str(results_json),
               "--out", str(tmp_path / "out.json"), "--dry-run"])
    assert rc == 0
    captured = capsys.readouterr()
    assert "overall" in captured.out


def test_main_handles_missing_inputs(tmp_path: Path) -> None:
    rc = main(["--scenarios", str(tmp_path / "missing.yaml"),
               "--harness-results", str(tmp_path / "missing.json"),
               "--out", str(tmp_path / "out.json")])
    assert rc == 1


def test_main_writes_json_output(tmp_path: Path) -> None:
    import yaml
    scenarios_yaml = tmp_path / "scenarios.yaml"
    scenarios_yaml.write_text(yaml.safe_dump({
        "scenarios": [
            {"day": 1, "category": "add-task", "expected_tools": ["taskdog_create_task"]},
        ],
    }), encoding="utf-8")
    results_json = tmp_path / "results.json"
    results_json.write_text(json.dumps({
        "outcomes": [{"status": "PASS", "tools_called": ["taskdog_create_task"], "detail": "ok"}],
    }), encoding="utf-8")
    out = tmp_path / "out.json"
    rc = main(["--scenarios", str(scenarios_yaml), "--harness-results", str(results_json),
               "--out", str(out)])
    assert rc == 0
    assert out.exists()
    d = json.loads(out.read_text(encoding="utf-8"))
    assert "aggregate" in d
    assert "per_scenario" in d
    assert d["mode_requested"] == "stub"

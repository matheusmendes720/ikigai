"""M126 tests — real-LLM smoke for llm_judge.py.

Verifies the end-to-end behavior of `--use-llm` mode WITHOUT actually
calling the Anthropic API (we have no real key, only a hermes-agent proxy
token that's not directly usable with ChatAnthropic).

Coverage:
- `_real_llm_score` catches ModelError/ConnectionError → falls back to stub
- `_real_llm_score` catches JSON parse error → falls back to stub
- `_real_llm_score` catches generic Exception → falls back to stub
- `judge_scenario_llm` with fake `sk-ant-*` key constructs the model
  (proves code path is reached) — mocked ChatAnthropic returns a real response
- `judge_scenario_llm` with hermes-agent proxy key (`sk-cp-...`) hits
  the auth error path and falls back to stub
- `judge_scenario_llm` with NO key stays stub (skips LLM entirely)
- Pipeline end-to-end: `python llm_judge.py --use-llm` writes a JSON
  with `mode: stub_fallback` when proxy key fails

Honest scope:
- We don't pay for a real Anthropic API call in CI (no key, $0 budget).
- These tests prove the code PATHS reach ChatAnthropic; they don't prove
  the model returns sensible JSON for a real prompt.
- A real-LLM smoke (M126 follow-up) would set ANTHROPIC_API_KEY, run on
  3 scenarios, verify mode=='llm' for all 3.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch as mock_patch

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from tools.backtest import llm_judge as lj  # noqa: E402
from tools.backtest.llm_judge import (  # noqa: E402
    _parse_llm_response,
    _real_llm_score,
    _stub_score,
    judge_scenario_llm,
    main,
)


@pytest.fixture
def minimal_scenario() -> dict[str, Any]:
    return {
        "day": 1,
        "category": "add-task",
        "prompt": "Add a task",
        "expected_tools": ["taskdog_create_task"],
    }


@pytest.fixture
def minimal_outcome() -> dict[str, Any]:
    return {
        "status": "PASS",
        "tools_called": ["taskdog_create_task"],
        "detail": "task created",
    }


# === _real_llm_score fallback paths ===

def test_real_llm_falls_back_on_connection_error(
    minimal_scenario: dict[str, Any], minimal_outcome: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Network/auth error → stub_fallback mode, not crash."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-fake-test-key")
    monkeypatch.setattr(lj, "_LANGCHAIN_AVAILABLE", True)

    fake_model = MagicMock()
    fake_model.invoke.side_effect = ConnectionError("proxy refused")

    # Patch at the module level — `from langchain_anthropic import ChatAnthropic`
    # inside _real_llm_score imports the symbol from langchain_anthropic.
    with mock_patch("langchain_anthropic.ChatAnthropic", return_value=fake_model):
        s = _real_llm_score(minimal_scenario, minimal_outcome)
    assert s["mode"] == "stub_fallback"
    assert "error" in s
    # Accept any error class — the goal is "didn't crash, fell back to stub".
    assert s["comment"].startswith("LLM call failed")


def test_real_llm_falls_back_on_model_error(
    minimal_scenario: dict[str, Any], minimal_outcome: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """ModelError (langchain_core.exceptions.ModelError) → stub_fallback."""
    from langchain_core.exceptions import ModelError
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-fake-test-key")
    monkeypatch.setattr(lj, "_LANGCHAIN_AVAILABLE", True)

    fake_model = MagicMock()
    fake_model.invoke.side_effect = ModelError("model not available")

    with mock_patch("langchain_anthropic.ChatAnthropic", return_value=fake_model):
        s = _real_llm_score(minimal_scenario, minimal_outcome)
    assert s["mode"] == "stub_fallback"
    assert s["comment"].startswith("LLM call failed")


def test_real_llm_falls_back_on_generic_exception(
    minimal_scenario: dict[str, Any], minimal_outcome: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Any other exception → stub_fallback."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-fake-test-key")
    monkeypatch.setattr(lj, "_LANGCHAIN_AVAILABLE", True)

    fake_model = MagicMock()
    fake_model.invoke.side_effect = RuntimeError("something weird")

    with mock_patch("langchain_anthropic.ChatAnthropic", return_value=fake_model):
        s = _real_llm_score(minimal_scenario, minimal_outcome)
    assert s["mode"] == "stub_fallback"


def test_real_llm_success_path(
    minimal_scenario: dict[str, Any], minimal_outcome: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Successful LLM call returns mode='llm' with parsed JSON."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-fake-test-key")
    monkeypatch.setattr(lj, "_LANGCHAIN_AVAILABLE", True)

    fake_model = MagicMock()
    fake_response = MagicMock()
    fake_response.content = json.dumps({
        "argument_quality": 0.9,
        "sequence_coherence": 0.8,
        "cultural_fit": 0.7,
        "tool_selection": 1.0,
        "comment": "Looks good",
    })
    fake_model.invoke.return_value = fake_response

    with mock_patch("langchain_anthropic.ChatAnthropic", return_value=fake_model):
        s = _real_llm_score(minimal_scenario, minimal_outcome)
    assert s["mode"] == "llm"
    assert s["argument_quality"] == 0.9
    assert s["sequence_coherence"] == 0.8
    assert s["cultural_fit"] == 0.7
    assert s["tool_selection"] == 1.0
    assert s["overall"] == pytest.approx(0.85, abs=0.01)


def test_real_llm_json_parse_failure_falls_back(
    minimal_scenario: dict[str, Any], minimal_outcome: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """LLM returns garbage (not JSON) → stub_fallback."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-fake-test-key")
    monkeypatch.setattr(lj, "_LANGCHAIN_AVAILABLE", True)

    fake_model = MagicMock()
    fake_response = MagicMock()
    fake_response.content = "I cannot evaluate this."
    fake_model.invoke.return_value = fake_response

    with mock_patch("langchain_anthropic.ChatAnthropic", return_value=fake_model):
        s = _real_llm_score(minimal_scenario, minimal_outcome)
    # No JSON in response → falls back to stub (not stub_fallback — that path
    # is reserved for exceptions; JSON parse failure uses stub mode silently).
    assert s["mode"] == "stub"


# === judge_scenario_llm dispatch ===

def test_judge_scenario_no_key_stays_stub(
    minimal_scenario: dict[str, Any], minimal_outcome: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """No ANTHROPIC_API_KEY and no CLAUDE_API_KEY → stub (never tries LLM)."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("CLAUDE_API_KEY", raising=False)
    monkeypatch.delenv("IKIGAI_FAKE_LLM", raising=False)
    s = judge_scenario_llm(minimal_scenario, minimal_outcome, use_llm=True)
    assert s["mode"] == "stub"


def test_judge_scenario_use_llm_false_stays_stub(
    minimal_scenario: dict[str, Any], minimal_outcome: dict[str, Any]
) -> None:
    """use_llm=False → stub (explicit opt-in required)."""
    s = judge_scenario_llm(minimal_scenario, minimal_outcome, use_llm=False)
    assert s["mode"] == "stub"


def test_judge_scenario_hermes_proxy_key_reaches_model(
    minimal_scenario: dict[str, Any], minimal_outcome: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Hermes-agent proxy key (sk-cp-...) → ChatAnthropic is constructed, then
    the call fails (auth error from real Anthropic API), then stub_fallback.

    This proves the code PATH reaches ChatAnthropic — not that the call
    succeeds (we don't have a real Anthropic key).
    """
    monkeypatch.setenv("CLAUDE_API_KEY", "sk-cp-i-test-proxy-key")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(lj, "_LANGCHAIN_AVAILABLE", True)

    fake_model = MagicMock()
    fake_model.invoke.side_effect = ConnectionError("proxy doesn't reach Anthropic")

    with mock_patch("langchain_anthropic.ChatAnthropic", return_value=fake_model) as mock_cls:
        s = judge_scenario_llm(minimal_scenario, minimal_outcome, use_llm=True)
    # ChatAnthropic was called (code path reached).
    mock_cls.assert_called_once()
    assert s["mode"] == "stub_fallback"


# === End-to-end CLI ===

def test_main_use_llm_writes_stub_fallback_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Full CLI run with --use-llm flag — JSON should have stub_fallback mode."""
    import yaml

    scenarios_yaml = tmp_path / "scenarios.yaml"
    scenarios_yaml.write_text(yaml.safe_dump({
        "scenarios": [{"day": 1, "category": "add-task", "expected_tools": ["taskdog_create_task"]}],
    }), encoding="utf-8")
    results_json = tmp_path / "results.json"
    results_json.write_text(json.dumps({
        "outcomes": [{"status": "PASS", "tools_called": ["taskdog_create_task"], "detail": "ok"}],
    }), encoding="utf-8")
    out = tmp_path / "out.json"

    # Simulate proxy key in env — but force failure to avoid any real call.
    monkeypatch.setenv("CLAUDE_API_KEY", "sk-cp-i-test-proxy")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(lj, "_LANGCHAIN_AVAILABLE", True)

    fake_model = MagicMock()
    fake_model.invoke.side_effect = ConnectionError("simulated")

    with mock_patch("langchain_anthropic.ChatAnthropic", return_value=fake_model):
        rc = main(["--scenarios", str(scenarios_yaml), "--harness-results", str(results_json),
                   "--out", str(out), "--use-llm"])

    assert rc == 0
    assert out.exists()
    d = json.loads(out.read_text(encoding="utf-8"))
    assert d["mode_requested"] == "llm"
    # All scenarios should be stub_fallback because the proxy key failed.
    modes = set(s["mode"] for s in d["per_scenario"])
    assert modes == {"stub_fallback"}


def test_main_use_llm_no_key_stays_stub(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """--use-llm flag without API key → stub mode (never tried)."""
    import yaml

    scenarios_yaml = tmp_path / "scenarios.yaml"
    scenarios_yaml.write_text(yaml.safe_dump({
        "scenarios": [{"day": 1, "category": "add-task"}],
    }), encoding="utf-8")
    results_json = tmp_path / "results.json"
    results_json.write_text(json.dumps({
        "outcomes": [{"status": "PASS", "tools_called": ["taskdog_create_task"], "detail": "ok"}],
    }), encoding="utf-8")
    out = tmp_path / "out.json"

    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("CLAUDE_API_KEY", raising=False)

    rc = main(["--scenarios", str(scenarios_yaml), "--harness-results", str(results_json),
               "--out", str(out), "--use-llm"])
    assert rc == 0
    d = json.loads(out.read_text(encoding="utf-8"))
    assert d["mode_requested"] == "llm"
    modes = set(s["mode"] for s in d["per_scenario"])
    # Without a key, the code path skips LLM entirely → stub mode.
    assert modes == {"stub"}


def test_model_name_env_var_is_honored(
    minimal_scenario: dict[str, Any], minimal_outcome: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """IKIGAI_MODEL env var overrides the default model name."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-fake-test-key")
    monkeypatch.setenv("IKIGAI_MODEL", "claude-3-haiku-20240307")
    monkeypatch.setattr(lj, "_LANGCHAIN_AVAILABLE", True)

    fake_model = MagicMock()
    fake_model.invoke.side_effect = ConnectionError("test")

    with mock_patch("langchain_anthropic.ChatAnthropic", return_value=fake_model) as mock_cls:
        _real_llm_score(minimal_scenario, minimal_outcome)
    # ChatAnthropic was called with the IKIGAI_MODEL value.
    args, kwargs = mock_cls.call_args
    assert kwargs.get("model") == "claude-3-haiku-20240307" or args and args[0] == "claude-3-haiku-20240307"


# === Real-shape integration smoke ===

def test_real_llm_integration_smoke_with_realistic_response(
    minimal_scenario: dict[str, Any], minimal_outcome: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """End-to-end smoke test with a realistic Anthropic response shape.

    Doesn't make a real API call — uses a mocked model that returns a response
    matching the shape Anthropic actually returns. Verifies:
    - .content attribute extraction (the canonical LangChain way)
    - JSON parsing of realistic 4-dimension response
    - mode='llm' assignment
    - all 4 dimensions extracted
    - comment field preserved

    This is the closest we can get to a real-LLM smoke without an API key.
    """
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-fake-test-key")
    monkeypatch.setattr(lj, "_LANGCHAIN_AVAILABLE", True)

    fake_model = MagicMock()
    # Mimic langchain_anthropic response shape — content is a string,
    # JSON-formatted, all 4 dimensions present.
    fake_model.invoke.return_value = MagicMock(content=(
        '{"argument_quality": 0.85, '
        '"sequence_coherence": 0.92, '
        '"cultural_fit": 0.65, '
        '"tool_selection": 0.98, '
        '"comment": "Good fit for the add-task scenario."}'
    ))

    with mock_patch("langchain_anthropic.ChatAnthropic", return_value=fake_model):
        s = _real_llm_score(minimal_scenario, minimal_outcome)
    assert s["mode"] == "llm"
    assert s["argument_quality"] == 0.85
    assert s["sequence_coherence"] == 0.92
    assert s["cultural_fit"] == 0.65
    assert s["tool_selection"] == 0.98
    # overall computed from 4 dims (not provided in response)
    expected_overall = round((0.85 + 0.92 + 0.65 + 0.98) / 4, 3)
    assert s["overall"] == expected_overall
    assert s["comment"] == "Good fit for the add-task scenario."


def test_real_llm_json_fence_parsed(
    minimal_scenario: dict[str, Any], minimal_outcome: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Response wrapped in ```json ... ``` fence is still parsed."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-fake-test-key")
    monkeypatch.setattr(lj, "_LANGCHAIN_AVAILABLE", True)

    fake_model = MagicMock()
    fake_model.invoke.return_value = MagicMock(content=(
        "```json\n"
        '{"argument_quality": 0.5, "sequence_coherence": 0.5, '
        '"cultural_fit": 0.5, "tool_selection": 0.5, "comment": "ok"}\n'
        "```"
    ))

    with mock_patch("langchain_anthropic.ChatAnthropic", return_value=fake_model):
        s = _real_llm_score(minimal_scenario, minimal_outcome)
    assert s["mode"] == "llm"
    assert s["overall"] == 0.5


def test_real_llm_prompt_includes_scenario_context(
    monkeypatch: pytest.MonkeyPatch
) -> None:
    """The prompt sent to ChatAnthropic contains scenario + outcome context."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-fake-test-key")
    monkeypatch.setattr(lj, "_LANGCHAIN_AVAILABLE", True)

    fake_model = MagicMock()
    fake_model.invoke.return_value = MagicMock(content=(
        '{"argument_quality": 0.7, "sequence_coherence": 0.7, '
        '"cultural_fit": 0.7, "tool_selection": 0.7}'
    ))

    scenario = {
        "day": 5,
        "category": "complete-task",
        "prompt": "Mark the daily task complete",
        "expected_tools": ["taskdog_complete_task"],
    }
    outcome = {
        "status": "PASS",
        "tools_called": ["taskdog_start", "taskdog_complete_task"],
        "detail": "Task 42 completed at 14:30",
    }

    with mock_patch("langchain_anthropic.ChatAnthropic", return_value=fake_model):
        _real_llm_score(scenario, outcome)

    # Verify the prompt included the scenario context.
    call_args = fake_model.invoke.call_args
    prompt_text = call_args[0][0] if call_args[0] else call_args.kwargs.get("input", "")
    assert "Day: 5" in prompt_text
    assert "complete-task" in prompt_text
    assert "taskdog_complete_task" in prompt_text
    assert "PASS" in prompt_text

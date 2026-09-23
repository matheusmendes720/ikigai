"""M116 — llm_judge.py

Optional LLM-judge layer that complements the rule-based judge (M114c).

Mode:
  - Default: rule-based only (M114c) — fast, deterministic, no API.
  - --use-llm: try to call an LLM via langchain_anthropic ChatAnthropic.
    Falls back to deterministic stub when:
      - IKIGAI_FAKE_LLM=1 (test mode)
      - ANTHROPIC_API_KEY not set
      - chat model raises ModelError / ConnectionError

LLM judge evaluates qualitative dimensions the rule judge can't:
  - Argument quality: did the agent pass sensible task_name / priority / tags?
  - Sequence coherence: did the agent follow a sensible order (create → start → complete)?
  - Cultural fit: does the response respect PT-BR + ABT framing where applicable?
  - Tool selection: did the agent pick the right tool for the scenario's intent?

Output: 4-dimension score 0.0-1.0 + qualitative comments per scenario.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

# Try to import langchain for LLM calls. Optional — gracefully degrade.
_LANGCHAIN_AVAILABLE = False
try:
    from langchain_anthropic import ChatAnthropic  # noqa: F401

    _LANGCHAIN_AVAILABLE = True
except ImportError:
    pass


# === Deterministic stub (IKIGAI_FAKE_LLM=1 or no LLM available) ===

def _stub_score(scenario: dict[str, Any], outcome: dict[str, Any]) -> dict[str, Any]:
    """Deterministic LLM-judge stub — heuristic qualitative scoring."""
    status = outcome.get("status", "PENDING")
    tools = outcome.get("tools_called", [])
    detail = outcome.get("detail", "")
    category = scenario.get("category", "")

    # Argument quality: did name/priority/tags look sensible?
    if "backtest" in detail.lower() or "day" in detail.lower():
        arg_quality = 0.8
    elif status == "PASS":
        arg_quality = 0.7
    else:
        arg_quality = 0.4

    # Sequence coherence: tools_called order matches scenario category intent.
    expected_seq: dict[str, list[str]] = {
        "add-task": ["taskdog_create_task"],
        "list-tasks": ["taskdog_list_tasks"],
        "update-task": ["taskdog_update_task"],
        "complete-task": ["taskdog_start", "taskdog_complete_task"],
        "decompose": ["taskdog_create_task"],
        "daily-plan": ["taskdog_list_tasks"],
        "weekly-review": ["taskdog_get_metrics"],
    }
    expected = expected_seq.get(category, [])
    seq_match = sum(1 for t in expected if any(t in ct for ct in tools)) / max(len(expected), 1)
    seq_coherence = max(0.0, min(1.0, 0.5 + 0.5 * seq_match))

    # Cultural fit: PT-BR tags / ABT framing.
    cultural_fit = 0.6 if status == "PASS" else 0.3

    # Tool selection: were the right tool types chosen?
    tool_selection = 1.0 if tools and status == "PASS" else (0.5 if tools else 0.0)

    overall = (arg_quality + seq_coherence + cultural_fit + tool_selection) / 4

    return {
        "mode": "stub",
        "argument_quality": round(arg_quality, 3),
        "sequence_coherence": round(seq_coherence, 3),
        "cultural_fit": round(cultural_fit, 3),
        "tool_selection": round(tool_selection, 3),
        "overall": round(overall, 3),
        "comment": f"Deterministic stub score for day {scenario.get('day')} ({category}); status={status}",
    }


# === LLM call (when available) ===

def _real_llm_score(
    scenario: dict[str, Any], outcome: dict[str, Any]
) -> dict[str, Any]:
    """Real LLM call via ChatAnthropic. Falls back to stub on any error."""
    from langchain_anthropic import ChatAnthropic  # type: ignore

    model_name = os.environ.get("IKIGAI_MODEL", "MiniMax-M2.7-highspeed")
    prompt = f"""You are an LLM-judge evaluating a backtest scenario.

Scenario:
- Day: {scenario.get('day')}
- Category: {scenario.get('category')}
- Prompt: {scenario.get('prompt', '?')}
- Expected tools: {scenario.get('expected_tools', [])}

Outcome:
- Status: {outcome.get('status')}
- Tools called: {outcome.get('tools_called', [])}
- Detail: {outcome.get('detail', '')}

Evaluate 4 dimensions (0.0-1.0):
1. argument_quality: did the agent pass sensible task_name / priority / tags?
2. sequence_coherence: did tool order follow a sensible workflow?
3. cultural_fit: does the response respect PT-BR + ABT framing where applicable?
4. tool_selection: did the agent pick the right tool for the intent?

Return JSON only, no prose:
{{"argument_quality": <float>, "sequence_coherence": <float>,
 "cultural_fit": <float>, "tool_selection": <float>,
 "comment": "<1-sentence PT-BR rationale>"}}"""

    try:
        model = ChatAnthropic(model=model_name)
        response = model.invoke(prompt)
        text = response.content if hasattr(response, "content") else str(response)
        return _parse_llm_response(text, scenario)
    except Exception as e:
        return {
            "mode": "stub_fallback",
            "argument_quality": 0.5,
            "sequence_coherence": 0.5,
            "cultural_fit": 0.5,
            "tool_selection": 0.5,
            "overall": 0.5,
            "comment": f"LLM call failed ({type(e).__name__}); using stub fallback",
            "error": str(e),
        }


def _parse_llm_response(text: str, scenario: dict[str, Any]) -> dict[str, Any]:
    """Extract JSON from LLM response, fall back to stub if parse fails."""
    # Find JSON block (handles ```json fences)
    m = re.search(r"\{[^{}]*\}", text, re.DOTALL)
    if not m:
        return _stub_score(scenario, {"status": "PARSED_FAILED", "tools_called": []})
    try:
        d = json.loads(m.group(0))
        d["mode"] = "llm"
        # Compute overall if not provided.
        if "overall" not in d:
            dims = [
                d.get("argument_quality", 0.0),
                d.get("sequence_coherence", 0.0),
                d.get("cultural_fit", 0.0),
                d.get("tool_selection", 0.0),
            ]
            d["overall"] = round(sum(dims) / 4, 3)
        return d
    except json.JSONDecodeError:
        return _stub_score(scenario, {"status": "PARSED_FAILED", "tools_called": []})


# === Public API ===

def judge_scenario_llm(
    scenario: dict[str, Any], outcome: dict[str, Any], *, use_llm: bool = False
) -> dict[str, Any]:
    """Returns LLM-judge qualitative scores for one scenario."""
    if not use_llm:
        return _stub_score(scenario, outcome)
    if os.environ.get("IKIGAI_FAKE_LLM", "0") == "1":
        return _stub_score(scenario, outcome)
    if not _LANGCHAIN_AVAILABLE:
        return _stub_score(scenario, outcome)
    if not _is_real_llm_available():
        return _stub_score(scenario, outcome)
    return _real_llm_score(scenario, outcome)


def _is_real_llm_available() -> bool:
    """M139: detect whether a real LLM call is possible.

    Returns True iff:
      - langchain_anthropic is importable, AND
      - IKIGAI_FAKE_LLM is not set to "1", AND
      - ANTHROPIC_API_KEY OR CLAUDE_API_KEY is set.

    When False, `judge_scenario_llm(..., use_llm=True)` will fall back
    to the stub. This is the canonical gate for tests that want to
    `pytest.skip` when the LLM is unavailable.
    """
    if not _LANGCHAIN_AVAILABLE:
        return False
    if os.environ.get("IKIGAI_FAKE_LLM", "0") == "1":
        return False
    if os.environ.get("ANTHROPIC_API_KEY"):
        return True
    if os.environ.get("CLAUDE_API_KEY"):
        return True
    return False


def aggregate_llm_scores(per_scenario: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate per-scenario LLM scores into a single roll-up."""
    if not per_scenario:
        return {
            "argument_quality": 0.0,
            "sequence_coherence": 0.0,
            "cultural_fit": 0.0,
            "tool_selection": 0.0,
            "overall": 0.0,
            "n_scenarios": 0,
        }
    n = len(per_scenario)
    dims = ["argument_quality", "sequence_coherence", "cultural_fit", "tool_selection"]
    out: dict[str, Any] = {d: round(sum(s.get(d, 0.0) for s in per_scenario) / n, 3) for d in dims}
    out["overall"] = round(sum(s.get("overall", 0.0) for s in per_scenario) / n, 3)
    out["n_scenarios"] = n
    out["modes"] = {}
    for s in per_scenario:
        m = s.get("mode", "?")
        out["modes"][m] = out["modes"].get(m, 0) + 1
    return out


# === CLI ===

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="LLM-judge layer for backtest scenarios.")
    parser.add_argument(
        "--scenarios", type=Path,
        default=REPO_ROOT / "vault" / "drafts" / "q3-scenarios.with-anchors.yaml",
    )
    parser.add_argument(
        "--harness-results", type=Path,
        default=REPO_ROOT / "reports" / "backtest-Q1-results.json",
    )
    parser.add_argument(
        "--out", type=Path,
        default=REPO_ROOT / "reports" / "backtest-Q1-llm-judgment.json",
    )
    parser.add_argument(
        "--use-llm", action="store_true",
        help="Try real LLM via ChatAnthropic; fallback to stub if unavailable.",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--limit", type=int, default=0,
        help="Limit number of scenarios (0 = all). Useful for smoke testing.",
    )
    args = parser.parse_args(argv)

    if not args.scenarios.exists():
        print(f"# Missing scenarios file: {args.scenarios}", file=sys.stderr)
        return 1
    if not args.harness_results.exists():
        print(f"# Missing harness results: {args.harness_results}", file=sys.stderr)
        return 1

    import yaml  # noqa: E402
    src = yaml.safe_load(args.scenarios.read_text(encoding="utf-8"))
    scenarios = src.get("scenarios", []) if isinstance(src, dict) else src
    harness = json.loads(args.harness_results.read_text(encoding="utf-8"))
    outcomes = harness.get("outcomes", [])

    if args.limit > 0:
        scenarios = scenarios[:args.limit]
        outcomes = outcomes[:args.limit]

    per_scenario: list[dict[str, Any]] = []
    for sc, oc in zip(scenarios, outcomes):
        score = judge_scenario_llm(sc, oc, use_llm=args.use_llm)
        score["day"] = sc.get("day")
        score["category"] = sc.get("category")
        score["status"] = oc.get("status")
        per_scenario.append(score)

    aggregate = aggregate_llm_scores(per_scenario)
    result = {
        "aggregate": aggregate,
        "per_scenario": per_scenario,
        "mode_requested": "llm" if args.use_llm else "stub",
    }
    print(json.dumps(aggregate, indent=2))
    if args.dry_run:
        return 0
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"# Wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""render_h4_market_fit — H4 market fit observation via LLM prompt.

Reads from vault/ikigai/meta/cycle_state/{date}.md (PAV-written) and emits
observation JSON via LLM. Falls back to deterministic stub when IKIGAI_FAKE_LLM=1.
"""

from __future__ import annotations

import json
import os
from datetime import date
from pathlib import Path
from typing import Any, cast

from langchain_core.prompts import PromptTemplate

_PROMPT = PromptTemplate(
    input_variables=["cycle_state", "habit_state", "strategics_excerpt"],
    template="""Você é o agente IKIGAI — assistente de planejamento (NÃO executa matemática).
Leia o estado do ciclo abaixo e emita uma observação estruturada em JSON.

## Estado do Ciclo (PAV-escrito)
{cycle_state}

## Estado do Hábito
{habit_state}

## Regras Estratégicas (PT-BR)
{strategics_excerpt}

## Tarefa
Estime o market fit (0.0-1.0) com base no ciclo atual.
Justifique em 2-3 frases em pt-BR.

Retorne JSON: {{"h4_market_fit": <float 0.0-1.0>, "rationale": "<pt-BR 2-3 sentences>"}}""",
)


def render_h4_market_fit(state: dict[str, Any]) -> dict[str, Any]:
    """Render H4 market fit observation via LLM (real LLM; deterministic stub when IKIGAI_FAKE_LLM=1)."""

    if os.environ.get("IKIGAI_FAKE_LLM", "0") == "1":
        return {"h4_market_fit": 0.5, "rationale": "[FAKE-LLM stub for test]"}
    today = date.today().isoformat()
    vault_root = Path(state.get("vault_root", "vault"))
    cycle_state = _read_vault(vault_root / "ikigai/meta/cycle_state" / f"{today}.md")
    habit_state = _read_vault(vault_root / "ikigai/meta/habit_state" / f"{today}.md")
    strategics = _read_vault(vault_root / "_strategics_excerpt.md")
    prompt = _PROMPT.format(
        cycle_state=cycle_state,
        habit_state=habit_state,
        strategics_excerpt=strategics[:2000],
    )
    try:
        # M158e: the shim MUST be imported before langchain_anthropic — it patches
        # anthropic.OverloadedError, which langchain_anthropic subclasses at import
        # time. Keep this import first (isort block order is intentional).
        import agents.v2.langchain_anthropic_shim  # noqa: F401, I001  # M158e
        from langchain_anthropic import ChatAnthropic

        # `model` is a pydantic field whose alias is `model_name`; the kwargs dict
        # keeps the runtime spelling `model=` (accepted via populate_by_name) while
        # satisfying mypy, whose dataclass_transform view of __init__ only exposes
        # the alias.
        llm_kwargs: dict[str, Any] = {
            "model": os.environ.get("IKIGAI_MODEL", "MiniMax-M2.7-highspeed")
        }
        model = ChatAnthropic(**llm_kwargs)
        response = model.invoke(prompt)
        # The shim (agents.v2.langchain_anthropic_shim.install_response_normalizer)
        # rewrites response.content to a plain str before it reaches us.
        return _parse_json(cast(str, response.content))
    except Exception as exc:
        return {"error": "llm_call_failed", "exception": str(exc)}


def _read_vault(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (FileNotFoundError, OSError):
        return ""


def _parse_json(content: str) -> dict[str, Any]:
    try:
        return cast(dict[str, Any], json.loads(content))
    except json.JSONDecodeError as exc:
        return {"error": "parse_failed", "raw": content, "exception": str(exc)}

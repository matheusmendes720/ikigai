"""render_h1_energy — H1 energy factor (0.0-1.0) via LLM prompt.

Reads from vault/ikigai/meta/cycle_state/{date}.md (PAV-written) and emits
observation JSON via LLM. Falls back to deterministic stub when IKIGAI_FAKE_LLM=1.
"""

from __future__ import annotations

import json
import os
from datetime import date
from pathlib import Path
from typing import Any

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
Estime o fator de energia requerida H1 (0.0-1.0) onde 1.0 = energia máxima necessária.
Justifique em 2-3 frases em pt-BR.

Retorne JSON: {{"h1_energy": <float 0.0-1.0>, "rationale": "<pt-BR 2-3 sentences>"}}""",
)


def render_h1_energy(state: dict[str, Any]) -> dict[str, Any]:
    """Render H1 energy observation via LLM (or deterministic stub in fake mode)."""
    if os.environ.get("IKIGAI_FAKE_LLM", "0") == "1":
        return {"h1_energy": 0.7, "rationale": "[FAKE-LLM stub for test]"}
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
        from langchain_anthropic import ChatAnthropic

        model = ChatAnthropic(model=os.environ.get("IKIGAI_MODEL", "MiniMax-M2.7-highspeed"))
        response = model.invoke(prompt)
        return _parse_json(response.content)
    except Exception as exc:
        return {"error": "llm_call_failed", "exception": str(exc)}


def _read_vault(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (FileNotFoundError, OSError):
        return ""


def _parse_json(content: str) -> dict[str, Any]:
    try:
        return json.loads(content)
    except json.JSONDecodeError as exc:
        return {"error": "parse_failed", "raw": content, "exception": str(exc)}

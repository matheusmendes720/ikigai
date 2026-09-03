"""surface_pav_intentions — pt-BR prompt template for surfacing PAV-written state.

Reads cycle_state + daily reports from vault (PAV-written) and emits
3-5 user-facing suggestion strings via LLM. Falls back to deterministic
stub when IKIGAI_FAKE_LLM=1 (test mode).
"""

from __future__ import annotations

import json
import os
from datetime import date
from pathlib import Path
from typing import Any

from langchain_core.prompts import PromptTemplate

_PROMPT = PromptTemplate(
    input_variables=["cycle_state", "daily_reports", "strategics_excerpt", "language"],
    template="""Você é o agente IKIGAI — assistente de planejamento (NÃO executa matemática).
Leia o estado PAV-escrito abaixo e emita 3-5 sugestões acionáveis para o usuário em pt-BR.

## Estado do Ciclo (PAV-escrito)
{cycle_state}

## Relatórios Diários (últimos 3)
{daily_reports}

## Regras Estratégicas (PT-BR)
{strategics_excerpt}

## Tarefa
Emita 3-5 sugestões concretas que o usuário pode considerar AGORA. Cada sugestão
deve ser específica (não genérica como "trabalhe mais") e referenciar elementos
do estado acima.

Retorne JSON: {{"suggestions": ["<pt-BR sugestão 1>", "<pt-BR sugestão 2>", ...]}}

IMPORTANTE: Responda no idioma: {language}""",
)


def render_surface_pav_intentions(state: dict[str, Any]) -> dict[str, Any]:
    """Render PAV intention surfacing via LLM (or deterministic stub in fake mode)."""
    if os.environ.get("IKIGAI_FAKE_LLM", "0") == "1":
        # Deterministic stub for tests
        return {
            "suggestions": [
                "[FAKE-LLM] Considere revisar tasks com regime RECOVER ativo",
                "[FAKE-LLM] Vector passion_score baixo — ajustar hábito matinal",
                "[FAKE-LLM] Q_HE em declínio — priorizar completion de tasks pendentes",
                "[FAKE-LLM] Verificar alinhamento com SONHO atual",
            ],
            "language": "pt-BR",
            "source": "fake-llm-stub",
        }

    today = date.today().isoformat()
    vault_root = Path(state.get("vault_root", "vault"))
    cycle_state_file = vault_root / "ikigai" / "meta" / "cycle_state" / f"{today}.md"
    cycle_state = _read_vault(cycle_state_file)

    # Read last 3 daily reports
    daily_reports: list[str] = []
    daily_reports_dir = vault_root / "ikigai" / "closing-2026"
    if daily_reports_dir.exists():
        for report_dir in daily_reports_dir.rglob("04-relatorios-diarios"):
            if report_dir.is_dir():
                reports = sorted(
                    report_dir.glob("*.md"),
                    key=lambda p: p.name,
                    reverse=True,
                )[:3]
                for r in reports:
                    daily_reports.append(_read_vault(r)[:1000])
    daily_reports_str = "\n\n---\n\n".join(daily_reports) if daily_reports else "(sem relatórios)"

    strategics = _read_vault(vault_root / "_strategics_excerpt.md")

    prompt = _PROMPT.format(
        cycle_state=cycle_state[:3000] if cycle_state else "(sem cycle_state)",
        daily_reports=daily_reports_str[:3000],
        strategics_excerpt=strategics[:1500],
        language="pt-BR",
    )
    try:
        from langchain_anthropic import ChatAnthropic

        model = ChatAnthropic(model=os.environ.get("IKIGAI_MODEL", "MiniMax-M2.7-highspeed"))
        response = model.invoke(prompt)
        parsed = _parse_json(response.content)
        parsed["language"] = "pt-BR"
        parsed["source"] = "llm"
        return parsed
    except Exception as exc:
        return {
            "suggestions": [],
            "error": "llm_call_failed",
            "exception": str(exc),
            "language": "pt-BR",
        }


def _read_vault(path: Path) -> str:
    """Read vault file safely; return empty string if missing."""
    try:
        return path.read_text(encoding="utf-8")
    except (FileNotFoundError, OSError):
        return ""


def _parse_json(content: str) -> dict[str, Any]:
    """Parse LLM JSON output; fall back to error dict on parse failure."""
    try:
        parsed = json.loads(content)
        if "suggestions" not in parsed:
            parsed = {"suggestions": [], "error": "missing_suggestions_field", "raw": content}
        return parsed
    except json.JSONDecodeError as exc:
        return {"suggestions": [], "error": "parse_failed", "raw": content, "exception": str(exc)}

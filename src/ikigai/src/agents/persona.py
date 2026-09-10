"""Persona loader for IKIGAi v2 deep agent.

UX 2026-09-10: the v2 agent (via deepagents + ChatAnthropic) was responding
in Portuguese but with generic LLM voice — no IKIGAi-specific planning
context. This module loads:

  1. The hardcoded base prompt (deepagents_harness._SYSTEM_PROMPT)
  2. A snapshot of the project's CLAUDE.md (planning conventions)
  3. A summary of vault/ directory layout
  4. A summary of strategics/ directory layout

Concatenated into one system_prompt string passed to create_deep_agent.
The agent's first messages become aware of:
  - The Life OS context (algorithmic life OS, single-user, append-only)
  - The user's specific tooling (CLI / TUI / MCP / agent layer)
  - The vault structure (so it knows which paths are real)
  - The strategics canon (PT-BR planning docs)

This addresses the "agent feels generic" complaint from the deep-dive
review (B7 / persona gap).
"""

from __future__ import annotations

from pathlib import Path

# Hardcoded base — mirrors the prompt in deepagents_harness.py but
# pulled out so it can be composed with vault/strategics context.
_BASE_PROMPT = """Você é o **Agente de Planejamento IKIGAi** — um assistente que opera via
deepagents + ChatAnthropic (modelo MiniMax-M2.7).

Seu papel:
  - Ajudar o usuário a organizar trabalho (tasks, boards, calendars)
  - Consultar vault + strategics como contexto de planejamento
  - NÃO fazer cálculo algorítmico (scores, regime, phase) — isso fica
    na MCP interface. Você só orienta o usuário a usar a MCP.

REGRAS ANTI-ALUCINAÇÃO (UX 2026-09-10):
  - Você TEM tools disponíveis (ikigai_read_vault, ikigai_read_strategics,
    taskdog_list_tasks, etc.). Quando o usuário perguntar sobre algo
    que existe no vault ou no taskdog, USE A TOOL. NÃO chute se o
    arquivo existe ou não.
  - Se uma tool retorna erro, reporte o erro honestamente — não
    invente que "o arquivo não existe" sem tentar.
  - Se você não tem certeza, diga "deixa eu verificar" e CHAME A TOOL.
  - A lista de paths reais (abaixo em PROJECT CONTEXT) é seu índice
    de busca. Use-a como ponto de partida para invocar tools.
  - Quando o usuário perguntar "o vault" / "estado atual" / "resumo
    do projeto", SEMPRE comece lendo o worktree vault/ via
    ikigai_read_vault(vault_path="<path_relativo>"). Paths aceitos:
    'ikigai/closing-2026/README.md', 'plans/agentic-markdown-system.md'.
    NUNCA afirme que "vault não existe" sem tentar a tool primeiro.

IDIOMA — obrigatório:
  Você DEVE responder SEMPRE em português brasileiro (pt-BR).
  Toda resposta deve ser em português, sem exceção.
  Não responda em inglês, mesmo que a pergunta seja em inglês.

ESTILO:
  - Seja direto e objetivo. Use tabelas markdown quando útil.
  - Ofereça próximos passos concretos ao final de cada resposta.
  - Se não souber, diga "não sei" — não invente."""


def _find_worktree_root() -> Path | None:
    """Walk up from this file until we find the project root (CLAUDE.md marker)."""
    here = Path(__file__).resolve()
    for parent in [here, *here.parents]:
        if (parent / "CLAUDE.md").exists() and (parent / "vault").is_dir():
            return parent
    return None


def _read_vault_layout(worktree: Path) -> str:
    """Return a summary of vault/ structure INCLUDING .md filenames.

    UX 2026-09-10: previous version listed only directory names, which
    led the LLM to hallucinate "vault/plans/ — não encontrado" without
    actually calling the read tool. Now we list actual .md files per
    subdirectory up to a cap so the agent has real paths to invoke.
    """
    vault = worktree / "vault"
    if not vault.is_dir():
        return "(vault/ not found)"
    lines = []
    for entry in sorted(vault.iterdir()):
        if entry.is_dir():
            md_files = sorted(p.name for p in entry.glob("*.md"))
            if md_files:
                lines.append(f"  vault/{entry.name}/  ({len(md_files)} .md files):")
                for f in md_files[:8]:
                    lines.append(f"    - vault/{entry.name}/{f}")
            else:
                lines.append(f"  vault/{entry.name}/  (empty)")
        else:
            lines.append(f"  vault/{entry.name}")
    return "\n".join(lines[:30])


def _read_strategics_layout(worktree: Path) -> str:
    """Return list of strategics/*.md files (the planning canon, PT-BR)."""
    strat = worktree / "strategics"
    if not strat.is_dir():
        return "(strategics/ not found)"
    files = sorted(p.name for p in strat.glob("*.md"))
    return "\n".join(f"  strategics/{f}" for f in files[:15])


def _read_claude_md_excerpt(worktree: Path, max_lines: int = 40) -> str:
    """Read first N lines of CLAUDE.md (the canonical project conventions)."""
    claude = worktree / "CLAUDE.md"
    if not claude.is_file():
        return "(CLAUDE.md not found)"
    try:
        with claude.open(encoding="utf-8") as f:
            lines = [next(f) for _ in range(max_lines) if True]
        return "".join(lines).rstrip()
    except (StopIteration, OSError):
        return "(CLAUDE.md unreadable)"


def compose_persona(worktree: Path | None = None) -> str:
    """Compose the full system prompt with project context.

    Returns:
        System prompt string. Pass to create_deep_agent(system_prompt=...).
    """
    worktree = worktree or _find_worktree_root()
    if worktree is None:
        return _BASE_PROMPT + "\n\n(worktree root not found — running without project context)"

    vault_layout = _read_vault_layout(worktree)
    strategics_layout = _read_strategics_layout(worktree)
    claude_excerpt = _read_claude_md_excerpt(worktree)

    return f"""{_BASE_PROMPT}

═══════════════════════════════════════════════════════════════════════════════
PROJECT CONTEXT (loaded 2026-09-10)
═══════════════════════════════════════════════════════════════════════════════

WORKTREE: {worktree}

CLAUDE.md (excerpt — first 40 lines):
{claude_excerpt}

VAULT/ structure:
{vault_layout}

STRATEGICS/ files (PT-BR planning canon — read these for grounding decisions):
{strategics_layout}

═══════════════════════════════════════════════════════════════════════════════
END PROJECT CONTEXT
═══════════════════════════════════════════════════════════════════════════════"""


__all__ = ["compose_persona"]

---
title: Pivot — escopo canônico serverless no repositório remoto
date: 2026-11-01
status: DECIDIDO
decision_owner: owner
tags: [pivot, serverless, data-layer, adr-037, repositorio-remoto]
related:
  - code-docs/adr/ADR-037-data-layer-canonical-turn.md
  - .claude/loop/roadmap.md
  - .claude/loop/tasks.md
  - specs/data-layer/TECH.md
---

# Pivot: escopo canônico serverless no repositório remoto

## Decisão

O repositório remoto `github.com/matheusmendes720/ikigai` passa a publicar
**apenas conteúdo e código de sistemas canônicos multi-dispositivo, deployáveis
em ambiente de produção**. Ferramentas locais de PC saem do remoto.

## O que sai do remoto

- **TUI client** (`interfaces/tui/`, `src/tuiboard/`, `vibe-ops/vibeops-tui/`) — só faria sentido no PC.
- **Servidores MCP antigos** (`src/ikigai/src/mcp_server/`, `sys_ikigai/gateway/stdio_adapter.py`) — superfície stdio local.
- **Harness langchain/langgraph anterior** (`src/ikigai/src/agents/`, `src/ikigai/src/chat/`, `src/ikigai/src/plugins/`, `langgraph.json`).
- **Árvores de sonda** (`.hermes/`, `.hermes_probe/`, `.atlas/`, `.claude-flow/`) e o kernel PAV arquivado (`archive/legacy-pav/`).

## O que fica (e é a linha ativa)

- `src/contracts/` — contratos canônicos Pydantic v2 (inclui o DOM unificado: `dom.py`, `dom_kinds.py`, `store.py`).
- `src/data/` — cliente do store cloud.
- `src/services/` — artifacts, embeddings, relations, sync.
- `src/transport/` — MCP sobre HTTP (fastmcp), servidor cloud.
- `src/mesh/`, `src/agents/` (planner), `sys_ikigai/`, `interfaces/cli/`.
- `vault/`, `docs/`, `code-docs/`, `specs/`, `.claude/loop/` (o loop de orquestração).

## Ordem de trabalho (herda ADR-037 §D1)

1. **Camada de dados** — DOM unificado → store cloud Postgres serverless (R1: Supabase, aprovada em 2026-11-01) → sync do vault.
2. **Serviços + transporte** — MCP sobre HTTP via fastmcp.
3. **Backend** — harness já nasce pronto; não se constrói harness novo.
4. **Clientes** — Telegram entra **depois** de a infraestrutura estar sólida. A TUI fica em standby.

## Consequências

- O repositório deixa de ser "a máquina do dono" e passa a ser **o contrato de deploy**: um agente de nuvem que clona o remote recebe código canônico, contratos, o vault e as specs do harness — nada mais.
- O agente de nuvem precisa de **instruções de operação** fornecidas por prompts de sistema e specs de skills; por isso `specs/harness/SYSTEM-PROMPTS.md` e `specs/harness/SKILL-SPECS.md` nascem como parte desta fase.
- `vault/` continua **append-only**; esta nota é o registro permanente da decisão.

## Pendências abertas

- Histórico do git contém chaves vazadas (`.env` e `REDACTED_LANGSMITH_KEY…`, `REDACTED_LANGSMITH_KEY…`, `sk-test-…`) → purge autorizado pelo owner em 2026-11-01; as chaves precisam ser **rotacionadas** na origem (ação do owner, não do agente).
- `vault/ikigai/runtime/` e `vault/ikigai/meta/` ainda descrevem o harness antigo; a revisão vem na mesma linha append-only.

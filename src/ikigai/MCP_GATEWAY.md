# MCP Gateway — Unified Interface Hub

## Arquitetura

```
LangChain Deep Agent ──HTTP+SSE──► Unified MCP Gateway
Claude Code CLI      ──stdio──►        │
                                        │
                        ┌──────────────┼──────────────┐
                        ▼              ▼              ▼
                   tuiboard       taskdog      solverforge
                   (stdio↔HTTP)   (stdio↔HTTP) (stdio↔HTTP)
```

## Quick Start

```bash
# Status de todas as interfaces
./start_mcp_gateway.sh status

# Testar todas as conexões
./start_mcp_gateway.sh test

# Ver menu interativo
./start_mcp_gateway.sh
```

## Interfaces Disponíveis

| Interface | Status | Ferramentas | Docs |
|-----------|--------|-------------|------|
| **IKIGAi** | ✅ | 8 tools (score, regime, phase, decompose, corrections, plan_cycle, checkpoint, sync_vault) | `run_mcp_server.py` |
| **tuiboard** | ✅ | 5 tools (board_list, board_tasks_get/create/update/delete) | Kanban boards em Markdown |
| **taskdog** | ✅ | 26 tools (list/create/complete/optimize tasks) | `uv run taskdog-mcp` |
| **solverforge** | ⚠️ | Needs Rust build | Calendário |

## Arquivos

```
ikigai/
├── start_mcp_gateway.sh   # Launcher script
├── mcp_config.json       # Claude Code MCP config
└── MCP_GATEWAY.md        # Este arquivo
```

## Configuração Claude Code

Copie `mcp_config.json` para:
- Linux/macOS: `~/.config/claude-code/mcp_servers.json`
- Windows: `%APPDATA%/claude-code/mcp_servers.json`

## Pré-requisitos

1. **IKIGAi**: Python env em `/tmp/ikigai-test/`
2. **tuiboard**: Bun em `~/.bun/bin/bun`
3. **taskdog**: Servidor em `:8000` + `uv` no PATH
4. **solverforge**: Rust toolchain com `cc` linker

## Tarefas IKIGAi em taskdog

```bash
# Listar tarefas
cd $TASKDOG_ROOT && uv run taskdog list

# Listar tarefas com tag ikigai
uv run taskdog list --tag ikigai
```

## Kanban tuiboard

Boards disponíveis:
- `BYD-Camacari-CV.md` — Pipeline de candidatura BYD

```bash
# Listar boards
~/.bun/bin/bun run $TUIBOARD_ROOT/bin/tuiboard-mcp.ts

# Ou via MCP tools
```

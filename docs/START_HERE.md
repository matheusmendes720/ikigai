# START_HERE.md

**Estado atual em 2026-09-10** (loop-prod-ready HEAD `41357c0`).

---

## TL;DR

`dcode` no seu shell = **nosso IKIGAI v2 harness** (com persona: vault/strategics/CLAUDE.md). Funciona em qualquer PowerShell com `.venv/Scripts/` no PATH (que `install.ps1` configurou).

`ikigai-chat` é alias exato (mesmo `main()`).

Pra testar upstream LangChain CLI (separado, sem afetar nada): `uvx --from deepagents-code@latest dcode`.

---

## Alias strategy (UX 2026-09-10 final)

| Alias | O que faz | Onde mora |
|-------|-----------|-----------|
| `dcode` | Nosso IKIGAI v2 harness (REPL com persona) | `.venv/Scripts/dcode.exe` (worktree) |
| `ikigai-chat` | Mesmo harness (alias, mais explícito) | `.venv/Scripts/ikigai-chat.exe` (worktree) |
| `uvx --from deepagents-code@latest dcode` | Upstream LangChain CLI (TUI separada, sem poluir PATH) | uvx cache global |

**NÃO há** `dcode` no global Python314 — foi uninstalled pra não dar conflito.

---

## Como testar agora (em NOVA janela PowerShell)

```powershell
PS> dcode --no-chat
# esperado: nosso harness help (claude-sonnet-4-5, checkpoint_db, etc)

PS> ikigai-chat
# esperado: chat REPL abre com persona carregada

PS> $env:ANTHROPIC_API_KEY='sk-cp-...'
PS> $env:IKIGAI_FAKE_LLM=''
PS> dcode --prompt "list my tasks"
# esperado: agent chama taskdog_list_tasks, retorna 1 task formatada
```

Para testar **upstream LangChain** (separado):
```powershell
PS> uvx --from deepagents-code@latest dcode
# NÃO toca no PATH. Roda via uvx cache.
# Tem TUI própria do LangChain (que tem BlockingError conhecido no Windows)
```

---

## Daily workflow

1. Abrir PowerShell
2. `cd C:\Users\mathe\code_space\life-oss\life\.worktrees\loop-prod-ready`
3. `.venv\Scripts\ikigai-chat.exe` (ou só `ikigai-chat` se PATH configurado)
4. Chat abre → digita prompt → Enter
5. Agent responde em PT-BR com contexto IKIGAI

---

## O que NÃO fazer

- ❌ Não rode `dcode` esperando LangChain TUI — vai bloquear no Windows
- ❌ Não instale `deepagents-code` no Python314 global — shadow conflict
- ❌ Não delete `.venv/Scripts/dcode.exe` (é nosso harness)

---

## O que FUNCIONA (commit 41357c0 + anteriores)

- ✅ `dcode` em nova janela PowerShell → nosso harness (REPL)
- ✅ `ikigai-chat` → mesmo harness (alias)
- ✅ `dcode --prompt "..."` → one-shot via harness
- ✅ `python -m interfaces.cli v2 chat` → CLI v2
- ✅ Drift net 46/46

## O que AINDA não funciona (deferred)

- ❌ Upstream dcode TUI no Windows (issue #5801 "Not planned")
- ❌ TUI nossa (interfaces/tui/operator) — user explicitamente não quer
- ❌ Persona ainda não carrega vault path explicitamente no startup (só se agente perguntar)

---

## Branch state atual

`loop/prod-ready` HEAD `41357c0` — 24 commits acima do master, incluindo:
- P0 fix (dcode opens via ikigai-chat)
- B1+B2 (UEID 4-part + state schema)
- B3-B6 (deep-dive bugs)
- consumer + taskdog tool direct DB
- persona with vault filenames
- silent shell + .pth
- upstream dcode eradicated, worktree dcode = our harness

---

## Próximo passo (quando quiser)

- Rodar `ikigai-chat` no dia-a-dia e me dizer o que tá faltando
- Decidir sobre persona (system prompt carregando vault/strategics)
- Quando estabilizar: mergear tudo pra master e fechar `loop-prod-ready`

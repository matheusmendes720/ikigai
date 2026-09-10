# START_HERE.md

**Estado em 2026-09-10** (loop-prod-ready HEAD final) — `dcode` foi completamente removido do projeto.

---

## TL;DR

**`dcode` não existe mais em lugar nenhum** (nem global Python314, nem worktree venv, nem WSL). User decidiu apagar upstream LangChain CLI por complexidade desnecessária (BlockingError no Windows).

**Único entry point agora:** `ikigai-chat` (nosso IKIGAI v2 harness).

---

## Alias strategy FINAL

| Alias | O que faz |
|-------|-----------|
| `ikigai-chat` | **Nosso IKIGAI v2 harness** (REPL com persona vault/strategics/CLAUDE.md) |

**Nada mais.** Sem `dcode`, sem `ikigai-tui`, sem upstream.

---

## Como testar agora (em NOVA janela PowerShell)

```powershell
PS> ikigai-chat --no-chat        # help do nosso harness
PS> ikigai-chat --prompt "list my tasks"  # one-shot
PS> ikigai-chat                 # REPL
```

**Se quiser testar upstream LangChain CLI** (separado, sem poluir nada):
```powershell
PS> uvx --from deepagents-code@latest dcode
# Roda via uvx cache. Não instala nada no projeto. Não toca no PATH.
# AVISO: tem BlockingError conhecido no Windows (#5801 'Not planned')
```

---

## Daily workflow

1. Abrir PowerShell
2. `cd C:\Users\mathe\code_space\life-oss\life\.worktrees\loop-prod-ready`
3. `ikigai-chat` (ou caminho absoluto `.\.venv\Scripts\ikigai-chat.exe`)
4. Chat REPL abre com persona carregada
5. Digita prompt → Enter → resposta em PT-BR

---

## O que foi REMOVIDO (dcode eradication)

- ❌ `.venv/Scripts/dcode.exe` (upstream v0.1.63, uninstalled)
- ❌ `C:\Users\mathe\AppData\Roaming\Python\Python314\Scripts\dcode.exe` (upstream v0.1.68, uninstalled)
- ❌ `/home/flytwist/.local/bin/dcode` (WSL, eradicated → /tmp/)
- ❌ `/home/flytwist/.local/share/uv/tools/deepagents-code/` (moved → /tmp/)
- ❌ `.deepagents/agents/ikigai-planner/AGENTS.md` (deleted — não tem mais dcode pra carregar)
- ❌ `pyproject.toml` `deepagents-code` dev dep (removed)
- ❌ `pyproject.toml` `dcode` entry point (only `ikigai-chat` remains)

---

## O que FUNCIONA (final state)

- ✅ `ikigai-chat` → nosso harness com persona (vault + strategics + CLAUDE.md)
- ✅ `ikigai-chat --prompt "..."` → one-shot
- ✅ `python -m interfaces.cli v2 chat` → CLI v2 one-shot
- ✅ Drift net 46/46 PASS
- ✅ `uvx --from deepagents-code@latest dcode` → upstream test (separado)

## O que NÃO funciona (deferred / out of scope)

- ❌ Upstream dcode TUI (BlockingError Windows)
- ❌ TUI nossa (interfaces/tui/operator) — user não quer
- ❌ Persona com auto-load do vault path (ainda requer agente chamar tool)

---

## Branch state

`loop-prod-ready` HEAD final — todos commits shipped, nenhum dcode.

---

## Próximo passo (quando você quiser)

- Usar `ikigai-chat` no dia-a-dia, me dizer o que falta
- Quando estabilizar: mergear tudo pra master
- Persona com auto-discovery de vault (se quiser) — fix futuro

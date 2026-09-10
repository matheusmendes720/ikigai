# START_HERE.md

**Read this first thing tomorrow.** Or in a week. Whenever you come back.

---

## Estado honesto

Depois de uma sessão de 8h nesta branch (`loop/prod-ready` HEAD `0621075`), o estado é:

- **Funciona** (verificado end-to-end uma vez): `v2 daily --json`, `v2 weekly --json`, `do_task_add`, `ikigai-taskdog-mcp` subprocess.
- **Não funciona** (verificado, falha reproduzível): `dcode --chat`, `ikigai.bat chat`, MCP no Claude Code, qualquer coisa que toque `sys_ikigai` ou OTel.

**Diagnóstico completo:** `~/.claude/projects/.../memory/loop-prod-ready-broken-state-2026-09-09.md` (260 linhas — TL;DR, 5 root causes, cascata, meta-lição, TODOs em P0/P1/P2/P3).

**Topologia visual:** `docs/agentic-systems-topology.html` (abrir no navegador).

---

## Protocolo de amanhã — 5 passos

### Passo 1 · Decisão macro (5 min)

Sem decidir isso, qualquer trabalho é desperdício. Três opções:

- **A) Consertar pra valer** — resolver OTel + sys_ikigai + bat + escrever integration test. Estimativa: **meio dia a 1 dia**.
- **B) Rollback** — `git revert 0621075 08dcd5b 7365b2f 04e87c2e`. Volta pra `edc313e2` (Tier 1 closeout, antes de eu quebrar tudo). Estimativa: **5 min**.
- **C) Pausar** — commitar estado, fechar branch, abrir outra do zero amanhã. Estimativa: **15 min**.

Você não precisa decidir agora. Mas amanhã, primeiro pensamento = qual dessas três.

---

### Passo 2 · Se escolher A (consertar) — ordem de execução

Em ordem. **Não pular etapa.** Cada uma valida a anterior.

#### P0-A · Resolver conflito OTel (~30 min)

Arquivo: `src/ikigai/pyproject.toml`

```toml
# Linha 24 (atual):
opentelemetry-instrumentation-langchain = "^0.42b0"

# Trocar pra:
opentelemetry-instrumentation-langchain = "^0.48b0"
```

Depois:
```bash
cd C:\...\loop-prod-ready
.venv\Scripts\uv.exe pip install --python .venv\Scripts\python.exe -e .  # SEM --no-deps
```

Validar:
```bash
.venv\Scripts\python.exe -c "from opentelemetry.trace import Status, StatusCode; print('OTel OK')"
```

Se falhar: tentar Opção B (`logging<0.48b0`).

#### P0-B · Consertar import sys_ikigai (~15 min)

Arquivo: `src/ikigai/pyproject.toml` linha 7

```toml
# Trocar:
packages = [{include = "mcp_server", from = "src"}, ...]
# Por:
packages = [{include = "sys_ikigai", from = ".."}, ...]
```

(assumindo que `sys_ikigai/` está no worktree root, com `from = ".."`)

Ou mais simples: deixar o pyproject como está, garantir que `PYTHONPATH` inclui worktree root (próximo passo).

#### P0-C · Consertar PYTHONPATH do `ikigai.bat` (~10 min)

Arquivo: `src/ikigai/ikigai.bat` linha 7

```bat
set "PYTHONPATH=%IKIGAI_ROOT%..\..\..\;%IKIGAI_ROOT%src;%IKIGAI_ROOT%..\..\..%"
#                                                                    ↑ mesma que entrada 1
```

Validar:
```bash
cd C:\...\loop-prod-ready\src\ikigai
cmd //c "ikigai.bat chat default"
# Esperado: REPL do deepagent aparece, prompt esperando input
```

#### P0-D · Teste manual final (~10 min)

```bash
.venv/Scripts/dcode.exe --chat --thread test-amanha
# Quando o prompt aparecer, digitar:
> /tasks list
# Esperado: resposta do LLM com tarefas
```

Se chegar aqui: **VOCÊ TEM O HARNESS FUNCIONANDO**. Pode parar e celebrar.

---

### Passo 3 · Se escolher B (rollback) — 5 min

```bash
cd C:\...\loop-prod-ready
git revert --no-edit 0621075 08dcd5b 7365b2f 04e87c2e
git log --oneline -5  # confirmar voltamos pra edc313e2 + 4 reverts
```

Estado pós-rollback: idêntico ao que estava em `edc313e2` (Tier 1 SHIPPED, antes da minha sessão). Os 5 broken items desta sessão somem.

---

### Passo 4 · Independentemente da escolha

Escrever um teste de integração que IMPEDISCA o problema de voltar:

`tests/integration/test_dcode_e2e_chat.py`:

```python
def test_dcode_chat_end_to_end():
    """Garante que dcode --chat funciona end-to-end antes de qualquer commit."""
    proc = subprocess.run(
        ["dcode.exe", "--chat", "--thread", "ci-test"],
        input="hello\n/exit\n",
        capture_output=True, text=True, timeout=30
    )
    assert proc.returncode == 0
    assert "hello" in proc.stdout.lower() or any(
        keyword in proc.stdout.lower()
        for keyword in ["skill", "regime", "task"]
    )
```

Adicionar `@pytest.mark.integration` e gate CI.

---

### Passo 5 · Honest note pra você

- A sessão de hoje não foi em vão. **4 dos 5 commits** funcionam isoladamente. O problema é integração.
- A lição mais importante: **smoke test unitário não é prova de sistema funcionando**. Cada "SHIPPED" que eu disse devia ter sido precedido por `dcode --chat` real.
- Se amanhã você decidir que **não vale o esforço** e quiser voltar pra fin_ops ou qualquer outra coisa do monorepo, **isso é uma resposta válida**. Não é derrota. É priorização.
- O harness tem 22 tools, 12 contracts, 3 adapters, 5 waves de trabalho. Não é uma coisa de uma sessão.

---

## TL;DR de uma linha

> **Amanhã, primeiro comando é: decidir A/B/C acima.** Sem decidir, não mexer.

Boa noite.

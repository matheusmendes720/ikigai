# M155 — Deep agent mínimo viável (sem PAV-math, com context awareness automático)

**Status:** 🟡 PLANNED
**Date:** 2026-09-29
**Author:** loop-orchestrator + user
**Builds on:** M154-AUDIT (v2 graph compila e executa, BlockingError era diagnóstico errado)
**Goal:** Deep agent CLI chat que conversa com você sobre o planning, lê o vault
automaticamente antes de cada reasoning, NUNCA auto-executa, e respeita ADR-013
(PAV-math FORA).

---

## TL;DR

Você já tem 6.337 LOC de v2 funcionando. O que falta é:

1. **Substituir 14 prompts PAV-math por stubs neutros** (M156, ~300 LOC)
2. **Fix do import `langchain_anthropic`** que está quebrado (M157, ~50 LOC)
3. **`td chat` REPL que invoca v2 graph** com streaming de "thinking aloud" (M158, ~150 LOC)
4. **Cache de embeddings do vault** (ChromaDB, M159, ~100 LOC)
5. **`td tui` painel "agent thinking"** (M160, ~200 LOC, opcional)

**Total:** ~800 LOC, 3-4 sessões. **SEM rewrite-from-scratch.**

---

## Arquitetura final (decidida nesta sessão)

### Camadas (de baixo pra cima)

```
┌────────────────────────────────────────────────────┐
│ Interface Layer                                    │
│   • td chat (REPL)              — M158 (FASE 1)   │
│   • td tui (Rich dashboard)     — M160 (FASE 2)   │
│   • Claude Code MCP             — já funciona      │
├────────────────────────────────────────────────────┤
│ Agent Layer (v2 graph)                             │
│   • 15 nodes: observe → recall → reason → ...      │
│   • context awareness AUTOMÁTICO em todo reasoning │
│   • meta_plan approval pattern (NUNCA auto-exec)   │
│   • 5 skills existentes (1/2 adaptados) + 2 novos  │
├────────────────────────────────────────────────────┤
│ Persistence Layer                                  │
│   • vault/ (markdown, SOT)                         │
│   • data/taskdog/tasks.db (SQLite)                 │
│   • data/chroma_db/ (embeddings cache, M159)       │
├────────────────────────────────────────────────────┤
│ Tool Layer (já funciona, M148)                     │
│   • 12 taskdog tools via MCP bridge                │
│   • 8 IKIGAI tools (5 reais + 3 stubs PAV-math)    │
│   • 3 investigation tools                          │
└────────────────────────────────────────────────────┘
```

### Princípios (constituição)

| Princípio | Como respeita |
|---|---|
| `composition_over_inheritance` | v2 graph é composição de 15 nodes, não herança |
| `tests_are_the_contract` | cada node tem teste isolado + teste de integração |
| `reversibility_over_cleverness` | toda proposta é APPROVAL-REQUIRED, nunca auto-exec |
| `state_on_disk_not_conversation` | vault é SOT, LLM é "processador de contexto" |
| `M148: writes via review queue` | mantém ADR-014 intacto |
| `M70: PAV-math OUT` | stubs substituem 14 prompts |

---

## 5 skills (1 adaptado) + 2 novos = 7

### Skills ADAPTADOS (mantidos com prompts PAV stubificados)

#### 1. `ikigai-daily` (cron 08:57) — mantém
- **Lê:** `vault/2026/{yesterday}.md` + `vault/meta/cycle_state/{today}.md` + `taskdog_list(done, 24h)`
- **Stub no lugar de PAV scoring:** apenas agrega contagens (tasks done, pending, cancelled)
- **Output:** 3-5 sugestões pt-BR em stdout (NÃO escreve nada)
- **Approval:** N/A (read-only, só sugere)

#### 2. `ikigai-weekly` (cron segunda 09:00) — adapta
- **Lê:** últimos 7 daily reports + cycle_state + habit_state
- **Stub no lugar de PAV score_vectors:** agrega (count done, count pending, count by tag se houver)
- **Output:** `vault/weekly-review/{date}.md` via `vault_write` MCP
- **Approval:** meta_plan style — escreve PROPOSTA primeiro, espera `--approve`

#### 3. `ikigai-monthly` (cron dia 1 10:00) — adapta
- **Lê:** últimos 4 weekly reviews
- **Stub no lugar de PAV regime:** apenas lista as 4 reviews e destaca padrões
- **Output:** `vault/monthly-review/{date}.md`
- **Approval:** idem weekly

#### 4. `ikigai-quarterly` (cron jan/abr/jul/out dia 1 11:00) — adapta
- **Lê:** últimos 3 monthly + 13 weekly
- **Stub no lugar de PAV Q_HE:** OKR rollup simples
- **Output:** `vault/quarterly-review/{date}.md` + `taskdog_create` OKRs
- **Approval:** idem weekly

#### 5. `meta_plan` (opt-in `/plan <req>`) — mantém (já respeita ADRs)
- **Lê:** user_request
- **Output:** Proposal tipada `pending`
- **Approval:** SEMPRE exige `--approve` ou `--reject X.field`

### Skills NOVOS (propostos nesta sessão)

#### 6. `taskdog-triage` (cron 09:00 diário)
- **Lê:** vault de hoje + `taskdog_list(active)` + memory recente
- **Detecta:**
  - tasks com deadline próximo (<48h) e status != done
  - tasks planned_start no passado e status == planned (overdue)
  - tasks sem descrição (UX ruim)
- **Output:** Proposal com lista de mudanças (update priority, add due date, etc)
- **Approval:** meta_plan style (NUNCA auto-exec)

#### 7. `vault-intent-extract` (cron 22:00 diário)
- **Lê:** `vault/{today}.md` (nota do dia)
- **Detecta via regex + LLM:**
  - "amanhã eu faço X" → task candidate
  - "deadline sexta" → task com due
  - "TODO", "FIXME", "lembrar" → task candidate
- **Output:** Proposal com tasks sugeridas (enqueue via review queue)
- **Approval:** meta_plan style (NUNCA auto-exec)

---

## Context awareness AUTOMÁTICO (decisão desta sessão)

**Toda request passa por `recall_node` ANTES de qualquer reasoning.**

```python
def recall_node(state: IKIGAiStateDict) -> dict:
    """Lê vault + taskdog + memory ANTES do reasoning.
    Obrigatório: este node é o primeiro após observe.
    """
    today = date.today().isoformat()
    context = {
        "vault_today": read_vault(f"vault/2026/{today}.md"),
        "vault_yesterday": read_vault(f"vault/2026/{yesterday}.md"),
        "cycle_state": read_vault(f"vault/meta/cycle_state/{today}.md"),
        "taskdog_active": taskdog_list(status="active"),
        "taskdog_recent": taskdog_list(since=24h),
        "memory": recall_memory(state.thread_id, k=5),
    }
    return {"context": context, "raw_request": state.raw_request}
```

**Implicação:** todo node downstream (`reason`, `plan`, `reflect`, etc.) recebe
`state.context` populated. Eles **DEVEM** consultar `state.context` antes de
propor qualquer mudança.

**Vault é SOT:** antes de qualquer modificação em taskdog/interface, o agent
escreve no vault (audit trail). Depois da aprovação e execução, escreve de novo
(registro da execução).

---

## Meta_plan approval pattern (NUNCA auto-exec)

Toda skill termina com `commit_node` que produz uma `Proposal`:

```python
@dataclass
class Proposal:
    skill: str                    # qual skill produziu
    reasoning: str                # por que essa proposta
    changes: list[TaskChange]     # 0+ mudanças propostas
    approval_state: str = "pending"
    proposed_at: datetime
    vault_log: str                # path do vault entry
```

**Fluxo:**
1. Skill roda → produz `Proposal(approval_state="pending")`
2. Agent emite proposta pro usuário (chat/tui)
3. Usuário responde `--approve` / `--reject campo` / `--edit campo=valor`
4. Só após `--approve` o agent aplica via `review_queue.enqueue`
5. Vault entry registra decisão + execução

**Implementação:** copiar padrão do `meta_plan` skill existente (já tem
ADR-029 wrap_vault_write + ADR-028 recall_memory).

---

## M156 — Stub 14 prompts PAV-math

| Prompt atual | Stub equivalente |
|---|---|
| `h1_energy.py` | retorna 0 |
| `h2_qhe_composite.py` | retorna 0 |
| `h3_regime_fsm.py` | retorna "neutral" |
| `h4_market_fit.py` | retorna 0 |
| `h5_skill_velocity.py` | retorna 0 |
| `h6_severity.py` | retorna 0 |
| `score_passion_observation.py` | retorna None |
| `score_revenue_observation.py` | retorna None |
| `score_skill_observation.py` | retorna None |
| `score_market_observation.py` | retorna None |
| `score_meta_vector_observation.py` | retorna None |
| `score_course_observation.py` | retorna None |
| `surface_pav_intentions.py` | retorna [] (vazio) |
| `decompose_rice_observation.py` | retorna None |
| `observe_qhe_observation.py` | retorna None |

**Critério:** stub deve passar nos 10 testes v2 (que estão em FAKE_LLM mode)
e ser idempotente (pode rodar N vezes sem side effect).

**LOC:** ~300 (15 arquivos × 20 LOC cada).

---

## M157 — Fix `langchain_anthropic` import quebrado

**Erro atual:**
```
File "...langchain_anthropic/chat_models.py", line 984
    class AnthropicOverloadedError(anthropic.OverloadedError, ModelAPIError):
                                   ^^^^^^^^^^^^^^^^^
AttributeError: module 'anthropic' has no attribute 'OverloadedError'
```

**Fix:**
```bash
# 1. Atualizar anthropic SDK
pip install --upgrade anthropic

# 2. Verificar langchain_anthropic compatível
pip install --upgrade langchain-anthropic

# 3. Testar import
python -c "from langchain_anthropic import ChatAnthropic; print('ok')"
```

**Se ainda falhar:** adicionar `try/except ImportError` no
`taskdog_mcp_graph._build_agent` pra usar `langchain_community` ou
fallback local (FAKE_LLM).

**LOC:** ~50 (try/except + fallback).

---

## M158 — `td chat` REPL (a peça que você QUER ver funcionando)

**O que faz:** REPL Python no PowerShell. Você digita linguagem natural,
o v2 graph processa, mostra "thinking aloud" + proposta + approval prompt.

### Comportamento esperado

```powershell
PS> td chat

[ikigai-chat] thread_id: chat-2026-09-29-001
[ikigai-chat] model: minimax-m3 (via ANTHROPIC_BASE_URL)
[ikigai-chat] skills: daily, weekly, monthly, quarterly, meta_plan, taskdog-triage, vault-intent-extract

> o que eu deveria fazer hoje?

[recall]    reading vault/2026/09-29.md ... 0 lines
[recall]    reading cycle_state/2026-09-29.md ... 12 lines
[recall]    taskdog_list(active) ... 3 tasks
[recall]    memory recall ... 5 chunks
[reason]    3 candidate intentions found
[reflect]   checking against Q4 OKRs ... 1 mismatch
[commit]    PROPOSAL: add 1 task, update 1 task

PROPOSAL #chat-001 (approval_state: pending):
  + add task ueid=tsk:daily:abcd:1234:5678 title="M155 M156 M157 setup"
  ~ update task ueid=study:topic:abc12345:abcd1234 status=in_progress

> --approve
[commit]    applied 2 changes via review queue
[commit]    vault entry: vault/2026/09-29.md#chat-001

> /plan meta review do Q4

[meta_plan] classifying intent: meta_review
[meta_plan] fetching context: 3 quarterly + 12 monthly
[meta_plan] proposal pending approval...

PROPOSAL #chat-002:
  + add quarterly-review task
  + add 4 weekly-review tasks
  ...

> /quit
[ikigai-chat] thread closed
```

### Implementação (M158, ~150 LOC)

**Arquivo:** `src/mesh/taskdog_chat.py`

```python
"""td chat REPL — interface CLI do v2 graph.

Stream events from langgraph as they're produced.
NO auto-execute. Always emit Proposal and wait for --approve.
"""
import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

def main(argv=None):
    parser = argparse.ArgumentParser(prog="ikigai-taskdog chat")
    parser.add_argument("--thread-id", default=None)
    parser.add_argument("--model", default="minimax-m3")
    args = parser.parse_args(argv)

    # Ensure v2 graph can be imported
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src" / "ikigai" / "src"))
    os.environ.setdefault("IKIGAI_FAKE_LLM", "0")

    thread_id = args.thread_id or f"chat-{datetime.now().isoformat()}"
    config = {"configurable": {"thread_id": thread_id}}

    print(f"[ikigai-chat] thread_id: {thread_id}")
    print(f"[ikigai-chat] model: {args.model}")
    print(f"[ikigai-chat] skills: 7 (daily/weekly/monthly/quarterly/meta_plan/taskdog-triage/vault-intent-extract)")

    from agents.v2.graph import graph

    while True:
        try:
            request = input("\n> ")
        except (EOFError, KeyboardInterrupt):
            print("\n[ikigai-chat] thread closed")
            break

        if not request.strip():
            continue
        if request.strip() in ("/quit", "/exit"):
            print("[ikigai-chat] thread closed")
            break

        # Slash command for skill invocation
        skill_name = None
        if request.startswith("/"):
            parts = request[1:].split(maxsplit=1)
            skill_name = parts[0]
            request = parts[1] if len(parts) > 1 else ""

        # Invoke graph with streaming
        try:
            for event in graph.stream(
                {"raw_query": request, "skill": skill_name},
                config=config,
            ):
                # Pretty-print each node's output
                for node_name, node_output in event.items():
                    print(f"[{node_name}]    {summarize(node_output)}")
        except Exception as e:
            print(f"[error] {type(e).__name__}: {e}")
            continue

        # Wait for user approval if Proposal was emitted
        approval = input("\n> ")
        if approval.startswith("--approve"):
            apply_pending_proposal(thread_id)
        elif approval.startswith("--reject"):
            reject_pending_proposal(thread_id, approval)
```

### Tests (M158, +5 tests)

| test | o que verifica |
|---|---|
| `test_chat_repl_invokes_graph` | `td chat "hello"` chama `graph.stream()` |
| `test_chat_repl_streams_events` | eventos chegam como `[node_name] ...` |
| `test_chat_repl_awaits_approval` | sem `--approve` nada é executado |
| `test_chat_repl_quit_closes` | `/quit` termina o loop |
| `test_chat_repl_handles_errors` | exception no graph não crasha o REPL |

---

## M159 — Vault embeddings cache (ChromaDB)

**Por que:** todo tool call do v2 graph pode triggar `recall_node` que precisa
embeddar o vault. Sem cache, custa API + tempo a cada chamada.

**O que cachear:** chunks de `vault/**/*.md` indexados por path + mtime.
Invalidar quando mtime muda.

**Implementação (~100 LOC):**

```python
# src/ikigai/src/agents/v2/vault_cache.py
import chromadb
from pathlib import Path

class VaultEmbeddingCache:
    def __init__(self, persist_dir="data/chroma_db"):
        self.client = chromadb.PersistentClient(path=persist_dir)
        self.collection = self.client.get_or_create_collection("vault")
        self._indexed_mtimes: dict[str, float] = {}

    def get_or_compute(self, file_path: str) -> list[float]:
        path = Path(file_path)
        mtime = path.stat().st_mtime
        if self._indexed_mtimes.get(file_path) == mtime:
            # Cache hit
            return self.collection.get(file_path)["embeddings"]
        # Cache miss: re-embed
        text = path.read_text()
        embedding = self._embed(text)
        self.collection.upsert(file_path, embedding, text)
        self._indexed_mtimes[file_path] = mtime
        return embedding
```

**Wired em `recall_node`:** sempre passa texto do vault por `get_or_compute`
antes de mandar pro LLM. ChromaDB já existe em `data/chroma_db/`, só
configurar collection.

---

## M160 — `td tui` painel "agent thinking" (opcional, FASE 2)

**Estende o `td tui` de M153** com painel à direita que mostra
output do agent em tempo real (sse_publisher já existe).

**Layout:**
```
┌─────────────────────────────────────────────────┐
│ Header: total=3 | planned=0 | done=0 | ...      │
├──────────────────────────┬──────────────────────┤
│ Tasks by priority        │ Agent thinking       │
│ ┌──────────────────────┐ │ [recall] ...         │
│ │ ueid | name | status │ │ [reason] ...         │
│ │ ...                  │ │ [commit] proposal #1 │
│ └──────────────────────┘ │ > awaiting --approve │
├──────────────────────────┴──────────────────────┤
│ Upcoming deadlines: 5                          │
└─────────────────────────────────────────────────┘
```

**LOC:** ~200.

---

## Roadmap de execução (ordem importa)

| M | título | LOC | deps | output |
|---|---|---|---|---|
| **M156** | Stub 14 prompts PAV-math | ~300 | M154 | v2 graph roda sem matemática |
| **M157** | Fix `langchain_anthropic` import | ~50 | — | LLM real funciona |
| **M158** | `td chat` REPL | ~150 | M156, M157 | **você conversa com o agent** |
| **M159** | Vault embeddings cache | ~100 | M158 | recall_node é rápido |
| **M160** | `td tui` painel agent | ~200 | M158 | você VÊ o agent pensando |
| **M161** | Skills `taskdog-triage` + `vault-intent-extract` | ~400 | M158 | 7 skills completos |
| **M162** | Adaptação daily/weekly/monthly/quarterly (substituir PAV) | ~300 | M156, M161 | cadência completa |

**Total:** ~1.500 LOC em 5-7 sessões.

---

## O que NÃO está nesta spec (decisões adiadas)

1. **Schema de vault:** `vault/2026/09-29.md` é o padrão? ou `vault/daily/2026-09-29.md`? Decidir em M161.
2. **Embeddings model:** qual modelo? OpenAI text-embedding-3-small? ou sentence-transformers local? ChromaDB aceita ambos, decidir em M159.
3. **Approval UX:** `--approve` no REPL é simples. Mas como você aprova no Claude Code MCP? Mesmo padrão? Decidir em M161.

---

## Critério de done (M155 inteira)

- [ ] M156: 14 stubs criados, 10/10 testes v2 passam, sem regressão
- [ ] M157: `from langchain_anthropic import ChatAnthropic` funciona
- [ ] M158: `td chat` REPL conversa, mostra thinking aloud, exige approval
- [ ] M159: vault embeddings cache hit > 80% em workload típico
- [ ] M160: `td tui` mostra painel "agent" (opcional, não bloqueia)
- [ ] M161: 2 skills novos funcionam
- [ ] M162: 4 skills adaptados rodam diariamente sem PAV-math
- [ ] Você consegue: `td chat` → pedir "review Q4" → agent lê vault → propõe
  → você aprova → taskdog_create via review queue
- [ ] Vault entry de cada chat/proposta/commit está em `vault/2026/09-29.md`

## Riscos

| Risco | Mitigação |
|---|---|
| `langchain_anthropic` ainda quebrar após upgrade | fallback pra `langchain_community.ChatLiteLLM` (já temos) |
| v2 graph dar erro de routing (loop infinito) | M88 já fixou com `MAX_REASON_LOOPS=2` |
| ChromaDB corromper | backup de `data/chroma_db/` antes de upgrade |
| Approval UX confuso | M161 define comando único `--approve` / `--reject campo` |
| Você não gostar do `td chat` | fallback é Claude Code MCP (já funciona) |

## Out of scope (explícito)

- ❌ PAV-math reativação (ADR-013, user confirmou FORA)
- ❌ Auto-approval (user pediu "NUNCA auto-exec" nesta sessão)
- ❌ Studio web UI (CORS-bloqueado, decidimos via td chat)
- ❌ Cross-fork reconciliation (já tem `agent_propagator` em M148)
- ❌ Vault schema migration (decidir em M161)
- ❌ Real-time vault watching (file watcher) — só cron + on-demand

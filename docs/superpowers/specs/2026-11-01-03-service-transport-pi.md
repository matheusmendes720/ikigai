# SPEC-03 — Services + Transporte MCP + o Harness pi

**Date:** 2026-11-01 · **Status:** proposed · **Depends on:** 01, 02 · **Blocks:** — (clientes)
**Origin:** [ADR-037 §3 D6, D7](../../code-docs/adr/ADR-037-data-layer-canonical-turn.md)

---

## Goal

A camada de dados **funcionando no fluxo normal de requisição de um agente** — com três camadas separáveis (dado, serviço, transporte) e **sem construir um harness novo**.

---

## Por que agora

O Vanilla Pivot §3 mediu: **10 dos 16 nós do LangGraph são prompts com roupa de Python**. E §4: o gateway MCP custom tem **22 tools, das quais 9 apontam para tools que não existem**.

A regra do owner nesta virada: *"um harness já pronto antes de focarmos em construir nosso próprio multiplicando a complexidade de manutenção"*.

O harness já pronto é o **pi** (`.pi/` existe no repo; `pi --session` / `pi --resume` documentados em `.pi/zero-resume.md`). A repo **não constrói** agent framework — ela entrega a **ferramenta** que o agente usa.

A prova que esta spec precisa produzir é simples e verificável:

> **Um pedido normal ao pi resulta em leitura/escrita no store — sem nenhum passo manual.**

---

## Anti-padrão que este spec evita

**Recriar o grafo.** A spec 03 do Vanilla Pivot (dispatcher `skill-run`) foi o jeito certo de chegar lá — mas como *producto*. Agora ela é **transporte**, e o transporte é MCP porque é o que o pi consome.

**O gateway de 22 tools.** Cada tool é um contrato a manter em sincronia com o servidor (o bug "bridge ⊆ server" do ADR-032). Com 6–8 tools sobre services, cada tool é uma linha de código de domínio.

**O cliente falando direto no banco.** Sem service layer, cada cliente reimplementa a lógica de escrita e cada um inventa sua própria política de conflito. A service layer é o **único writer**.

**O MCP que só expõe o banco.** Uma tool por tabela é um RPC de banco de dados com nome bonito. A tool expõe **intenção de domínio** (`search_artifacts`, `upsert_artifact`), não CRUD.

---

## Decisões

- **D1 — Três camadas, três responsabilidades.**

  ```
  src/data/       client Postgres — pool, retry, transação. Sem lógica de domínio.
  src/services/   domínio puro — validação, regras, versionamento. Sem I/O de transporte.
  src/transport/  MCP sobre HTTP — traduce intenção de domínio em tool calls.
  ```

  Cada camada é testável isoladamente. `services/` é o único que os clientes alcançam (D: ADR-037 §6 R2).

- **D2 — O transporte é MCP sobre HTTP, via `fastmcp`.** É o caminho que o SPEC-05 (Vanilla Pivot) já indicava como D4 — *"o caminho é `fastmcp` sobre a CLI (~50 LOC)"* — generalised para `fastmcp` **sobre as services**.

- **D3 — Superfície de tools pequena e por intenção.** 6 tools:

  | Tool | Intenção |
  |---|---|
  | `search_artifacts` | buscar por índice estruturado, texto ou semântica |
  | `get_artifact` | ler um artefato + suas relações (1 hop) |
  | `upsert_artifact` | escrever com versionamento otimista + idempotência |
  | `delete_artifact` | **soft delete** (`deleted_at`) — nunca físico |
  | `list_relations` | navegar o grafo (vizinhos de um artefato, por tipo de relação) |
  | `embed_text` | vetoriza um texto e devolve o embedding |

  Cada tool é uma **função de service** exposta. Nenhuma tool expõe SQL.

- **D4 — Erros são parte do contrato.** O MCP devolve erros tipados: `CONFLICT` (409, `expected_revision` desatualizado), `NOT_FOUND`, `VALIDATION` (Pydantic), `FORBIDDEN` (RLS). O agente distingue "conflito, releia" de "inválido, corrija" de "sem permissão".

- **D5 — O pi é o cliente de referência, e a prova é comportamental.** A spec **não assume** o formato de config do pi — descobre. O que se exige é o **efeito**: um pedido ao pi chega ao store.

- **D6 — Sync do vault markdown com o store.** O ingestion lê `vault/ikigai/closing-2026/**` e faz UPSERT idempotente no store; a escrita de volta (prosa editada num cliente) vai para o markdown **e** para o store. Em campo estruturado, **o store vence** (ADR-037 D4).

- **D7 — Cache local com write-behind.** Leitura vai pro store; escrita vai pro store **e** enfileira a reconciliação do markdown. O markdown nunca é o caminho de leitura para dado estruturado.

- **D8 — `client_id` viaja, mas é do harness.** O pi fala com a service layer; a service injeta o `client_id` do token da própria service. O cliente **não** escolhe o `client_id` — isso seria um furo de segurança.

---

## Files

- **Create:** `src/data/client.py` (~180 LOC) — pool, `execute`, retry com backoff, transação, helper de RPC
- **Create:** `src/data/repository.py` (~260 LOC) — as operações de persistência (upsert, search, relations, revisions). **Nenhuma regra de domínio aqui.**
- **Create:** `src/services/artifacts.py` (~200 LOC) — `upsert_artifact`, `search_artifacts`, `get_artifact`; validação + versionamento + idempotência
- **Create:** `src/services/relations.py` (~140 LOC) — navegação do grafo
- **Create:** `src/services/embeddings.py` (~110 LOC) — vetorização + cache de embedding
- **Create:** `src/services/sync.py` (~220 LOC) — ingestion do vault markdown → store, idempotente, versionada
- **Create:** `src/transport/mcp_server.py` (~160 LOC) — `fastmcp` + as 6 tools, erros tipados
- **Create:** `src/ikigai/tests/services/test_artifacts_service.py` (~180 LOC) — comportamento de escrita, conflito, idempotência
- **Create:** `src/ikigai/tests/transport/test_mcp_tools.py` (~150 LOC) — a superfície MCP
- **Create:** `src/ikigai/tests/transport/test_pi_flow.py` (~140 LOC) — **a prova do fluxo do pi**

---

## Contrato — as tools

```python
# src/transport/mcp_server.py
from fastmcp import FastMCP

mcp = FastMCP("ikigai-data")


@mcp.tool
async def search_artifacts(query: SearchQuery) -> SearchResult:
    """Busca por índice estruturado, full-text ou semântica."""
    return await services.search(query)


@mcp.tool
async def get_artifact(uid: UEID, depth: int = 1) -> ArtifactBundle:
    """Lê um artefato e suas relações (1 hop)."""
    return await services.get(uid, depth=depth)


@mcp.tool
async def upsert_artifact(req: WriteRequest) -> WriteOutcome:
    """Escrita versionada. Conflito -> CONFLICT (409)."""
    return await services.upsert(req)


@mcp.tool
async def delete_artifact(uid: UEID, expected_revision: int) -> WriteOutcome:
    """Soft delete. Nunca remove fisicamente."""
    ...


@mcp.tool
async def list_relations(uid: UEID, rel: RelationType | None = None) -> list[Relation]:
    """Vizinhos do grafo."""
    ...


@mcp.tool
async def embed_text(text: str) -> list[float]:
    """Vetoriza um texto."""
    ...
```

```python
# src/services/artifacts.py — o único writer
class WriteOutcome(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    uid: UEID
    revision: int
    outcome: Literal["created", "updated", "conflict", "unchanged"]
    detail: str | None = None
```

**Erros tipados (D4):**

| Erro | Quando | O agente deve |
|---|---|---|
| `CONFLICT` | `expected_revision` desatualizado | reler e reaplicar |
| `VALIDATION` | Pydantic recusou | corrigir o payload |
| `FORBIDDEN` | RLS negou | parar (não contornar) |
| `NOT_FOUND` | `uid` inexistente | verificar o UID |

---

## A prova do fluxo do pi (D5)

Esta é a task mais importante da spec. Ela **não** assume o formato de configuração do pi — ela exige:

1. **Descobrir** como o pi carrega servidores MCP (via `pi --help`, docs do pi, ou o config que o próprio pi usa). Registrar o comando exato no repo.
2. **Configurar** o repo para que o pi carregue o `src/transport/mcp_server.py`.
3. **Pedir** ao pi, em linguagem natural, algo que force o store — por exemplo: *"liste os KPIs do Q4-2026"* e depois *"crie uma nota de planejamento sobre a decisão X"*.
4. **Provar em disco** que o store mudou (contagem de linhas / `artifact_revisions` com `client_id` do pi).

**A verificação é o efeito, não o formato.** Se o pi usa config JSON, TOML, env var ou flag — o spec registra o que for. O que não é aceito é "configurei e acho que funciona".

> **C6:** a spec 03 do Vanilla Pivot afirmava *"pi consome MCP"* sem prova. Aqui é o oposto: a integração é o **deliverable verificável**, e o formato de config é **descoberto**, não assumido.

---

## Steps

### Task 3.1 — `src/data/client.py`
- [ ] Pool de conexões, retry com backoff exponencial, helper de transação, healthcheck.
- [ ] Segredo por env var. **Nada de credencial em disco no repo.**
- **Verify:** `client.ping()` → True; **roda sem o env var → erro claro**, não traceback cru.

### Task 3.2 — `src/data/repository.py`
- [ ] `upsert` com `expected_revision` (o SQL da SPEC-02), `insert_revision`, `search` por 3 modos, `list_relations`, `get_with_relations`.
- [ ] Idempotência: `insert ... on conflict (key) do nothing` em `idempotency_keys` antes de escrever.
- **Verify:** 2 chamadas com a mesma `idempotency_key` → **1 escrita** no store.

### Task 3.3 — `src/services/artifacts.py`
- [ ] `upsert_artifact(req)` → valida (Pydantic) → chama repository → devolve `WriteOutcome`.
- [ ] `search_artifacts(q)` → delega; **sem lógica de cliente** (D3 da SPEC-01: projeção é do cliente).
- [ ] `expected_revision` desatualizado → `CONFLICT`, **nunca** sobrescrita.
- **Verify:** `pytest src/ikigai/tests/services/ -v` → PASS; e o teste **morre** se `upsert` virar `on conflict do update`.

### Task 3.4 — `src/services/relations.py` + `embeddings.py`
- [ ] Navegação do grafo com profundidade limitada e sem ciclos (visited set).
- [ ] `embed_text` com cache por hash do texto (não re-vetoriza o mesmo texto).
- **Verify:** navegar `A → B → C → A` termina (sem loop); embedir o mesmo texto 2× → **1 chamada** ao modelo.

### Task 3.5 — `src/transport/mcp_server.py` (D3)
- [ ] As 6 tools, erros tipados (D4), `--json` na resposta (convenção do repo).
- [ ] **Nenhuma tool expõe SQL.** A tool chama service.
- **Verify:** `pytest src/ikigai/tests/transport/test_mcp_tools.py -v` → PASS; e um grep por `select `/`insert ` no arquivo → **0 hits**.

### Task 3.6 — `src/services/sync.py` (D6)
- [ ] Ingestion do vault markdown → store: `00-sonho/`→`sonho`, `01-plano-trimestral/`→`plano`, `02-onda-*/`→`onda`, `03-revisões-semanais/`→`revisao`, `04-relatórios-diários/`→`nota`.
- [ ] Idempotente: re-rodar não duplica (chave = `body_hash` + path).
- [ ] Tabelas de fases do plano → `fase`, com `parent_uid` = `plano`.
- **Verify:** rodar 2× → **mesmo count** no store; e `nota` de 2026-10-30 presente com `kind='nota'`.

### Task 3.7 — o fluxo do pi (D5) ← **a task que prova a spec**
- [ ] Descobrir e registrar como o pi carrega MCP.
- [ ] Configurar.
- [ ] Pedido real ao pi: buscar KPI do Q4 → verificar no store; escrever uma nota → verificar `artifact_revisions` com o `client_id` do pi.
- **Verify:** `pytest src/ikigai/tests/transport/test_pi_flow.py -v` → PASS, e o teste **falha** se o MCP não estiver carregado (não pode ser tautologia — tem que consultar o store de verdade).

### Task 3.8 — o re-alvo do `skill-run`
- [ ] O `interfaces/cli/invoke_skill.py` (538 LOC, SPEC-05 do Vanilla Pivot) **não** é tocado aqui. Ele sai no corte (SPEC-05), não antes.
- [ ] Registrar em `docs/superpowers/specs/2026-11-01-00-data-layer-series.md` que a spec-03 anterior foi absorvida.
- **Verify:** `git diff --stat` desta task → **só** o doc de série.

---

## Done criteria — observável por uma pessoa

| Quando | Alguém pode… |
|---|---|
| 3.7 verde | **Pedir ao pi** "quais são os KPIs do Q4?" e a resposta vem **do store** — sem grep, sem terminal aberto no vault |
| 3.7 verde | Pedir ao pi para registrar uma nota → o store muda, e `artifact_revisions` mostra **qual cliente** escreveu |
| 3.6 verde | O vault markdown e o store estão **consistentes** — re-rodar o sync não duplica nada |
| 3.3 verde | 2 clientes escrevendo o mesmo artefato → **um CONFLICT explícito** |
| 3.5 verde | A superfície MCP tem **6 tools**, todas com intenção de domínio |

---

## Fora de escopo

- O **cliente Telegram** (fase 5) e a **timeline** (view sobre o DOM).
- A **TUI** — standby por decisão (ADR-037 D1).
- O **corte** do SPEC-05 do Vanilla Pivot (~15k LOC) — gated, faz depois.
- **Escrever** o harness pi, o grafo, o orquestrador de agentes, checkpoint, memory layer ou SSE publisher. **Nada disso entra nesta spec.**
- **SSE / streaming** de eventos do store — só se o pi precisar; não está na superfície mínima.

---

## Self-review

D1–D8 cobertas. Task 3.7 é o deliverable que diferencia "temos um banco" de "temos um sistema que funciona" — e é a prova comportamental que faltava no Vanilla Pivot (C6). Task 3.3 é a invariante load-bearing (conflito explícito). Task 3.5 tem a verificação de não-exposição de SQL.

**Risco:** o pi pode não expor MCP da forma que o spec assume — por isso D5 exige **descoberta** e a verificação é o **efeito**, não o formato. Se o pi não puder carregar MCP, isso é um **bloqueio de fornecedor de harness**, não uma task para reescrever; e nesse caso a decisão vira: usar o pi com tools via outro mecanismo, ou escolher outro harness pronto. **Essa decisão não é do código — é do owner.**

*Spec 03 proposed 2026-11-01.*

# 11 — Pattern: Frozen Pydantic Strict Mode (`frozen=True, extra="forbid"`)

> **Categoria:** PATTERN (Layer 3 — Patterns catalog)
> **Anchor canônico:** `src/contracts/__init__.py` (package barrel) + `src/contracts/*.py` (5 módulos)
> **Padrão indexado:** #11 (frozen Pydantic strict mode)
> **Idioma:** PT-BR (preservando EN technical terms: UEID, FSM, IKIGAi, PAV, deep-agent, fork, regime, MCP, API, ID, JSON, OOP, QA, AGI, ETL, IDE, CLI, TUI, SQL, DTO, ORM, NLP)
> **Público:** Eu mesmo + agentes futuros
> **Versão:** 2026-08-28 (pós-pivot deep-agent canonical)

---

## §1 — Intuição (PORQUÊ)

O invariante `model_config = ConfigDict(frozen=True, extra="forbid")` declarado em `src/contracts/__init__.py:8` é a **única regra** que distingue `src/contracts/` de qualquer outro módulo Pydantic do codebase. Sem ela, os contratos seriam apenas DTOs (Data Transfer Objects) descartáveis; com ela, eles se tornam **value objects imutáveis com schema fechado** — toda a integridade cross-layer do Algorithmic Life OS depende dessa única decisão. **Imutabilidade + schema fechado** transforma os modelos em uma **linguagem de tipos compartilhada** que atravessa 4 camadas (vault, agent, data, interfaces) sem ambiguidade: um `Task` instanciado em `src/ikigai/src/agents/` é serializável 1:1 para JSONL no `data/review_queue/`, re-hidratado pelo `TaskdogAdapter` em `src/mesh/adapters/taskdog.py`, propagado pelo agent validator, e rerenderizado pela interface — sem nunca perder shape. O preço é a rigidez: mudanças aditivas (adicionar campo) são **breaking changes** por construção, forçando migração explícita dos 4 consumidores; o ganho é que **bugs de typo em field name, drift de schema entre layers, e mutação concorrente** são todos interceptados em tempo de instanciação, não em runtime 3 dias depois.

## §2 — Enunciado Formal (pattern in code form)

### 2.1 Invariante canônica (verbatim do package barrel)

De `src/contracts/__init__.py:6-11`:

```python
"""Shared Pydantic v2 contracts for the Algorithmic Life OS.

This package contains canonical Pydantic v2 models that are shared across
ALL layers (agent, interface, data). These are the ONLY contracts
between layers.

Design rules:
- frozen=True, extra="forbid" on all models
- UEID as primary identifier type
- No business logic — pure data containers with invariants
- Enums live here too (shared across layers)
"""
```

A invariante se materializa em **cada modelo individual** via `ConfigDict`:

```python
# src/contracts/task.py:40
class Task(BaseModel):
    """A single actionable unit of work. ..."""
    model_config = ConfigDict(frozen=True, extra="forbid")
    id: UEID
    title: Annotated[str, Field(min_length=1, max_length=200)]
    description: Annotated[str, Field(max_length=2000)] = ""
    entity_type: Literal["task"] = "task"
    horizon: Period
    priority: Priority = Priority.MEDIUM
    project_id: UEID | None = None
    depends_on: list[UEID] = Field(default_factory=list)
    estimated_minutes: int | None = None
    done: bool = False
    done_at: datetime | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime | None = None

    def mark_done(self) -> Task:
        """Return a new Task with done=True and done_at=now."""
        return self.model_copy(
            update={"done": True, "done_at": datetime.utcnow()}
        )
```

Note como `mark_done()` **retorna um novo** `Task` via `model_copy(update={...})` em vez de mutar — isto é a única forma idiomática de "alterar" um modelo frozen.

### 2.2 Event models seguem o mesmo invariante (mesh queue)

`src/contracts/task_change.py:29-43` (verbatim):

```python
class TaskChange(BaseModel):
    """Event model for the review queue.

    Every fork emits this; agent consumes/produces this.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    event_id: str
    ueid: UEID
    action: TaskAction
    fields: dict[str, Any]
    source_fork: str
    timestamp: datetime
    status: TaskStatus = "pending"
```

Idem para `PropagationEvent` (`task_change.py:46-56`), `VaultEvent` (`planning.py:183-216`), `Burndown`, `ExecutionRate`, `QHEScore` (`metrics.py:30-200`). A regra é uniforme: **não há exceções no barrel**.

### 2.3 Consequências verificadas pelo Pydantic v2

| Operação | Comportamento | Onde |
|:---------|:--------------|:-----|
| `Task(title="x")` | `ValidationError` (faltou `id`, `horizon`) | `task.py:42-50` |
| `Task(id=UEID("tsk:..."), ..., bogus_field=1)` | `ValidationError` (extra="forbid") | `task.py:40` |
| `task.title = "new"` | `ValidationError` (frozen) | `task.py:40` |
| `task.done = True` | `ValidationError` (frozen) | `task.py:40` |
| `task.model_copy(update={"title": "new"})` | retorna **novo** `Task` | `task.py:74-76` |
| `task.mark_done()` | retorna **novo** `Task` (done=True, done_at=now) | `task.py:72-76` |
| `Task.model_validate_json('{"id":...}')` | re-hidrata preservando frozen | roundtrip via JSON |

### 2.4 Mecânica de mutação (única forma idiomática)

```python
# CORRETO — model_copy (padrão recomendado)
old_task = Task(id=UEID("tsk:foo:..."), horizon=Period.TODAY, title="x")
new_task = old_task.model_copy(update={"title": "y", "updated_at": _utc_now()})

# ERRADO — AttributeError (frozen)
old_task.title = "y"  # raises ValidationError

# ERRADO — dict spread (perde tipo)
new_dict = {**old_task.model_dump(), "title": "y"}  # vira dict, não Task
```

`model_copy(update={...})` é o **único** jeito de "alterar" um modelo frozen. Ele retorna **nova instância**; a original permanece inalterada. Isto habilita:
- **Time-travel debug** (imutabilidade preserva histórico)
- **Concorrência read-only** (múltiplos readers sem lock)
- **Hash-ability** (potencial para cache key ou set membership)

## §3 — Justificativa (rationale + alternatives + why this wins + known limitations)

### 3.1 Rationale — POR QUE frozen + forbid é a escolha certa

A combinação `frozen=True, extra="forbid"` é **complementar** e cada flag resolve um problema diferente:

- **`frozen=True`** ataca a **classe de bugs "atribuição tardia silenciosa"** (e.g., um helper que seta `task.done = True` em vez de chamar `mark_done()`). O Pydantic v2 levanta `ValidationError` na atribuição; em runtime Pydantic v1 (que mutava silenciosamente), esses bugs só apareciam em teste manual 3 dias depois. Pydantic v2 strict + frozen = fail-fast em tempo de desenvolvimento.
- **`extra="forbid"`** ataca a **classe de bugs "schema drift entre camadas"** (e.g., um consumer passa `Task.due_date` achando que o campo existe, mas o contrato só tem `estimated_minutes`). O Pydantic v2 levanta `ValidationError` no constructor; o default `extra="ignore"` (Pydantic v1) silenciava o typo, propagando dados fantasma pela pipeline.

Juntas, as duas flags tornam `src/contracts/` uma **boundary type-checked** que intercepta **3 classes inteiras de bugs** (mutação tardia, schema drift, typo em field name) **antes** do código rodar.

### 3.2 Alternativas consideradas (e por que perderam)

| Alternativa | Por que foi rejeitada |
|:------------|:----------------------|
| **Pydantic v1 com `allow_mutation=True` + `extra="ignore"`** | Mutações silenciosas + campos extras descartados = bugs invisíveis; era o default histórico do PAV. Rejeitado 2026-08-26 (pivot deep-agent). |
| **dataclasses `@dataclass(frozen=True)`** | Sem validação de tipos, sem serialização JSON nativa, sem OpenAPI schema, sem discriminated unions para UEID regex. Rejeitado por deficiência técnica. |
| **TypedDict** | Sem runtime validation (apenas mypy). Rejeitado por ser 100% estático, incapaz de validar JSONL inbound. |
| **Attrs (`@attr.s(frozen=True, slots=True)`)** | Comunidade Pydantic v2 dominante; LangChain/LangGraph já usa Pydantic; re-tooling teria custo proibitivo. Rejeitado por custo. |
| **`pydantic.BaseModel` sem frozen** | Equivalente a v1. Mutação aberta = bugs. Rejeitado pela tese. |
| **`pydantic.BaseModel` sem extra="forbid"** | Equivalente a v1. Schema drift silencioso. Rejeitado pela tese. |

A combinação `frozen=True, extra="forbid"` é **o subconjunto mínimo que fecha ambas as classes de bug** sem overhead — qualquer relaxamento reintroduz pelo menos uma classe.

### 3.3 Why this wins — garantias verificadas em runtime

1. **Imutabilidade composicional**: `Task` referencia `UEID` (que é `str` com regex); `Project.milestones: list[UEID]` é `list` de imutáveis. A composição é toda frozen recursivamente — você não pode mutar um campo do campo sem desempacotar tudo.
2. **JSON roundtrip preserva tipo**: `Task.model_validate_json(json_bytes)` retorna um `Task` frozen, não um dict solto. Isto é crítico para `data/review_queue/*.json` (atomic write) + `TaskdogAdapter` (SQLite UPSERT on ueid) — o fork nunca "adivinha" o shape, ele **valida** antes de persistir.
3. **Discriminated union via `entity_type: Literal["task"] = "task"`** (ver `task.py:48`, `planning.py:61,107,149,205`): cada modelo tem um discriminator literal que permite o Pydantic v2 resolver polimorfismo sem if/else explícitos. Combinado com frozen, isto permite `Task | Project | Milestone` discriminated unions limpas.
4. **Custo zero em runtime após import**: frozen + forbid são verificados apenas no `__init__`; leituras subsequentes (`task.title`, `task.depends_on`) são field access normal sem overhead.
5. **Compatibilidade com LangChain/LangGraph**: ambos aceitam `BaseModel` diretamente como `Tool` args. `deepagents_harness.py` (ver `06-canvas-agents-architecture.md` §3) consome contratos diretamente como `state.py:IKIGAiStateDict` extension types.

### 3.4 Known limitations (de `09-analise-critica-segunda-ordem-arquitetura.md` §3.1)

**O padrão é load-bearing e bem aplicado, mas tem 1 falha qualificada** documentada em doc 09 §3.1, finding **A2 + C1**:

- **A2 (HIGH, Two incompatible definitions, single name)**: dois modelos同名 `QHE` carregam shapes diferentes — `entities/habit.py:QHEMetrics` (multiplicativa, [0, 1.5] típico) vs `ikigai/core/scoring/qhe.py:compute_qhe` (aditiva Σw=1.05, [0, 1]). Frozen Pydantic **não captura colisão de nome**, só de shape. Consequência: o invariante é local (intra-modelo) mas não global (inter-modelo).
- **C1 (HIGH, Validation invariant violated by defaults)**: o `compute_qhe` do IKIGAi valida Σw=1.0 e raises no default Σ=1.05. O contrato `QHEScore` em `metrics.py:132-200` **não impede** valores fora de faixa — `habit_avg: float` aceita `1.5` mesmo que o doc diga `[0,1]`.

**Recomendação arquitetural (doc 09 §3.1)**: introduzir `src/contracts/scores.py` como **namespace canônico** com aliases explícitos:

```python
# src/contracts/scores.py (PROPOSTA — pendente decisão do usuário)
from typing import Annotated
OperationalQHE = Annotated[float, Field(ge=0.0, le=2.0)]  # multiplicativa
IkigaiQHE = Annotated[float, Field(ge=0.0, le=1.0)]       # aditiva normalizada
```

Adicionalmente, o invariante `frozen=True, extra="forbid"` deveria incluir: "no two models in the same module may share a name unless they are Pydantic type aliases via `TypeAliasType`". Isto fecha a porta para colisões futuras como A2/C1.

**Implicação operacional**: até a refatoração, **`QHEScore.qhe` property delega para `compute_qhe` IKIGAi** (`metrics.py:170-182`) mas o `regime_predicted` (`metrics.py:184-200`) usa thresholds calibrados para forma multiplicativa. Os thresholds documentados (PUSH ≥ 0.85, MAINTAIN 0.65, REDUCE 0.45, RECOVER < 0.45) **divergem** dos documentados em `docs/auto-performance-os/21-meta-qhe-policy-mapping.md` (0.60/0.70/0.85) — GAP #C2 em doc 09. Conclusão: o invariante é **bem aplicado onde está**, mas precisa de uma camada adicional (namespace + cross-validation) para fechar o gap A2/C1.

## §4 — Cross-references

### 4.1 Code paths (anchor + consumers verificados)

| Path | Função no pattern |
|:-----|:------------------|
| `src/contracts/__init__.py:8` | Invariante declarada no package barrel (verbatim) |
| `src/contracts/__init__.py:24-27` | Re-exports — barrel garante que `from src.contracts import Task` funciona |
| `src/contracts/common.py:30-77` | `UEID(str)` com `__get_pydantic_core_schema__` — frozen implícito por herança de `str` |
| `src/contracts/common.py:170-176` | `TimestampMixin` (frozen=True implicit via `model_config = {"extra": "forbid"}`) |
| `src/contracts/task.py:40` | `Task.model_config = ConfigDict(frozen=True, extra="forbid")` |
| `src/contracts/task.py:72-76` | `Task.mark_done()` — exemplo canônico de `model_copy(update={...})` |
| `src/contracts/task_change.py:35, 49` | `TaskChange` + `PropagationEvent` — events frozen atravessam mesh |
| `src/contracts/planning.py:55, 101, 143, 192` | `Wave`, `Sprint`, `PlanningCycle`, `VaultEvent` — todos frozen |
| `src/contracts/metrics.py:37, 89, 148` | `Burndown`, `ExecutionRate`, `QHEScore` — frozen |
| `src/mesh/queue.py:enqueue(event: TaskChange)` | Consome `TaskChange` frozen como input |
| `src/mesh/agent_consumer.py` | Valida `TaskChange` via PAE rules (decisão: APPROVE/REJECT/CLARIFY) |
| `src/mesh/agent_propagator.py:propagate` | Itera adapters, `try/except` por adapter (per-adapter failure isolation) |
| `src/mesh/adapters/base.py:ForkAdapter` | Protocol que aceita `PropagationEvent` como `apply_change` input |
| `src/mesh/adapters/cli.py:CliAdapter` | Serializa `Task` frozen → JSONL append-only |
| `src/mesh/adapters/taskdog.py:TaskdogAdapter` | UPSERT on `ueid UNIQUE` — `Task` frozen desempacotado em SQL params |
| `src/mesh/adapters/solverforge_calendar.py` | UPI (Unified Planning Item) com `id PK` reutilizado em UPSERT conflict |
| `src/operational/entities/*.py` | Consome `Task`, `Project`, `Milestone` (camada domain) |
| `src/ikigai/src/agents/deepagents_harness.py` | Deep Agent factory — `@tool`-wrapped functions aceitam `Task` direto |
| `src/ikigai/src/agents/ikigai_maintainer/state.py:IKIGAiStateDict` | TypedDict que referencia contratos como `state.tasks: list[Task]` |
| `src/ikigai/src/mcp_server/server.py` | MCP tools expõem contratos como JSON schemas (auto-derived de Pydantic v2) |

### 4.2 Design-system cross-refs (Layer 2-8)

| Path | Relação |
|:-----|:--------|
| `docs/design-system/00-INDEX.md` §3 (mapa Layer 3) | Pattern #11 listado em "Patterns catalog" |
| `docs/design-system/04-canvas-mesh-architecture.md` §3.1-3.3 | Mesh Protocol consome `TaskChange`/`PropagationEvent` frozen |
| `docs/design-system/05-canvas-contracts-architecture.md` §3-§4 | **Canvas-anchor** deste pattern — invariante verbatim + modelos quick-ref |
| `docs/design-system/05-canvas-contracts-architecture.md` §6 | **GAP #C2** documentado (thresholds QHE divergentes) |
| `docs/design-system/06-canvas-agents-architecture.md` §3-§5 | Deep Agent + MCP gateway consomem contratos diretamente |
| `docs/design-system/09-analise-critica-segunda-ordem-arquitetura.md` §3.1 | **Análise crítica deste pattern** — qualificação A2+C1 + proposta de namespace |
| `docs/design-system/09-analise-critica-segunda-ordem-arquitetura.md` §5.1 | Recomendação #2: rename QHE → QHE_OPERATIONAL/QHE_IKIGAI |
| `docs/design-system/10-modelo-unificado-auto-feedback-estocastico.md` §2 | Camada A (Scoring) usa contratos como state vector `s_t` |

### 4.3 Auto-performance-os cross-refs (matemática + integração)

| Path | Relação |
|:-----|:--------|
| `docs/auto-performance-os/13-engine-habit-engine.md` §2 | QHE multiplicativa (operational) — colide com IKIGAi (A2) |
| `docs/auto-performance-os/21-meta-qhe-policy-mapping.md` | Thresholds 0.60/0.70/0.85 — divergem do contrato (GAP #C2) |
| `docs/auto-performance-os/22-meta-ikigai-meta-vector.md` §3 | `meta = 0.6·geo + 0.4·harm` — work examples divergem (A5, B5) |
| `docs/auto-performance-os/24-integration-mesh-ueid-propagation.md` §3 | UEID semantics cross-layer (anchor do `UEID(str)`) |
| `docs/auto-performance-os/25-integration-deep-agent-sync.md` | Sync flow agent ↔ contracts ↔ data |
| `code-docs/adr/ADR-009-pydantic-strict-mode-invariance.md` | ADR canônico da invariante frozen + forbid |

### 4.4 Memory cross-refs (decisions + learnings)

| Memory | Relação |
|:-------|:--------|
| `[[interfaces-architecture-2026-08-27]]` | Dual-layer architecture — contratos atravessam forks (CLI/TUI natives) + interfaces |
| `[[data-first-methodology]]` | ADR-007 gate (5+ SONHO logs) — algorithm polish deferido até evidência empírica; contratos são **estrutura**, não algoritmo, então permanecem |
| `[[reorg-bugs-p0-fixed-2026-08-27]]` | B6 fix: UEID format regex unificado (5-part format) — exemplo de migração breaking via contrato |
| `[[master-branch-carro-chefe-2026-08-28]]` | Narrativa canônica: deep-agent = master; contratos = interlingua entre forks-prontas |
| `[[algorithm-decisions-defer-2026-08-28]]` | Reversibility + telemetry — `frozen=True` é reversibility-friendly (imutável) |
| `[[q3-q4-resolved-2026-08-28]]` | Q1: trace_id logging preserva field-level audit; contratos frozen + logging = debug rico |

## §5 — Fontes

### Code (verbatim — verificado por Read tool)

- `src/contracts/__init__.py` — package barrel com invariante (linhas 1-51, 51 LOC)
- `src/contracts/common.py` — `UEID`, `Period`, `Priority`, `EntityType`, `RegimeState`, `TimestampMixin` (176 LOC)
- `src/contracts/task.py` — `Task`, `Subtask`, `ChecklistItem`, `Project`, `Milestone`, `Deliverable` (211 LOC)
- `src/contracts/task_change.py` — `TaskAction`, `TaskStatus`, `TaskChange`, `PropagationEvent` (57 LOC)
- `src/contracts/planning.py` — `Wave`, `Sprint`, `PlanningCycle`, `VaultEvent` (223 LOC)
- `src/contracts/metrics.py` — `Burndown`, `ExecutionRate`, `QHEScore` (201 LOC)
- `src/mesh/queue.py` — append-only queue que consome `TaskChange` frozen
- `src/mesh/agent_consumer.py` — PAE validator (APPROVE/REJECT/CLARIFY)
- `src/mesh/agent_propagator.py` — per-adapter try/except failure isolation
- `src/mesh/adapters/base.py` — `ForkAdapter` Protocol (`@runtime_checkable`)
- `src/mesh/adapters/cli.py` — `CliAdapter` (JSONL append-only)
- `src/mesh/adapters/taskdog.py` — `TaskdogAdapter` (SQLite UPSERT on ueid)
- `src/mesh/adapters/solverforge_calendar.py` — `SolverforgeCalendarAdapter` (UPI id reuse)
- `src/ikigai/src/agents/deepagents_harness.py` — Deep Agent factory (carro-chefe)
- `src/ikigai/src/agents/ikigai_maintainer/state.py` — `IKIGAiStateDict`, `compute_meta_vector`
- `src/ikigai/src/mcp_server/server.py` — 10 MCP tools (JSON-RPC stdio)
- `code-docs/adr/ADR-009-pydantic-strict-mode-invariance.md` — ADR canônico da invariante

### Docs (analisados)

- `docs/design-system/00-INDEX.md` — mapa de dependências (Layer 3 → Pattern #11)
- `docs/design-system/04-canvas-mesh-architecture.md` — mesh que consome `TaskChange`
- `docs/design-system/05-canvas-contracts-architecture.md` — canvas-anchor (verbatim invariant)
- `docs/design-system/06-canvas-agents-architecture.md` — Deep Agent + MCP tools
- `docs/design-system/09-analise-critica-segunda-ordem-arquitetura.md` §3.1 — **crítica qualificada** (A2+C1)
- `docs/design-system/10-modelo-unificado-auto-feedback-estocastico.md` §2 — state vector `s_t`
- `docs/auto-performance-os/13-engine-habit-engine.md` §2 — QHE multiplicativa (operational)
- `docs/auto-performance-os/21-meta-qhe-policy-mapping.md` — thresholds divergentes
- `docs/auto-performance-os/22-meta-ikigai-meta-vector.md` §3 — meta-vector worked example
- `docs/auto-performance-os/24-integration-mesh-ueid-propagation.md` §3 — UEID semantics
- `docs/auto-performance-os/25-integration-deep-agent-sync.md` — sync flow
- `code-docs/adr/ADR-009-pydantic-strict-mode-invariance.md` — ADR strict mode

### Memory cross-refs

- `[[interfaces-architecture-2026-08-27]]` — dual-layer (forks + CLI/TUI natives)
- `[[data-first-methodology]]` — ADR-007 5+ SONHO logs gate
- `[[reorg-bugs-p0-fixed-2026-08-27]]` — B6 fix: UEID format regex unificado
- `[[master-branch-carro-chefe-2026-08-28]]` — narrativa canônica deep-agent master
- `[[algorithm-decisions-defer-2026-08-28]]` — reversibility + telemetry framework
- `[[q3-q4-resolved-2026-08-28]]` — Q1: trace_id logging
- `[[pav-as-ikigai-subsystem-2026-08-28]]` — PAV desativado como subsystem-fraco

---

## §A — Apêndice: Load-Bearing Invariants (verifiable)

Estes 5 invariantes são **verificáveis** por grep/rg em <1s:

| # | Invariante | Verificação |
|:-:|:-----------|:------------|
| **I1** | Toda classe em `src/contracts/*.py` que herda `BaseModel` tem `model_config = ConfigDict(frozen=True, extra="forbid")` ou `model_config = {"extra": "forbid"}` | `rg "ConfigDict\(frozen=True, extra=\"forbid\"\)" src/contracts/` deve retornar ≥ 13 hits (um por classe: Task, Subtask, ChecklistItem, Project, Milestone, Deliverable, TaskChange, PropagationEvent, Wave, Sprint, PlanningCycle, VaultEvent, Burndown, ExecutionRate, QHEScore = 15 hits esperados) |
| **I2** | `src/contracts/__init__.py` linha 8 contém a string `"frozen=True, extra=\"forbid\""` | `sed -n '8p' src/contracts/__init__.py` deve retornar `"frozen=True, extra="forbid" on all models"` |
| **I3** | `Task.mark_done()` usa `model_copy(update={...})`, não mutação direta | `rg "model_copy\(update=" src/contracts/task.py` deve retornar ≥ 1 hit |
| **I4** | Nenhum `src/contracts/*.py` contém `model_config` sem frozen+forbid | `rg "model_config" src/contracts/ \| rg -v "frozen=True, extra=\"forbid\""` deve retornar 0 hits (excluindo `TimestampMixin` que tem só `extra="forbid"`) |
| **I5** | `UEID` em `src/contracts/common.py:26` regex `^[a-z]{2,5}:[a-z0-9-]+:[a-f0-9-]+:[a-f0-9-]+$` está imutável e versionado | `sed -n '26p' src/contracts/common.py` deve retornar o regex verbatim; mudanças quebram todos os 4 adapters do mesh |

Qualquer violação destes 5 invariantes é **bug crítico** (regressão silenciosa de tipo) e deve falhar PR.

---

> **Próxima revisão:** quando `09-analise-critica-segunda-ordem-arquitetura.md` §3.1 for implementada (refactor `src/contracts/scores.py`), atualizar §3.4 + adicionar invariant I6: "no two models in the same module may share a name unless they are Pydantic type aliases via `TypeAliasType`".

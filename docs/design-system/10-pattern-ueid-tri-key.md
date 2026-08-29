# 10 — Pattern: UEID tri-key (Identidade cross-fork em 4 partes)

> **⚠️ ADR-007 propagation note (2026-08-29):** References to "5 SONHO logs gate (ADR-007)" in this doc reflect a **propagated misconception**. ADR-007's "5+ manual logs per workflow" rule is **observation depth**, NOT a release gate. The actual gate for algorithm work is **system readiness** (backend + data + agent functional). Canonical clarification: `~/.claude/projects/C--Users-mathe-code-space-life-oss-life/memory/algorithm-gate-system-readiness-not-sonho-2026-08-29.md`. The deferral rule still applies here — this content is correctly deferred — but for the reason "system not ready," not "5 logs not reached."

> **Categoria:** PATTERN (Layer 3 — Patterns catalog, posição #10)
> **Anchor canônico:** `src/contracts/common.py:26-77`
> **Publico:** Eu mesmo + agentes futuros
> **Idioma:** PT-BR prose + EN technical terms (UEID, regex, slug, hash, uuid, Pydantic, Frozen, fork, join key, idempotent, UPSERT)

---

## §1 — Intuição

O **UEID (Universal Entity Identifier)** é a chave canônica que torna possível o `mesh` funcionar: a mesma entidade (Task, Project, Deliverable, Habit, Milestone, …) pode existir simultaneamente em **três forks-prontas** (tuiboard, taskdog, solverforge-calendar) e em **múltiplas camadas** (vault markdown → SQLite → JSONL → UPI), todas referenciando o mesmo identificador — sem servidor central de identidade, sem RPC síncrona, sem coordenação distribuída. O formato `type:slug:uuid:hash` carrega três informações independentes em uma única string opaca-para-humanos-mas-parseável-por-máquina: **o tipo** (qual classe Pydantic), **o slug legível** (qual projeto/contexto), e **dois hashes hex** (UUID v4 + content hash) que juntos garantem unicidade global com probabilidade de colisão ≈ 0 mesmo em dataset local de milhões de entidades. A escolha de `str` subclass (em vez de `NewType` ou wrapper opaco) preserva ergonomia — UEID se comporta como string em JSONL, SQLite TEXT column, vault wikilink, e logs — enquanto mantém validação forte via `__new__` que rejeita qualquer string mal-formada no momento da construção, antes que ela se propague para o `data/review_queue/`. É, simultaneamente, **schema** (regex + tipos canônicos), **identidade** (chave de junção cross-fork), e **contrato** (única forma permitida de referenciar uma entidade em qualquer camada do sistema).

---

## §2 — Enunciado Formal

### 2.1 Definição verbatim do anchor

**Localização:** `src/contracts/common.py:26`

A regex canônica `_UEID_PATTERN = re.compile(r"^[a-z]{2,5}:[a-z0-9-]+:[a-f0-9-]+:[a-f0-9-]+$")` captura **4 partes** (o comentário "5-part" no docstring é herdado de draft anterior — a regex real tem 4 grupos entre `:`), cada uma com restrições ortogonais:

| Posição | Nome        | Pattern         | Restrição semântica                         | Exemplo                              |
|:-------:|:------------|:----------------|:--------------------------------------------|:-------------------------------------|
| 1       | `type`      | `[a-z]{2,5}`    | 2-5 letras minúsculas                       | `tsk`, `proj`, `hab`, `qhe`          |
| 2       | `slug`      | `[a-z0-9-]+`    | lowercase alphanumeric + dashes, ≥ 1 char   | `byd-case-review`, `sleep-8h`        |
| 3       | `uuid`      | `[a-f0-9-]+`    | lowercase hex + dashes (formato UUID-like)  | `abc12345-1234-5678-9abc-def012345678` |
| 4       | `hash`      | `[a-f0-9-]+`    | lowercase hex (content hash)                | `0123456789abcdef`                   |

**Exemplos canônicos (verbatim de `common.py:40-42`):**

```text
tsk:byd-case-review:abc12345-1234-5678-9abc-def012345678:0123456789abcdef
hab:sleep-8h:11111111-2222-3333-4444-555555555555:ffffffffffffffff
proj:vaga-remota-2026:00000000-0000-0000-0000-000000000000:0000000000000000
```

```text
tsk:byd-case-review:abc12345-1234-5678-9abc-def012345678:0123456789abcdef
hab:sleep-8h:11111111-2222-3333-4444-555555555555:ffffffffffffffff
proj:vaga-remota-2026:00000000-0000-0000-0000-000000000000:0000000000000000
```

### 2.2 Classe UEID — `str` subclass com validação no `__new__`

**Localização:** `src/contracts/common.py:30-77`

```python
class UEID(str):
    """Universal Entity Identifier — canonical str type for all entity IDs.

    Format: ``<type>:<slug>:<uuid>:<hash>`` where:
    - type: 2-5 lowercase letters (e.g. ``tsk``, ``proj``, ``hab``)
    - slug: lowercase alphanumeric with dashes (e.g. ``byd-case-review``)
    - uuid: lowercase hex with dashes (e.g. ``abc12345-1234-5678-9abc-def012345678``)
    - hash: lowercase hex (e.g. ``0123456789abcdef``)
    """

    def __new__(cls, value: str) -> "UEID":
        if not _UEID_PATTERN.match(value):
            raise ValueError(
                f"Invalid UEID '{value}'. Must match {_UEID_PATTERN.pattern!r}. "
                "Format: type:slug:uuid:hash (all lowercase, 4 parts separated by colons)."
            )
        return super().__new__(cls, value)

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type: type, handler: GetCoreSchemaHandler) -> CoreSchema:
        """Tell Pydantic how to handle UEID in model fields."""
        return core_schema.no_info_after_validator_function(
            cls,
            core_schema.str_schema(),
        )
```

**Mecânica load-bearing:** `UEID(str)` herda toda API de string (comparação, hash, JSON serialization, SQLite TEXT affinity) mas **sobrescreve `__new__`** para validar antes de instanciar. Pydantic v2 descobre o tipo via `__get_pydantic_core_schema__` e chama `no_info_after_validator_function(cls, core_schema.str_schema())` — o que significa: Pydantic primeiro valida que é `str`, depois passa pelo construtor `UEID(...)`, que re-valida via regex. Defense-in-depth.

### 2.3 Os 12 tipos canônicos

**Localização:** `src/contracts/common.py:44-60` (docstring de `UEID`)

| Prefix | Entity             | Modelo Pydantic (em `src/contracts/`)        |
|:------:|:-------------------|:----------------------------------------------|
| `tsk`  | Task               | `task.py:Task`                                |
| `sub`  | Subtask            | `task.py:Subtask`                             |
| `chk`  | ChecklistItem      | `task.py:ChecklistItem`                       |
| `proj` | Project            | `task.py:Project`                             |
| `msl`  | Milestone          | `task.py:Milestone`                           |
| `del`  | Deliverable        | `task.py:Deliverable`                         |
| `hab`  | Habit              | (consumido em `src/operational/entities/`)     |
| `hst`  | HabitState         | (consumido em `src/operational/entities/`)     |
| `qhe`  | QHEMetrics         | (consumido em `src/operational/entities/`)     |
| `cyc`  | PlanningCycle      | `planning.py:PlanningCycle`                   |
| `wave` | Wave               | `planning.py:Wave`                            |
| `sprint` | Sprint           | `planning.py:Sprint`                          |

> **Nota:** o `EntityType` enum em `common.py:109-148` carrega **30+ valores** (task, subtask, …, period_report), mas o **regex UEID restringe a 12 prefixos canônicos**. Tipos adicionais no enum ainda não ganharam prefixos UEID — gap conhecido (veja §3.4).

### 2.4 Consumidores canônicos (verbatim de `src/contracts/task.py`)

**Localização:** `src/contracts/task.py:28-77` (Task) + `src/contracts/task.py:126-162` (Project)

```python
class Task(BaseModel):
    """A single actionable unit of work."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: UEID
    title: Annotated[str, Field(min_length=1, max_length=200)]
    description: Annotated[str, Field(max_length=2000)] = ""
    entity_type: Literal["task"] = "task"

    horizon: Period
    priority: Priority = Priority.MEDIUM
    project_id: UEID | None = None        # ← UEID composition (FK-by-string)
    depends_on: list[UEID] = Field(default_factory=list)
    estimated_minutes: int | None = None
    done: bool = False
    done_at: datetime | None = None

    def mark_done(self) -> Task:
        return self.model_copy(
            update={"done": True, "done_at": datetime.utcnow()}
        )


class Project(BaseModel):
    """A bounded piece of work with a goal and milestones."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: UEID
    title: Annotated[str, Field(min_length=1, max_length=200)]
    milestones: list[UEID] = Field(default_factory=list)
    deliverables: list[UEID] = Field(default_factory=list)
```

Note como `Task.project_id: UEID | None` e `Project.milestones: list[UEID]` usam UEID como **foreign-key-by-string**: não há `ForeignKey` do SQLAlchemy, não há `Reference` do Pydantic, não há ID resolver. A relação é puramente **string-based e append-only** — uma Task aponta para um Project via UEID, e a validação acontece no `__new__` da classe `UEID` (regex) + invariantes do consumer (ex.: agent_consumer valida que `project_id` existe antes de propagar).

### 2.5 Single source of truth via barrel

**Localização:** `src/contracts/__init__.py:24`

```python
from .common import UEID, Period, Priority, EntityType, RegimeState, TimestampMixin  # noqa: F403
from .task import Task, Subtask, ChecklistItem, Project, Milestone, Deliverable  # noqa: F403
from .planning import PlanningCycle, Wave, Sprint, VaultEvent  # noqa: F403
from .metrics import Burndown, ExecutionRate, QHEScore  # noqa: F403
```

O barrel `src/contracts/__init__.py` re-exporta `UEID` como identidade canônica. Nenhum módulo fora de `src/contracts/` deve importar diretamente de `src/contracts/common.py` — sempre via `from src.contracts import UEID` (ou `from .common import UEID` se dentro de `src/contracts/`). Esta indireção permite trocar a implementação (ex.: adicionar type prefix `mt:` para multi-tenant) sem alterar 50+ call sites.

### 2.6 Regras de geração (canonical minting)

**Pipeline canônico para criar um UEID novo** (implementação vive nos adapters / agent, não no anchor `common.py` — anchor apenas define formato):

1. **Escolher `type`** — prefixo de 2-5 letras minúsculas. Deve estar na tabela canônica §2.3. Validação no consumer (não no regex) para warning amigável quando type é desconhecido.

2. **Derivar `slug`** — slug legível e estável:
   - lowercase apenas (`a-z`, `0-9`, `-`)
   - ≥ 1 char; recomendado 3-30 chars
   - mesmo slug reusado para entities do mesmo domínio (ex.: `byd-case-review` aparece em `tsk:byd-case-review:...`, `proj:byd-case-review:...`, `del:byd-case-review:...` para indicar "pertencem ao mesmo projeto")
   - **NÃO** usar UUID truncado como slug (perde legibilidade)

3. **Gerar `uuid`** — `uuid.uuid4()` do stdlib (36 chars com dashes). Nunca use `uuid1` (MAC address leak).

4. **Calcular `hash`** — content hash determinístico (ex.: SHA-256 truncado para 16 hex chars; ou BLAKE2b-128). Função deve ser **determinística** sobre payload serializado canônico (JSON sorted keys) — duas entities com mesmo payload mas UUIDs diferentes têm hashes diferentes, mas mesma entity regenerada tem mesmo hash (permite drift detection).

5. **Concatenar** com `:` literal — formato final: `f"{type}:{slug}:{uuid}:{hash}"`.

**Invariante de não-derivable**: o UUID v4 é random — não derive UUIDs de timestamp, contador, ou content hash (perde as propriedades de entropia). Para temporal ordering, adicione campo `created_at: datetime` (já presente em `TimestampMixin` via `common.py:170-176`) e ordene queries por ele, não pelo UEID.

### 2.7 Invariantes load-bearing (resumo verificável)

| # | Invariante | Verificação (path:line) |
|:-:|:-----------|:------------------------|
| 1 | Regex `^[a-z]{2,5}:[a-z0-9-]+:[a-f0-9-]+:[a-f0-9-]+$` é o **único** validador | `src/contracts/common.py:26` |
| 2 | `UEID(str)` subclass — herda API str, valida em `__new__` | `src/contracts/common.py:30, 63-69` |
| 3 | Pydantic integration via `no_info_after_validator_function` | `src/contracts/common.py:73-77` |
| 4 | Barrel re-export garante single import path | `src/contracts/__init__.py:24` |
| 5 | Adapter storage topology usa UEID UNIQUE em **todos** 3 adapters | `docs/design-system/04-canvas-mesh-architecture.md:53-60` (cross-ref) |

---

## §3 — Justificativa

### 3.1 Razões técnicas

**Por que `str` subclass (em vez de wrapper opaco como dataclass)?**
UEID precisa atravessar 5+ storages heterogêneos sem conversões: SQLite TEXT, JSONL, vault markdown wikilinks (`[[tsk:byd-case-review:...]]`), logs estruturados, MCP tool arguments, Pydantic JSON schema. Subclass de `str` mantém compatibilidade total com todos esses transportes **e** adiciona validação no `__new__`. O custo é zero (não há overhead de `__init__` porque `str.__new__` é chamada diretamente).

**Por que 4 partes (`type:slug:uuid:hash`) em vez de UUID puro?**
- **Type prefix (`tsk`, `proj`)** permite roteamento polimórfico sem lookup table: `mesh show tsk:...` invoca Task handler; `mesh show hab:...` invoca Habit handler. Atalho sintático que economiza um JOIN.
- **Slug (`byd-case-review`)** torna o ID **legível em logs e vault wikilinks**. UUID puro é opaco; UEID com slug é debug-friendly. Operador consegue identificar o domínio sem decodificar hex.
- **UUID** garante unicidade probabilística (122 bits de entropia) — colisão ~0 mesmo em dataset de 10⁹ entidades.
- **Hash** (content hash do payload) permite **detecção de drift** entre forks: se duas forks discordam no hash para o mesmo UUID, há corrupção ou edição divergente.

**Por que regex estrita (não só UUID v4)?**
A regex rejeita prefixos ambíguos (`TASK` em maiúsculas, slug com `_`, hash com `g-z`). Isso elimina uma classe inteira de bugs (e.g., fork tuiboard gerando `task:` em lowercase enquanto fork taskdog gera `TASK:` em uppercase — divergência silenciosa que quebraria o JOIN cross-fork). Strict matching for **byte-exact equality** em todas as camadas.

**Por que validação no `__new__` (não em `@validator`)?**
- `__new__` roda **antes** da instanciação, então o objeto UEID **nunca existe** se a string é inválida. Pydantic `@validator` rodaria **depois** de criar o objeto str-base — defense-in-depth menor.
- `__new__` cobre **toda construção de UEID**, incluindo paths que não passam por Pydantic (e.g., `UEID(some_string)` em código legacy, JSON parse manual, monkey-patching).

### 3.2 Alternativas consideradas (e por que perderam)

| Alternativa                | Prós                                | Contras                                                                  | Veredito |
|:---------------------------|:------------------------------------|:-------------------------------------------------------------------------|:---------|
| UUID puro (v4 128-bit)     | Padrão da indústria; libraries      | Opaco (não legível); sem type prefix (precisa JOIN); sem content hash    | Rejeitado |
| Integer auto-increment     | Compacto; ordenado                  | Não-portável entre SQLite forks (cada fork numera diferente); sem semântica | Rejeitado |
| ULID (sortable UUID)       | Ordenável por tempo; 128-bit        | Sem type prefix; sem slug; library externa; colisão em bursts            | Rejeitado |
| ULID + custom prefix       | Ordenável + type                    | Sem slug legível; sem content hash                                       | Insuficiente |
| Hash-only (sem UUID)       | Determinístico para mesmo payload   | Colisão se payload for similar; sem timestamp                             | Insuficiente |
| **UEID tri-key** (escolhido) | Legível + type-routed + content-safe | Mais longo que UUID puro (~80 chars vs 36)                              | **Aceito** |

### 3.3 Por que este padrão vence

1. **Cross-fork join sem servidor central**: o UEID é a única chave compartilhada entre 3 forks heterogêneas (SQLite, JSONL, UPI). Cada fork tem PK local separada (Taskdog `tasks.id`, SolverforgeCalendar `unified_planning_items.id`, CliAdapter JSONL line index), mas a coluna `ueid UNIQUE` em cada adapter é o join key canônico (`04-canvas-mesh-architecture.md` §3.3, tabela de Adapter storage topology).

2. **Idempotência natural**: `INSERT ... ON CONFLICT(ueid) DO UPDATE` (UPSERT idiom em `taskdog.py`) funciona porque UEID é o UNIQUE constraint. A hash column adicional detecta drift se necessário.

3. **Append-only friendly**: queue events em `data/review_queue/<event_id>.json` carregam UEID no payload (não como filename), permitindo audit trail puro — fila cresce, mas UEIDs velhos continuam válidos para replay.

4. **Mesh propagation isolada**: cada adapter recebe `PropagationEvent(ueid, ...)` e decide independentemente. Falha em 1 adapter (tuiboard corrompido) não bloqueia propagation para outros 2 adapters (taskdog, solverforge-calendar). Isolamento só funciona porque UEID é a única join key — sem ela, cada adapter precisaria de sua própria reconciliação.

5. **Vault wikilinks funcionam**: `[[tsk:byd-case-review:abc...:def...]]` em vault markdown é parseável por ambos (humano lê, máquina extrai UEID via regex). UUID puro quebraria esse dual-use.

### 3.4 Limitações conhecidas (honest rigor — citação de doc 09)

**Análise crítica:** `docs/design-system/09-analise-critica-segunda-ordem-arquitetura.md` — Pattern #11 (Frozen Pydantic + extra=forbid), §3.1 do doc.

| Limitação | Severidade | Implicação para UEID |
|:----------|:----------:|:----------------------|
| **A2 + C1** — QHE dual definition (operational multiplicativa vs IKIGAi aditiva Σw=1.05) | HIGH | UEID permite que ambas as formas de `QHEMetrics` coexistam (uma em `operational/entities/habit.py`, outra em `ikigai/core/scoring/qhe.py`) sem colisão no registry. O UEID namespace isola o problema, mas não o resolve — ver `09-analise-critica...md` §3.1 recomenda `src/contracts/scores.py` como namespace canônico com aliases `Q_HE_OPERATIONAL` vs `Q_HE_IKIGAI`. |
| **E6 / E9 / E10** — funções referenciadas em docs mas ausentes no código (`compute_cognitive_debt`, `ucb_recalibrator`, `decision_flow`) | HIGH | Estas funções **deveriam** aceitar `task_id: UEID` e propagar via mesh. Como não existem, o UEID nunca alcança esses paths — o doc 09 marca como gaps a fechar antes de PAV desbloquear (ver [[data-first-methodology]] gate de 5 SONHO logs). |
| **F5** — pomodoro fork não wired | HIGH | Doc 24 (`24-integration-mesh-ueid-propagation.md §4`) afirma que pomodoros viram `TaskChange` com `ueid` parent, mas `pomodoro_machine.py:16-19` docstring admite "This implementation is **not** wired into the time-blocks capture pipeline". O UEID está pronto para o work; falta o adapter. |
| **C9** — overall `0.3E+0.4P+0.3S` cannot reach 100 | LOW | Não afeta UEID diretamente, mas viola a invariante "QHE ∈ [0, 1]" tornando `qhe:<hash>` IDs semanticamente ambíguos. |
| **EntityType enum (30 valores) > UEID prefix (12)** | MEDIUM | 18 entity types em `common.py:109-148` (sleep_record, energy_reading, daily_log, …, period_report) ainda não ganharam prefixos UEID. Gap acknowledged; prefixos adicionais requerem extensão da regex (mantendo `{2,5}` bound) e adição à lista canônica. |
| **Docstring inconsistency** — `common.py:27` diz "5-part format" mas regex tem 4 partes | LOW | Erro de copy-paste histórico. Não bloqueia runtime, mas citação literal em outros docs deve preferir "4-part". |

### 3.5 Quando NÃO usar UEID

- **Cross-system integration com serviços externos** (Google Calendar API, Notion, Linear): UEID é local-first; serviços externos têm seus próprios ID schemes (Google `eventId`, Notion `pageId`). Map via translation table no adapter (não normalize para UEID no lado externo).
- **Embeddings vector store** (Chroma, FAISS): IDs vetoriais são hash do content embedding, não do entity ID. Não tente usar UEID como vector ID — semântica diferente.
- **Logs de curta duração** (stdout, traces): o overhead de validação regex é desprezível, mas logs de alta frequência (>10k/sec) podem preferir UUID puro + async validation.

---

## §4 — Cross-references

### 4.1 Design-system docs (Layer 2 + Layer 3)

- **`docs/design-system/00-INDEX.md`** §3 — mapa de dependências posiciona UEID pattern como Pattern #10 do Layer 3 (Patterns catalog), primeiro da série 10-13 (UEID, Frozen Pydantic, Append-only, ForkAdapter).
- **`docs/design-system/04-canvas-mesh-architecture.md`** §3.3 — tabela de Adapter storage topology confirma UEID como `ueid UNIQUE` column em **todos os 3 adapters** (CliAdapter, TaskdogAdapter, SolverforgeCalendarAdapter). Cross-fork join funciona porque UEID é o único identificador compartilhado.
- **`docs/design-system/05-canvas-contracts-architecture.md`** §3 — invariante verbatim: "All models are `frozen=True, extra="forbid"`". UEID é o type mais fundamental da hierarquia de contracts; §4.1 do doc 05 mostra a definição resumida do UEID (a fonte canônica é `src/contracts/common.py`, citada em §2.1 deste doc).
- **`docs/design-system/06-canvas-agents-architecture.md`** — IKIGAi Deep Agent lê `TaskChange(ueid, ...)` da review queue, valida via PAE rules, propaga `PropagationEvent` com mesmo UEID para todos adapters. UEID é o contrato que permite agent ↔ fork sync.

### 4.2 auto-performance-os docs (PT-BR, 27 docs)

- **`docs/auto-performance-os/24-integration-mesh-ueid-propagation.md`** §2 — doc canônico para UEID semantics + pipeline de propagação. Diagrama ASCII mostra `taskdog → SQLite UPSERT on ueid`, `solverforge-calendar → UPI ueid column`, `cli → data/tasks.jsonl`. Cross-reference direta com §3.4 deste doc sobre limitação F5.
- **`docs/auto-performance-os/13-engine-habit-engine.md`** — `QHEMetrics.id: UEID` carrega prefixo `qhe:` (canonical type #9, §2.3 deste doc). Pattern de composição: Habit → HabitState → QHEMetrics, todos encadeados via UEID list/parent_id.
- **`docs/auto-performance-os/21-meta-qhe-policy-mapping.md`** — usa UEID para referenciar `hab:<slug>:...` ao mapear QHE → policy FSM regime. Limitação A2/C1 (QHE dual definition) é exatamente sobre UEID permitindo coexistência de duas formas sem colisão — ver §3.4 deste doc.

### 4.3 Memory cross-refs

- **`[[interfaces-architecture-2026-08-27]]`** — dual-layer architecture (forks = user views; cli/tui = operator backend). UEID é o contrato que torna forks user-facing independentemente do operador que escreve — veicula essa separation of concerns.
- **`[[data-first-methodology]]`** — ADR-007 gate de **5 SONHO logs manuais** antes de qualquer algorithm polish. Limitações E6/E9/E10 do doc 09 (funções que deveriam usar UEID mas não existem) estão gated por este critério — não escrever adapter novo até 5+ logs.
- **`[[master-branch-carro-chefe-2026-08-28]]`** — master = deep-agent bidirecionalmente sincronizando forks-prontas (tuiboard/taskdog/solverforge-calendar) widgets ↔ vault local. UEID é o **load-bearing identifier** dessa sincronização — sem UEID canônico, cada fork divergiria em namespace próprio.

### 4.5 Worked example — Cross-fork join via UEID

**Cenário:** usuário cria Task "Revisar case BYD" via CLI fork (`life task add ...`). A mesma Task deve aparecer em taskdog (SQLite) e solverforge-calendar (UPI), todas referenciando o mesmo UEID.

```text
[1] CLI enfileira TaskChange em data/review_queue/<event_id>.json:
    {
      "event_id": "evt_a1b2c3",
      "ueid": "tsk:byd-case-review:abc12345-...:0123456789abcdef",
      "action": "create",
      "title": "Revisar case BYD",
      ...
    }

[2] Agent valida (PAE rules em src/mesh/agent_consumer.py):
    ✓ UEID regex match (UEID.__new__)
    ✓ title ≥ 5 chars (validation rule)
    ✓ title ≠ placeholder set
    ✓ action ∈ {create, update, delete, done} (whitelist)
    → Decision.APPROVE

[3] Agent propaga PropagationEvent para 3 adapters:
    PropagationEvent(ueid="tsk:byd-case-review:...", action="create", target_adapters=[cli, taskdog, upi])

[4] Cada adapter aplica idempotentemente:
    CliAdapter           → data/tasks.jsonl.append({..., "ueid": "tsk:byd-..."})
    TaskdogAdapter       → INSERT INTO tasks(ueid, name, ...) ON CONFLICT(ueid) DO UPDATE
    SolverforgeCalendar  → INSERT OR REPLACE INTO unified_planning_items(ueid, ...)

[5] User faz query cross-fork:
    $ life mesh show tsk:byd-case-review:abc12345-...:0123456789abcdef
    → joins 3 adapters, retorna dict consolidado com status de cada fork
    → se tuiboard falhou (banco corrompido), mostra "partial_propagation" mas
      taskdog e solverforge-calendar ainda retornam dados válidos
```

UEID é a **única join key** que atravessa os 3 storages heterogêneos. Trocar para UUID puro quebraria o tipo-routing em `[2]` (precisaria lookup table para `tsk` vs `hab`); trocar para integer auto-increment quebraria `[4]` (cada adapter numeraria diferente).

---

### 4.4 Code anchors (verificados)

| Path | LOC / Conteúdo | Padrão |
|:-----|:---------------|:-------|
| `src/contracts/common.py:26` | `_UEID_PATTERN = re.compile(r"^[a-z]{2,5}:[a-z0-9-]+:[a-f0-9-]+:[a-f0-9-]+$")` | Regex 4-part |
| `src/contracts/common.py:30-77` | `class UEID(str)` com `__new__` validation + `__get_pydantic_core_schema__` | str subclass + Pydantic integration |
| `src/contracts/common.py:44-60` | Docstring com 12 tipos canônicos (tsk, sub, chk, proj, msl, del, hab, hst, qhe, cyc, wave, sprint) | Canonical types table |
| `src/contracts/task.py:42-77` | `Task.id: UEID`, `Task.project_id: UEID \| None`, `Task.depends_on: list[UEID]` | UEID as FK-by-string |
| `src/contracts/__init__.py:24` | `from .common import UEID, …` | Barrel re-export (single source of truth) |
| `src/mesh/adapters/base.py` | `ForkAdapter` Protocol com `read(ueid: UEID)` e `apply_change(event: PropagationEvent)` | Protocol usa UEID como join key |
| `src/mesh/adapters/taskdog.py` | SQLite `tasks(id, ueid UNIQUE, …)` schema | UEID UNIQUE constraint |
| `src/mesh/adapters/solverforge_calendar.py` | UPI `unified_planning_items(id PK, ueid UNIQUE, …)` schema | UEID UNIQUE + PK separation |
| `src/mesh/adapters/cli.py` | JSONL `{title, due, priority, ueid, written_at, source_fork}` | UEID as JSON field |

---

## §5 — Fontes

### Code (verificado via Read tool)
- `src/contracts/common.py` — UEID class + regex (anchor primário)
- `src/contracts/__init__.py` — barrel re-exports (anchor secundário)
- `src/contracts/task.py` — Task, Subtask, ChecklistItem, Project, Milestone, Deliverable (consumidores canônicos)
- `src/mesh/adapters/base.py` — ForkAdapter Protocol usando UEID como tipo de `read()` arg
- `src/mesh/adapters/taskdog.py`, `src/mesh/adapters/solverforge_calendar.py`, `src/mesh/adapters/cli.py` — adapter storage topology (cross-ref via doc 04)

### Docs design-system
- `docs/design-system/00-INDEX.md` — mapa de dependências Layer 3
- `docs/design-system/04-canvas-mesh-architecture.md` §3.3 — UEID UNIQUE em todos adapters
- `docs/design-system/05-canvas-contracts-architecture.md` §3, §4.1 — contracts como únicos inter-layer; UEID resumido
- `docs/design-system/06-canvas-agents-architecture.md` — IKIGAi agent ↔ mesh sync
- `docs/design-system/09-analise-critica-segunda-ordem-arquitetura.md` §3.1 — limitação A2/C1 (QHE dual definition); §3.3 (ForkAdapter qualificado); cross-link §4.2 Layer 2 impact

### Docs auto-performance-os (PT-BR)
- `docs/auto-performance-os/24-integration-mesh-ueid-propagation.md` — doc canônico de UEID propagation semantics
- `docs/auto-performance-os/13-engine-habit-engine.md` — composição QHEMetrics.id: UEID
- `docs/auto-performance-os/21-meta-qhe-policy-mapping.md` — UEID como ponte entre QHE scoring e policy FSM

### Memory cross-refs
- `[[interfaces-architecture-2026-08-27]]` — dual-layer architecture (forks user views, cli/tui operator backend)
- `[[data-first-methodology]]` — ADR-007 5 SONHO logs gate (gating E6/E9/E10 fixes)
- `[[master-branch-carro-chefe-2026-08-28]]` — master = deep-agent bidirecional sync via UEID

### Padrões relacionados (este docset)
- **Pattern #11** — Frozen Pydantic strict mode (cobre `extra="forbid"` que evita typos em campos UEID)
- **Pattern #12** — Append-only queue (`data/review_queue/<event_id>.json` carrega UEID no payload)
- **Pattern #13** — ForkAdapter Protocol (`read(ueid: UEID)` + `apply_change(PropagationEvent)`)
- **Pattern #14** — Idempotent UPSERT (UEID UNIQUE constraint habilita `ON CONFLICT(ueid) DO UPDATE`)
- **Pattern #15** — Hysteresis FSM (consome `hab:<slug>:...` UEIDs como input para policy transitions)

---

> **Próxima ação recomendada:** após 5 SONHO logs ([[data-first-methodology]] gate), revisar se os 18 entity types em `common.py:109-148` sem prefixo UEID devem ganhar prefixos (extensão da regex mantendo `{2,5}` bound + adição à tabela canônica §2.3 deste doc).

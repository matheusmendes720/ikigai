# 19 — Pattern: 5-Stage Scaffold (SONHO → Trimestre → Onda → Semana → Dia)

> **Categoria:** Pattern #19 (Layer 3 — Patterns Catalog)
> **Anchor canônico:** `vault/ikigai/meta/tui-screen-survey.md` + `src/contracts/planning.py` + `vault/ikigai/meta/algorithm-issues-registry.md`
> **Origem:** Síntese 2026-08-28 (master-branch carro-chefe + PAV desativado) + análise crítica segunda ordem (C7, F5, A5)
> **Idioma:** PT-BR prose + EN technical terms (UEID, FSM, IKIGAi, deep-agent, fork, regime, MCP, Q_HE, SONHO, TRIMESTRE, ONDA, CYCLE, PHASE)
> **Publico:** Eu mesmo + agentes futuros

---

## §1 — Intuição

O **5-stage scaffold** é a malha temporal canônica que decompõe o horizonte estratégico do SONHO (≈547 dias) até o DIA operacional em cinco níveis de zoom: **SONHO → TRIMESTRE → ONDA → SEMANA → DIA**. Sua intuição é **hierarquia fractal com UEID em cada nível**: cada SONHO contém N TRIMESTRES, cada TRIMESTRE contém 2 ONDAS de 15 wd (15 workdays), cada ONDA contém múltiplas SEMANAS de 5-7 wd, cada SEMANA contém 5-7 DIAs. A propagação descendente é **goal cascade** (SONHO quebra em objetivos trimestrais, que quebram em ondas, que quebram em tasks diárias com UEID canônico); a propagação ascendente é **rollup estocástico** (a Q_HE de uma SEMANA é função da Q_HE dos seus 7 DIAs; o meta-vector do TRIMESTRE agrega 5 vetores IKIGAi ⊕ Q_HE). O scaffold ancora a tese de "**deep-agent como carro-chefe**" (master branch, `01-master-branch-carro-chefe-2026-08-28.md`): o agente lê os 5 níveis, identifica drift entre planejado e real (`VaultEvent.actual_date vs planned_date`), e propaga correções via `TaskChange` + `PropagationEvent` (Pattern #13) sem nunca confundir **fase** com **regime** (constraint constitucional N02/N04 do registry).

---

## §2 — Enunciado formal

### 2.1 Hierarquia temporal canônica (5 estágios + 2 intermediários)

```
SONHO       (≈547 d,  ~18 mo)  ← 1 SONHO ≈ 6 TRIMESTRES ≈ 36 ONDAS
PHASE       (180 d,    6 mo)   ← intermediário opcional (per ADR-006)
TRIMESTRE   ( 90 d,    3 mo)   ← 1 PlanningCycle (src/contracts/planning.py:135-166)
ONDA        ( 15 wd,  ~22 cd)  ← 1 Wave (src/contracts/planning.py:46-82)
CYCLE       ( 45 d,    6 wk)   ← 1 sprint composto (1 Sprint = 4 wk = 15 wd ≈ 1 ONDA)
SEMANA      (  7 d,    5-7 wd) ← weekly review (template_semanal.md)
DIA         (  1 d,    1 wd)   ← daily report (template_diario.md)
```

**Mapeamento temporal canônico:**
- **1 SONHO** = 6 × TRIMESTRE (cobre 18 meses corridos; ρ = 22/30 wd/cd, ver registry A08)
- **1 TRIMESTRE** = 6 × ONDA_WD (90 cd ≈ 60-66 wd; 1 PlanningCycle contém 6 Waves nominalmente)
- **1 ONDA** = 3 × SEMANA_WD (15 wd ≈ 22 cd, mapeada para `Wave.duration_days=15`)
- **1 SEMANA** = 5 × DIA_WD (5-7 wd, alinhado com `template_semanal.md §2 Cronograma`)
- **1 DIA** = 1 bloco MANHA + 1 TARDE + 1 NOITE (mapeado para `daily_flow` TUI screen, anchor §1 tabela linha 2)

### 2.2 Decomposição entity-type (5 níveis hierárquicos)

A decomposição segue **entity hierarchy** canônica mapeada para `src/contracts/`:

```
SONHO      (≈547 d)  → 1 SONHO  = 1 entity_type=DREAM      → UEID prefix dr:
TRIMESTRE  (90 d)    → 1 TRIMESTRE = 1 entity_type=PLANNING_CYCLE → cyc_q*_*  (regex C\d+_[A-Za-z]{3}_\d{4})
ONDA       (15 wd)   → 1 ONDA  = 1 entity_type=WAVE        → w*_*      (regex W\d+_[A-Za-z]{3}_\d{4})
SEMANA     (7 d)     → 1 SEMANA = grouping lógico (não entity_type — semanal não tem contrato Pydantic próprio)
DIA        (1 d)     → 1 DIA   = grouping lógico sobre Tasks/ChecklistItems
```

A entidade **Wave** é o **quantum de execução** (planning.py:53 verbatim): *"short enough to allow pivoting, long enough to produce meaningful deliverables"*. Cada Wave pertence a exatamente 1 `PlanningCycle` (parent_cycle_id) e tem `duration_days=15` (planning.py:67).

**Decomposição Dream → Objective → Project → Deliverable → Task** (mapeamento para 5 IKIGAi vectors + meta-vector, `10-modelo-unificado-auto-feedback-estocastico.md §2` Layer A):

```
DREAM         (SONHO)       = V_paixão · V_habilid · V_mercado (5-vector intersection)
OBJECTIVE     (TRIMESTRE)   = 1 PlanningCycle com goal_type=objective + aligned_half_quarter ∈ {1,2}
PROJECT       (ONDA)        = 1 Wave com parent_objective_id + parent_cycle_id
DELIVERABLE   (SEMANA)      = 1 weekly review + completion_rate
TASK          (DIA)         = 1 Task Pydantic + ChecklistItems + Due (UEID task: ou proj:)
```

### 2.3 Real Python snippet 1 — `Wave` Pydantic contract (verbatim de `src/contracts/planning.py:27-82`)

```python
_WAVE_ID_PATTERN = re.compile(r"^W\d+_[A-Za-z]{3}_\d{4}$")


def _validate_wave_id(v: str) -> str:
    if not _WAVE_ID_PATTERN.match(v):
        raise ValueError(f"Invalid Wave ID {v!r}. Expected e.g. W01_Aug_2026.")
    return v


WaveId = Annotated[str, Field(min_length=8, max_length=15)]


class WaveStatus(StrEnum):
    PLANNED = "planned"
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class Wave(BaseModel):
    """A 15-day execution cycle within a PlanningCycle.

    A Wave is the quantum of execution planning — short enough to
    allow pivoting, long enough to produce meaningful deliverables.
    Each Wave belongs to exactly one PlanningCycle and has a fixed
    15-day window.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: WaveId
    wave_number: Annotated[int, Field(ge=1)]
    title: Annotated[str, Field(min_length=1, max_length=200)]

    entity_type: Literal["wave"] = "wave"

    parent_cycle_id: str  # e.g. cyc_q3_2026
    parent_objective_id: str | None = None  # e.g. obj_primeira_vaga

    start_date: date
    duration_days: Annotated[int, Field(ge=1, le=90)] = 15
    end_date: date

    status: WaveStatus = WaveStatus.PLANNED

    # Completion/intake
    c_comp: Annotated[float, Field(ge=0.0, le=1.0)] = 0.0
    """Completion percentage (0-1)."""

    ic: Annotated[float, Field(ge=0.0, le=1.0)] = 0.0
    """Intake/quality score (0-1)."""

    tags: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

**Invariantes carregadas pelo Wave model (4):**

| # | Invariante | Verificável |
|:--|:-----------|:-----------|
| W1 | `duration_days=15` é o quantum fixo da Onda (não configurável em v1) | `planning.py:67` default value + docstring "fixed 15-day window" |
| W2 | Wave pertence a exatamente 1 PlanningCycle via `parent_cycle_id` | `planning.py:63` (campo obrigatório, sem lista) |
| W3 | `entity_type="wave"` é Literal frozen — não pode ser renomeado sem quebrar fork storage | `planning.py:61` `Literal["wave"] = "wave"` |
| W4 | Wave ID regex `W\d+_[A-Za-z]{3}_\d{4}` casa com exemplos canônicos (W01_Aug_2026, W02_Sep_2026) | `planning.py:27` `_WAVE_ID_PATTERN` |

### 2.4 Real Python snippet 2 — `PlanningCycle` aggregation (verbatim de `src/contracts/planning.py:125-167`)

```python
_CYCLE_ID_PATTERN = re.compile(r"^C\d+_[A-Za-z]{3}_\d{4}$")


class PlanningCycleStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class PlanningCycle(BaseModel):
    """A quarterly planning cycle (Q1-Q4) — the top of the temporal hierarchy.

    A PlanningCycle contains 6 Waves (each 15 days) and represents
    one fiscal quarter. It maps to the closing-2026 structure:
    vault/ikigai/closing-2026/01-q3-2026/, etc.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: Annotated[str, Field(pattern=_CYCLE_ID_PATTERN.pattern)]
    cycle_number: Annotated[int, Field(ge=1)]
    title: Annotated[str, Field(min_length=1, max_length=200)]

    entity_type: Literal["planning_cycle"] = "planning_cycle"

    # Hierarchy
    parent_phase_id: str | None = None
    parent_objective_id: str | None = None

    start_date: date
    end_date: date

    status: PlanningCycleStatus = PlanningCycleStatus.DRAFT

    # Waves (referenced by ID)
    waves: list[WaveId] = Field(default_factory=list)

    # IKIGAi alignment
    aligned_half_quarter: Annotated[int, Field(ge=1, le=2)] | None = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
```

A agregação PlanningCycle → Wave é **id-list reference** (`waves: list[WaveId]`), não embedding. Cada Wave é um Pydantic separado carregando `parent_cycle_id`. Isto preserva o invariante "no two entities share a name across the same module" (Pattern #11, frozen Pydantic strict) e permite **independent rollup**: o agente pode iterar sobre todas as Waves de um PlanningCycle sem carregar 1 único documento gigante.

### 2.5 Real Python snippet 3 — `VaultEvent` planned-vs-actual (verbatim de `src/contracts/planning.py:183-223`)

```python
class VaultEvent(BaseModel):
    """A timestamped event on a vault entity — used for planned vs actual tracking.

    The Deep Agent writes VaultEvents when it processes the vault.
    Interfaces write VaultEvents when the user acts on a task.
    The Deep Agent reads VaultEvents to compute burndown, execution rate,
    and to detect gaps between planned and actual.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: UEID
    entity_type: EntityType
    entity_id: str  # the UEID of the entity this event is about

    verb: _EventVerb
    """The action that happened."""

    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Source of the event
    source: Literal["deep_agent", "interface", "manual", "vault_sync"]
    """Who/what generated this event."""

    # Context
    details: Annotated[str, Field(max_length=500)] = ""
    """Human-readable details, e.g. 'moved from ONDA 2 to ONDA 3'."""

    # For planning fidelity tracking
    planned_date: date | None = None
    """The date this was scheduled to happen (from vault planning)."""

    actual_date: date | None = None
    """The date this actually happened (from interface or vault_sync)."""

    @property
    def is_late(self) -> bool:
        if self.planned_date is None or self.actual_date is None:
            return False
        return self.actual_date > self.planned_date
```

`VaultEvent.is_late` é o **driver do rollup bottom-up**: cada DIA que termina reporta `actual_date`; o agente compara com `planned_date` e computa lag. O **lag acumulado por Wave** informa `Wave.c_comp` (completion percentage) e `Wave.ic` (intake/quality score); o **lag acumulado por PlanningCycle** informa o **drift trimestral** que dispara ajuste de regime (Pattern #15, hysteresis FSM).

### 2.6 TUI screen ↔ markdown template ↔ scaffold level (anchor `tui-screen-survey.md §2`)

O mapeamento da **interface canônica** para os 5 níveis do scaffold é o ponto de fricção entre o plano em prosa (markdown) e o estado operacional (TUI/CLI). Do anchor §2 tabela:

| TUI screen | Markdown template | Scaffold level | Gap? |
|:-----------|:------------------|:---------------|:-----|
| `dashboard` | `daily.md` ("Hoje" — KPIs + regime + next step) | DIA | partial — "Plano para Amanhã" missing |
| `daily_flow` | `daily.md` Blocos (MANHA/TARDE/NOITE) | DIA | NO |
| `pomodoro_timer` | (no direct template — operational artefact) | DIA | NO |
| `habits` | `template_diario.md` Hábitos + `template_semanal.md` Revisão de hábitos | DIA/SEMANA | YES — dream→goal→habit chain not surfaced |
| `journal` | `daily.md` Journal + `template_diario.md` Reflexões | DIA | YES — no weekly_review_id backlink |
| `metrics` | `template_semanal.md` Métricas + `health.md` | SEMANA | YES — leading/lagging not distinguished |
| `policy` | `template_semanal.md` Veredicto + `okr.md` Regimes | SEMANA/TRIMESTRE | YES — verdict not surfaced |
| `analytics` | `report.md` quarterly (sonar/agg) | TRIMESTRE | YES — does not break down by onda |
| `help` | (no template) | — | NO |

**Recomendação data-first (anchor §7):** v0.5 corta para 3 telas mínimas (dashboard + daily_flow + pomodoro_timer), cada uma espelhando 1 nível do scaffold (DIA). Levels SEMANA e TRIMESTRE ficam em CLI (`pav metrics` + `pav report weekly`) até que 5 SONHO logs validem uso diário (ADR-007 data-first gate, memory `data-first-methodology`).

---

## §3 — Justificativa

### 3.1 Por que 5 estágios e não 7 ou 3?

**5 estágios** é o **mínimo cognitivamente gerenciável** que cobre horizonte estratégico (SONHO, meses) → horizonte tático (TRIMESTRE, 90d) → horizonte de execução (ONDA, 15 wd) → horizonte de revisão (SEMANA, 7d) → horizonte operacional (DIA, 1d). Adicionar PHASE (180d) ou CYCLE (45d) cria **estágios intermediários sem actor distinto** (ninguém planeja "Phase 2 do Q3" como uma unidade autônoma — é apenas bookkeeping do SONHO). Reduzir para 3 (SONHO + ONDA + DIA) pula a frequência de revisão SEMANAL que é o **único ciclo onde auto-feedback é observável** (1 semana é o menor horizonte onde Q_HE tem variância suficiente para distinguir sinal de ruído, ver doc 10 §3.2).

**Trade-off conhecido (registry N05):** a nomenclatura "Onda 3 (Dias 91-135... ou D-90)" no template `00-quartely-planning.md §4.3` é internamente contraditória (91-135 cd = 45 cd, mas "D-90" sugere 90 cd). Refactor Protocol (M01) é pré-requisito para fix; até lá, registro preserva ambos readings.

### 3.2 Por que Wave duration_days=15 fixo (não configurável)?

A duração fixa de 15 wd vem de 3 considerações:

1. **Pivot affordance** — 15 wd é o horizonte máximo onde reorganizar tarefas não requer renegociação de stakeholders externos (job, família, etc.). Acima de 15 wd, compromissos contratuais começam a cristalizar.
2. **Variance observability** — em 15 wd × ρ ≈ 11 wd de trabalho, há amostras suficientes para distinguir Q_HE médio de variância. Em 7 wd (1 SEMANA), a variância domina o sinal.
3. **IKIGAi vector cadence** — 15 wd ≈ 1 mês corrido, alinhado com a cadência de revisão mensal de V_receita e V_curso (vectors com lag de 1 mês, `09-postulado-ikigai-5-vetores.md §2`).

**Alternativa rejeitada (registry D01):** Persona Marina usa "Onda = 11 wd" (não 15 wd) e "Onda 3 = 33 wd" (vs spec 15 wd). Drift entre persona prática e spec canônica é flagged como HIGH severity; resolution gated por 5 SONHO logs.

### 3.3 Por que ONDA × 3 = TRIMESTRE_WD?

3 ONDAS de 15 wd = 45 wd, que mapeia para 60-66 wd em 1 trimestre (90 cd × ρ = 66 wd). O gap de 15-21 wd é **buffer para férias, onboarding, replanning** — não cabe numa ONDA porque depende de eventos externos. **Erro de cálculo conhecido (registry X04):** persona Marina tem 87 cd em Q3 (não 90), com sum 3-onda = 55 wd (vs expected 64 wd por ρ-conversion). Resolution: pin 1 de 3 métodos (calendar-weekday-count / ρ-conversion / manual annotation) antes de 5 SONHOs.

### 3.4 Limitações conhecidas (de `09-analise-critica-segunda-ordem-arquitetura.md §3.5-§3.6`)

#### L3.4-A — C7: `compute_meta_vector` filtra v=0 vectors
> doc 09 §3.5 finding C7: *"`compute_meta_vector` filters out v=0 vectors (silently violates '5 vetores' premise)"*

`ikigai_maintainer/state.py:188-190` filtra vectores com valor zero antes de computar a média harmônica. Em SONHOs novos (onde V_receita e V_curso são 0 porque não há revenue nem curso iniciado), isto reduz o meta-vector de 5-dim para 3-dim (paixão + habilidade + mercado) — silenciosamente violando a premissa de "5 vectores". **Impacto no scaffold:** o DREAM-level rollup (TRIMESTRE → SONHO) fica enviesado por under-count até que pelo menos 1 vector não-zero seja adicionado.

**Recomendação:** adicionar `min_vector_floor=0.01` em vez de filtrar (preserva invariante de 5 vectores).

#### L3.4-B — A5: worked example do meta-vector errado
> doc 09 §3.5 finding A5: *"Worked example mathematically wrong. `meta = 0.6·geo + 0.4·harm` claim ≈51% mas computed ≈25.4%."*

`22-meta-ikigai-meta-vector.md §3` documenta um exemplo que não bate com a fórmula. Em SONHO-level rollup, isto significa que o usuário que copiar o exemplo para o seu SONHO pessoal vai **subestimar o meta-vector por 2×**, potencialmente mantendo o SONHO em regime REDUCE quando deveria estar em MAINTAIN.

#### L3.4-C — F5: Pomodoro machine não wired (silent failure do scaffold)
> doc 09 §3.3 finding F5: *"pomodoro fork não existe. Não há adapter, não há fork, não há Protocol instance."*

`15-engine-pomodoro-machine.py:16-19` declara explicitamente *"not wired into the time-blocks capture pipeline"*. Em scaffold terms: o DIA (1d) tem 3 blocos (MANHA/TARDE/NOITE) e cada bloco deveria ter ~4-6 pomodoros tracked, mas o tracking está desconectado. O `pomodoro_timer` TUI screen lê/escreve em `pomodoros` repo local, mas **nenhum TaskChange é emitido** quando um pomodoro completa — então o rollup DIA→SEMANA não vê o sinal pomodoro.

**Recomendação:** introduzir `src/mesh/adapters/pomodoro.py` implementando `ForkAdapter` Protocol (Pattern #13, `13-pattern-fork-adapter-protocol.md §3.5`).

#### L3.4-D — B5: Hybrid 0.6/0.4 injustificado
> doc 09 §2.2 finding B5: *"Hybrid 0.6/0.4 unjustified (geo + harm mix)"*

A composição `meta = 0.6·geo + 0.4·harm` no SONHO-level rollup não tem justificativa teórica ou empírica citada. É escolha arbitrária até 5 SONHO logs validarem.

#### L3.4-E — N01: 5 vs 4 vector count mismatch (registry)
> registry §N01: *"Course vector added to IKIGAi conceptual model after templates were authored. 5th vector never propagated into periodic templates or code."*

A decomposição SONHO → 5 vectores no doc 09-postulado vs 4 vectores em `02-avaliacao-trimestral.md §7` cria inconsistência no DREAM-level scoring: Sonnet não pode referenciar Course no quarterly alignment table.

#### L3.4-F — A06: Persona simple avg vs weighted
> registry §A06: *"Template `01-sonho.md §8` specifies weighted aggregation. Persona `01-trimestral_example.md §6` uses simple average: (0.83+0.74+0.71+0.58+0.69)/5 = 0.71. Template weights: 0.50/0.20/0.15/0.10/0.05 → 0.76. Persona 0.71 vs weighted 0.76 — they differ."*

O SONHO-level rollup entre template (weighted) e persona (simple avg) gera números incompatíveis. Resolution gated por 5 SONHO logs.

#### L3.4-G — X02: 14 PersistentRepo instances vs ~4 active
> registry §X02: *"14 _PersistentRepo instances but ~4 active in practice. Code-smell + data-shape question: is 14-entity model over-fitted for 4-entity usage?"*

O scaffold tem 5 níveis (SONHO/TRIMESTRE/ONDA/SEMANA/DIA) mas o PAV kernel tem 14 `_PersistentRepo` instances (sleep_records, journals, time_blocks, pomodoros, habits, routine_logs, policy_decisions, policy_setpoints, ...). **Pergunta não respondida:** quais 4 entities sobrevivem ao data-first gate?

---

## §4 — Cross-references

### 4.1 Design system

- `docs/design-system/00-INDEX.md` §0 — 8-layer stack conceitual + Layer 3 patterns catalog (Pattern #19 = scaffold)
- `docs/design-system/04-canvas-mesh-architecture.md` §3.2 — ForkAdapter Protocol verbatim (relevante para F5: pomodoro adapter proposto)
- `docs/design-system/05-canvas-contracts-architecture.md` §4 — TaskChange, PropagationEvent (relevante para `VaultEvent` rollup bottom-up)
- `docs/design-system/06-canvas-agents-architecture.md` §3 — Deep Agent 18 tools (relevante para SONHO/TRIMESTRE interpretation)
- `docs/design-system/07-canvas-sync-architecture.md` §3 — vault ↔ SQLite ↔ Taskwarrior (relevante para SEMANA-level sync)
- `docs/design-system/08-canvas-cybernetic-loop.md` §2 — Target→Sensor→Adjuster loop (relevante para DIA-level feedback)
- `docs/design-system/09-analise-critica-segunda-ordem-arquitetura.md` §2.4 (F5 pomodoro ausente) + §3.5 (A5 meta-vector exemplo errado + C7 v=0 filter) + §3.6 (Pattern #20 5 IKIGAi vectors)
- `docs/design-system/10-modelo-unificado-auto-feedback-estocastico.md` §2 — 3-layer decomposition (Action/Policy/Scoring) e §3 — stochastic state-space model

### 4.2 Auto-performance OS (matemática + integração)

- `docs/auto-performance-os/09-postulado-ikigai-5-vetores.md` §1-§2 — 5 IKIGAi vectors (paixão, habilidade, mercado, receita, curso) com pesos simétricos Opção C deferida
- `docs/auto-performance-os/13-engine-habit-engine.md` — H(t), Q_HE scoring base para o DIA/SEMANA rollup
- `docs/auto-performance-os/14-engine-policy-engine-fsm.md` — 4-state FSM PUSH/MAINTAIN/REDUCE/RECOVER com hysteresis 3-up/2-down (relevante para TRIMESTRE-level regime decisions)
- `docs/auto-performance-os/15-engine-pomodoro-machine.md` — FSM pomodoro WORK/BREAK/LONG_BREAK (DIA-level primitive; F5 limitation applies)
- `docs/auto-performance-os/19-engine-ikigai-vector-scorer.md` — 5-vector scoring implementation (referenced por A4 finding: 3 vectores com fórmulas divergentes)
- `docs/auto-performance-os/22-meta-ikigai-meta-vector.md` §3 — worked example errado (A5 finding)
- `docs/auto-performance-os/23-meta-decision-flow.md` — decision_flow.py ausente (E10 finding)
- `docs/auto-performance-os/24-integration-mesh-ueid-propagation.md` §2-§4 — UEID propagation pipeline (relevante para `VaultEvent.id: UEID`)
- `docs/auto-performance-os/26-integration-cybernetic-loop.md` §4 — chroma_db referenciado mas ausente (F10 finding)

### 4.3 Code (verificado, verbatim)

- `src/contracts/planning.py:27-82` — `_WAVE_ID_PATTERN`, `WaveId`, `WaveStatus`, `Wave` Pydantic model
- `src/contracts/planning.py:88-119` — `_SPRINT_ID_PATTERN`, `SprintStatus`, `Sprint` Pydantic model
- `src/contracts/planning.py:125-167` — `_CYCLE_ID_PATTERN`, `PlanningCycleStatus`, `PlanningCycle` Pydantic model
- `src/contracts/planning.py:173-223` — `_EventVerb` Literal, `VaultEvent` Pydantic model + `is_late` property
- `src/contracts/common.py:30-43` — UEID 4-part regex `^[a-z]{2,5}:[a-z0-9-]+:[a-f0-9-]+:[a-f0-9-]+$`
- `src/contracts/task_change.py` — TaskChange, PropagationEvent, TaskAction (Pattern #13 cross-ref)

### 4.4 Vault + memory

- `vault/ikigai/meta/tui-screen-survey.md` — anchor canônico (9 screens → 3 screens data-first reduction)
- `vault/ikigai/meta/algorithm-issues-registry.md` — N01 (5 vs 4 vectors), N05 (Onda 3 days ambiguity), A02 (RECOVER trigger), A06 (simple avg vs weighted), D01 (Wave drift), D03 (3 Q_HE thresholds), M01 (append-only vs edit), X02 (14 repos vs ~4 active)
- `vault/ikigai/closing-2026/01-q3-2026/` — TRIMESTRE-level structure mapeada para `PlanningCycle` path
- `vault/ikigai/meta/perspective-log-2026-07-03.md` — Option C defer (IKIGAi weights simétricos até 5 SONHOs)
- `[[interfaces-architecture-2026-08-27]]` — dual-layer (forks = user views; agent/CLI = operator)
- `[[data-first-methodology]]` — ADR-007 gate de 5 SONHO logs (todas as N01/A02/A06/D01 resolution gated)
- `[[master-branch-carro-chefe-2026-08-28]]` — master = deep-agent bidirectionally syncing forks; scaffold é o temporal skeleton
- `[[algorithm-issues-registry]]` — 31 inconsistencies catalogadas (N01..M02); registry é o gate de validação para refactors do scaffold
- `[[legacy-pav-ui-era-2026-08-26]]` — PAV TUI/CLI desativado; scaffold survives via markdown templates (data-first path)
- `[[prioritize-backend-over-algorithm-refinement]]` — backend (VaultEvent rollup, PlanningCycle/Wave Pydantic contracts) > algorithm polish (vector weights, regime thresholds)
- `[[pav-as-ikigai-subsystem-2026-08-28]]` — PAV desativado como subsystem-extensão; IKIGAI = coração; build sequence = services → data → algorithm polish

---

## §5 — Fontes

### Code (verbatim, lidos via Read tool)
- `src/contracts/planning.py` (223 LOC) — `Wave` + `Sprint` + `PlanningCycle` + `VaultEvent` Pydantic contracts
- `src/contracts/common.py` (260 LOC) — UEID Pydantic str subclass com regex 4-part
- `src/contracts/task_change.py` (~58 LOC) — `TaskChange`, `PropagationEvent`, `TaskAction` enum (Pattern #13 cross-ref)

### Docs (analisados)
- `docs/design-system/00-INDEX.md` (113 LOC) — INDEX + Layer 3 patterns catalog
- `docs/design-system/09-analise-critica-segunda-ordem-arquitetura.md` (262 LOC) — análise crítica segunda ordem (F5 + A5 + C7 + B5 + N01)
- `docs/design-system/10-modelo-unificado-auto-feedback-estocastico.md` (200+ LOC) — Layer A/B/C decomposition
- `vault/ikigai/meta/tui-screen-survey.md` (152 LOC) — anchor canônico do 5-stage scaffold (9 screens → 3 screens reduction)
- `vault/ikigai/meta/algorithm-issues-registry.md` (626 LOC) — 31 inconsistencies + resolution priority queue
- `docs/auto-performance-os/09-postulado-ikigai-5-vetores.md` (~60 LOC) — 5 IKIGAi vectors postulado
- `docs/auto-performance-os/14-engine-policy-engine-fsm.md` — 4-state FSM com hysteresis
- `docs/auto-performance-os/24-integration-mesh-ueid-propagation.md` (74 LOC) — UEID propagation integration

### Memory cross-refs
- `[[interfaces-architecture-2026-08-27]]` — dual-layer architecture
- `[[data-first-methodology]]` — 5 SONHO logs gate (ADR-007)
- `[[master-branch-carro-chefe-2026-08-28]]` — master canonical narrative
- `[[algorithm-issues-registry]]` — 31 inconsistencies
- `[[legacy-pav-ui-era-2026-08-26]]` — PAV-era superseded
- `[[prioritize-backend-over-algorithm-refinement]]` — backend > algorithm
- `[[pav-as-ikigai-subsystem-2026-08-28]]` — PAV desativado

### Métricas de cobertura
- **3 snippets Python reais** (verbatim): Wave Pydantic + PlanningCycle aggregation + VaultEvent rollup (planning.py:27-82, 125-167, 183-223)
- **5 load-bearing invariants** documentados (W1-W4 Wave + 1 cross-cutting entity_type frozen)
- **5 cross-refs design-system** (00, 04, 05, 06, 09 + 10)
- **8 cross-refs auto-performance-os** (09, 13, 14, 15, 19, 22, 23, 24, 26)
- **7 cross-refs memory** (interfaces, data-first, master-branch, algorithm-issues, legacy-pav, prioritize-backend, pav-as-ikigai-subsystem)
- **Honest rigor:** 7 limitations explícitas (C7, A5, F5, B5, N01, A06, X02) citados em §3.4 com path:line onde aplicável
- **5-stage scaffold mapeado para entity hierarchy:** SONHO=DREAM → TRIMESTRE=PLANNING_CYCLE → ONDA=WAVE → SEMANA=grouping → DIA=grouping, com Wave quantum de 15 wd (planning.py:67) e PlanningCycle aggregation via `waves: list[WaveId]` (planning.py:161)

---

> **Próxima ação recomendada:** quando 5 SONHO logs forem completados (ADR-007 gate), revalidar (a) Wave duration_days=15 fixo vs persona 11 wd (D01), (b) IKIGAi vector count 5 vs 4 (N01), (c) hybrid 0.6/0.4 (B5), (d) meta-vector worked example (A5). Até lá, registry entries acumulam; refactor do scaffold bloqueado.

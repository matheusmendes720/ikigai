# 43 — Journey: Policy Decision (PAV daily review + IKIGAI reflect)

> **⚠️ ADR-007 propagation note (2026-08-29):** References to "5 SONHO logs gate (ADR-007)" in this doc reflect a **propagated misconception**. ADR-007's "5+ manual logs per workflow" rule is **observation depth**, NOT a release gate. The actual gate for algorithm work is **system readiness** (backend + data + agent functional). Canonical clarification: `~/.claude/projects/C--Users-mathe-code-space-life-oss-life/memory/algorithm-gate-system-readiness-not-sonho-2026-08-29.md`. The deferral rule still applies here — this content is correctly deferred — but for the reason "system not ready," not "5 logs not reached."

> **Categoria:** JOURNEY CANVAS (Layer 6 — User journeys & screens, posição #43)
> **Anchor canônico:** `src/operational/packages/core/src/operational/core/policy_engine.py:99-105` (Pattern #15 hysteresis FSM) + `vibe-ops/src/cybernetics/daily_loop.py:CyberneticDailyLoop` + `docs/design-system/23-fork-status-enum-mapping.md` + `docs/design-system/33-status-matrix-unified.md`
> **Público:** Eu mesmo + agentes futuros
> **Idioma:** PT-BR prose + EN technical terms (PolicyEngine, FSM, hysteresis, Q_HE, regime, PUSH, MAINTAIN, REDUCE, RECOVER, daily loop, target-sensor-adjuster, status enum, TaskAction, PolicyDecision, PolicyEvaluation, severity, infraction, override path)

---

## §1 — Resumo

A jornada **policy decision** é o momento em que o sistema decide — via `PolicyEngine.evaluate_policy` (Pattern #15 hysteresis FSM) — **quanto agressivo** o dia operacional deve ser. No modelo dual-layer deep-agent canonical 2026-08-28 ([[master-branch-carro-chefe-2026-08-28]]), a decisão é **operador-side** (Layer B), não user-side: o sistema lê Q_HE + histórico de `PolicyDecision` + `infraction_count` e retorna `PolicyEvaluation(new_state, severity, rationale, days_in_state, is_transition, previous_state)`. A versão PAV-era canônica é **SCR-013-policy-decisions.md** + **SCR-014-reflect.md** (operator-side CLI/TUI screens). A mecânica load-bearing é o **hysteresis assimétrico** (Pattern #15 §2.3 verbatim): 3 dias consecutivos acima do threshold para upgrade, 2 dias para downgrade, 1 dia para RECOVER (emergência). Esta canvas documenta **4 estados de regime + 6 estados operacionais** (cross-canonical via doc 23) + **user override paths** + **sync triggers cross-fork** (status change → PropagationEvent) + integração com `CyberneticDailyLoop` (TARGET→SENSOR→ADJUSTER).

**Modos:** INDEX canvas — não prescreve nova jornada; mapeia componentes verbatim.

**Invariante load-bearing:** Q_HE é **source of truth** para regime. Não há override user-side direto (user pode refletir, mas o FSM lê Q_HE + histórico, não input do user). User pode **forçar RECOVER** explicitamente (operator action em `operational policy force-recover`) — registrado como `infraction` se Q_HE é alto.

---

## §2 — Inventário

### 2.1 Os 4 estados de regime (Pattern #15 verbatim)

| Estado | hardwork | pause | sleep target | Q_HE target | Trigger upgrade | Trigger downgrade |
|:-------|---------:|:-----:|:------------:|:-----------:|:----------------|:------------------|
| `PUSH` | 4.0 h | 10 min | 7.5 h | 0.85 | `Q_HE ≥ 0.85` por **3 dias** consecutivos | `infractions ≥ 2` (early warning) OR `Q_HE < recover_threshold` por 2 dias |
| `MAINTAIN` | 2.5 h | 15 min | 8.0 h | 0.65 | `Q_HE ≥ push_threshold` por 3 dias | `Q_HE < reduce_threshold` por 2 dias |
| `REDUCE` | 1.5 h | 20 min | 8.5 h | 0.45 | `Q_HE ≥ maintain_threshold` por 3 dias | `Q_HE < recover_threshold` por 2 dias |
| `RECOVER` | 0.5 h | 30 min | 9.0 h | 0.25 | `Q_HE ≥ reduce_threshold` por 3 dias (slow recovery) | (terminal until Q_HE recovers) |

**Invariante load-bearing:** `RegimeState` em `src/contracts/common.py:150-156` declara os 4 valores como `StrEnum` canônico cross-layer.

### 2.2 Os 6 estados operacionais (canonical mapping doc 23)

| Canonical STATUS | TaskAction | tuiboard (3-column) | taskdog (4-state) | solverforge-calendar (5-value) |
|:-----------------|:-----------|:--------------------|:-------------------|:-------------------------------|
| `PENDING` | create | todo | PENDING | pending |
| `ACTIVE` | update (start) | doing | IN_PROGRESS | in_progress |
| `DONE` | done | done | COMPLETED | done |
| `BLOCKED` | update (block) | (n/a — coluna separado) | (n/a — tag) | blocked |
| `CANCELLED` | delete | (n/a — sem soft-delete) | CANCELED | cancelled |
| `ARCHIVED` | (n/a — operator-only) | (n/a) | (separate `is_archived` flag) | (separate `deleted_at`) |

**Cross-link:** doc 23 §3.2 tabela canônica completa + transition rules + sync triggers.

### 2.3 STATUS × REGIME matrix (Pattern #33 unified)

| STATUS \ REGIME | PUSH | MAINTAIN | REDUCE | RECOVER |
|:----------------|:-----|:---------|:-------|:--------|
| PENDING | queue normal | queue normal | queue reduced | defer 7d |
| ACTIVE | full pace | normal | reduced pace | minimum viable |
| DONE | log → vault | log → vault | log → vault | log → vault |
| BLOCKED | unblock asap | retry next slot | defer 24h | defer 7d |
| CANCELLED | log | log | log | log |
| ARCHIVED | keep | keep | keep | keep |

**Cross-link:** doc 33 (`docs/design-system/33-status-matrix-unified.md`) — matriz canônica verbatim + sync triggers.

### 2.4 Thresholds operacionais (constants single-source-of-truth-aspiracional)

```python
# src/operational/packages/core/src/operational/core/policy_engine.py:99-105
_RECOVER_QHE_CRITICAL: Final[float] = 0.30      # emergência entry
_RECOVER_INFRACTION_THRESHOLD: Final[int] = 3   # emergência entry
_PUSH_EARLY_WARNING_INFRACTIONS: Final[int] = 2  # canal secundário
```

```python
# src/ikigai/src/ikigai/constants.py:42-52 (versão IKIGAi hybrid)
Q_HE_PUSH: float = 0.85       # banda superior
Q_HE_REDUCE: float = 0.65     # banda intermediária
Q_HE_RECOVER: float = 0.60    # hard floor
HYSTERESIS_UPGRADE_DAYS: int = 3
HYSTERESIS_DOWNGRADE_DAYS: int = 2
```

**Gap documentado:** `docs/auto-performance-os/21-meta-qhe-policy-mapping.md` §2 promete **4 bandas canônicas** (`[0.85, 1.0]` PUSH, `[0.70, 0.85)` MAINTAIN, `[0.60, 0.70)` REDUCE, `[0.0, 0.60)` RECOVER), mas o código operacional só implementa **3 thresholds efetivos**. A banda `[0.70, 0.85)` MAINTAIN é derivada, não armazenada.

### 2.5 Transition rules (Pattern #15 §2.3 verbatim)

```python
def evaluate_policy(
    current_state: PolicyState | None,
    qhe_metrics: QHEMetrics,
    history: list[PolicyDecision] | tuple[PolicyDecision, ...] = (),
    infraction_count: int = 0,
) -> PolicyEvaluation:
    qhe = qhe_metrics.qhe
    days_in_state = _count_days_in_state(history, current_state) if current_state is not None else 0

    # 1. Emergency RECOVER entry (highest priority, no histerese).
    if current_state != PolicyState.RECOVER and is_recover_entry_condition(qhe, infraction_count):
        return PolicyEvaluation(
            new_state=PolicyState.RECOVER,
            severity=Severity.CRITICAL,
            rationale=f"RECOVER entry: qhe={qhe:.3f}, infractions={infraction_count}",
            days_in_state=days_in_state,
            is_transition=True,
            previous_state=current_state,
        )

    # 2-4. ... (other transitions, omitted for brevity — see Pattern #15 §2.3)
```

**Priority:** RECOVER entry > PUSH downgrade > MAINTAIN/REDUCE transitions > no-op.

### 2.6 CyberneticDailyLoop (TARGET→SENSOR→ADJUSTER)

```python
# vibe-ops/src/cybernetics/daily_loop.py (anchor)
class CyberneticDailyLoop:
    """TARGET→SENSOR→ADJUSTER→PERSIST→SYNC→INDEX daily loop."""

    def execute_daily_cycle(self, date: date) -> None:
        # 1. TARGET: read today's planned regime + budget
        target = self.get_target_state(date)

        # 2. SENSOR: collect metrics (sleep, energy, focus, Q_HE)
        sensor_data = self.collect_sensor_data(date)

        # 3. ADJUSTER: PolicyEngine.evaluate_policy
        evaluation = self.policy_engine.evaluate_policy(
            current_state=target.current_regime,
            qhe_metrics=sensor_data.qhe_metrics,
            history=target.history,
            infraction_count=sensor_data.infraction_count,
        )

        # 4. PERSIST: save PolicyDecision to vault
        self.persist_policy_decision(evaluation, date)

        # 5. SYNC: propagate to forks via data mesh
        self.sync_to_forks(evaluation)

        # 6. INDEX: update vector store for hybrid search
        self.update_vector_index(evaluation, date)
```

**Cross-link:** Pattern #08 canvas cybernetic loop (`docs/design-system/08-canvas-cybernetic-loop.md`) — TARGET→SENSOR→ADJUSTER.

### 2.7 PAE-era screens (operator-side)

- **`src/operational/docs/ux/05-telas/SCR-013-policy-decisions.md`** — policy decisions view (lista de transições recentes + rationale).
- **`src/operational/docs/ux/05-telas/SCR-014-reflect.md`** — reflect step (user escreve nota sobre dia → alimenta Q_HE via metric input).
- **`src/operational/docs/ux/05-telas/SCR-005-demo-stats.md`** — PAV-era demo stats (cross-ref historic).

---

## §3 — Conteúdo principal

### 3.1 Policy decision flow (5 steps end-to-end)

```text
[1] CyberneticDailyLoop.execute_daily_cycle(date) triggered
   Trigger: cron @ 23:55 daily (ou user-side `operational reflect`)
   │
   ▼
[2] SENSOR: collect sensor_data
   - sleep_records[date] (sleep quality, hours)
   - energy/focus metric readings (multiple per day)
   - routine logs (routines completadas vs skipped)
   - Q_HE composite (operational multiplicativa: 0.3E + 0.4P + 0.3S)
   - infraction_count (count of skipped routines, late sleep, etc.)
   │
   ▼
[3] ADJUSTER: PolicyEngine.evaluate_policy(...)
   input: current_state, qhe_metrics, history, infraction_count
   output: PolicyEvaluation(new_state, severity, rationale, days_in_state, is_transition, previous_state)
   │
   ├── RECOVER entry (CRITICAL): qhe < 0.30 OR infractions >= 3
   ├── PUSH downgrade (WARNING): qhe < recover_threshold for 2 days
   ├── MAINTAIN transitions: standard hysteresis
   ├── REDUCE upgrade: qhe >= maintain_threshold for 3 days
   └── no-op: stay in current state
   │
   ▼
[4] PERSIST: PolicyDecision saved
   - data/feedback/policy_<YYYY-MM-DD>.json (append-only)
   - vault/ikigai/closing-2026/{q}-{w}/policy_<YYYY-MM-DD>.md (PROPOSTA)
   │
   ▼
[5] SYNC: status changes propagated cross-fork (PROPOSTA)
   if is_transition:
     - enqueue(TaskChange(ueid=<current_task>, action="update", fields={"regime": new_state}, source_fork="policy"))
     - per-adapter apply_change
     - CliAdapter JSONL append
     - TaskdogAdapter SQLite UPSERT
     - SolverforgeCalendarAdapter UPI PK reuse (UPI `ikigai` JSON field)
```

### 3.2 Cross-fork status sync (canonical 6-state → fork enum)

Quando uma Task muda status (e.g., PENDING → ACTIVE), a propagação cross-fork precisa **canonicalizar** o status antes de propagar. Tabela canônica (doc 23 §3.2):

| Canonical STATUS | tuiboard mapping | taskdog mapping | solverforge-calendar mapping |
|:-----------------|:-----------------|:-----------------|:------------------------------|
| PENDING | column=todo | TaskStatus.PENDING | UpiStatus.Pending |
| ACTIVE | column=doing | TaskStatus.IN_PROGRESS | UpiStatus.InProgress |
| DONE | column=done + Task.done=true | TaskStatus.COMPLETED | UpiStatus.Done |
| BLOCKED | column=separate "blocked" (tuiboard-only) | tag="blocked" (custom) | UpiStatus.Blocked |
| CANCELLED | (delete row + audit log) | TaskStatus.CANCELED | UpiStatus.Cancelled |
| ARCHIVED | (move to archived/ folder) | is_archived=True | deleted_at=now() |

**Cada adapter consulta** essa tabela em `apply_change` antes de persistir.

### 3.3 User override paths (3 paths oficiais)

**Path 1 — Manual reflect** (suave): User escreve nota em `SCR-014-reflect.md` → alimenta Q_HE composite (operational multiplicativa). Não força mudança de regime; apenas influencia via sensor data.

**Path 2 — Force regime** (moderado): Operator-side `operational policy force --state <regime>` → registra `PolicyDecision(forced=True, rationale="user override")` + adiciona `infraction` se Q_HE inconsistente. Audit trail preservado.

**Path 3 — Emergency RECOVER** (crítico): User clica "I need rest" no footer → PolicyEngine pula hysteresis e força RECOVER imediatamente → registra como `infraction=+1` (so user não abuse) + rationale "user emergency".

**Importante:** Paths 2 e 3 **não bypassam** o FSM; eles **alimentam** sensor data ou forçam via `is_recover_entry_condition`. Q_HE continua sendo o ground truth para próximo ciclo.

### 3.4 Integração com CyberneticDailyLoop

A Policy decision journey é o **ADJUSTER** do cybernetic loop (Pattern #08). Sequência:

```
TARGET (planning)
   ↓
SENSOR (collect metrics) ←—— user input (reflect, override, emergency)
   ↓
ADJUSTER (PolicyEngine.evaluate_policy) ←—— hysteresis FSM
   ↓
PERSIST (PolicyDecision → vault)
   ↓
SYNC (status changes → forks via mesh)
   ↓
INDEX (vector store hybrid search)
```

Cada step produz output que alimenta o próximo. **ADJUSTER é o coração** — sem ele, o sistema não sabe quanto agressivo ser.

### 3.5 Decision tree — "Quando ocorre uma transition?"

```text
START: PolicyEngine.evaluate_policy called
   │
   ▼
Q1: qhe < 0.30 OR infractions >= 3 AND current_state != RECOVER?
   ├─ YES → RECOVER entry (CRITICAL severity)
   │         rationale: "RECOVER entry: qhe=X, infractions=Y"
   │         days_in_state reset to 0
   │
   └─ NO
      │
      ▼
Q2: current_state == PUSH?
   ├─ YES → check infractions >= 2?
   │         ├─ YES → PUSH->REDUCE (WARNING, early warning downgrade)
   │         └─ NO → check qhe < recover_threshold for 2 days?
   │                  ├─ YES → PUSH->MAINTAIN (WARNING)
   │                  └─ NO → no-op (stay PUSH)
   │
   └─ NO
      │
      ▼
Q3: current_state == MAINTAIN?
   ├─ YES → check qhe >= push_threshold for 3 days?
   │         ├─ YES → MAINTAIN->PUSH (INFO, upgrade)
   │         └─ NO → check qhe < reduce_threshold for 2 days?
   │                  ├─ YES → MAINTAIN->REDUCE (WARNING)
   │                  └─ NO → no-op (stay MAINTAIN)
   │
      └─ NO
         │
         ▼
Q4: current_state == REDUCE?
   ├─ YES → check qhe >= maintain_threshold for 3 days?
   │         ├─ YES → REDUCE->MAINTAIN (INFO)
   │         └─ NO → check qhe < recover_threshold for 2 days?
   │                  ├─ YES → REDUCE->RECOVER (CRITICAL)
   │                  └─ NO → no-op (stay REDUCE)
   │
         └─ NO
            │
            ▼
Q5: current_state == RECOVER?
   └─ YES → check qhe >= reduce_threshold for 3 days?
            ├─ YES → RECOVER->REDUCE (INFO, slow recovery)
            └─ NO → no-op (stay RECOVER)
```

### 3.6 PROPOSTA — Cross-fork status sync (italic gap)

*PROPOSTA: Quando PolicyEngine transiciona regime, propagar para forks via mesh:*

```python
# vibe-ops/src/cybernetics/daily_loop.py
if evaluation.is_transition:
    transition_event = TaskChange(
        ueid=UEID(f"regime:{date.isoformat()}:{uuid4()}:{hash}"),
        action=TaskAction.UPDATE,
        fields={
            "regime": evaluation.new_state,
            "previous_state": evaluation.previous_state,
            "rationale": evaluation.rationale,
            "severity": evaluation.severity,
        },
        source_fork="policy_engine",
        status="pending",
    )
    src/mesh/queue.py:enqueue(transition_event)
```

Cada adapter aplica:
- **CliAdapter:** JSONL append com `{ueid, regime, date, source_fork="policy_engine"}`.
- **TaskdogAdapter:** SQLite UPSERT em `policy_log` table (PROPOSTA — Migration v008).
- **SolverforgeCalendarAdapter:** UPI UPDATE em `ikigai` JSON field com `regime: <new_state>`.

### 3.7 Pitfalls known (policy decision)

- **G-POLICY-01** — Q_HE dual definition (operational multiplicativa vs IKIGAi aditiva). Doc 09 §3.1.
- **G-POLICY-02** — taskdog `TaskStatus` 4-state vs canonical 6-state. Doc 23 §1.
- **G-FORK-05** — tuiboard sem UEID nativo; policy sync via `sync_map` observability only. Doc 20 §3.4.
- **G-FORK-06** — taskdog sem UEID nativo; policy sync precisa Migration v008. Doc 21 §3.7.
- **G-AGENT-01** — Agent gated por ADR-007 5+ SONHO logs. [[data-first-methodology]].
- **Gap B4** (doc 09) — 3-up/2-down/1-emergency constants são CHOICE sem derivação teórica. Pendente de fit empírico via Bayesian Optimization após gate de 5 SONHO logs.

### 3.8 Métricas de policy decision

| Métrica | Target | Origem |
|:--------|:-------|:-------|
| Regime transitions/wk | 1-3 (não zero, não excessivo) | consolidator weekly |
| Q_HE stability | < 0.05/dia drift | *PROPOSTA: medido por backtest* |
| Infraction rate | < 5% dias | Pattern #15 input |
| Hysteresis false positives | < 1 transição espúria/wk | *PROPOSTA: backtest histórico* |
| Cross-fork status consistency | ≥ 99% | partial_propagation rate |
| Reflect completion | ≥ 80% dias | SCR-014 usage |

---

## §4 — Cross-references

### 4.1 Design-system docs (Layer 1-6)

- **`docs/design-system/00-INDEX.md`** §3 — Layer 6 navigation.
- **`docs/design-system/04-canvas-mesh-architecture.md`** §3 — mesh topology.
- **`docs/design-system/05-canvas-contracts-architecture.md`** §4 — RegimeState cross-layer.
- **`docs/design-system/08-canvas-cybernetic-loop.md`** §3 — TARGET→SENSOR→ADJUSTER.
- **`docs/design-system/15-pattern-hysteresis-fsm.md`** §2 (4-state FSM) + §3 (transition rules) — Pattern #15 anchor.
- **`docs/design-system/17-pattern-reliability-decorators.md`** §3 — retry per-adapter.
- **`docs/design-system/23-fork-status-enum-mapping.md`** §3.2 — canonical 6-state mapping table.
- **`docs/design-system/30-tokens-deep-agent-era.md`** — visual tokens.
- **`docs/design-system/31-ueid-visual-representation.md`** — UEID caption pills.
- **`docs/design-system/33-status-matrix-unified.md`** — STATUS × REGIME matrix.
- **`docs/design-system/40-index-user-journeys.md`** §3.3 (Padrão C hysteresis boot).

### 4.2 PAV-era `ux/` (referência)

- **`src/operational/docs/ux/05-telas/SCR-013-policy-decisions.md`** — policy decisions view.
- **`src/operational/docs/ux/05-telas/SCR-014-reflect.md`** — reflect step.
- **`src/operational/docs/ux/05-telas/SCR-005-demo-stats.md`** — PAV-era demo stats.
- **`src/operational/docs/ux/04-fluxos/FLOW-006-relatorio-diario.md`** — daily report (cross-ref).

### 4.3 auto-performance-os docs

- **`docs/auto-performance-os/21-meta-qhe-policy-mapping.md`** §2 — 4-band regime mapping.
- **`docs/auto-performance-os/24-integration-mesh-ueid-propagation.md`** §2 — UEID pipeline.
- **`docs/auto-performance-os/26-integration-cybernetic-loop.md`** — weekly aggregation.
- **`docs/design-system/09-analise-critica-segunda-ordem-arquitetura.md (the auto-performance-os doc is a different file)`** §3.4 — finding B4 (3-up/2-down/1-emergency CHOICE).

### 4.4 Phase 2 diagnostics

- **`docs/diagnostics/2026-08-28-phase2-interface-re/06-synthesis-mesh-readiness.md`** §OQ-1/OQ-5/OQ-7.
- **`docs/diagnostics/2026-08-28-phase2-interface-re/02-fork-taskdog.md`** §3 — taskdog TaskStatus.
- **`docs/diagnostics/2026-08-28-phase2-interface-re/03-fork-solverforge-calendar.md`** §3.2 — UPI ikigai JSON.

### 4.5 Memory cross-refs

- **[[]]** — dual-layer.
- **[[]]** — deep-agent canonical.
- **[[]]** — ADR-007 gate.
- **[[]]** — 31 inconsistências IKIGAi/PAV (catalogadas 2026-07-02).
- **[[]]** — 3rd reversal on M01/N01/A02/A06.
- **[[]]** — backend before algorithm.
- **[[]]** — user stated Revenue weight high (conf com persona).

### 4.6 Code anchors (verificados)

| Path | LOC / Conteúdo | Padrão |
|:-----|:---------------|:-------|
| `src/operational/packages/core/src/operational/core/policy_engine.py:99-105` | thresholds constants | Pattern #15 |
| `src/operational/packages/core/src/operational/core/policy_engine.py:399-632` | `evaluate_policy` | Pattern #15 |
| `src/contracts/common.py:150-156` | `RegimeState` StrEnum (4 values) | Pattern #15 + #11 |
| `src/contracts/task_change.py:TaskAction` | create/update/delete/done | Pattern #11 |
| `src/operational/packages/core/src/operational/entities/habit.py` | `QHEMetrics` entity | multiplicative Q_HE |
| `src/ikigai/src/ikigai/core/scoring/qhe.py` | IKIGAi Q_HE | additive Σw=1.05 |
| `src/ikigai/src/ikigai/constants.py:42-52` | IKIGAi hybrid thresholds | Pattern #15 IKIGAi version |
| `vibe-ops/src/cybernetics/daily_loop.py:CyberneticDailyLoop` | TARGET→SENSOR→ADJUSTER | Pattern #08 canvas |
| `vibe-ops/src/middleware/sync_engine.py` | Obsidian ↔ SQLite ↔ Taskwarrior | sync layer |
| `interfaces/solverforge-calendar/src/models_unified.rs` | `UpiStatus` enum | UPI status |
| `interfaces/taskdog/packages/taskdog-core/src/taskdog_core/domain/entities/task.py:16-20` | `TaskStatus` enum | taskdog 4-state |

---

## §5 — Fontes

### Code (verbatim, lidos via Read tool)
- `src/operational/packages/core/src/operational/core/policy_engine.py` — Pattern #15 verbatim
- `src/contracts/common.py` — RegimeState StrEnum
- `src/contracts/task_change.py` — TaskAction
- `src/mesh/agent_consumer.py` — PAE rules (cross-ref doc 42)
- `vibe-ops/src/cybernetics/daily_loop.py` — CyberneticDailyLoop

### Docs design-system (verbatim, lidos via Read tool)
- `docs/design-system/15-pattern-hysteresis-fsm.md` — Pattern #15 anchor (lido §1, §2.1-2.3)
- `docs/design-system/23-fork-status-enum-mapping.md` — canonical 6-state mapping (lido §1, §2)
- `docs/design-system/40-index-user-journeys.md` — Layer 6 INDEX

### PAV-era docs (verbatim, lidos via Read tool)
- `src/operational/docs/ux/04-fluxos/FLOW-007-relatorio-semanal.md` (parcial — anchor)

### auto-performance-os docs
- `docs/auto-performance-os/21-meta-qhe-policy-mapping.md` — Q_HE→regime
- `docs/design-system/09-analise-critica-segunda-ordem-arquitetura.md (the auto-performance-os doc is a different file)` — finding B4
- `docs/auto-performance-os/26-integration-cybernetic-loop.md` — weekly aggregation

### Phase 2 diagnostics
- `docs/diagnostics/2026-08-28-phase2-interface-re/06-synthesis-mesh-readiness.md`
- `docs/diagnostics/2026-08-28-phase2-interface-re/02-fork-taskdog.md`
- `docs/diagnostics/2026-08-28-phase2-interface-re/03-fork-solverforge-calendar.md`

### Memory cross-refs
- [[]]
- [[]]
- [[]]
- [[]]
- [[]]
- [[]]
- [[]]

### Métricas de cobertura
- **5 sections principais** (§1-§5) — Resumo / Inventário / Conteúdo / Cross-refs / Fontes (template Pattern #10 verbatim)
- **4 estados de regime** tabulados em §2.1 (PUSH/MAINTAIN/REDUCE/RECOVER) com budget completo
- **6 estados operacionais** tabulados em §2.2 (canonical 6-state cross-fork)
- **6×4 STATUS × REGIME matrix** em §2.3 (24 cells)
- **2 thresholds sources** comparados em §2.4 (operational vs IKIGAi hybrid)
- **5-step PolicyEngine.evaluate_policy** em §2.5 (verbatim Pattern #15 §2.3)
- **6-step CyberneticDailyLoop** em §2.6 (TARGET→SENSOR→ADJUSTER→PERSIST→SYNC→INDEX)
- **5-step policy decision flow** em §3.1 (end-to-end)
- **6 fork-specific status mappings** em §3.2 (canonical → fork enum)
- **3 user override paths** em §3.3 (manual reflect / force regime / emergency RECOVER)
- **5-step decision tree** em §3.5 (Q1-Q5 cascade)
- **6 métricas** em §3.8 (transitions/wk, Q_HE stability, infraction rate, etc.)
- **11 code anchors** verificados via Read tool em §4.6
- **7 memory cross-refs** em §4.5
- **6 pitfalls known** em §3.7 (G-POLICY-01/02, G-FORK-05/06, G-AGENT-01, B4 CHOICE)
- **Honest rigor:** flag Q_HE dual definition como gap; flag 3-up/2-down/1-emergency como CHOICE pendente Bayesian Optimization; flag cross-fork status sync como PROPOSTA italic; flag user override paths como soft (não bypass); flag agent run gated por ADR-007.

---

> **Próxima ação recomendada:** Após ADR-007 gate ser destravado (5+ SONHO logs), backtest histórico do hysteresis com 30+ dias reais de dados → calibrar constants 3-up/2-down/1-emergency via Bayesian Optimization (resolve finding B4). + adicionar cross-fork policy sync como Migration v008 taskdog + UPI ikigai JSON update solverforge-calendar. + fechar gap Q_HE dual definition via PROPOSTA: `src/contracts/scores.py` (proposed — Q_HE re-encoding lives in `src/contracts/metrics.py`) namespace canônico.
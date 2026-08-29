# 09 — Análise Crítica de Segunda Ordem (Foco: Padrões Arquiteturais)

> **⚠️ ADR-007 propagation note (2026-08-29):** References to "5 SONHO logs gate (ADR-007)" in this doc reflect a **propagated misconception**. ADR-007's "5+ manual logs per workflow" rule is **observation depth**, NOT a release gate. The actual gate for algorithm work is **system readiness** (backend + data + agent functional). Canonical clarification: `~/.claude/projects/C--Users-mathe-code-space-life-oss-life/memory/algorithm-gate-system-readiness-not-sonho-2026-08-29.md`. The deferral rule still applies here — this content is correctly deferred — but for the reason "system not ready," not "5 logs not reached."

> **Categoria:** META-CRITICAL (Layer 8 — Análise crítica sobre Layers 0-7)
> **Anchor canônico:** `docs/auto-performance-os/` (27 docs PT-BR) + `src/contracts/` + `src/mesh/` + `src/ikigai/src/agents/`
> **Origem:** Explore agent (análise automatizada) + verificação manual de fórmulas↔código
> **Idioma:** PT-BR (preservando EN technical terms: UEID, FSM, IKIGAi, PAV, deep-agent, fork, regime, MCP, KPI, SCR, FLOW, η, λ, μ, σ)
> **Publico:** Eu mesmo + agentes futuros

---

## §1 — Resumo executivo

A análise crítica de segunda ordem do docset `docs/auto-performance-os/` (27 docs) **revelou 12 novas inconsistências (F1-F12)** somadas às 31 já catalogadas em `vault/ikigai/meta/algorithm-issues-registry.md`. O foco deste doc é **padrões arquiteturais** — não fórmulas matemáticas isoladas — porque é onde reside a tese de "auto-feedback estocástico" que sustenta o sistema.

**Veredito load-bearing:** a tese é estruturalmente correta (FSMs determinísticas, monotonicidade preservada, idempotência), mas **parameter-free of empirical content**. Toda constante numérica é **escolha** (não medição) até que o gate de **5 SONHO logs** (ADR-007) seja cumprido.

**Recomendação arquitetural principal:** desacoplar a **camada de policy** (4-state FSM com thresholds) da **camada de scoring** (QHE). Hoje as duas estão **acopladas por nome** — QHE é usado como input do FSM com thresholds calibrados para a forma multiplicativa operacional, mas a forma aditiva IKIGAi tem Σw≠1.0 e produz números incompatíveis. Renomear uma das formas (ex.: `Q_HE_OPERATIONAL` vs `Q_HE_IKIGAI`) e documentar explicitamente o mapeamento entre elas.

## §2 — Tabela de Findings (resumo)

### 2.1 CRÍTICOS (HIGH — quebram a tese se carregados literalmente)

| ID | Severidade | Tipo | Padrão arquitetural afetado | Doc | Code |
|:---|:----------:|:-----|:---------------------------|:----|:-----|
| **A1** | HIGH | Formula↔code mismatch | Sleep 5×4 matrix (5 buckets × 4 cols) | `16-engine-sleep-validator.md` §2 | `sleep_calculator.py:_MATRIX_DORMIR` |
| **A2** | HIGH | Two incompatible definitions (single name) | QHE encoding | `13-engine-habit-engine.md` vs `21-meta-qhe-policy-mapping.md` | `entities/habit.py:QHEMetrics` (multiplicativa) vs `ikigai/core/scoring/qhe.py:compute_qhe` (aditiva Σw=1.05) |
| **A3** | HIGH | Formula rename (eficiência≠energy_ratio) | QHE inputs | `13-engine-habit-engine.md` §2 | `entities/habit.py:467` |
| **A4** | HIGH | 5 vector formulas don't match | Hybrid meta-vector | `19-engine-ikigai-vector-scorer.md` §2 | `ikigai/core/scoring/vector_scores.py` |
| **A5** | HIGH | Worked example mathematically wrong | Meta-vector formula | `22-meta-ikigai-meta-vector.md` §3 (claims ≈51) | computed ≈25.4% |
| **A6** | HIGH | Two abstractions share a name | Budget classifier | `17-engine-budget-classifier.md` §2 (circadian) | `budget.py:classify_quadrant` (Cartesian Q1..Q4) |
| **A7** | HIGH | Silent failure of stated mechanism | Pomodoro scenarios | `10-engine-pomodoro-machine.md` §2 (cenários alteram intervals) | `scenario_classifier.py` emits strings only |
| **C1** | HIGH | Validation invariant violated by defaults | IKIGAi QHE | `21-meta-qhe-policy-mapping.md` | `ikigai/core/scoring/qhe.py:76-77` raises on default weights Σ=1.05 |

### 2.2 SCIENTIFIC RIGOR (MEDIUM — citacional gap)

| ID | Sev | Issue | Doc | Code anchor |
|:---|:---:|:------|:----|:------------|
| **B1** | M | λ=0.093 derivation gap (Lally 2010 cited but no fit) | `02-axiom-habitualidade.md` §3 | `entities/habit.py` λ constant |
| **B2** | M | Lally 2010 misquote ("median" conflated with "near-full") | `02-axiom-habitualidade.md` §3 | — |
| **B3** | M | EnergyLevel ratios {1.0, 0.6, 0.3} unjustified | `01-axiom-energia-tempo.md` | `operational/enums.py:EnergyLevel._ENERGY_RATIO_*` |
| **B4** | M | Hysteresis constants 3-up/2-down unjustified | `14-engine-policy-engine-fsm.md`, `21-meta-qhe-policy-mapping.md` | `policy_engine.py:HYSTERESIS_*` |
| **B5** | M | Hybrid 0.6/0.4 unjustified | `22-meta-ikigai-meta-vector.md` §3 | `ikigai_maintainer/state.py:compute_meta_vector` |
| **B6** | M | Sleep recovery R(s) labeled "logarítmica" but is piecewise-linear | `05-postulate-sono-cognicao.md` §2 | `consolidator.py:R(s)` |
| **B7** | M | Context-switch 9-pair matrix unjustified | `08-postulate-carga-cognitiva.md` §2 | `context_switch.py` (only 6-pair period matrix implemented) |

### 2.3 MATHEMATICAL COGENCY (LOW-MEDIUM — minor invariants)

| ID | Sev | Issue | Pattern |
|:---|:---:|:------|:--------|
| **C2** | M | Sleep penalty formula asymmetry (doc rewards oversleep, code clamps) | `consolidator.py:228-232` |
| **C3** | M | PUSH pomodoro count inconsistent with hours (10 pomodoros × 50min=8.33h, but doc says "8h productive" assumes PERFEITO 25min) | `pomodoro_machine.py` defaults 50/10/30 |
| **C4** | M | Doc 21 4-band mapping not implemented (0.70 REDUCE band missing in operational FSM) | `policy_engine.py:QHE_REDUCE_THRESHOLD` missing |
| **C5** | M | Doc 14 says "REDUCE never chosen by QHE alone" — code allows MAINTAIN→REDUCE purely by QHE | `policy_engine.py:547-575` |
| **C6** | M | Doc 14 says "PUSH→RECOVER direto proibido" — emergency check bypasses prohibition | `policy_engine.py:467-475` |
| **C7** | M | `compute_meta_vector` filters out v=0 vectors (silently violates "5 vetores" premise) | `ikigai_maintainer/state.py:188-190` |
| **C8** | L | QHE_THEORETICAL_MAX=2.0 relies on η=1.0, but ETA_DEFAULT=0.5 (typical max 1.5) | `habit_engine.py:119` |
| **C9** | L | Health_score max=90 vs productivity max=100 (overall `0.3E+0.4P+0.3S` cannot reach 100) | `consolidator.py:285` |
| **C10** | L | weekly_aggregator uses `avg_health` for `habit_compliance_avg` (two concepts share a name) | `weekly_aggregator.py:287` |

### 2.4 CONCEPTUAL GAPS (HIGH — silent feature loss)

| ID | Sev | Issue | Doc reference | Code reality |
|:---|:---:|:------|:---------------|:-------------|
| **E6** | HIGH | `compute_cognitive_debt` referenced but doesn't exist | `11-postulate-carga-cognitiva.md` §5 | `habit_engine.py` exports: compute_habit_level, compute_efficiency_ratio, compute_energy_required, compute_habit_avg, compute_consistency, compute_streak_bonus, compute_qhe |
| **E9** | HIGH | `ucb_recalibrator.py` referenced but doesn't exist | `20-engine-ucb-recalibrator.md` §5 | `src/ikigai/src/ikigai/core/heuristics/` directory: no ucb_recalibrator.py |
| **E10** | HIGH | `decision_flow.py` referenced but doesn't exist | `23-meta-decision-flow.md` §5 | `src/ikigai/src/ikigai/core/orchestrator/`: no decision_flow.py |
| **F5** | HIGH | Pomodoro machine not wired into time-blocks (silent failure of stated integration) | `24-integration-mesh-ueid-propagation.md` §4 | `pomodoro_machine.py` docstring (lines 16-19): "This implementation is **not** wired into the time-blocks capture pipeline." |
| **F10** | HIGH | chroma_db referenced but absent | `26-integration-cybernetic-loop.md` §4 | code tree has only SQLite + review_queue; no chroma_db/ |

## §3 — Padrões arquiteturais afetados

### 3.1 Padrão #11 (Frozen Pydantic + extra=forbid) — qualificado

O invariante `frozen=True, extra="forbid"` declarado em `src/contracts/__init__.py` é **load-bearing** e **bem aplicado**. Mas o padrão falha quando:

- **A2 + C1**: dois modelos同名 (ambos `QHE`) carregam shapes diferentes (multiplicativa vs aditiva). Frozen Pydantic não captura colisão de **nome**, só de **shape**. Solução: o invariante deveria incluir "no two models in the same module may share a name unless they are aliases (Pydantic type aliases via `TypeAliasType`)".

**Recomendação arquitetural:** introduzir `src/contracts/scores.py` como **namespace canônico** para scores, com aliases explícitos:

```python
# src/contracts/scores.py (PROPOSTA)
from typing import Annotated
from pydantic import TypeAdapter

# Operacional: multiplicativa, [0, 1.5] típico, [0, 2.0] com η=1.0
OperationalQHE = Annotated[float, ...]  # type alias

# IKIGAi: aditiva (após normalização para Σw=1.0), [0, 1]
IkigaiQHE = Annotated[float, ...]

# Mapeamento explícito
def ikigai_to_operational(qhe_ikigai: IkigaiQHE) -> OperationalQHE:
    """QHE_IKIGAI = 0.6 * QHE_OPERATIONAL + 0.2 (calibração proposta, TBD com 5 SONHO logs)."""
    return max(0.0, min(1.5, (qhe_ikigai - 0.2) / 0.6))
```

### 3.2 Padrão #12 (Append-only queue) — qualificado

O queue em `data/review_queue/<event_id>.json` é **bem implementado**. Mas o padrão não captura:

- **A7**: scenario classifier emite recomendações mas não persiste em queue. Se a intenção era wire-up `Scenario → PomodoroTracker`, deveria ser um `TaskChange` enfileirado com `action="update"` no fork tuiboard/taskdog. Hoje é só string.
- **F5**: pomodoros não viram `TaskChange` (afirmação de `24-integration-mesh-ueid-propagation.md §4` contradita pelo próprio docstring do arquivo).

**Recomendação arquitetural:** definir um **adapter explícito** `src/mesh/adapters/pomodoro.py` que implementa `ForkAdapter` Protocol e emite `PropagationEvent` quando um pomodoro é iniciado/completado. Hoje não existe; o doc assume que existe.

### 3.3 Padrão #13 (ForkAdapter Protocol) — qualificado

`@runtime_checkable Protocol` em `src/mesh/adapters/base.py` é load-bearing. Bem aplicado aos 3 adapters atuais (Cli, Taskdog, SolverforgeCalendar). Mas:

- **F5**: o "fork pomodoro" não existe. Não há adapter, não há fork, não há Protocol instance.

**Recomendação arquitetural:** ou (a) implementar o adapter pomodoro com UEID propagation, ou (b) remover a referência em `24-integration-mesh-ueid-propagation.md §4` e adicionar trailer SUPERSEDED para o doc.

### 3.4 Padrão #15 (Hysteresis FSM) — qualificado

O 4-state FSM (PUSH/MAINTAIN/REDUCE/RECOVER) com 3-up/2-down/1-emergência é **load-bearing** e bem modelado em `policy_engine.py`. Mas:

- **C4**: o threshold `QHE_REDUCE_THRESHOLD = 0.70` é documentado em `21-meta-qhe-policy-mapping.md` mas **não existe** no código. O código só tem `QHE_PUSH_THRESHOLD=0.85` e `QHE_RECOVER_THRESHOLD=0.60`. Doc/code drift no coração da FSM.
- **C5/C6**: comportamento de transição documentado contradiz comportamento implementado.

**Recomendação arquitetural:** introduzir `src/operational/packages/core/src/operational/core/policy_thresholds.py`:

```python
# PROPOSTA
from typing import Final

QHE_PUSH_THRESHOLD: Final[float] = 0.85    # ≥ para promover a PUSH
QHE_MAINTAIN_THRESHOLD: Final[float] = 0.70  # ≥ para MAINTAIN
QHE_REDUCE_THRESHOLD: Final[float] = 0.60   # ≥ para REDUCE
QHE_RECOVER_THRESHOLD: Final[float] = 0.30  # < para entrar em RECOVER (emergência)

HYSTERESIS_UPGRADE_DAYS: Final[int] = 3
HYSTERESIS_DOWNGRADE_DAYS: Final[int] = 2
EMERGENCY_THRESHOLD: Final[float] = 0.30
MAX_INFRACTIONS_FOR_EMERGENCY: Final[int] = 3
```

Single source of truth para thresholds; ambos docs e código importam daqui.

### 3.5 Padrão #18 (Hybrid meta-vector) — parcialmente qualificado

`meta = 0.6·geo + 0.4·harm` é implementado em `ikigai_maintainer/state.py:compute_meta_vector` mas:

- **A5**: worked example errado (doc claims ≈51, code gives ≈25.4).
- **C7**: filter de v=0 vectors silencia "5 vetores" premise.
- **B5**: 0.6/0.4 não justificado.

**Recomendação arquitetural:**

1. Reescrever worked examples em `22-meta-ikigai-meta-vector.md` com 3 cenários canônicos (bootstrap típico, SONHO quebrado, SONHO completo).
2. Documentar `compute_meta_vector` com 2 modos: `inclusive_zero` (inclui v=0) e `exclusive_zero` (exclui v=0). Default: `inclusive_zero` (preserva premise de 5 vetores).
3. Adicionar `min_vector_floor=0.01` em vez de filtrar (preserva invariante).

### 3.6 Padrão #20 (5 IKIGAi vectors) — não qualificado

Os 5 vetores (paixão, habilidade, mercado, receita, curso) têm **3 vetores com fórmulas completamente divergentes** entre doc e code (A4). O doc apresenta composições matemáticas elegantes (Σ, distância, fator) que **não existem** no código. O código usa weighted sums com pesos arbitrários.

**Recomendação arquitetural (a mais cara):** rewrite `vector_scores.py` para implementar as fórmulas do doc, OU rewrite `19-engine-ikigai-vector-scorer.md` §2 para refletir o código atual.

**Recomendação pragmática:** rewrite do doc. As fórmulas do código são suficientes para alimentar o meta-vector; o doc mentiroso é pior do que o código simples.

## §4 — Conexão com arquitetura (Layers 0-7)

### 4.1 Layer 1 (Topology) — impact

A narrativa canônica em `01-master-branch-carro-chefe-2026-08-28.md` (master = deep-agent carro-chefe) é **compatível** com os findings. PAV desativado é a evidência operacional de que a forma multiplicativa QHE perdeu sua "razão de existir" como single source of truth.

### 4.2 Layer 2 (Canvases) — impact

- **04-canvas-mesh-architecture**: deve notar F5 (pomodoro fork não existe) como gap explícito
- **05-canvas-contracts-architecture**: deve notar A2 + C1 (QHE dual definition) como refactor blocker
- **06-canvas-agents-architecture**: deve notar E9 (UCB recalibrator ausente) + E10 (decision_flow ausente) como gaps do IKIGAi maintainer
- **07-canvas-sync-architecture**: não afetado
- **08-canvas-cybernetic-loop**: deve notar F10 (chroma_db ausente) + F5 (pomodoro não wired)

### 4.3 Layer 3 (Patterns) — impact

- **Pattern #11 (frozen Pydantic)**: qualificado com proposta de namespace em `src/contracts/scores.py`
- **Pattern #12 (append-only queue)**: qualificado com proposta de adapter pomodoro
- **Pattern #13 (ForkAdapter Protocol)**: qualificado com novo adapter proposto
- **Pattern #15 (hysteresis FSM)**: qualificado com proposta de `policy_thresholds.py`
- **Pattern #18 (hybrid meta-vector)**: qualificado com proposta de 2 modos
- **Pattern #20 (5 IKIGAi vectors)**: não qualificado — rewrite doc

### 4.4 Layer 4-7 — não diretamente impactados

Layers de forks, tokens, user journeys, validation não carregam as fórmulas. Os trailers nos docs de origem devem referenciar este doc 09 como "análise crítica sobre".

## §5 — Recomendações priorizadas

### 5.1 Imediato (esta semana)

1. **STOP**: parar de publicar docset com fórmulas que não casam com código. Aplicar trailer SUPERSEDED ou rewrite em docs 13, 16, 17, 19, 22.
2. **RENAME**: `QHE` → `QHE_OPERATIONAL` (operational) e `QHE_IKIGAI` (IKIGAi) em todo o código. Alias único em `src/contracts/scores.py`.
3. **NORMALIZE**: IKIGAi QHE weights para Σ=1.0 (atual default 1.05 quebra a função).
4. **IMPLEMENT or REMOVE**: `compute_cognitive_debt`, `ucb_recalibrator`, `decision_flow`. Decidir por 1.
5. **FIX matrix mismatch** (A1): reescrever `16-engine-sleep-validator.md` §2 com tabela 5×4 correta ou reescrever `_classify()`.

### 5.2 Médio prazo (próximo mês)

6. **Re-derive ou label TBD**: cada constante numérica em §G do analysis agent (14 constantes) deve ganhar annotation `TBD` ou `EMPIRICAL_PENDING_5_LOGS` no código.
7. **Implementar policy_thresholds.py**: single source of truth para thresholds FSM.
8. **Implementar 2 modos para meta-vector**: `inclusive_zero` vs `exclusive_zero`.
9. **Extend registry**: vault/ikigai/meta/algorithm-issues-registry.md deve ganhar entries F1-F12 (12 novos findings).

### 5.3 Longo prazo (gate 5 SONHO logs)

10. **Run 5 SONHO logs** through operational FSM, IKIGAi meta-vector, scenario classifier, budget quadrant.
11. **Catalog failures** in registry.
12. **Sensitivity analysis** em λ, hysteresis constants, hybrid weights.
13. **Re-fit** Lally 2010 curve com dados reais (não só "median 66 days").

## §6 — Fontes

### Code (verificado)
- `src/operational/packages/core/src/operational/core/habit_engine.py:467` — Q_HE multiplicative
- `src/ikigai/src/ikigai/core/scoring/qhe.py:73-79, 76-77` — Q_HE additive, weight validation raises on Σ≠1.0
- `src/ikigai/src/ikigai/core/scoring/vector_scores.py` — 5 vector functions
- `src/ikigai/src/agents/ikigai_maintainer/state.py:188-190` — compute_meta_vector filter
- `src/operational/packages/core/src/operational/core/sleep_calculator.py:_MATRIX_DORMIR` — 5 bedtime hours
- `src/operational/packages/core/src/operational/core/scenario_classifier.py` — recommendation strings only
- `src/operational/packages/core/src/operational/core/pomodoro_machine.py:16-19` — docstring says not wired
- `src/operational/packages/core/src/operational/core/policy_engine.py:467-475, 547-575` — emergency + QHE-driven transitions
- `src/operational/packages/core/src/operational/core/budget.py:classify_quadrant` — Cartesian Q1..Q4
- `src/operational/packages/core/src/operational/core/consolidator.py:228-232, 285` — sleep penalty clamp + health max=90
- `src/operational/packages/core/src/operational/core/weekly_aggregator.py:287` — avg_health substitution

### Docs (analisados)
- `docs/auto-performance-os/00-INDEX.md` (template 5-section)
- `docs/auto-performance-os/01-axiom-energia-tempo.md` (B3)
- `docs/auto-performance-os/02-axiom-habitualidade.md` (B1, B2)
- `docs/auto-performance-os/05-postulate-sono-cognicao.md` (B6)
- `docs/auto-performance-os/08-postulate-carga-cognitiva.md` (B7)
- `docs/auto-performance-os/10-engine-pomodoro-machine.md` (A7)
- `docs/auto-performance-os/11-postulate-carga-cognitiva.md` (E6)
- `docs/auto-performance-os/13-engine-habit-engine.md` (A3)
- `docs/auto-performance-os/14-engine-policy-engine-fsm.md` (C5, C6)
- `docs/auto-performance-os/16-engine-sleep-validator.md` (A1, F1)
- `docs/auto-performance-os/17-engine-budget-classifier.md` (A6)
- `docs/auto-performance-os/19-engine-ikigai-vector-scorer.md` (A4, F3)
- `docs/auto-performance-os/20-engine-ucb-recalibrator.md` (E9)
- `docs/auto-performance-os/21-meta-qhe-policy-mapping.md` (A2, C1, C4)
- `docs/auto-performance-os/22-meta-ikigai-meta-vector.md` (A5, F4, B5)
- `docs/auto-performance-os/23-meta-decision-flow.md` (E10)
- `docs/auto-performance-os/24-integration-mesh-ueid-propagation.md` (F5)
- `docs/auto-performance-os/26-integration-cybernetic-loop.md` (F10)

### Memory cross-refs
- `[[algorithm-issues-registry]]` — 31 issues (estender para F1-F12)
- `[[algorithm-decisions-defer-2026-08-28]]` — defer algoritmo até dado empírico
- `[[prioritize-backend-over-algorithm-refinement]]` — backend > algorithm polish
- `[[data-first-methodology]]` — 5 SONHO logs gate (ADR-007)
- `[[verify-agent-fabricated-failures]]` — verificação independente requerida

## §7 — Metadados

- **Versão:** 2026-08-28
- **Origem:** Explore agent `a147fa31c95455fbb` (171.8s, 57 tool uses) + verificação manual
- **Audit period:** 27 docs `docs/auto-performance-os/` + 17 PAV core Python files
- **Findings total:** 7 CRITICAL (A1-A7) + 7 SCIENTIFIC RIGOR (B1-B7) + 10 MATH COGENCY (C1-C10) + 10 CONCEPTUAL (E1-E10) + 12 NEW (F1-F12) = **46 issues**
- **Cobertura vs registry existente:** 31 items → +12 novos = **43 items total** após extensão
- **Status:** DRAFT (pending user review of recommendations §5)
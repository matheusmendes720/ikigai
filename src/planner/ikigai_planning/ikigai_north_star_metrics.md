# IKIGAi North Star Metrics

> As **constantes que regem** todo o sistema. São as "estrelas" que
> `policy_engine`, `temporal_engine`, e `habit_engine` usam como setpoints.
>
> Toda decisão algorítmica (regime, fase, priorização) **deve respeitar
> estas constantes** ou documentar exceção.

---

## 1. Janelas Temporais Canônicas

| Constante | Valor | Origem Canônica | Impacto | Cluster |
|---|---|---|---|---|
| `HORARIO_ACORDAR_MIN` | `3` (3 AM) | [`vibe-ops/base/Produtividade Algorítmica Visual.md §1`](../../../vibe-ops/base/Produtividade%20Algor%C3%ADtmica%20Visual.md) | 🔴 Crítico | PLAN |
| `HORARIO_ACORDAR_MAX` | `5` (5 AM) | Idem | 🔴 Crítico | PLAN |
| `HORARIO_DORMIR_MIN` | `18` (18h) | Idem | 🔴 Crítico | PLAN |
| `HORARIO_DORMIR_MAX` | `21` (21h) | Idem | 🟡 Alto | PLAN |
| `HORARIO_ULTIMA_REFEICAO` | `15-18` (range) | Idem | 🟡 Alto | PLAN |
| `SONO_OPCOES_HORAS` | `[9, 8, 7, 4]` | Idem | 🔴 Crítico | PLAN |
| `LUZ_AZUL_CORTE` | `18` (18h) | Idem | 🟡 Alto | PLAN |
| `TRANSITION_RITUAL_MAX_MIN` | `5 min` | [`CONCEPTUAL_MODEL.md §1 T01`](../../../CONCEPTUAL_MODEL.md) | 🔴 Crítico | PLAN |
| `OVERHEAD_TRANSICAO_TOTAL_MAX_MIN` | `45 min/dia` (alvo) | derivado de `IKIGAi.md §157,5 min` | 🟡 Alto | PLAN |

## 2. Pomodoro Canônico

| Constante | Valor | Origem Canônica | Impacto | Cluster |
|---|---|---|---|---|
| `POMODORO_WORK_MIN` | `50 min` | PAV §1 | 🟢 Médio | PLAN/PROJ/STUDY |
| `POMODORO_BREAK_MIN` | `10 min` | Idem | 🟢 Médio | PLAN/PROJ/STUDY |
| `POMODORO_ROUNDS_MIN` | `3` | Idem | 🟢 Médio | PLAN |
| `POMODORO_ROUNDS_MAX` | `4` (curso) / `5-6` (livre) | [`vibe-ops/base/IKIGAi.md §Setpoints`](../../../vibe-ops/base/IKIGAi.md) | 🟢 Médio | PLAN |

## 3. Constantes Matemáticas do Sistema

| Constante | Valor | Origem Canônica | Impacto | Cluster |
|---|---|---|---|---|
| `λ` (taxa aprendizado hábito) | `0.093 D⁻¹` | [`life-ops/planner/time-lenghts_reviews.md §9.2`](../../time-lenghts_reviews.md) | 🟡 Médio | PLAN/STUDY |
| `ρ` (conversão calend. W→D) | `11/15 ≈ 0.7333` | [`life-ops/planner/time-lenghts_reviews.md §1.2`](../../time-lenghts_reviews.md) | 🟡 Médio | PLAN |
| `WORK_RATIO` | `22/30 = 0.7333` | Idem | 🟡 Médio | PLAN |
| `BUFFER_CYCLE` | `3 D ≈ 2 W` (~6.7% margem) | [`life-ops/planner/time-lenghts_reviews.md §3.5`](../../time-lenghts_reviews.md) | 🟢 Médio | PLAN |

## 4. WAVE / CYCLE / PHASE (Fractal Temporal)

| Constante | Valor | Origem Canônica | Impacto | Cluster |
|---|---|---|---|---|
| `WAVE` | `15 D = 11 W` | [`time-lenghts_reviews.md §2.1`](../../time-lenghts_reviews.md) | 🟡 Médio | PLAN |
| `CYCLE` | `45 D = 33 W ≡ HALF_QUARTER` | [`time-lenghts_reviews.md §2.2`](../../time-lenghts_reviews.md) | 🟡 Médio | PLAN |
| `PHASE` | `180 D = 132 W ≡ 2×QUARTER` | [`time-lenghts_reviews.md §2.1`](../../time-lenghts_reviews.md) | 🟡 Médio | PLAN |
| `$H_{wave}$` alvo (d15) | `75%` | [`time-lenghts_reviews.md §9.2`](../../time-lenghts_reviews.md) | 🟡 Médio | PLAN |
| `$H_{cycle}$` alvo (d45) | `98.5%` | Idem | 🟡 Médio | PLAN |
| `$H_{phase}$` alvo (d180) | `99.98%` | Idem | 🟡 Médio | PLAN |

## 5. Regime $\pi(s_t)$ — Thresholds de Q_HE

| Constante | Valor | Origem Canônica | Impacto | Cluster |
|---|---|---|---|---|
| `Q_HE_target` (PUSH) | `≥ 0.85` | [`CONCEPTUAL_MODEL.md §4`](../../../CONCEPTUAL_MODEL.md) | 🔴 Crítico | PLAN |
| `Q_HE_threshold_DOWN` (REDUCE) | `≤ 0.65` (2 dias consecutivos) | [`life-ops/planner/Points_of_premisses-task-habits.md §4`](../../Points_of_premisses-task-habits.md) | 🟡 Alto | PLAN |
| `Q_HE_threshold_RECOVER` | `< 0.60` (2 dias consecutivos) | Idem | 🟡 Alto | PLAN |
| `Q_HE_promote_window` | `3 dias` (upward) | Idem (histerese) | 🟢 Médio | PLAN |
| `Q_HE_demote_window` | `2 dias` (downward) | Idem | 🟢 Médio | PLAN |
| `Q_HE_recovery_target` | `≥ 0.70` para sair de RECOVER | Idem | 🟡 Alto | PLAN |

## 6. IKIGAi Scoring Weights (por fase)

| Fase | $w_1$ Passion | $w_2$ Skill | $w_3$ Market | $w_4$ Revenue | $w_5$ Course |
|---|:---:|:---:|:---:|:---:|:---:|
| **Fundamentação** (Build to Learn) | 0.15 | 0.40 | 0.15 | 0.10 | 0.20 |
| **Busca de Mercado** (Market/Networking) | 0.10 | 0.15 | 0.45 | 0.20 | 0.10 |
| **Hackathon** (Build to Earn) | 0.10 | 0.20 | 0.20 | 0.40 | 0.10 |
| **Recuperação** (pós-infração) | 0.50 | 0.10 | 0.05 | 0.05 | 0.30 |
| **Overclocking** (emergência) | 0.15 | 0.15 | 0.15 | 0.50 | 0.05 |

> **Origem conceitual:** [`vibe-ops/vectors/README.md`](../../../vibe-ops/vectors/README.md) + [`CONCEPTUAL_MODEL.md §3`](../../../CONCEPTUAL_MODEL.md)

## 7. Q_HE Components (Ponderação)

| Componente $H_i(t)$ | Peso Base $w_i$ | Origem Canônica | Cluster |
|---|:---:|---|---|
| $H_{sono}(t)$ (18-21h → 3-5h) | 0.35 | [`Points_of_premisses-task-habits.md §3`](../../Points_of_premisses-task-habits.md) | PLAN |
| $H_{med}(t)$ (meditação matinal) | 0.20 | Idem | PLAN |
| $H_{workout}(t)$ (treino físico) | 0.25 | Idem | PLAN |
| $H_{lunch}(t)$ (almoço leve ≤35min) | 0.10 | Idem | PLAN |
| $S_{streak}$ (streak rotina-âncora) | $\eta=0.15$ | Idem | PLAN |

## 8. Princípio: Single Source of Truth

Cada constante **deve ter 1 fonte autoritativa**. Conflitos entre fontes são resolvidos por prioridade:

1. `vibe-ops/base/Produtividade Algorítmica Visual.md §1` (constantes brutas, primeira declaração)
2. `vibe-ops/base/IKIGAi.md §Setpoints` (ajustes ao perfil do Matheus)
3. `CONCEPTUAL_MODEL.md` (vetor canônico do sistema)
4. `life-ops/planner/time-lenghts_reviews.md` (constantes matemáticas)
5. `vibe-ops/vectors/vector-*.md` (ajustes por vetor)
6. `CLUSTER_*.md` (override contextual por cluster)

> **Conflito histórico documentado:** [`vibe-ops/src/pipeline/ikigai_scorer.py`](../../../vibe-ops/src/pipeline/ikigai_scorer.py) usa nomes divergentes (`study/dev/health/global`) em vez dos canônicos (`passion/skill/market/revenue`). Sprint 1 corrige.

## 9. Cross-cluster Enforcement

Cada cluster consome estas constantes de forma específica:

| Cluster | Constantes que consome | Validação |
|---|---|---|
| **CLUSTER_PLAN** | Janelas 3-5h/18-21h, pomodoro 50+10, Q_HE target, regime thresholds | `CLUSTER_PLAN.md §4.5 IKIGAi↔PAV` |
| **CLUSTER_PROJ** | Phase weights $w_i$, IKIGAi score, vector tags | `CLUSTER_PROJ.md §3 RICE+IKIGAi` |
| **CLUSTER_STUDY** | λ (taxa aprendizado), retention thresholds, WAVE/CYCLE | `CLUSTER_STUDY.md §3 Cognitive Debt` |
| **IKIGAi (meta-brain)** | TODAS (fonte primária) | este doc |
| **Habit/Cybernetics** | Q_HE formula, regime, histerese | `vibe-ops/planning/PRD-02-habit-tracker.md` |

## 10. Validação e Auditoria

Como auditar se constantes estão sendo respeitadas:

1. **Testes unitários** (Sprint 1): validar `policy_engine.py` retorna PUSH quando Q_HE ≥ 0.85
2. **M3 HabitEngine** (futuro): calcula Q_HE automaticamente a partir de H(t), E(t), S_streak
3. **CLI `life plan check-constants`** (a criar): verifica que valores hardcoded em código batem com este doc
4. **Review trimestral**: re-validar 5 fontes autoritativas

---

## 11. Cross-refs

| Doc | Propósito |
|---|---|
| [`vibe-ops/base/Produtividade Algorítmica Visual.md §1`](../../../vibe-ops/base/Produtividade%20Algor%C3%ADtmica%20Visual.md) | Constantes brutas (janelas, pomodoros) |
| [`vibe-ops/base/IKIGAi.md §Setpoints`](../../../vibe-ops/base/IKIGAi.md) | Ajustes ao perfil do Matheus |
| [`CONCEPTUAL_MODEL.md §3-4`](../../../CONCEPTUAL_MODEL.md) | Vetores + regime |
| [`life-ops/planner/time-lenghts_reviews.md`](../../time-lenghts_reviews.md) | WAVE/CYCLE/PHASE + ρ + WORK_RATIO |
| [`life-ops/planner/Points_of_premisses-task-habits.md §3-4`](../../Points_of_premisses-task-habits.md) | Q_HE + histerese |
| [`vibe-ops/vectors/README.md`](../../../vibe-ops/vectors/README.md) | Vector tags |
| [`vibe-ops/architecture/ADR-003-ikigai-as-meta-brain.md`](../../../vibe-ops/architecture/ADR-003-ikigai-as-meta-brain.md) | IKIGAi como meta-brain |

---

*ikigai_north_star_metrics.md — v1.0 — 2026-06-05 — Constantes canônicas do sistema*

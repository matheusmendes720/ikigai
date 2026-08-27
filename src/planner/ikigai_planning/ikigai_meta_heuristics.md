# IKIGAi Meta-Heuristics — Decision Algorithms

> Algoritmos determinísticos (sem LLM) que o IKIGAi usa para decidir
> **regime**, **fase**, e **priorização**. Apenas aritmética + funções algébricas.
>
> Estes algoritmos são o "cérebro" do sistema: recebem inputs (vector scores,
> Q_HE, pipeline de oportunidades) e emitem decisões (regime π(s_t), phase pivot,
> weight recalibration).

---

## 1. Regime Decision: PUSH / MAINTAIN / REDUCE / RECOVER

### 1.1. Input

- $Q_{HE}(t)$: quociente de eficiência habitual (rolling 7d)
- $C_{comp}(t)$: completion ratio (deliverables feitas / planejadas)
- $\text{Infrações}_{24h}$: contador de infrações (acordar > 5h, sono < 6h, etc.)
- $R_{qual}$: qualidade da review quinzenal (BOM, EXCELENTE, RUIM)

### 1.2. Algoritmo (canônico)

```python
def compute_regime(
    qhe_7d_avg: float,
    c_comp_24h: float,
    infractions_24h: int,
    sleep_debt_h: float
) -> RegimeType:
    """
    Decide regime π(s_t) com histerese.
    Sem LLM, sem NLP, apenas aritmética.
    """
    # 1. Hard floor: RECOVER se Q_HE muito baixo
    if qhe_7d_avg < 0.60 and sleep_debt_h > 2.0:
        return RegimeType.RECOVER

    # 2. PUSH: alta performance
    if qhe_7d_avg >= 0.85 and c_comp_24h >= 0.90 and infractions_24h == 0:
        return RegimeType.PUSH

    # 3. MAINTAIN: normal
    if 0.70 <= qhe_7d_avg < 0.85 and 0.80 <= c_comp_24h < 0.90:
        return RegimeType.MAINTAIN

    # 4. REDUCE: degradação
    if 0.60 <= qhe_7d_avg < 0.70 or 0.70 <= c_comp_24h < 0.80:
        return RegimeType.REDUCE

    # 5. Default: RECOVER (conservador)
    return RegimeType.RECOVER
```

### 1.3. Histerese (origem: `Points_of_premisses-task-habits.md §4`)

| Transição | Janela | Propósito |
|---|---|---|
| **UPGRADE** (REDUCE → MAINTAIN → PUSH) | **3 dias consecutivos** acima do limiar | Evita oscilação por pico isolado |
| **DOWNGRADE** (PUSH → MAINTAIN → REDUCE) | **2 dias consecutivos** abaixo do limiar | Resposta rápida a degradação |
| **RECOVER entry** (qualquer → RECOVER) | **imediato** (1 dia) se Q_HE < 0.60 + sleep_debt > 2h | Emergência |
| **RECOVER exit** (RECOVER → REDUCE) | **3 dias** com Q_HE ≥ 0.65 + 0 infrações | Não forçar |

### 1.4. Setpoints por Regime (origem: `vibe-ops/src/schemas/pydantic_v2.py PolicyState`)

| Regime | hardwork_budget_h | pause_min | sleep_target_h | Q_HE target | C_comp target |
|---|:---:|:---:|:---:|:---:|:---:|
| PUSH | 4.0 | 10 | 7.5 | 0.85 | 0.90 |
| MAINTAIN | 2.5 | 15 | 8.0 | 0.65 | 0.85 |
| REDUCE | 1.5 | 20 | 8.5 | 0.45 | 0.75 |
| RECOVER | 0.5 | 30 | 9.0 | 0.25 | 0.65 |

## 2. Phase Pivot: FUNDAÇÃO → BUSCA → HACKATHON → RECUPERAÇÃO → OVERCLOCKING

### 2.1. Input

- $\|\vec{I}\|$: IKIGAi Score (meta-vetor, 0-100)
- $\text{revenue\_actual}$: receita realizada últimos 30d
- $\text{revenue\_target}$: meta receita (soma `project.target_revenue`)
- $\text{opportunities\_pipeline}$: count de OpportunitySignal(status=PURSUING)
- $\text{cognitive\_debt}$: soma de StudyTopic com pré-req não satisfeito (CLUSTER_STUDY)

### 2.2. Algoritmo

```python
def compute_phase(
    ikigai_score: float,
    revenue_actual_30d: float,
    revenue_target: float,
    opportunities_pursuing: int,
    cognitive_debt: float
) -> Phase:
    """
    Decide phase pivot baseado em momentum estratégico.
    """
    revenue_pct = revenue_actual_30d / max(revenue_target, 1)
    momentum = 0.4 * ikigai_score + 0.6 * (revenue_pct * 100)

    # OVERCLOCKING: emergência
    if cognitive_debt > 5.0 or ikigai_score < 30:
        return Phase.OVERCLOCKING

    # HACKATHON: pronto para entregar
    if momentum > 70 and opportunities_pursuing >= 2:
        return Phase.HACKATHON

    # BUSCA: mercado aquecido
    if momentum > 50 and opportunities_pursuing >= 3:
        return Phase.BUSCA

    # FUNDAÇÃO: foco em skill
    if cognitive_debt > 1.0 or ikigai_score < 60:
        return Phase.FUNDACAO

    # RECUPERAÇÃO: baixa energia
    if ikigai_score < 40:
        return Phase.RECUPERACAO

    # Default: FUNDAÇÃO (manter consistência)
    return Phase.FUNDACAO
```

### 2.3. Critérios de Pivot (cruzam com weights $w_i$)

| De → Para | Critério | Weights Re-arranjados |
|---|---|---|
| FUNDAÇÃO → BUSCA | $\|\vec{I}\| \geq 60$ + opportunities_pipeline ≥ 3 | $w_3$ (market) sobe 0.15 → 0.45 |
| BUSCA → HACKATHON | revenue_actual ≥ 70% target + interviews ≥ 2 | $w_4$ (revenue) sobe 0.20 → 0.40 |
| HACKATHON → BUSCA | sprint velocity < 70% target por 2 sprints | $w_3$ (market) sobe 0.40 → 0.20 |
| BUSCA → FUNDAÇÃO | opportunities_pipeline < 1 + skill_gap > 3 tópicos | $w_2$ (skill) sobe 0.15 → 0.40 |
| qualquer → RECUPERAÇÃO | Q_HE < 0.60 sustentado 2d | $w_1$ (passion) sobe 0.10 → 0.50 |
| qualquer → OVERCLOCKING | deadline crítico (< 7d) com revenue_actual < 30% | $w_4$ (revenue) sobe 0.40 → 0.50 |

## 3. Vector Weight Recalibration (UCB)

### 3.1. Input

- $\Delta \text{score}_i$: mudança no score do vetor $i$ últimos 7d
- $\sigma_i$: desvio padrão histórico do vetor $i$
- $n_i$: número de eventos do vetor $i$

### 3.2. Algoritmo (Upper Confidence Bound)

```python
def recalibrate_weight_ucb(
    w_i: float,
    delta_score_i: float,
    sigma_i: float,
    n_i: int,
    max_weight: float = 1.5
) -> float:
    """
    UCB: w_i(t+1) = w_i(t) + α · (Δscore_i / max_score) - β · σ_i + c · sqrt(ln(N) / n_i)
    """
    import math
    N = sum([n_j for n_j in all_n.values()])
    ucb_bonus = 0.05 * math.sqrt(math.log(N + 1) / max(n_i, 1))

    delta_weight = (
        0.05 * (delta_score_i / 100.0)  # α
        - 0.02 * sigma_i                  # β
        + ucb_bonus                       # c · sqrt(ln(N) / n_i)
    )
    new_weight = max(0.0, min(max_weight, w_i + delta_weight))
    return new_weight
```

**Coeficientes** (calibrados com dados históricos):
- $\alpha = 0.05$: peso da melhoria
- $\beta = 0.02$: penalidade da variância
- $c = 0.05$: exploração UCB

### 3.3. Quando rodar

- Trimestral (PHASE_END), após consolidar dados
- Nunca em regime RECOVER (inviável calibrar com dados ruidosos)
- Output: 5 novos $w_i$ para a próxima PHASE

## 4. Opportunity Scoring (Market Vector)

### 4.1. Input

- `required_skills`: lista de skills da oportunidade
- `user_skills`: skills atuais do operador
- `deadline`: prazo
- `estimated_revenue`: receita estimada
- `estimated_hours`: esforço estimado

### 4.2. Algoritmo (fit_score)

```python
def compute_opportunity_fit(
    required_skills: list[str],
    user_skills: list[str],
    deadline_days: int,
    estimated_revenue: float,
    estimated_hours: float,
    ikigai_alignment: dict
) -> float:
    """
    fit_score ∈ [0, 1]
    """
    # 1. Skills match: 0-1
    skills_match = len(set(required_skills) & set(user_skills)) / max(len(required_skills), 1)

    # 2. Deadline feasibility: 0-1
    days_available = deadline_days
    hours_per_day_needed = estimated_hours / max(days_available, 1)
    deadline_feasible = 1.0 if hours_per_day_needed <= 2.0 else 0.5

    # 3. Revenue per hour: 0-1 (normalizado por R$30/h target)
    rph = estimated_revenue / max(estimated_hours, 1)
    rph_normalized = min(1.0, rph / 30.0)

    # 4. IKIGAi alignment: 0-1 (média dos scores por vetor)
    alignment_avg = sum(ikigai_alignment.values()) / max(len(ikigai_alignment), 1)

    # Fit final (ponderado)
    fit_score = (
        skills_match * 0.4 +
        deadline_feasible * 0.2 +
        rph_normalized * 0.2 +
        alignment_avg * 0.2
    )
    return min(1.0, max(0.0, fit_score))
```

### 4.3. Threshold de Decisão

| fit_score | Decisão |
|---|---|
| `>= 0.70` | 🟢 PURSUING (pursue ativamente) |
| `[0.50, 0.70)` | 🟡 EVALUATING (avaliar mais 7d) |
| `[0.30, 0.50)` | 🟠 DETECTED (registrar, não priorizar) |
| `< 0.30` | 🔴 LOST (descartar) |

## 5. Skill Velocity Decision (CLUSTER_STUDY)

### 5.1. Input

- `current_level`: nível atual da skill
- `target_level`: nível alvo
- `hours_invested`: horas investidas
- `target_hours`: horas target para o nível
- `days_in_phase`: dias na fase atual

### 5.2. Algoritmo (level promotion)

```python
def should_promote_skill(
    current_level: str,
    target_level: str,
    hours_invested: float,
    target_hours: float,
    days_in_phase: int,
    retention_score_avg: float
) -> bool:
    """
    Decide se uma skill deve ser promovida de nível.
    """
    level_map = {"beginner": 0, "intermediate": 1, "advanced": 2, "expert": 3}
    if level_map[current_level] >= level_map[target_level]:
        return False  # já no alvo

    hours_pct = hours_invested / max(target_hours, 1)
    days_threshold = 45  # mínimo 45 dias no nível

    if hours_pct >= 0.80 and days_in_phase >= days_threshold and retention_score_avg >= 0.75:
        return True
    return False
```

### 5.3. Critério de Velocidade (origem: `PRD-03 §6`)

- Alvo: **≥ 1 nível por PHASE (180d)**
- Se < 0.3 níveis em 6 meses: **estagnação detectada** → forçar sprint de skill

## 6. Cross-cluster Priority (PROJ ↔ STUDY)

### 6.1. Algoritmo RICE + IKIGAi

```python
def compute_task_priority(
    reach: float,        # 1-10
    impact: float,       # 0.25-3
    confidence: float,   # 0-1
    effort: float,       # horas
    w_ikigai: float,     # peso do vetor IKIGAi do projeto
    w_deadline: float,   # peso por proximidade do deadline
) -> float:
    """
    PriorityScore = (R × I × C / E) × w_ikigai × w_deadline
    """
    rice = (reach * impact * confidence) / max(effort, 0.5)
    return rice * w_ikigai * w_deadline
```

### 6.2. Pesos de IKIGAi por vetor (origem: `ikigai_north_star_metrics.md §6`)

```python
W_IKIGAI = {
    VectorType.PASSION: 1.0,  # baseline
    VectorType.SKILL: 1.2,    # skill building weighted higher
    VectorType.MARKET: 1.5,   # market signal = big opportunity
    VectorType.REVENUE: 1.5,  # revenue = direct value
    VectorType.COURSE: 0.8,   # course = obligation, lower
}
```

### 6.3. Pesos de Deadline

| Deadline | Weight |
|---|:---:|
| `< 7 dias` | 1.5 (urgente) |
| `[7, 30 dias)` | 1.2 (normal) |
| `[30, 90 dias)` | 1.0 (default) |
| `> 90 dias` | 0.8 (baixa urgência) |

## 7. Resumo: Decision Tree Completo

```mermaid
flowchart TD
    A[Inputs:<br/>Q_HE, C_comp, vector scores,<br/>ikigai_score, opportunities, debt] --> B{Compute<br/>Regime}
    A --> C{Compute<br/>Phase}
    A --> D{Recalibrate<br/>Weights}
    A --> E{Score<br/>Opportunities}
    A --> F{Promote<br/>Skills}
    A --> G{Compute<br/>Task Priority}

    B --> H[Output: π s t]
    C --> I[Output: phase pivot]
    D --> J[Output: new w_i for next phase]
    E --> K[Output: fit_score → DECIDED|EVALUATING|LOST]
    F --> L[Output: promote boolean]
    G --> M[Output: priority score → TW UDA]

    H --> N[policy_decisions]
    I --> O[temporal_waves cycles phases]
    J --> P[ikigai_vectors weights]
    K --> Q[opportunity_signals]
    L --> R[skill_nodes]
    M --> S[tasks + TW]

    style A fill:#1a1a2e,stroke:#ff6b6b
    style N fill:#2d2d44,stroke:#4a6fa5
```

## 8. Princípios Algorítmicos (Invariantes)

1. **Determinismo:** mesmas inputs → mesmas outputs (sem random, sem LLM)
2. **Auditabilidade:** cada decisão tem `rationale` explicável
3. **Histerese:** promoção lenta (3d), demoção rápida (2d)
4. **Conservadorismo:** default é `RECOVER` (não `PUSH`) em caso de dúvida
5. **Composabilidade:** algoritmos são funções puras, podem ser encadeados
6. **Reversibilidade:** cada decisão pode ser overridden manualmente (audit log)

## 9. Cross-refs

| Doc | Propósito |
|---|---|
| [`CONCEPTUAL_MODEL.md §4`](../../../CONCEPTUAL_MODEL.md) | State machine regime |
| [`life-ops/planner/Points_of_premisses-task-habits.md §4`](../../Points_of_premisses-task-habits.md) | Histerese, Q_HE matriz |
| [`vibe-ops/planning/PRD-06-policy-governance.md`](../../../vibe-ops/planning/PRD-06-policy-governance.md) | Spec PolicyEngine |
| [`vibe-ops/planning/PRD-07-ikigai-vectors.md §4`](../../../vibe-ops/planning/PRD-07-ikigai-vectors.md) | Spec score algorithms |
| [`vibe-ops/src/pipeline/policy_engine.py`](../../../vibe-ops/src/pipeline/policy_engine.py) | Implementação atual (4-state) |
| [`vibe-ops/src/schemas/pydantic_v2.py`](../../../vibe-ops/src/schemas/pydantic_v2.py) | PolicyState + setpoints |
| [`vibe-ops/architecture/ADR-003-ikigai-as-meta-brain.md`](../../../vibe-ops/architecture/ADR-003-ikigai-as-meta-brain.md) | IKIGAi como meta-brain |
| [`ikigai_north_star_metrics.md`](ikigai_north_star_metrics.md) | Constantes (thresholds) |
| [`CLUSTER_PLAN.md §4`](../../../CLUSTER_PLAN.md) | Consumo do regime |

---

*ikigai_meta_heuristics.md — v1.0 — 2026-06-05 — Algoritmos determinísticos (sem LLM) para decisão*

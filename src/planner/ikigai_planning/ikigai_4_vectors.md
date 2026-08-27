# IKIGAi 4 Vectors (Canônicos) + 5º Contextual

> **Drilldown do modelo conceitual** ([`vibe-ops/base/IKIGAi.md`](../../../vibe-ops/base/IKIGAi.md))
> em especificações executáveis para o meta-brain.

---

## 1. Os 4 Vetores Canônicos + 5º Contextual

O IKIGAi do Matheus opera com **5 vetores** (4 canônicos do framework original + 1 contextual reconhecido por ele em [`CONCEPTUAL_MODEL.md`](../../../CONCEPTUAL_MODEL.md) §3).

### ❤️ Passion (Reset de Cache Metabólico)

| Atributo | Valor |
|---|---|
| **Pergunta canônica** | "O que me energiza e dá sentido?" |
| **Substrato** | sono, treino, meditação, hábitos biológicos |
| **Fórmula H(t)** | $1 - e^{-\lambda \cdot streak}$, $\lambda = 0.093 \, D^{-1}$ |
| **Peso típico $w_1$** | 0.10 (Fundamentação) → 0.50 (Recuperação) |
| **Tag TW** | `phase:train`, `@training` |
| **Cluster primário** | CLUSTER_PLAN (rotinas manhã) |
| **Pydantic model** | `Habit` (habit_entities.py) + `IKIGAiVectorEntity(vector_type=PASSION)` |
| **Cross-refs** | [`vibe-ops/vectors/vector-passion.md`](../../../vibe-ops/vectors/vector-passion.md), [`vibe-ops/planning/PRD-02-habit-tracker.md`](../../../vibe-ops/planning/PRD-02-habit-tracker.md), [`vibe-ops/base/IKIGAi.md §Hypervisor`](../../../vibe-ops/base/IKIGAi.md) |

### 💼 Skill (Torque Técnico)

| Atributo | Valor |
|---|---|
| **Pergunta canônica** | "No que sou genuinamente bom?" |
| **Substrato** | study_sessions, project_completion_rate, horas investidas |
| **Cálculo** | $\text{skill\_score} = (\Sigma \text{skill.level\_score} \times \text{market\_demand\_weight}) \times 0.5 + \text{learning\_momentum} \times 0.3 + \text{project\_completion} \times 0.2$ |
| **Peso típico $w_2$** | 0.20 (Busca) → 0.40 (Fundamentação) |
| **Tag TW** | `phase:learn`, `@vscode` + `@obsidian` |
| **Cluster primário** | CLUSTER_STUDY |
| **Pydantic model** | `SkillNode` (PRD-07) + `StudySession` (study_entities.py) |
| **Cross-refs** | [`vibe-ops/vectors/vector-skill.md`](../../../vibe-ops/vectors/vector-skill.md), [`vibe-ops/planning/PRD-03-study-backlog.md`](../../../vibe-ops/planning/PRD-03-study-backlog.md) |

### 🎯 Market (Tração no Mundo)

| Atributo | Valor |
|---|---|
| **Pergunta canônica** | "Do que o mundo precisa e paga?" |
| **Substrato** | revenue_actual, client_feedback, opportunities |
| **Cálculo** | $\text{market\_score} = \text{fit\_avg} \times 0.4 + \text{skills\_demand\_avg} \times 0.4 + \text{opportunities\_pipeline} \times 0.2$ |
| **Peso típico $w_3$** | 0.20 (Hackathon) → 0.45 (Busca) |
| **Tag TW** | `phase:share`, `@browser` |
| **Cluster primário** | CLUSTER_PROJ (Content Lab) |
| **Pydantic model** | `OpportunitySignal` (PRD-07) + `ContentSession` (market.md Pydantic) |
| **Cross-refs** | [`vibe-ops/vectors/vector-market.md`](../../../vibe-ops/vectors/vector-market.md), [`vibe-ops/vectors/README.md`](../../../vibe-ops/vectors/README.md) |

### 💰 Revenue (Fluxo de Caixa)

| Atributo | Valor |
|---|---|
| **Pergunta canônica** | "Com o que posso ser pago?" |
| **Substrato** | actual_revenue, pipeline, freelance wins, fin_ops |
| **Cálculo** | $\text{revenue\_score} = \frac{\text{revenue\_actual}}{\max(\text{revenue\_target}, 1)} \times 70 + \text{pipeline\_health} \times 30$ |
| **Peso típico $w_4$** | 0.40 (Fundamentação) → 1.20 (Hackathon) |
| **Tag TW** | `phase:earn`, `@vscode` + `@browser` |
| **Cluster primário** | CLUSTER_PROJ |
| **Pydantic model** | `RevenueSession` (revenue.md Pydantic) + `JobApplication` |
| **Cross-refs** | [`vibe-ops/vectors/vector-revenue.md`](../../../vibe-ops/vectors/vector-revenue.md) |

### 🎓 Course (5º Vetor Contextual)

| Atributo | Valor |
|---|---|
| **Pergunta canônica** | "Estou cumprindo o ônus do curso com mínimo atrito?" |
| **Origem** | Reconhecido em [`CONCEPTUAL_MODEL.md`](../../../CONCEPTUAL_MODEL.md) §3 (adaptação do Matheus) |
| **Quando se aplica** | Período SENAI (6-12h, dias úteis) |
| **Substrato** | presença em aula, provas, trabalhos |
| **Cálculo** | $\text{course\_score} = \text{attendance\_rate} \times 0.5 + \text{assignments\_on\_time} \times 0.3 + \text{exam\_avg} \times 0.2$ |
| **Peso típico $w_5$** | 0.10 (lifecycle) → 0.30 (early ADS) → 0.00 (pós-curso) |
| **Tag TW** | `phase:learn` (categoria `course`), `@senai` |
| **Cluster primário** | externo (SENAI), com tracking em CLUSTER_PLAN |
| **Pydantic model** | `CourseEntity` (a criar, gap) |
| **Por que é vetor separado** | consome 27% do dia, exige rastreamento específico |
| **Cross-refs** | [`CONCEPTUAL_MODEL.md §3`](../../../CONCEPTUAL_MODEL.md), [`vibe-ops/base/IKIGAi.md §1.4`](../../../vibe-ops/base/IKIGAi.md) |

---

## 2. Meta-Vetor (agregado)

A **nota IKIGAi geral** é o módulo do meta-vetor:

$$
|\vec{Ikigai}| = \sqrt{(w_1 \vec{P}) \cdot (w_2 \vec{S})} \cdot 0.3 + \sqrt{(w_1 \vec{P}) \cdot (w_3 \vec{M})} \cdot 0.2 + \sqrt{(w_2 \vec{S}) \cdot (w_3 \vec{M}) \cdot (w_4 \vec{R})} \cdot 0.3 + \sqrt{(w_3 \vec{M}) \cdot (w_4 \vec{R})} \cdot 0.2
$$

| Score Final | Label | Implicação |
|---|---|---|
| `>= 75` | `ALIGNED` | Sistema no sweet spot IKIGAi |
| `[50, 75)` | `CONVERGING` | Tendência de alinhamento |
| `[25, 50)` | `MISALIGNED` | Re-pivotar pesos $w_i$ |
| `< 25` | `CRITICAL` | Realinhamento estratégico urgente |

---

## 3. Pydantic Models (canônicos)

```python
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from datetime import date, datetime
from enum import Enum
from uuid import UUID

class VectorType(str, Enum):
    PASSION = "passion"
    SKILL = "skill"
    MARKET = "market"
    REVENUE = "revenue"
    COURSE = "course"  # 5º contextual

class VectorTrend(str, Enum):
    UP = "up"
    STABLE = "stable"
    DOWN = "down"

class AlignmentLabel(str, Enum):
    ALIGNED = "aligned"
    CONVERGING = "converging"
    MISALIGNED = "misaligned"
    CRITICAL = "critical"

class VectorScorePoint(BaseModel):
    date: date
    score: float = Field(ge=0, le=100)
    evidence: str  # o que justifica o score

class IKIGAiVectorEntity(BaseModel):
    """5 vetores canônicos. GAP: ikigai_entities.py atual tem só 18 linhas."""
    id: UUID
    vector_type: VectorType
    name: str
    description: str
    current_score: float = Field(ge=0, le=100)
    target_score: float = Field(ge=0, le=100)
    score_history: List[VectorScorePoint] = []
    activities: List[str] = []  # atividades que alimentam este vetor
    projects: List[UUID] = []  # projetos alinhados
    habits: List[UUID] = []  # hábitos que fortalecem
    last_updated: datetime
    trend: VectorTrend
    weight: float = Field(ge=0, le=1.5)  # peso dinâmico w_i

class IKIGAiProfile(BaseModel):
    """Snapshot completo do IKIGAi em uma data."""
    id: UUID
    date: date
    passion_score: float
    skill_score: float
    market_score: float
    revenue_score: float
    course_score: float = 0.0  # 5º contextual
    # Zonas de interseção
    vocacao_score: float      # passion ∩ skill
    missao_score: float       # passion ∩ market
    profissao_score: float    # skill ∩ market ∩ revenue
    negocio_score: float      # market ∩ revenue
    # Score final
    ikigai_score: float       # meta-vetor
    alignment_label: AlignmentLabel
    # Diagnóstico
    weakest_vector: VectorType
    biggest_opportunity: str
    alerts: List[str] = []

class SkillNode(BaseModel):
    id: UUID
    name: str  # ex: "FastAPI", "Data Mesh", "SQL"
    category: str  # programming, data, cloud, devops, soft_skill, domain, tool
    level: str  # BEGINNER|INTERMEDIATE|ADVANCED|EXPERT
    level_score: float = Field(ge=0, le=100)
    market_demand: str  # LOW|MEDIUM|HIGH|VERY_HIGH
    learning_hours: float = 0.0
    last_practiced: Optional[date] = None
    prerequisites: List[UUID] = []
    certifications: List[str] = []
    projects_using: List[UUID] = []
    vector_contribution: float  # quanto contribui para vetor SKILL

class OpportunitySignal(BaseModel):
    id: UUID
    title: str
    source: str  # LinkedIn, Upwork, Direct, Network
    signal_type: str  # JOB|FREELANCE|PARTNERSHIP|PRODUCT
    required_skills: List[str]
    estimated_revenue: Optional[float] = None
    estimated_hours: Optional[float] = None
    deadline: Optional[date] = None
    fit_score: float = Field(ge=0, le=1)
    status: str  # DETECTED|EVALUATING|PURSUING|WON|LOST
    ikigai_alignment: Dict[VectorType, float]  # score por vetor
    created_at: datetime
    notes: Optional[str] = None
```

---

## 4. Gap de Implementação ATUAL

### 🔴 Gap 1: `vibe-ops/src/pipeline/ikigai_scorer.py` (46 linhas) DIVERGE do conceitual

**Estado atual (errado):**
```python
return {"study": ..., "dev": ..., "health": ..., "global": ...}
```

**Estado alvo (5 vetores canônicos):**
```python
return {
    "passion": float,
    "skill": float,
    "market": float,
    "revenue": float,
    "course": float,  # 5º contextual
    "ikigai_score": float,  # meta-vetor
    "alignment_label": "aligned|converging|misaligned|critical"
}
```

**Sprint 1 task:** Reescrever `ikigai_scorer.py` para usar 5 vetores canônicos (sem LLM, apenas queries SQLite + aritmética).

### 🔴 Gap 2: `vibe-ops/src/models/ikigai_entities.py` (18 linhas) — INSUFICIENTE

**Estado atual:**
```python
class IKIGAiProfile(BaseModel):
    passion: float  # ⚠️ sem current_score, target_score, history
    skill: float
    market: float
    revenue: float
```

**Estado alvo:** Expandir para `IKIGAiVectorEntity` (com score_history), `IKIGAiProfile` (com 5 vetores + zones), `SkillNode`, `OpportunitySignal` — todos derivados de `PRD-07 §3`.

**Sprint 1 task:** Expandir `ikigai_entities.py` para ~150-200 linhas (Pydantic v2 canônicos).

### 🟡 Gap 3: Course vector (5º contextual) NÃO documentado em `vibe-ops/`

- `PRD-07-ikigai-vectors.md` (311 linhas) só tem 4 vetores (passion/skill/market/revenue)
- `vector-*.md` (4 docs) só cobre 4 vetores
- `ikigai_entities.py` (18 linhas) só tem 4 fields
- **Course é reconhecido em `CONCEPTUAL_MODEL.md §3` mas não está formalizado em `vibe-ops/`**

**Sprint 1 task:** Adicionar Course em `PRD-07-ikigai-vectors.md` e em `vectors/vector-course.md` (a criar).

---

## 5. Cross-refs

| Doc | Propósito |
|---|---|
| [`vibe-ops/base/IKIGAi.md`](../../../vibe-ops/base/IKIGAi.md) | Conceitual (90K) |
| [`vibe-ops/vectors/vector-passion.md`](../../../vibe-ops/vectors/vector-passion.md) | Vetor Passion |
| [`vibe-ops/vectors/vector-skill.md`](../../../vibe-ops/vectors/vector-skill.md) | Vetor Skill |
| [`vibe-ops/vectors/vector-market.md`](../../../vibe-ops/vectors/vector-market.md) | Vetor Market |
| [`vibe-ops/vectors/vector-revenue.md`](../../../vibe-ops/vectors/vector-revenue.md) | Vetor Revenue |
| [`vibe-ops/planning/PRD-07-ikigai-vectors.md`](../../../vibe-ops/planning/PRD-07-ikigai-vectors.md) | Spec entities + scores |
| [`vibe-ops/src/models/ikigai_entities.py`](../../../vibe-ops/src/models/ikigai_entities.py) | Pydantic atual (GAP) |
| [`vibe-ops/src/pipeline/ikigai_scorer.py`](../../../vibe-ops/src/pipeline/ikigai_scorer.py) | Scorer atual (GAP) |
| [`vibe-ops/planning/PRD-02-habit-tracker.md`](../../../vibe-ops/planning/PRD-02-habit-tracker.md) | Habit cybernetic (Passion) |
| [`vibe-ops/planning/PRD-03-study-backlog.md`](../../../vibe-ops/planning/PRD-03-study-backlog.md) | Skill entities |
| [`vibe-ops/planning/PRD-06-policy-governance.md`](../../../vibe-ops/planning/PRD-06-policy-governance.md) | Regime + meta-heuristics |
| [`CONCEPTUAL_MODEL.md §3`](../../../CONCEPTUAL_MODEL.md) | Meta-vetor $\|\vec{I}\|$ |
| [`CLUSTER_PLAN.md §4.5`](../../../CLUSTER_PLAN.md) | IKIGAi↔PAV mapping |
| [`life-ops/planner/Points_of_premisses-task-habits.md`](../../Points_of_premisses-task-habits.md) | Q_HE (Passion input) |
| [`life-ops/planner/time-lenghts_reviews.md`](../../time-lenghts_reviews.md) | WAVE/CYCLE/PHASE |

---

*ikigai_4_vectors.md — v1.0 — 2026-06-05 — Drilldown dos 4 vetores canônicos + 5º contextual*

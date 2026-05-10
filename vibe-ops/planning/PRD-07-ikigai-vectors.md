# PRD-07: IKIGAi Vectors Engine
**Versão:** 1.0.0 | **Status:** Draft | **Data:** 2026-05-10

> **Standalone Memory Machine** — Especificação autônoma do subgrafo IKIGAi. Cobre os 4 vetores (Passion, Skill, Market, Revenue) como entidades vivas que evoluem no tempo, com scoring dinâmico e alinhamento estratégico.

---

## 1. Propósito

O **IKIGAi Engine** é a camada de propósito do Data-Mesh — o "Norte Verdadeiro" que orienta todas as decisões. Ele:

- Mantém os 4 vetores como entidades quantificáveis e rastreáveis
- Calcula o **IKIGAi Score** dinâmico (alinhamento atual)
- Conecta cada projeto, hábito e tarefa a vetores específicos
- Detecta desvios de alinhamento e emite alertas estratégicos
- Serve como input para o PolicyEngine e TemporalEngine nas decisões de prioridade

---

## 2. Os 4 Vetores

### Definições Fundamentais

| Vetor | Pergunta Central | Fonte de Dados |
|:---|:---|:---|
| **Passion** | O que me energiza e dá sentido? | habit_compliance, energy durante atividades |
| **Skill** | No que sou genuinamente bom? | study_sessions, project_completion_rate |
| **Market** | O que o mundo precisa e paga? | revenue_actual, client_feedback, opportunities |
| **Revenue** | Com o que posso ser pago? | actual_revenue, pipeline, freelance wins |

### Zona de Alinhamento (Sweet Spot)

```
PAIXÃO ∩ HABILIDADE = O que você ama e é bom → VOCAÇÃO
PAIXÃO ∩ MERCADO = O que você ama e o mundo quer → MISSÃO
HABILIDADE ∩ MERCADO ∩ RECEITA = O que você é bom e paga → PROFISSÃO
MERCADO ∩ RECEITA = O que o mundo paga → NEGÓCIO

IKIGAi = Passion ∩ Skill ∩ Market ∩ Revenue
```

---

## 3. Modelos Pydantic

### IKIGAiVector (entidade viva)
```python
class IKIGAiVectorEntity(BaseModel):
    id: UUID
    vector_type: VectorType          # PASSION|SKILL|MARKET|REVENUE
    name: str                        # ex: "Python/Data Engineering"
    description: str
    current_score: float = Field(ge=0, le=100)
    target_score: float = Field(ge=0, le=100)
    score_history: list[VectorScorePoint] = []
    activities: list[str]            # atividades que alimentam este vetor
    projects: list[UUID]             # projetos alinhados
    habits: list[UUID]               # hábitos que fortalecem
    skills_required: list[str]       # para o vetor SKILL
    market_signals: list[str]        # para o vetor MARKET
    revenue_sources: list[str]       # para o vetor REVENUE
    last_updated: datetime
    trend: VectorTrend               # UP|STABLE|DOWN

class VectorType(str, Enum):
    PASSION = "passion"
    SKILL = "skill"
    MARKET = "market"
    REVENUE = "revenue"

class VectorTrend(str, Enum):
    UP = "up"
    STABLE = "stable"
    DOWN = "down"

class VectorScorePoint(BaseModel):
    date: date
    score: float
    evidence: str                    # o que justifica o score
```

### IKIGAiProfile (snapshot completo)
```python
class IKIGAiProfile(BaseModel):
    id: UUID
    date: date                       # data do snapshot
    passion_score: float
    skill_score: float
    market_score: float
    revenue_score: float
    # Zonas de interseção
    vocacao_score: float             # passion ∩ skill
    missao_score: float              # passion ∩ market
    profissao_score: float           # skill ∩ market ∩ revenue
    negocio_score: float             # market ∩ revenue
    # Score final
    ikigai_score: float              # alinhamento total (0-100)
    alignment_label: AlignmentLabel
    # Gaps identificados
    weakest_vector: VectorType
    biggest_opportunity: str
    alerts: list[str]

class AlignmentLabel(str, Enum):
    ALIGNED = "aligned"              # ikigai_score >= 75
    CONVERGING = "converging"        # 50 <= score < 75
    MISALIGNED = "misaligned"        # 25 <= score < 50
    CRITICAL = "critical"            # score < 25
```

### SkillNode (grafo de habilidades)
```python
class SkillNode(BaseModel):
    id: UUID
    name: str                        # ex: "FastAPI", "Data Mesh", "SQL"
    category: SkillCategory
    level: SkillLevel                # BEGINNER|INTERMEDIATE|ADVANCED|EXPERT
    level_score: float = Field(ge=0, le=100)
    market_demand: DemandLevel       # LOW|MEDIUM|HIGH|VERY_HIGH
    learning_hours: float = 0.0      # horas investidas
    last_practiced: Optional[date]
    prerequisites: list[UUID]        # outros skills necessários
    certifications: list[str]
    projects_using: list[UUID]
    vector_contribution: float       # quanto contribui para o vetor SKILL

class SkillCategory(str, Enum):
    PROGRAMMING = "programming"
    DATA = "data"
    CLOUD = "cloud"
    DEVOPS = "devops"
    SOFT_SKILL = "soft_skill"
    DOMAIN = "domain"
    TOOL = "tool"

class SkillLevel(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"

class DemandLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"
```

### OpportunitySignal (vetor MARKET)
```python
class OpportunitySignal(BaseModel):
    id: UUID
    title: str
    source: str                      # "LinkedIn", "Upwork", "Direct", "Network"
    signal_type: SignalType          # JOB|FREELANCE|PARTNERSHIP|PRODUCT
    required_skills: list[str]
    estimated_revenue: Optional[float]
    estimated_hours: Optional[float]
    deadline: Optional[date]
    fit_score: float                 # quão alinhado com skill atual
    status: OpportunityStatus        # DETECTED|EVALUATING|PURSUING|WON|LOST
    ikigai_alignment: dict[VectorType, float]  # score por vetor
    created_at: datetime
    notes: Optional[str]

class SignalType(str, Enum):
    JOB = "job"
    FREELANCE = "freelance"
    PARTNERSHIP = "partnership"
    PRODUCT = "product"

class OpportunityStatus(str, Enum):
    DETECTED = "detected"
    EVALUATING = "evaluating"
    PURSUING = "pursuing"
    WON = "won"
    LOST = "lost"
```

---

## 4. Algoritmos de Score

### Passion Score (baseado em energia e compliance)
```
passion_activities = [h for h in habits if h.vector == PASSION]
energy_during_passion = média(energy_readings durante atividades de paixão)
compliance_passion = compliance média dos hábitos de paixão

passion_score = (energy_during_passion * 0.6 + compliance_passion * 0.4)
```

### Skill Score (baseado em progresso de aprendizado)
```
skills_weighted = Σ(skill.level_score * skill.market_demand_weight)
learning_momentum = study_hours_30d / target_study_hours_30d
project_completion = projetos_completos / projetos_iniciados

skill_score = (skills_weighted * 0.5 + learning_momentum * 0.3 + project_completion * 0.2)
```

### Market Score (baseado em sinais externos)
```
opportunities_detected = len([o for o in opportunities if o.status != LOST])
fit_avg = média(o.fit_score for o in opportunities)
skills_demand_avg = média(skill.market_demand_score for skill in skills)

market_score = (fit_avg * 0.4 + skills_demand_avg * 0.4 + opportunities_pipeline * 0.2)
```

### Revenue Score (baseado em receita real vs target)
```
revenue_actual = Σ(project.actual_revenue for project in active_projects)
revenue_target = Σ(project.target_revenue for project in active_projects)
pipeline_value = Σ(o.estimated_revenue * o.fit_score for o in pursuing)

revenue_score = (revenue_actual / max(revenue_target, 1)) * 70 + pipeline_health * 30
```

### IKIGAi Score Final
```
ikigai_score = (
    (passion_score * skill_score) ** 0.5 * 0.3 +   # vocação
    (passion_score * market_score) ** 0.5 * 0.2 +   # missão
    (skill_score * revenue_score) ** 0.5 * 0.3 +    # profissão
    (market_score * revenue_score) ** 0.5 * 0.2     # negócio
)
```

---

## 5. Frontmatter Schema

### Vector Markdown (vectors/*.md)
```yaml
---
type: ikigai_vector
vector: passion
name: "Software Engineering & Problem Solving"
current_score: 78
target_score: 90
activities:
  - "Coding side projects"
  - "Contributing to open source"
  - "Teaching/mentoring"
projects:
  - "vibe-ops"
  - "AxeGuard"
habits:
  - "morning-code"
  - "reading-tech"
trend: up
last_updated: "2026-05-10"
---
```

---

## 6. Eventos Data-Mesh

| Evento Emitido | Trigger |
|:---|:---|
| `ikigai.score_updated` | recálculo semanal |
| `ikigai.alignment_changed` | label mudou |
| `ikigai.opportunity_detected` | novo OpportunitySignal |
| `ikigai.skill_leveled` | SkillNode.level aumentou |

| Evento Consumido | Origem |
|:---|:---|
| `study.session_completed` | StudyBacklog → skill_score |
| `project.milestone` | ProjectEngine → market/revenue |
| `metric.energy_high_during` | MetricsEngine → passion_score |

---

## 7. CLI Interface

```bash
# Dashboard IKIGAi
vibe-ops ikigai dashboard

# Score atual detalhado
vibe-ops ikigai score --breakdown

# Adicionar oportunidade
vibe-ops ikigai opportunity add --title "..." --source upwork

# Atualizar skill
vibe-ops ikigai skill update --skill python --level advanced --hours 200

# Histórico de alinhamento
vibe-ops ikigai history --last 90d

# Gaps e recomendações
vibe-ops ikigai gaps
```

---

## 8. Módulos

| Arquivo | Responsabilidade |
|:---|:---|
| `src/models/ikigai_entities.py` | Modelos Pydantic (novo) |
| `src/pipeline/ikigai_scorer.py` | Cálculo de scores (novo) |
| `src/pipeline/opportunity_tracker.py` | Pipeline de oportunidades (novo) |
| `vectors/*.md` | Dados dos vetores em markdown |

---

*PRD-07 — IKIGAi Vectors Engine | vibe-ops v1.0.0 | 2026-05-10*

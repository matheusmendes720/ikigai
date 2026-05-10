# Schema: Planner Extension — WAVE / CYCLE / PHASE / Habit

**Versao:** 0.1.0
**Ultima Atualizacao:** 2026-05-09
**Referencia:** `specs/schema-frontmatter-contract.md`, `specs/schema-pydantic-models.md`, `doc/03-data-mesh-enrichment.md`, `architecture/ADR-001-data-flow-topology.md`

Este documento define a extensao do modelo de dados do Vibe-Ops Data-Mesh com quatro novas entidades de planejamento — **Cycle**, **Wave**, **Phase**, **Habit** — mapeando-as a hierarquia existente e a todos os subsistemas downstream (Taskwarrior, Timewarrior, SQLite Analytics, fin_ops, DailyMetrics).

---

## 1. Entity Hierarchy Extension

### 1.1. Visao Geral: Duas Hierarquias + Duas Dimencoes Transversais

O sistema operara com **duas hierarquias principais** (estrategica e temporal) e **duas dimencoes transversais** (operacional e comportamental) que se cruzam via FKs e tags:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    🗺️  MAPA COMPLETO DE ENTIDADES                       │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  HIERARQUIA ESTRATEGICA (Goal-Oriented)                                 │
│  ──────────────────────────────────────────────────────────────────     │
│                                                                         │
│  Dream (S1) ──► Objective (O2) ──► Meta (M3) ──► Project (proj) ──► Task│
│   [Anual]        [Quarterly]       [Sprint]        [Weekly]      [Atom] │
│                                                                         │
│  HIERARQUIA TEMPORAL (Time-Boxed Containers)                            │
│  ──────────────────────────────────────────────────────────────────     │
│                                                                         │
│  Cycle (C1) ──► Wave (W2_Jul) ──► Meta (M3)  [CROSS-REFERENCE]        │
│   [4-12w]        [2w]                                                      │
│                                                                         │
│  DIMENSAO OPERACIONAL (Cross-Cutting Tags)                              │
│  ──────────────────────────────────────────────────────────────────     │
│                                                                         │
│  Phase: learn │ earn │ train │ share │ review  [Aplicado via tags]      │
│   [DeepWork]   [Labor] [Training] [Content] [DataReview]                │
│                                                                         │
│  DIMENSAO COMPORTAMENTAL (Parallel Tracking)                            │
│  ──────────────────────────────────────────────────────────────────     │
│                                                                         │
│  Habit (habit_*)  [Recorrente, independente de Tasks]                   │
│   [Workout] [Reading] [Meditation] [Review]                             │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 1.2. Relacionamento Detalhado

| Entidade | Tipo | Posicao na Hierarquia | Relacao com Existentes |
|:---------|:-----|:----------------------|:-----------------------|
| **Cycle** | Container Temporal | Acima de Wave, paralelo a Objective | `Cycle.parent_objective` (FK opcional), `Cycle.parent_dream` (FK opcional) |
| **Wave** | Container Temporal | Acima de Meta, filho de Cycle | `Wave.cycle` (FK obrigatoria), `Wave.quarter` (string), referenciado por `Meta.wave` (FK) |
| **Phase** | Dimensao Operacional | Cross-cutting (aplicada via tags) | Referenciado por `Task.tags`, `TimewarriorInterval.tags`, `Habit.linked_phase` |
| **Habit** | Entidade Paralela | Fora da hierarquia de entregaveis | `Habit.linked_phase` (FK opcional), `Habit.linked_dream` (FK opcional), rastreado via Timewarrior |

### 1.3. Regra de Cruzamento

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    🔗  REGRAS DE INTEGRIDADE CRUZADA                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  1. Toda Meta DEVE pertencer a uma Wave (Meta.wave → Wave.id)          │
│  2. Toda Wave DEVE pertencer a um Cycle (Wave.cycle → Cycle.id)        │
│  3. Todo Cycle DEVE estar contido em um Quarter (Cycle.start_date)     │
│  4. Todo Project herda a Wave de sua Meta (cascata)                    │
│  5. Todo Task herda a Phase via tags (classificacao operacional)       │
│  6. Todo Habit PODE linkar a uma Phase (Habit.linked_phase)            │
│  7. Todo intervalo Timewarrior DEVE ter uma phase tag                  │
│                                                                         │
│  VALIDACOES DO PIPELINE:                                                │
│  ✅ Cycle.start_date < Cycle.end_date                                    │
│  ✅ Wave.start_date < Wave.end_date                                      │
│  ✅ Wave.cycle existe no registro de Cycles                            │
│  ✅ Meta.wave existe e esta ativa                                        │
│  ✅ Phase.id esta no vocabulario controlado                            │
│  ✅ Habit.frequency e coerente com custom_days                         │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Frontmatter Schemas (YAML)

### 2.1. Convenções de Nomenclatura (Extensao)

| Campo | Formato | Exemplos |
|:------|:--------|:---------|
| `id` (Cycle) | `C` + numero inteiro | `C1`, `C2`, `C15` |
| `id` (Wave) | `W[N]_` + Mmm_YYYY | `W2_Jul_2026`, `W1_Jan_2027` |
| `id` (Phase) | `phase_` + snake_case | `phase_learn`, `phase_earn` |
| `id` (Habit) | `habit_` + snake_case | `habit_morning_workout`, `habit_daily_review` |
| `cycle_type` | enum string | `fundamentacao`, `busca`, `hackathon`, `consolidacao`, `execucao` |
| `frequency` | enum string | `daily`, `weekly`, `weekdays`, `weekends`, `custom` |
| `tracking_type` | enum string | `binary`, `duration`, `count`, `scale` |

### 2.2. Cycle (`entity_type: "cycle"`)

```yaml
---
# ═══════════════════════════════════════════════════
# CAMPOS OBRIGATORIOS
# ═══════════════════════════════════════════════════
id: "C1"
title: "Fase de Fundamentacao Tecnica"
entity_type: "cycle"
status: "active"                     # active | paused | completed | archived
created: "2026-07-01"

# ═══════════════════════════════════════════════════
# CAMPOS ESPECIFICOS DO CYCLE
# ═══════════════════════════════════════════════════
cycle_type: "fundamentacao"          # fundamentacao | busca | hackathon | consolidacao | execucao
start_date: "2026-07-01"             # Inicio do ciclo (ISO 8601)
end_date: "2026-09-30"               # Termino do ciclo (ISO 8601)
quarter: "Q3_2026"                   # Quarter de abrangencia

# FKs opcionais (pelo menos uma deve ser preenchida)
parent_objective: "O2"               # FK → ObjectiveEntity.id (opcional)
parent_dream: "S1"                   # FK → DreamEntity.id (opcional)

# Foco estrategico: qual vetor IKIGAi este ciclo privilegia
ikigai_focus: "skill"                # passion | skill | market | revenue

# Distribuicao alvo de horas por fase (setpoints)
phase_targets:
  phase_learn: 120                   # horas totais no ciclo
  phase_earn: 60
  phase_train: 30
  phase_share: 20
  phase_review: 10

# Campo computado (gerado pelo pipeline, NAO editado manualmente):
# total_target_hours: 240             # SUM(phase_targets.values())
# wave_count: 6                       # COUNT(Wave where wave.cycle == C1)
# completion_pct: 0.0                 # Computado no reverse sync

# ═══════════════════════════════════════════════════
# CAMPOS OPCIONAIS
# ═══════════════════════════════════════════════════
tags: ["backend", "fundamentos", "sprint_zero"]
notes: "Ciclo focado em algoritmos, estruturas de dados e fundamentos de IA"
---
```

### 2.3. Wave (`entity_type: "wave"`)

```yaml
---
# ═══════════════════════════════════════════════════
# CAMPOS OBRIGATORIOS
# ═══════════════════════════════════════════════════
id: "W2_Jul_2026"
title: "Wave 2 — API REST e Autenticacao"
entity_type: "wave"
status: "active"                     # active | planned | completed | archived
created: "2026-07-15"

# ═══════════════════════════════════════════════════
# CAMPOS ESPECIFICOS DA WAVE
# ═══════════════════════════════════════════════════
cycle: "C1"                          # FK → Cycle.id (OBRIGATORIO)
quarter: "Q3_2026"                   # Quarter de abrangencia
start_date: "2026-07-15"             # Inicio da wave (ISO 8601)
end_date: "2026-07-28"               # Termino da wave (ISO 8601)

# Capacidade e alocacao
capacity_hours: 60.0                 # Horas liquidas disponiveis (setpoint)
# allocated_hours: 45.0              # COMPUTADO: SUM(Meta.estimated_hours where meta.wave == W2_Jul_2026)
# remaining_hours: 15.0             # COMPUTADO: capacity_hours - allocated_hours

# Distribuicao alvo de horas por fase (setpoints para esta wave)
phase_distribution:
  phase_learn: 20.0
  phase_earn: 25.0
  phase_train: 7.5
  phase_share: 5.0
  phase_review: 2.5

# Campo computado (gerado pelo pipeline):
# meta_count: 3                      # COUNT(Meta where meta.wave == W2_Jul_2026)
# project_count: 5                   # COUNT(Project via Meta cascade)
# task_count: 12                     # COUNT(Task via Project cascade)
# burndown_velocity: 0.0             # COMPUTADO: tasks_completed / dias_decorridos

# ═══════════════════════════════════════════════════
# CAMPOS OPCIONAIS
# ═══════════════════════════════════════════════════
tags: ["api", "jwt", "sprint"]
notes: "Wave focada em completar o modulo de autenticacao do portfolio"
---
```

### 2.4. Phase (`entity_type: "phase"`)

```yaml
---
# ═══════════════════════════════════════════════════
# CAMPOS OBRIGATORIOS
# ═══════════════════════════════════════════════════
id: "phase_learn"
title: "Deep Work — Build to Learn"
entity_type: "phase"
status: "active"                     # active | deprecated

# ═══════════════════════════════════════════════════
# CAMPOS ESPECIFICOS DA PHASE
# ═══════════════════════════════════════════════════
ikigai_vector: "skill"               # passion | skill | market | revenue
phase_code: "learn"                  # Codigo curto para tags: learn | earn | train | share | review

# Time-blocking default (pode ser sobrescrito pelo Hypervisor)
time_block_default:
  start: "04:45"
  end: "06:15"
setpoint_minutes: 90                 # Duracao alvo em minutos por sessao

# Contexto de aplicacao
day_type: "both"                     # curso | livre | both (quando esta phase se aplica)
context_tags: ["@vscode", "@terminal"] # Tags de contexto operacional recomendadas

# Regras de negocio para o Hypervisor
hypervisor_rules:
  min_energy_required: 6             # Energia minima (1-10) para alocar esta phase
  max_daily_sessions: 2              # Maximo de sessoes por dia
  recovery_cost: 10                  # Minutos de pausa obrigatoria apos sessao

# Campo computado:
# total_hours_this_week: 0.0         # COMPUTADO: SUM(timewarrior intervals with +phase.learn)
# avg_session_duration: 0.0          # COMPUTADO: media de duracao das sessoes

# ═══════════════════════════════════════════════════
# CAMPOS OPCIONAIS
# ═══════════════════════════════════════════════════
tags: ["deep_work", "estudo", "fundamentos"]
notes: "Fase de aprendizado denso. Requer ambiente silencioso e VS Code aberto."
---
```

### 2.5. Habit (`entity_type: "habit"`)

```yaml
---
# ═══════════════════════════════════════════════════
# CAMPOS OBRIGATORIOS
# ═══════════════════════════════════════════════════
id: "habit_morning_workout"
title: "Treino Matinal"
entity_type: "habit"
status: "active"                     # active | paused | archived
created: "2026-01-15"

# ═══════════════════════════════════════════════════
# CAMPOS ESPECIFICOS DO HABIT
# ═══════════════════════════════════════════════════
frequency: "weekdays"                # daily | weekly | weekdays | weekends | custom
custom_days: [0, 1, 2, 3, 4]        # 0=Dom, 1=Seg... (apenas se frequency=custom)

# Trigger e contexto
trigger_context: "after_wakeup"      # after_wakeup | before_sleep | after_meal | scheduled | ad_hoc
scheduled_time: "05:00"              # HH:MM (apenas se trigger_context=scheduled)

# Links opcionais
linked_phase: "phase_train"          # FK → Phase.id (opcional)
linked_dream: "S1"                   # FK → Dream.id (opcional)

# Configuracao de tracking
tracking_type: "duration"            # binary | duration | count | scale
target_value: 60.0                   # Meta de valor (1 para binary, minutos para duration, etc.)
target_unit: "minutes"               # minutes | repetitions | score

# Tags para Timewarrior (injetadas automaticamente)
tw_tags: ["habit.morning_workout", "phase.train", "health"]

# Configuracao de streak
streak_config:
  grace_period_days: 1               # Dias de tolerancia antes de quebrar streak
  min_success_rate: 0.8              # Taxa minima para manter streak (80%)

# Campos computados (gerados pelo pipeline, NAO editados):
# streak_current: 12                 # COMPUTADO: dias consecutivos cumpridos
# streak_best: 21                    # COMPUTADO: recorde historico
# success_rate_7d: 0.857             # COMPUTADO: 6/7 dias cumpridos
# success_rate_30d: 0.833            # COMPUTADO: 25/30 dias cumpridos
# last_completed: "2026-05-08"       # COMPUTADO: ultima data de cumprimento

# ═══════════════════════════════════════════════════
# CAMPOS OPCIONAIS
# ═══════════════════════════════════════════════════
tags: ["calistenia", "cardio", "saude"]
notes: "Treino de forca e cardio logo apos acordar. Minimo 45min para contar."
---
```

---

## 3. Pydantic Models (Python)

### 3.1. Enums de Suporte

```python
from enum import Enum

class CycleType(str, Enum):
    FUNDAMENTACAO = "fundamentacao"
    BUSCA = "busca"
    HACKATHON = "hackathon"
    CONSOLIDACAO = "consolidacao"
    EXECUCAO = "execucao"

class PhaseCode(str, Enum):
    LEARN = "learn"
    EARN = "earn"
    TRAIN = "train"
    SHARE = "share"
    REVIEW = "review"

class HabitFrequency(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    WEEKDAYS = "weekdays"
    WEEKENDS = "weekends"
    CUSTOM = "custom"

class HabitTrackingType(str, Enum):
    BINARY = "binary"       # Fez/nao fez
    DURATION = "duration"   # Minutos
    COUNT = "count"         # Repeticoes
    SCALE = "scale"         # Nota 1-10

class HabitTriggerContext(str, Enum):
    AFTER_WAKEUP = "after_wakeup"
    BEFORE_SLEEP = "before_sleep"
    AFTER_MEAL = "after_meal"
    SCHEDULED = "scheduled"
    AD_HOC = "ad_hoc"
```

### 3.2. PhaseTargets — Distribuicao de Horas por Fase

```python
from pydantic import BaseModel, Field, field_validator
from typing import Dict

class PhaseTargets(BaseModel):
    """
    Distribuicao de horas alvo por fase IKIGAi.
    Usado em Cycle e Wave para definir setpoints.
    """
    phase_learn: float = Field(ge=0, default=0.0, description="Horas alvo: Deep Work / Build to Learn")
    phase_earn: float = Field(ge=0, default=0.0, description="Horas alvo: Laborative / Build to Earn")
    phase_train: float = Field(ge=0, default=0.0, description="Horas alvo: Training / Reset de Cache")
    phase_share: float = Field(ge=0, default=0.0, description="Horas alvo: Content Lab / Documentar")
    phase_review: float = Field(ge=0, default=0.0, description="Horas alvo: Data Review / Analise")

    @field_validator('phase_learn', 'phase_earn', 'phase_train', 'phase_share', 'phase_review')
    @classmethod
    def validate_non_negative(cls, v: float) -> float:
        if v < 0:
            raise ValueError("Horas de fase nao podem ser negativas")
        return v

    @computed_field
    @property
    def total_hours(self) -> float:
        """Soma total de horas alocadas."""
        return (
            self.phase_learn + self.phase_earn + self.phase_train +
            self.phase_share + self.phase_review
        )

    @computed_field
    @property
    def distribution_pct(self) -> Dict[str, float]:
        """Distribuicao percentual por fase."""
        total = self.total_hours
        if total == 0:
            return {k: 0.0 for k in ['learn', 'earn', 'train', 'share', 'review']}
        return {
            'learn': round(self.phase_learn / total * 100, 1),
            'earn': round(self.phase_earn / total * 100, 1),
            'train': round(self.phase_train / total * 100, 1),
            'share': round(self.phase_share / total * 100, 1),
            'review': round(self.phase_review / total * 100, 1),
        }
```

### 3.3. CycleEntity — Ciclo Estrategico

```python
from datetime import date
from typing import Optional, List

class CycleEntity(BaseModel):
    """
    Ciclo estrategico: container temporal de 4-12 semanas.
    Exemplos: 'Fase de Fundamentacao', 'Sprint de Hackathon', 'Busca de Mercado'.
    Hierarquia: Cycle → Wave → Meta → Project → Task
    """
    id: str = Field(pattern=r'^C\d+$', description="ID unico: C1, C2, etc.")
    title: str = Field(min_length=5, max_length=200)
    entity_type: str = Field(default="cycle", pattern=r'^cycle$')
    status: str = Field(default="active", pattern=r'^(active|paused|completed|archived)$')
    created: date

    # Especificos do Cycle
    cycle_type: CycleType = Field(description="Tipo estrategico do ciclo")
    start_date: date
    end_date: date
    quarter: str = Field(pattern=r'^Q[1-4]_\d{4}$', description="Ex: Q3_2026")

    # FKs (pelo menos uma deve ser preenchida)
    parent_objective: Optional[str] = Field(
        default=None, pattern=r'^O\d+$', description="FK → ObjectiveEntity.id"
    )
    parent_dream: Optional[str] = Field(
        default=None, pattern=r'^S\d+$', description="FK → DreamEntity.id"
    )

    # Foco estrategico
    ikigai_focus: str = Field(
        default="skill", pattern=r'^(passion|skill|market|revenue)$'
    )
    phase_targets: PhaseTargets = Field(default_factory=PhaseTargets)

    tags: List[str] = Field(default_factory=list)

    # Validacao: start_date < end_date
    @field_validator('end_date')
    @classmethod
    def validate_date_range(cls, v: date, info) -> date:
        start = info.data.get('start_date')
        if start and v <= start:
            raise ValueError("end_date deve ser posterior a start_date")
        return v

    # Validacao: pelo menos uma FK pai deve existir
    @field_validator('parent_dream')
    @classmethod
    def validate_parent_chain(cls, v: Optional[str], info) -> Optional[str]:
        objective = info.data.get('parent_objective')
        dream = v
        if not objective and not dream:
            raise ValueError("Cycle deve ter parent_objective ou parent_dream (pelo menos um)")
        return v

    @computed_field
    @property
    def duration_days(self) -> int:
        """Duracao do ciclo em dias."""
        return (self.end_date - self.start_date).days

    @computed_field
    @property
    def duration_weeks(self) -> float:
        """Duracao do ciclo em semanas (arredondado)."""
        return round(self.duration_days / 7, 1)

    @computed_field
    @property
    def total_target_hours(self) -> float:
        """Soma total de horas alvo (delegado para PhaseTargets)."""
        return self.phase_targets.total_hours

    @computed_field
    @property
    def tw_project_prefix(self) -> str:
        """
        Prefixo de projeto para Taskwarrior.
        Formato: C1 (usado como segmento em project hierarchies)
        """
        return self.id
```

### 3.4. WaveEntity — Onda Quinzenal

```python
class WaveEntity(BaseModel):
    """
    Wave quinzenal: container temporal de 2 semanas.
    Herda o ciclo estrategico e contem Metas/Sprints.
    Hierarquia: Cycle → Wave → Meta → Project → Task
    """
    id: str = Field(
        pattern=r'^W\d+_[A-Z][a-z]{2}_\d{4}$',
        description="ID unico: W2_Jul_2026, W1_Jan_2027"
    )
    title: str = Field(min_length=5, max_length=200)
    entity_type: str = Field(default="wave", pattern=r'^wave$')
    status: str = Field(default="active", pattern=r'^(active|planned|completed|archived)$')
    created: date

    # FK obrigatoria
    cycle: str = Field(pattern=r'^C\d+$', description="FK → CycleEntity.id")
    quarter: str = Field(pattern=r'^Q[1-4]_\d{4}$', description="Ex: Q3_2026")

    # Time-boxing
    start_date: date
    end_date: date
    capacity_hours: float = Field(ge=1, le=200, description="Horas liquidas disponiveis")

    # Distribuicao de fases (setpoints para esta wave)
    phase_distribution: PhaseTargets = Field(default_factory=PhaseTargets)

    tags: List[str] = Field(default_factory=list)

    @field_validator('end_date')
    @classmethod
    def validate_date_range(cls, v: date, info) -> date:
        start = info.data.get('start_date')
        if start and v <= start:
            raise ValueError("end_date deve ser posterior a start_date")
        return v

    @field_validator('capacity_hours')
    @classmethod
    def validate_capacity(cls, v: float) -> float:
        if v > 120:
            # Alerta: mais de 120h em 2 semanas = 60h/semana, risco de burnout
            # Nao bloqueia, mas o pipeline pode emitir warning
            pass
        return v

    @computed_field
    @property
    def duration_days(self) -> int:
        """Duracao da wave em dias (esperado: 14)."""
        return (self.end_date - self.start_date).days

    @computed_field
    @property
    def allocated_hours(self) -> float:
        """
        COMPUTADO NO PIPELINE: soma de Meta.estimated_hours onde meta.wave == self.id.
        Valor padrao 0.0 ate o pipeline calcular.
        """
        # Este campo e enriquecido pelo pipeline durante FK resolution
        return 0.0  # Placeholder — pipeline sobrescreve

    @computed_field
    @property
    def remaining_hours(self) -> float:
        """Horas nao alocadas na wave."""
        return self.capacity_hours - self.allocated_hours

    @computed_field
    @property
    def utilization_rate(self) -> float:
        """Taxa de utilizacao da capacidade (0.0 a 1.0+)."""
        if self.capacity_hours == 0:
            return 0.0
        return round(self.allocated_hours / self.capacity_hours, 3)

    @computed_field
    @property
    def tw_project_key(self) -> str:
        """
        Chave de projeto para Taskwarrior.
        Formato: C1.W2_Jul_2026 (concatena cycle + wave)
        """
        return f"{self.cycle}.{self.id}"
```

### 3.5. PhaseEntity — Fase Operacional

```python
class TimeBlock(BaseModel):
    """Bloco de horario para time-blocking."""
    start: str = Field(pattern=r'^\d{2}:\d{2}$', description="HH:MM")
    end: str = Field(pattern=r'^\d{2}:\d{2}$', description="HH:MM")

    @field_validator('end')
    @classmethod
    def validate_time_order(cls, v: str, info) -> str:
        start = info.data.get('start')
        if start and v <= start:
            raise ValueError("Horario de fim deve ser posterior ao inicio")
        return v

    @property
    def duration_minutes(self) -> int:
        """Duracao do bloco em minutos."""
        from datetime import datetime
        fmt = "%H:%M"
        s = datetime.strptime(self.start, fmt)
        e = datetime.strptime(self.end, fmt)
        delta = e - s
        return int(delta.total_seconds() / 60)


class HypervisorRules(BaseModel):
    """Regras do Hypervisor para alocacao de phase."""
    min_energy_required: int = Field(ge=1, le=10, default=5)
    max_daily_sessions: int = Field(ge=1, le=10, default=3)
    recovery_cost: int = Field(ge=0, le=60, default=10, description="Minutos de pausa obrigatoria")


class PhaseEntity(BaseModel):
    """
    Fase operacional: dimensao cross-cutting de classificacao de tempo.
    NAO e container — e uma etiqueta operacional com metadados ricos.
    Aplicada via tags em Tasks e Timewarrior intervals.
    """
    id: str = Field(
        pattern=r'^phase_(learn|earn|train|share|review)$',
        description="ID controlado: phase_learn, phase_earn, etc."
    )
    title: str = Field(min_length=5, max_length=200)
    entity_type: str = Field(default="phase", pattern=r'^phase$')
    status: str = Field(default="active", pattern=r'^(active|deprecated)$')

    # Mapeamento IKIGAi
    ikigai_vector: str = Field(
        pattern=r'^(passion|skill|market|revenue)$',
        description="Vetor IKIGAi associado"
    )
    phase_code: PhaseCode = Field(description="Codigo curto para tags")

    # Time-blocking
    time_block_default: Optional[TimeBlock] = None
    setpoint_minutes: int = Field(ge=15, le=480, default=90, description="Duracao alvo em minutos")

    # Contexto
    day_type: str = Field(
        default="both", pattern=r'^(curso|livre|both)$',
        description="Tipo de dia onde se aplica"
    )
    context_tags: List[str] = Field(
        default_factory=list,
        description="Tags de contexto operacional recomendadas (@vscode, etc.)"
    )

    # Regras do Hypervisor
    hypervisor_rules: HypervisorRules = Field(default_factory=HypervisorRules)

    tags: List[str] = Field(default_factory=list)

    @field_validator('context_tags')
    @classmethod
    def validate_context_tags(cls, v: List[str]) -> List[str]:
        for tag in v:
            if tag.startswith('@') and ' ' in tag:
                raise ValueError(f"Tags de contexto nao podem ter espacos: {tag}")
        return v

    @computed_field
    @property
    def tw_tag(self) -> str:
        """Tag do Timewarrior para esta phase."""
        return f"phase.{self.phase_code.value}"

    @computed_field
    @property
    def ikigai_emoji(self) -> str:
        """Emoji representativo do vetor IKIGAi."""
        mapping = {
            "passion": "❤️",
            "skill": "💼",
            "market": "🎯",
            "revenue": "💰"
        }
        return mapping.get(self.ikigai_vector, "📊")
```

### 3.6. HabitEntity — Habito Recorrente

```python
class StreakConfig(BaseModel):
    """Configuracao de streak para um habito."""
    grace_period_days: int = Field(ge=0, le=7, default=1)
    min_success_rate: float = Field(ge=0.0, le=1.0, default=0.8)


class HabitEntity(BaseModel):
    """
    Habito recorrente: entidade paralela a Task para rastreamento comportamental.
    Rastreado via Timewarrior com tags especificas, NAO e uma Task no TW.
    """
    id: str = Field(
        pattern=r'^habit_[a-z0-9_]+$',
        description="ID unico: habit_morning_workout, habit_daily_review"
    )
    title: str = Field(min_length=3, max_length=200)
    entity_type: str = Field(default="habit", pattern=r'^habit$')
    status: str = Field(default="active", pattern=r'^(active|paused|archived)$')
    created: date

    # Frequencia
    frequency: HabitFrequency = Field(description="Frequencia de execucao")
    custom_days: Optional[List[int]] = Field(
        default=None,
        description="Dias da semana (0=Dom, 6=Sab) se frequency=custom"
    )

    # Trigger e contexto
    trigger_context: HabitTriggerContext = Field(description="Gatilho de execucao")
    scheduled_time: Optional[str] = Field(
        default=None, pattern=r'^\d{2}:\d{2}$',
        description="Horario agendado HH:MM"
    )

    # Links opcionais
    linked_phase: Optional[str] = Field(
        default=None, pattern=r'^phase_(learn|earn|train|share|review)$',
        description="FK → PhaseEntity.id"
    )
    linked_dream: Optional[str] = Field(
        default=None, pattern=r'^S\d+$',
        description="FK → DreamEntity.id"
    )

    # Tracking
    tracking_type: HabitTrackingType = Field(description="Tipo de metrica")
    target_value: float = Field(gt=0, description="Meta de valor")
    target_unit: str = Field(
        default="minutes", pattern=r'^(minutes|repetitions|score)$'
    )

    # Tags para Timewarrior
    tw_tags: List[str] = Field(
        default_factory=list,
        description="Tags injetadas no Timewarrior ao rastrear"
    )

    # Streak
    streak_config: StreakConfig = Field(default_factory=StreakConfig)

    tags: List[str] = Field(default_factory=list)

    @field_validator('custom_days')
    @classmethod
    def validate_custom_days(cls, v: Optional[List[int]], info) -> Optional[List[int]]:
        freq = info.data.get('frequency')
        if freq == HabitFrequency.CUSTOM and (not v or len(v) == 0):
            raise ValueError("custom_days e obrigatorio quando frequency='custom'")
        if v:
            for day in v:
                if day < 0 or day > 6:
                    raise ValueError(f"Dia da semana invalido: {day} (deve ser 0-6)")
        return v

    @field_validator('scheduled_time')
    @classmethod
    def validate_scheduled_time(cls, v: Optional[str], info) -> Optional[str]:
        trigger = info.data.get('trigger_context')
        if trigger == HabitTriggerContext.SCHEDULED and not v:
            raise ValueError("scheduled_time e obrigatorio quando trigger_context='scheduled'")
        return v

    @field_validator('tw_tags')
    @classmethod
    def validate_tw_tags(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError("tw_tags nao pode estar vazio — precisa de pelo menos uma tag para Timewarrior")
        # Primeira tag deve ser habit.<id>
        habit_tag = f"habit.{v[0].replace('habit.', '')}" if v else ""
        return v

    @computed_field
    @property
    def primary_tw_tag(self) -> str:
        """Tag principal do habito para Timewarrior."""
        return f"habit.{self.id.replace('habit_', '')}"

    @computed_field
    @property
    def expected_sessions_per_week(self) -> int:
        """Numero esperado de sessoes por semana."""
        mapping = {
            HabitFrequency.DAILY: 7,
            HabitFrequency.WEEKLY: 1,
            HabitFrequency.WEEKDAYS: 5,
            HabitFrequency.WEEKENDS: 2,
            HabitFrequency.CUSTOM: len(self.custom_days or []),
        }
        return mapping.get(self.frequency, 0)

    @computed_field
    @property
    def is_binary(self) -> bool:
        """True se o habito e do tipo binario (fez/nao fez)."""
        return self.tracking_type == HabitTrackingType.BINARY
```

### 3.7. Modelos de Transporte Estendidos

```python
class TaskPayloadExtended(TaskPayload):
    """
    Extensao do TaskPayload com campos das novas entidades.
    Herda de TaskPayload (schema-pydantic-models.md) e adiciona:
    - wave: Wave.id para rastreamento temporal
    - cycle: Cycle.id para rastreamento estrategico
    - phase: Phase.tw_tag para classificacao operacional
    - habit_tag: tag de habito (se task for derivada de habito)
    """
    wave: Optional[str] = Field(
        default=None, pattern=r'^W\d+_[A-Z][a-z]{2}_\d{4}$',
        description="FK → WaveEntity.id"
    )
    cycle: Optional[str] = Field(
        default=None, pattern=r'^C\d+$',
        description="FK → CycleEntity.id"
    )
    phase: Optional[str] = Field(
        default=None, pattern=r'^phase\.(learn|earn|train|share|review)$',
        description="Tag de phase injetada"
    )
    habit_tag: Optional[str] = Field(
        default=None, pattern=r'^habit\.[a-z0-9_]+$',
        description="Tag de habito (se aplicavel)"
    )

    # UDA customizado para tracking de fase no TW
    phase_uda: Optional[str] = Field(
        default=None, description="UDA 'phase' no Taskwarrior"
    )
```

---

## 4. Pipeline Integration Spec

### 4.1. Push Pipeline (Markdown → Taskwarrior)

#### 4.1.1. Compilacao por Tipo de Entidade

| Entidade | Compila para TW? | Forma no TW | Project Key | Tags Injetadas | UDAs Injetadas |
|:---------|:-----------------|:------------|:------------|:---------------|:---------------|
| **Cycle** | NAO | Container puro | — | — | — |
| **Wave** | NAO | Container puro | — | — | — |
| **Phase** | NAO | Classificacao via tags | — | `+phase.{code}` | — |
| **Habit** | SIM | Recurring Task (template) | `habits` | `+habit.{id}` `+phase.{code}` | `recurrence:` `size:` |
| **Meta** | SIM (ja existente) | Task agrupadora | `{dream}.{objective}.{meta}` | `+sprint` | `wave:` `upstream_id:` |
| **Project** | SIM (ja existente) | Task agrupadora | `{dream}.{objective}.{meta}.{project}` | `+epic` | `size:` `upstream_id:` |
| **Task** | SIM (ja existente) | Task atomica | herda do Project | herda + contexto | `size:` `upstream_id:` `phase:` |

#### 4.1.2. Regras de Heranca de Phase

```python
# Pseudocodigo do pipeline — determinacao de phase tag para Task

def resolve_phase_tag(task: TaskEntity, project: ProjectEntity, meta: MetaEntity) -> str:
    """
    Resolve a phase tag para uma task baseado na hierarquia.
    Prioridade (maior para menor):
    1. Tag explicita no corpo da task (e.g., [phase:learn])
    2. Phase inferida do dominio tecnico (e.g., 'backend' → phase:earn)
    3. Phase padrao da Meta (via Meta.tags)
    4. Phase padrao do projeto (via Project.tags)
    5. Fallback: phase:earn (Build to Earn como padrao)
    """
    # 1. Tag explicita no corpo do markdown
    explicit = extract_phase_from_markdown(task.raw_body)
    if explicit:
        return f"phase.{explicit}"

    # 2. Mapeamento por dominio tecnico
    domain_map = {
        "study": "learn",
        "reading": "learn",
        "backend": "earn",
        "frontend": "earn",
        "devops": "earn",
        "content": "share",
        "writing": "share",
        "review": "review",
        "workout": "train",
        "meditation": "train",
    }
    for tag in task.tags:
        if tag in domain_map:
            return f"phase.{domain_map[tag]}"

    # 3. Phase da Meta
    for tag in meta.tags:
        if tag.startswith("phase:"):
            return tag.replace(":", ".")

    # 4. Phase do Project
    for tag in project.tags:
        if tag.startswith("phase:"):
            return tag.replace(":", ".")

    # 5. Fallback
    return "phase.earn"
```

#### 4.1.3. Geracao de TW Project Keys (Completo)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    🔑  HIERARQUIA DE PROJECT KEYS TW                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Nivel 1 — Dream:          S1                                          │
│  Nivel 2 — Objective:      S1.O2                                       │
│  Nivel 3 — Cycle:          S1.O2.C1          (NOVO — opcional)         │
│  Nivel 4 — Wave:           S1.O2.C1.W2_Jul_2026  (NOVO — opcional)    │
│  Nivel 5 — Meta:           S1.O2.M3                                    │
│  Nivel 6 — Project:        S1.O2.M3.proj_alfa_01                       │
│  Nivel 7 — Task:           herda project do pai                        │
│                                                                         │
│  REGRAS:                                                                │
│  • Cycle e Wave sao OPCIONAIS na chave (configuravel no pipeline)      │
│  • Chave padrao (compatibilidade): S1.O2.M3.proj_alfa_01               │
│  • Chave estendida: S1.O2.C1.W2_Jul_2026.M3.proj_alfa_01               │
│  • Habit tasks usam project:habits (projeto isolado)                   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

#### 4.1.4. Injetor de Habitos no TW

```python
# Pseudocodigo — criacao de recurring tasks para habitos

def compile_habit_to_tw(habit: HabitEntity) -> TaskPayloadExtended:
    """
    Compila um Habit em uma recurring task no Taskwarrior.
    """
    # Determina recorrencia
    recurrence_map = {
        HabitFrequency.DAILY: "daily",
        HabitFrequency.WEEKLY: "weekly",
        HabitFrequency.WEEKDAYS: "mon,tue,wed,thu,fri",
        HabitFrequency.WEEKENDS: "sat,sun",
        HabitFrequency.CUSTOM: format_custom_days(habit.custom_days),
    }
    recurrence = recurrence_map.get(habit.frequency, "daily")

    # Monta tags
    tags = [habit.primary_tw_tag]
    if habit.linked_phase:
        tags.append(PhaseEntity(id=habit.linked_phase).tw_tag)
    tags.extend(habit.tw_tags)
    tags.extend(habit.tags)
    tags = list(set(tags))  # deduplica

    # Monta UDA phase
    phase_uda = habit.linked_phase.replace("phase_", "") if habit.linked_phase else "train"

    return TaskPayloadExtended(
        description=habit.title,
        project="habits",
        tags=tags,
        priority="M",  # Habits sao medium priority por padrao
        recurrence=recurrence,
        size=f"{habit.target_value}m" if habit.tracking_type == HabitTrackingType.DURATION else "1",
        phase_uda=phase_uda,
        upstream_id=TaskPayload.generate_upstream_id(habit.id, 0),
    )
```

### 4.2. Reverse Sync (TW → Analytics)

#### 4.2.1. Extracao de Dados por Entidade

| Fonte | Dados Extraidos | Filtros | JOIN Key |
|:------|:----------------|:--------|:---------|
| **TW Export** | Tasks com `project:habits` | `status:completed` ou `status:pending` | `upstream_id` → HabitEntity |
| **TW Export** | Tasks com `+phase.*` | todas | `upstream_id` → ProjectEntity → MetaEntity |
| **Timewarrior** | Intervals com `+phase.*` | `start >= wave.start_date` | tags → PhaseEntity |
| **Timewarrior** | Intervals com `+habit.*` | todas | tags → HabitEntity |
| **TW Export** | Tasks completadas por wave | `end >= wave.start_date AND end <= wave.end_date` | `upstream_id` → MetaEntity.wave |

#### 4.2.2. Logica de JOIN

```sql
-- Pseudocodigo SQL dos JOINs do Reverse Sync

-- 1. Horas por Phase (diario)
SELECT
    DATE(ti.start) as date,
    p.phase_code,
    p.ikigai_vector,
    SUM(ti.duration_minutes) / 60.0 as hours
FROM timewarrior_intervals ti
JOIN phases p ON ti.tags LIKE '%phase.' || p.phase_code || '%'
WHERE DATE(ti.start) = :target_date
GROUP BY DATE(ti.start), p.phase_code;

-- 2. Progresso de Habit (diario)
SELECT
    h.id as habit_id,
    h.title,
    DATE(ti.start) as date,
    COUNT(*) as sessions,
    SUM(ti.duration_minutes) as total_minutes,
    CASE
        WHEN h.tracking_type = 'binary' AND COUNT(*) > 0 THEN 1
        WHEN h.tracking_type = 'duration' AND SUM(ti.duration_minutes) >= h.target_value THEN 1
        ELSE 0
    END as completed
FROM habits h
JOIN timewarrior_intervals ti ON ti.tags LIKE '%' || h.primary_tw_tag || '%'
WHERE DATE(ti.start) = :target_date
GROUP BY h.id, DATE(ti.start);

-- 3. Progresso de Wave
SELECT
    w.id as wave_id,
    w.cycle,
    COUNT(DISTINCT t.uuid) as tasks_total,
    COUNT(DISTINCT CASE WHEN t.status = 'completed' THEN t.uuid END) as tasks_completed,
    SUM(CASE WHEN t.status = 'completed' THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as completion_pct,
    SUM(ti.duration_minutes) / 60.0 as hours_logged
FROM waves w
LEFT JOIN metas m ON m.wave = w.id
LEFT JOIN projects p ON p.parent_meta = m.id
LEFT JOIN tasks t ON t.project LIKE p.tw_project_key || '%'
LEFT JOIN timewarrior_intervals ti ON ti.tags LIKE '%' || w.id || '%'
WHERE w.status = 'active'
GROUP BY w.id;
```

#### 4.2.3. Metricas Computadas

| Metrica | Formula | Granularidade |
|:--------|:--------|:--------------|
| `habit_compliance_rate` | `completed_days / expected_days` | Diario/Semanal/Mensal |
| `habit_streak_current` | `MAX(consecutive_completed_days)` | Atual |
| `phase_hour_distribution` | `hours_phase / total_hours` | Diario/Semanal |
| `wave_burndown_velocity` | `tasks_completed / days_elapsed` | Wave |
| `wave_utilization_rate` | `allocated_hours / capacity_hours` | Wave |
| `cycle_phase_alignment` | `actual_hours_phase / target_hours_phase` | Cycle |
| `ikigai_balance_score` | `1 - std_dev(phase_distribution_pct)` | Semanal |
| `energy_phase_correlation` | `CORR(energy_level, phase_hours)` | Diario (requere 7+ dias) |

---

## 5. Timewarrior Tag Taxonomy

### 5.1. Vocabulario Completo de Tags

#### 5.1.1. Phase Tags (OBRIGATORIAS para trabalho)

| Tag | Sintaxe TW | Significado | IKIGAi Vector | Bloco Default |
|:----|:-----------|:------------|:--------------|:--------------|
| Deep Work / Learn | `+phase.learn` | Estudo denso, leitura, teoria | 💼 Skill | 04:45-06:15 |
| Laborative / Earn | `+phase.earn` | Codigo, entregas, freelas | 💰 Revenue | 14:00-17:00 |
| Training / Reset | `+phase.train` | Treino fisico, meditacao | ❤️ Passion | 05:00-06:00 |
| Content Lab / Share | `+phase.share` | Documentar, posts, videos | 🎯 Market | 17:15-18:00 |
| Data Review | `+phase.review` | Analise de metricas, weekly | 📊 Missao | 18:00-18:15 |

#### 5.1.2. Habit Tracking Tags

| Padrao | Exemplo | Significado |
|:-------|:--------|:------------|
| `habit.{habit_id}` | `+habit.morning_workout` | Tag principal do habito |
| `habit.{habit_id}.done` | `+habit.morning_workout.done` | Marcador de conclusao (hook) |
| `habit.{habit_id}.skipped` | `+habit.morning_workout.skipped` | Marcador de skip |

#### 5.1.3. Study Session Tags

| Tag | Contexto | Usar Com |
|:----|:---------|:---------|
| `+study.reading` | Leitura de livros/artigos | `+phase.learn` |
| `+study.coding` | Pratica de programacao | `+phase.learn` |
| `+study.algorithms` | Estudo de algoritmos | `+phase.learn` |
| `+study.system_design` | Design de sistemas | `+phase.learn` |
| `+study.writing` | Escrita tecnica | `+phase.share` |
| `+study.review` | Revisao de material | `+phase.review` |

#### 5.1.4. Energy / Focus State Tags

| Tag | Significado | Quando Usar |
|:----|:------------|:------------|
| `+energy.high` | Energia 8-10 | Inicio do dia, pos-cafe |
| `+energy.medium` | Energia 5-7 | Meio do dia |
| `+energy.low` | Energia 1-4 | Fim do dia, pre-sono |
| `+focus.deep` | Foco profundo (50min+) | Sessoes longas sem interrupcao |
| `+focus.shallow` | Foco raso (tarefas admin) | Email, mensagens, organizacao |
| `+flow.state` | Estado de flow detectado | Quando perdeu nocao do tempo |

#### 5.1.5. Contexto Operacional (Prefixo `@`)

| Tag | Significado |
|:----|:------------|
| `+@vscode` | Trabalho no editor |
| `+@terminal` | Trabalho em CLI |
| `+@obsidian` | Documentacao |
| `+@browser` | Pesquisa/web |
| `+@wsl` | Ambiente Linux |
| `+@mobile` | Smartphone |

### 5.2. Regras de Heranca e Composicao

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    🏷️  REGRAS DE COMPOSICAO DE TAGS                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  REGRA 1: OBRIGATORIEDADE                                               │
│  ──────────────────────────────────────────────────────────────────     │
│  Todo intervalo de trabalho (nao-habito) DEVE ter EXATAMENTE UMA       │
│  phase tag: +phase.learn, +phase.earn, +phase.train, +phase.share,     │
│  ou +phase.review.                                                      │
│                                                                         │
│  REGRA 2: HERANCA DE HABITO                                             │
│  ──────────────────────────────────────────────────────────────────     │
│  Todo intervalo de habito DEVE ter a tag +habit.{id} e PODE ter        │
│  uma phase tag herdada de Habit.linked_phase.                            │
│  Ex: habit_morning_workout → tw_tags: ["habit.morning_workout",         │
│                                        "phase.train", "health"]         │
│                                                                         │
│  REGRA 3: COMPOSICAO DE ESTUDO                                          │
│  ──────────────────────────────────────────────────────────────────     │
│  Sessoes de estudo devem ter: phase tag + study tag + context tag       │
│  Ex: +phase.learn +study.algorithms +@vscode                            │
│                                                                         │
│  REGRA 4: ENERGIA (OPCIONAL)                                            │
│  ──────────────────────────────────────────────────────────────────     │
│  Tags de energia sao opcionais mas recomendadas. Maximo UMA por         │
│  intervalo.                                                             │
│                                                                         │
│  REGRA 5: FOCUS (OPCIONAL)                                              │
│  ──────────────────────────────────────────────────────────────────     │
│  Tags de foco sao opcionais. NAO usar +focus.deep em sessoes < 25min.   │
│                                                                         │
│  REGRA 6: PROIBICOES                                                    │
│  ──────────────────────────────────────────────────────────────────     │
│  • NUNCA usar duas phase tags no mesmo intervalo                        │
│  • NUNCA usar +phase.* em tarefas de kernel (sono, refeicoes)           │
│  • NUNCA usar +habit.* sem o habito correspondente estar registrado     │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 5.3. Exemplos de Composicao Validos

```bash
# Sessao de Deep Work (estudo de algoritmos)
timew start @vscode phase.learn study.algorithms energy.high

# Treino matinal (habito)
timew start habit.morning_workout phase.train health energy.medium

# Sessao laborativa (codigo de backend)
timew start @vscode phase.earn backend energy.high focus.deep

# Content Lab (escrita de post)
timew start @obsidian phase.share study.writing energy.medium

# Data Review (analise de metricas)
timew start @terminal phase.review energy.low
```

---

## 6. SQLite Analytics Schema

### 6.1. Tabela: habit_states

```sql
-- ═══════════════════════════════════════════════════
-- TABELA: habit_states
-- Proposito: Registro diario de cumprimento de habitos
-- Granularidade: 1 row por habito por dia
-- ═══════════════════════════════════════════════════

CREATE TABLE habit_states (
    -- Chave primaria composta
    habit_id        TEXT NOT NULL,           -- FK → habit registry (HabitEntity.id)
    date            DATE NOT NULL,           -- Data do registro

    -- Dados brutos (extraidos do Timewarrior)
    sessions_count  INTEGER DEFAULT 0,       -- Numero de sessoes no dia
    total_minutes   REAL DEFAULT 0.0,        -- Duracao total em minutos
    max_session_min REAL DEFAULT 0.0,        -- Duracao da sessao mais longa
    avg_session_min REAL DEFAULT 0.0,        -- Duracao media por sessao

    -- Classificacao de cumprimento
    target_value    REAL NOT NULL,           -- Meta do habito (copiado de HabitEntity)
    target_unit     TEXT NOT NULL,           -- minutes | repetitions | score
    actual_value    REAL DEFAULT 0.0,        -- Valor real alcancado
    completed       INTEGER DEFAULT 0,       -- 1 = cumprido, 0 = nao cumprido
    completion_pct  REAL DEFAULT 0.0,        -- actual_value / target_value

    -- Streak (computado)
    streak_before   INTEGER DEFAULT 0,       -- Streak antes deste dia
    streak_after    INTEGER DEFAULT 0,       -- Streak apos este dia
    streak_broken   INTEGER DEFAULT 0,       -- 1 = streak quebrou neste dia

    -- Metadados
    notes           TEXT,                    -- Anotacoes livres
    source_tags     TEXT,                    -- Tags do Timewarrior (JSON array)
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (habit_id, date),
    FOREIGN KEY (habit_id) REFERENCES habits(id) ON DELETE CASCADE
);

-- Indices
CREATE INDEX idx_habit_states_date ON habit_states(date);
CREATE INDEX idx_habit_states_completed ON habit_states(completed);
CREATE INDEX idx_habit_states_streak ON habit_states(streak_after DESC);
```

### 6.2. Tabela: wave_progress

```sql
-- ═══════════════════════════════════════════════════
-- TABELA: wave_progress
-- Proposito: Snapshot diario de progresso de waves
-- Granularidade: 1 row por wave por dia
-- ═══════════════════════════════════════════════════

CREATE TABLE wave_progress (
    -- Chave primaria composta
    wave_id         TEXT NOT NULL,           -- FK → WaveEntity.id
    date            DATE NOT NULL,           -- Data do snapshot

    -- Dados da wave (denormalizados para performance)
    cycle_id        TEXT NOT NULL,           -- FK → CycleEntity.id
    quarter         TEXT NOT NULL,           -- Q3_2026, etc.
    start_date      DATE NOT NULL,           -- Inicio da wave
    end_date        DATE NOT NULL,           -- Fim da wave
    capacity_hours  REAL NOT NULL,           -- Capacidade total

    -- Progresso de tasks (extraido do TW)
    tasks_total     INTEGER DEFAULT 0,       -- Total de tasks na wave
    tasks_pending   INTEGER DEFAULT 0,       -- Tasks pendentes
    tasks_completed INTEGER DEFAULT 0,       -- Tasks completadas
    tasks_deleted   INTEGER DEFAULT 0,       -- Tasks deletadas
    completion_pct  REAL DEFAULT 0.0,        -- tasks_completed / tasks_total

    -- Horas logadas (extraido do Timewarrior)
    hours_learn     REAL DEFAULT 0.0,        -- Horas em phase.learn
    hours_earn      REAL DEFAULT 0.0,        -- Horas em phase.earn
    hours_train     REAL DEFAULT 0.0,        -- Horas em phase.train
    hours_share     REAL DEFAULT 0.0,        -- Horas em phase.share
    hours_review    REAL DEFAULT 0.0,        -- Horas em phase.review
    hours_total     REAL DEFAULT 0.0,        -- SUM de todas as fases

    -- Metricas derivadas
    burndown_velocity REAL DEFAULT 0.0,      -- tasks_completed / dias_decorridos
    utilization_rate  REAL DEFAULT 0.0,      -- hours_total / capacity_hours
    phase_alignment   REAL DEFAULT 0.0,      -- Correlacao target vs actual

    -- Metadados
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (wave_id, date),
    FOREIGN KEY (wave_id) REFERENCES waves(id) ON DELETE CASCADE,
    FOREIGN KEY (cycle_id) REFERENCES cycles(id) ON DELETE CASCADE
);

-- Indices
CREATE INDEX idx_wave_progress_date ON wave_progress(date);
CREATE INDEX idx_wave_progress_cycle ON wave_progress(cycle_id);
CREATE INDEX idx_wave_progress_completion ON wave_progress(completion_pct);
```

### 6.3. Tabela: cycle_metrics

```sql
-- ═══════════════════════════════════════════════════
-- TABELA: cycle_metrics
-- Proposito: Metricas agregadas por ciclo
-- Granularidade: 1 row por ciclo (atualizado no fim do ciclo)
-- ═══════════════════════════════════════════════════

CREATE TABLE cycle_metrics (
    -- Chave
    cycle_id        TEXT PRIMARY KEY,        -- FK → CycleEntity.id

    -- Dados do ciclo (denormalizados)
    cycle_type      TEXT NOT NULL,           -- fundamentacao | busca | hackathon | ...
    start_date      DATE NOT NULL,
    end_date        DATE NOT NULL,
    quarter         TEXT NOT NULL,
    ikigai_focus    TEXT NOT NULL,           -- passion | skill | market | revenue

    -- Targets (copiados do CycleEntity.phase_targets)
    target_hours_learn  REAL DEFAULT 0.0,
    target_hours_earn   REAL DEFAULT 0.0,
    target_hours_train  REAL DEFAULT 0.0,
    target_hours_share  REAL DEFAULT 0.0,
    target_hours_review REAL DEFAULT 0.0,
    target_hours_total  REAL DEFAULT 0.0,

    -- Actuals (agregados das waves)
    actual_hours_learn  REAL DEFAULT 0.0,
    actual_hours_earn   REAL DEFAULT 0.0,
    actual_hours_train  REAL DEFAULT 0.0,
    actual_hours_share  REAL DEFAULT 0.0,
    actual_hours_review REAL DEFAULT 0.0,
    actual_hours_total  REAL DEFAULT 0.0,

    -- Variancia
    variance_learn      REAL DEFAULT 0.0,    -- actual - target
    variance_earn       REAL DEFAULT 0.0,
    variance_train      REAL DEFAULT 0.0,
    variance_share      REAL DEFAULT 0.0,
    variance_review     REAL DEFAULT 0.0,
    variance_total      REAL DEFAULT 0.0,

    -- Tasks
    tasks_total         INTEGER DEFAULT 0,
    tasks_completed     INTEGER DEFAULT 0,
    tasks_completion_pct REAL DEFAULT 0.0,

    -- Waves
    waves_total         INTEGER DEFAULT 0,
    waves_completed     INTEGER DEFAULT 0,

    -- IKIGAi score
    ikigai_alignment_score REAL DEFAULT 0.0, -- 0.0 a 1.0 (quanto mais proximo do target)

    -- Timestamp
    computed_at         DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (cycle_id) REFERENCES cycles(id) ON DELETE CASCADE
);

-- Indices
CREATE INDEX idx_cycle_metrics_type ON cycle_metrics(cycle_type);
CREATE INDEX idx_cycle_metrics_quarter ON cycle_metrics(quarter);
CREATE INDEX idx_cycle_metrics_ikigai ON cycle_metrics(ikigai_focus);
```

### 6.4. Tabela: daily_qhe

```sql
-- ═══════════════════════════════════════════════════
-- TABELA: daily_qhe (Quality of Health / Energy)
-- Proposito: Input manual matinal + dados computados
-- Granularidade: 1 row por dia
-- ═══════════════════════════════════════════════════

CREATE TABLE daily_qhe (
    -- Chave
    date            DATE PRIMARY KEY,

    -- Input manual (Morning Survey, 04:30h)
    sleep_hours     REAL,                    -- Horas de sono (6.5, 8.0, etc.)
    sleep_quality   INTEGER,                 -- 1-10 (subjetivo)
    energy_level    INTEGER,                 -- 1-10 (nivel inicial)
    mood_score      INTEGER,                 -- 1-10 (humor matinal)
    stress_level    INTEGER,                 -- 1-10 (1 = tranquilo)
    physical_state  TEXT,                    -- good | fair | poor | injured

    -- Inputs binarios
    had_coffee      INTEGER DEFAULT 0,       -- 1 = sim
    had_alcohol     INTEGER DEFAULT 0,       -- 1 = sim (noite anterior)
    took_meds       INTEGER DEFAULT 0,       -- 1 = sim

    -- Contexto do dia
    day_type        TEXT DEFAULT 'curso',    -- curso | livre | overclock
    has_deadline    INTEGER DEFAULT 0,       -- 1 = tem deadline urgente
    has_course      INTEGER DEFAULT 1,       -- 1 = tem aula SENAI

    -- Computado (Reverse Sync)
    pomodoros_completed INTEGER DEFAULT 0,
    tasks_completed INTEGER DEFAULT 0,
    tasks_created   INTEGER DEFAULT 0,
    orphan_tasks    INTEGER DEFAULT 0,

    -- Horas por fase (do Timewarrior)
    hours_learn     REAL DEFAULT 0.0,
    hours_earn      REAL DEFAULT 0.0,
    hours_train     REAL DEFAULT 0.0,
    hours_share     REAL DEFAULT 0.0,
    hours_review    REAL DEFAULT 0.0,
    hours_total     REAL DEFAULT 0.0,

    -- Habitos
    habits_total    INTEGER DEFAULT 0,       -- Habitos esperados
    habits_done     INTEGER DEFAULT 0,       -- Habitos cumpridos
    habits_skipped  INTEGER DEFAULT 0,       -- Habitos pulados
    habits_rate     REAL DEFAULT 0.0,        -- habits_done / habits_total

    -- Metricas derivadas
    efficiency_ratio REAL,                   -- hours_total / setpoint_previsto
    ikigai_balance   REAL,                   -- 1 - std_dev(phase_distribution)
    energy_correlation REAL,                 -- Correlacao energia x produtividade

    -- Hypervisor
    hypervisor_setpoints TEXT,               -- JSON: {deep_work: 90, laborative: 240, ...}
    hypervisor_alerts TEXT,                  -- JSON array de alertas

    -- Timestamp
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Indices
CREATE INDEX idx_daily_qhe_date ON daily_qhe(date);
CREATE INDEX idx_daily_qhe_energy ON daily_qhe(energy_level);
CREATE INDEX idx_daily_qhe_daytype ON daily_qhe(day_type);
CREATE INDEX idx_daily_qhe_efficiency ON daily_qhe(efficiency_ratio);
```

### 6.5. Tabela: policy_decisions

```sql
-- ═══════════════════════════════════════════════════
-- TABELA: policy_decisions
-- Proposito: Log de decisoes do Hypervisor
-- Granularidade: 1 row por decisao
-- ═══════════════════════════════════════════════════

CREATE TABLE policy_decisions (
    -- Chave
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    date            DATE NOT NULL,           -- Data da decisao
    timestamp       DATETIME DEFAULT CURRENT_TIMESTAMP,

    -- Contexto da decisao
    decision_type   TEXT NOT NULL,           -- setpoint_adjust | priority_change | alert | recommendation | phase_switch
    trigger_metric  TEXT,                    -- Qual metrica disparou (sleep_hours, energy_level, etc.)
    trigger_value   REAL,                    -- Valor da metrica no momento
    threshold_value REAL,                    -- Limiar que foi cruzado

    -- Decisao
    decision        TEXT NOT NULL,           -- Descricao da decisao
    old_value       TEXT,                    -- Valor anterior (JSON se necessario)
    new_value       TEXT,                    -- Novo valor (JSON se necessario)

    -- Impacto
    affected_entity TEXT,                    -- Qual entidade foi afetada (Wave, Cycle, Task, etc.)
    affected_id     TEXT,                    -- ID da entidade

    -- Aprovacao (human-in-the-loop)
    auto_applied    INTEGER DEFAULT 1,       -- 1 = aplicado automaticamente
    human_override  INTEGER DEFAULT 0,       -- 1 = humano sobrescreveu
    human_note      TEXT,                    -- Justificativa da sobrescricao

    -- Metadados
    hypervisor_version TEXT DEFAULT '1.0'    -- Versao das regras do Hypervisor
);

-- Indices
CREATE INDEX idx_policy_date ON policy_decisions(date);
CREATE INDEX idx_policy_type ON policy_decisions(decision_type);
CREATE INDEX idx_policy_entity ON policy_decisions(affected_entity, affected_id);
```

### 6.6. Tabela: study_sessions

```sql
-- ═══════════════════════════════════════════════════
-- TABELA: study_sessions
-- Proposito: Rastreamento detalhado de sessoes de estudo
-- Granularidade: 1 row por sessao de estudo
-- Fonte: Timewarrior intervals com +study.*
-- ═══════════════════════════════════════════════════

CREATE TABLE study_sessions (
    -- Chave
    id              INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Identificacao
    session_id      TEXT UNIQUE,             -- UUID gerado pelo pipeline
    date            DATE NOT NULL,

    -- Tempo
    start_time      DATETIME NOT NULL,
    end_time        DATETIME,
    duration_minutes REAL,                   -- Computado: end - start

    -- Classificacao
    study_type      TEXT NOT NULL,           -- reading | coding | algorithms | system_design | writing | review
    phase           TEXT NOT NULL,           -- learn | share | review
    topic           TEXT,                    -- Topico especifico (e.g., "Graph Algorithms")
    source_material TEXT,                    -- Livro, curso, artigo

    -- Contexto
    energy_before   INTEGER,                 -- 1-10 (auto-reported)
    energy_after    INTEGER,                 -- 1-10 (auto-reported)
    focus_level     INTEGER,                 -- 1-10 (subjetivo)
    interruptions   INTEGER DEFAULT 0,       -- Numero de interrupcoes

    -- Output
    notes_taken     INTEGER DEFAULT 0,       -- 1 = gerou notas
    code_written    INTEGER DEFAULT 0,       -- 1 = escreveu codigo
    exercises_done  INTEGER DEFAULT 0,       -- Quantidade de exercicios
    flashcards_created INTEGER DEFAULT 0,    -- Cards criados

    -- Links
    linked_project    TEXT,                  -- FK → ProjectEntity.id (opcional)
    linked_meta       TEXT,                  -- FK → MetaEntity.id (opcional)
    linked_objective  TEXT,                  -- FK → ObjectiveEntity.id (opcional)

    -- Tags brutos do Timewarrior
    tw_tags           TEXT,                  -- JSON array de tags

    -- Timestamp
    created_at        DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (linked_project) REFERENCES projects(id) ON DELETE SET NULL,
    FOREIGN KEY (linked_meta) REFERENCES metas(id) ON DELETE SET NULL,
    FOREIGN KEY (linked_objective) REFERENCES objectives(id) ON DELETE SET NULL
);

-- Indices
CREATE INDEX idx_study_date ON study_sessions(date);
CREATE INDEX idx_study_type ON study_sessions(study_type);
CREATE INDEX idx_study_phase ON study_sessions(phase);
CREATE INDEX idx_study_project ON study_sessions(linked_project);
```

### 6.7. Tabela Auxiliar: habits (Registry)

```sql
-- ═══════════════════════════════════════════════════
-- TABELA: habits (Registry)
-- Proposito: Registro mestre de habitos (mirror do Frontmatter)
-- Granularidade: 1 row por habito
-- ═══════════════════════════════════════════════════

CREATE TABLE habits (
    id              TEXT PRIMARY KEY,        -- habit_*
    title           TEXT NOT NULL,
    status          TEXT DEFAULT 'active',
    created         DATE NOT NULL,
    frequency       TEXT NOT NULL,
    custom_days     TEXT,                    -- JSON array [0,1,2,3,4]
    trigger_context TEXT NOT NULL,
    scheduled_time  TEXT,                    -- HH:MM
    linked_phase    TEXT,                    -- FK → phases
    linked_dream    TEXT,                    -- FK → dreams
    tracking_type   TEXT NOT NULL,
    target_value    REAL NOT NULL,
    target_unit     TEXT NOT NULL,
    tw_tags         TEXT,                    -- JSON array
    grace_period    INTEGER DEFAULT 1,
    min_success_rate REAL DEFAULT 0.8,
    tags            TEXT,                    -- JSON array
    notes           TEXT,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_habits_status ON habits(status);
CREATE INDEX idx_habits_phase ON habits(linked_phase);
```

### 6.8. Tabela Auxiliar: phases (Registry)

```sql
-- ═══════════════════════════════════════════════════
-- TABELA: phases (Registry)
-- Proposito: Registro mestre de fases (mirror do Frontmatter)
-- Granularidade: 1 row por phase
-- ═══════════════════════════════════════════════════

CREATE TABLE phases (
    id              TEXT PRIMARY KEY,        -- phase_*
    title           TEXT NOT NULL,
    status          TEXT DEFAULT 'active',
    ikigai_vector   TEXT NOT NULL,
    phase_code      TEXT NOT NULL,           -- learn | earn | train | share | review
    setpoint_minutes INTEGER DEFAULT 90,
    day_type        TEXT DEFAULT 'both',
    context_tags    TEXT,                    -- JSON array
    min_energy      INTEGER DEFAULT 5,
    max_sessions    INTEGER DEFAULT 3,
    recovery_cost   INTEGER DEFAULT 10,
    tags            TEXT,                    -- JSON array
    notes           TEXT
);
```

---

## 7. Integration Points

### 7.1. Matriz de Integracao Completa

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    🔌  PONTOS DE INTEGRACAO POR SUBSISTEMA              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  NOVAS ENTIDADES ──►│ CYCLE │ WAVE  │ PHASE │ HABIT │                 │
│  ───────────────────┼───────┼───────┼───────┼───────┤                 │
│  IKIGAi Vectors     │   ✓   │   ✓   │   ✓   │   ✓   │                 │
│  Taskwarrior        │   ○   │   ○   │   ✓   │   ✓   │                 │
│  Timewarrior        │   ○   │   ○   │   ✓   │   ✓   │                 │
│  fin_ops            │   ✓   │   ✓   │   ○   │   ○   │                 │
│  DailyMetrics       │   ○   │   ✓   │   ✓   │   ✓   │                 │
│                                                                         │
│  Legenda: ✓ = Integracao direta │ ○ = Indireto (via outra entidade)   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 7.2. IKIGAi Vectors Integration

| Entidade | Vetor Primario | Como Integra | Campo/Caminho |
|:---------|:---------------|:-------------|:--------------|
| **Cycle** | Configuravel (`ikigai_focus`) | Ciclo inteiro privilegia um vetor | `CycleEntity.ikigai_focus` |
| **Wave** | Herdado do Cycle | Distribuicao de horas por fase reflete vetores | `WaveEntity.phase_distribution` |
| **Phase** | Fixo por fase | Cada phase mapeia 1:1 para um vetor | `PhaseEntity.ikigai_vector` |
| **Habit** | Configuravel (`linked_dream`) | Habito contribui para o vetor do Dream | `HabitEntity.linked_dream` → `DreamEntity.ikigai_vectors` |

```python
# Pseudocodigo — calculo de contribuicao IKIGAi por entidade

def compute_ikigai_contribution(entity, hours_spent: float) -> Dict[str, float]:
    """
    Calcula quanto cada vetor IKIGAi foi contribuido por uma entidade.
    """
    if isinstance(entity, PhaseEntity):
        # Phase contribui 100% para seu vetor
        return {entity.ikigai_vector: hours_spent}

    elif isinstance(entity, HabitEntity):
        # Habit contribui para o vetor do Dream linkado
        if entity.linked_dream:
            dream = resolve_dream(entity.linked_dream)
            # Distribui proporcionalmente aos vetores do Dream
            vectors = dream.ikigai_vectors
            total = vectors.composite_score
            return {
                'passion': hours_spent * vectors.passion / total,
                'skill': hours_spent * vectors.skill / total,
                'market': hours_spent * vectors.market / total,
                'revenue': hours_spent * vectors.revenue / total,
            }
        return {'passion': hours_spent}  # Default: passion (treino/saude)

    elif isinstance(entity, CycleEntity):
        # Cycle contribui para o vetor de foco
        return {entity.ikigai_focus: hours_spent}

    return {}
```

### 7.3. Taskwarrior Integration

| Entidade | TW Project | TW Tags | TW UDAs | Comando de Exemplo |
|:---------|:-----------|:--------|:--------|:-------------------|
| **Cycle** | — | — | — | Nao compila diretamente |
| **Wave** | — | — | — | Nao compila diretamente |
| **Phase** | — | `+phase.{code}` | — | Injetado como tag em tasks |
| **Habit** | `habits` | `+habit.{id}` `+phase.{code}` | `recurrence:` `phase:` | `task add "Treino Matinal" project:habits +habit.morning_workout recurrence:weekdays phase:train` |
| **Meta** (existente) | `S1.O2.M3` | `+sprint` | `wave:` `upstream_id:` | `task add "Sprint API" project:S1.O2.M3 +sprint wave:W2_Jul_2026` |
| **Task** (existente) | herda do Project | herda + `+phase.{code}` | `phase:` `upstream_id:` | `task add "Implementar JWT" project:S1.O2.M3.proj_alfa +phase.learn phase:learn` |

**Configuracao no `.taskrc`:**

```ini
# UDAs para as novas entidades
uda.phase.type=string
uda.phase.label=Phase
uda.phase.values=learn,earn,train,share,review

uda.wave.type=string
uda.wave.label=Wave

uda.recurrence.type=string
uda.recurrence.label=Recurrence

# Urgencia: boost por phase (opcional)
urgency.user.tag.phase.learn.coefficient=2.0
urgency.user.tag.phase.earn.coefficient=3.0
urgency.user.tag.phase.train.coefficient=1.5
```

### 7.4. Timewarrior Integration

| Entidade | Tag Pattern | Comando de Tracking | Report Nativo |
|:---------|:------------|:--------------------|:--------------|
| **Phase** | `phase.{code}` | `timew start phase.learn @vscode` | `timew summary phase.learn` |
| **Habit** | `habit.{id}` | `timew start habit.morning_workout` | `timew summary habit.morning_workout` |
| **Study** | `study.{type}` | `timew start study.algorithms phase.learn` | `timew summary study.*` |
| **Energy** | `energy.{level}` | `timew start phase.earn energy.high` | `timew summary energy.high` |

**Configuracao no `.timewarrior/timewarrior.cfg`:**

```ini
# Tags excluidas de reports gerais (kernel time)
exclusions = @sleep, @meal, @hygiene

# Jornada padrao para calculo de horas
hours = 04:45-18:15
```

**Hook de integracao (on-stop):**

```python
# ~/.timewarrior/extensions/vibe-ops-hook.py
# Executado a cada 'timew stop' — envia dados para o SQLite Analytics

import json
import sys
import sqlite3

def on_stop(interval):
    """Hook chamado quando um intervalo e fechado."""
    conn = sqlite3.connect("~/vibe-ops/analytics.db")

    # Extrai tags
    tags = interval.get('tags', [])
    phases = [t for t in tags if t.startswith('phase.')]
    habits = [t for t in tags if t.startswith('habit.')]
    studies = [t for t in tags if t.startswith('study.')]
    energies = [t for t in tags if t.startswith('energy.')]

    # Insere em habit_states se for habito
    for habit_tag in habits:
        habit_id = habit_tag.replace('habit.', 'habit_')
        # INSERT OR UPDATE habit_states...

    # Insere em study_sessions se for estudo
    if studies:
        # INSERT INTO study_sessions...
        pass

    conn.commit()
    conn.close()
```

### 7.5. fin_ops Integration

| Entidade | Dado Enviado para fin_ops | Formato | Trigger |
|:---------|:--------------------------|:--------|:--------|
| **Cycle** | Budget de horas por ciclo | JSON | Ciclo iniciado |
| **Wave** | Horas alocadas vs realizadas | JSON | Wave completada |
| **Phase** | Horas por vetor (para DRE) | JSON | Reverse sync diario |
| **Habit** | — | — | Nao integra diretamente |

```python
# Pseudocodigo — envio de dados para fin_ops

def sync_to_fin_ops(date: date, conn: sqlite3.Connection):
    """
    Envia dados de produtividade para fin_ops para calculo de ROI.
    """
    # Horas por fase (vetor IKIGAi)
    cursor = conn.execute("""
        SELECT phase, hours_total FROM wave_progress WHERE date = ?
    """, (date,))
    phase_hours = dict(cursor.fetchall())

    # Converte para formato fin_ops
    fin_ops_payload = {
        "date": date.isoformat(),
        "time_investment": {
            "learn": phase_hours.get('learn', 0) * 50.0,  # R$/hora base
            "earn": phase_hours.get('earn', 0) * 50.0,
            "train": phase_hours.get('train', 0) * 0.0,   # Sem retorno direto
            "share": phase_hours.get('share', 0) * 25.0,  # Retorno indireto
            "review": phase_hours.get('review', 0) * 0.0,
        },
        "cycle_id": get_active_cycle(date),
        "wave_id": get_active_wave(date),
    }

    # Envia para fin_ops via CLI
    # life finance track --category time_investment --amount {value} --desc "{phase}"
    return fin_ops_payload
```

### 7.6. DailyMetrics Integration

| Entidade | Campo em DailyMetrics | Fonte | Computo |
|:---------|:----------------------|:------|:--------|
| **Cycle** | `active_cycle` | CycleEntity (where status='active') | FK reference |
| **Wave** | `active_wave` | WaveEntity (where status='active') | FK reference |
| **Phase** | `hours_learn`, `hours_earn`, `hours_train`, `hours_share`, `hours_review` | Timewarrior intervals | SUM por phase tag |
| **Habit** | `habits_total`, `habits_done`, `habits_rate` | habit_states | COUNT/SUM |
| **Habit** | `streak_best`, `streak_current` | habit_states | MAX/consecutive |

```python
# Pseudocodigo — agregacao diaria no DailyMetrics

class DailyMetricsExtended(DailyMetrics):
    """
    Extensao do DailyMetrics com campos das novas entidades.
    """
    # Referencias temporais
    active_cycle: Optional[str] = None          # FK → CycleEntity.id
    active_wave: Optional[str] = None           # FK → WaveEntity.id
    active_quarter: Optional[str] = None        # Q3_2026

    # Habitos (agregados da tabela habit_states)
    habits_total: int = Field(ge=0, default=0)
    habits_done: int = Field(ge=0, default=0)
    habits_skipped: int = Field(ge=0, default=0)
    habits_rate: float = Field(ge=0.0, le=1.0, default=0.0)
    streak_current_max: int = Field(ge=0, default=0)  # Maior streak ativa do dia

    # Phase (detalhamento das horas IKIGAi)
    hours_learn: float = Field(ge=0, default=0.0)
    hours_earn: float = Field(ge=0, default=0.0)
    hours_train: float = Field(ge=0, default=0.0)
    hours_share: float = Field(ge=0, default=0.0)
    hours_review: float = Field(ge=0, default=0.0)

    # Metricas derivadas
    @computed_field
    @property
    def ikigai_balance_score(self) -> float:
        """
        Score de equilibrio IKIGAi (1.0 = perfeitamente balanceado).
        Calcula 1 - coeficiente de variacao das horas por vetor.
        """
        hours = [self.hours_learn, self.hours_earn, self.hours_train,
                 self.hours_share, self.hours_review]
        total = sum(hours)
        if total == 0:
            return 0.0
        mean = total / 5
        variance = sum((h - mean) ** 2 for h in hours) / 5
        std_dev = variance ** 0.5
        cv = std_dev / mean if mean > 0 else 0
        return max(0.0, 1.0 - cv)

    @computed_field
    @property
    def phase_distribution_pct(self) -> Dict[str, float]:
        """Distribuicao percentual de horas por fase."""
        total = self.total_hardwork_hours
        if total == 0:
            return {k: 0.0 for k in ['learn', 'earn', 'train', 'share', 'review']}
        return {
            'learn': round(self.hours_learn / total * 100, 1),
            'earn': round(self.hours_earn / total * 100, 1),
            'train': round(self.hours_train / total * 100, 1),
            'share': round(self.hours_share / total * 100, 1),
            'review': round(self.hours_review / total * 100, 1),
        }

    @computed_field
    @property
    def total_hardwork_hours(self) -> float:
        """Soma de todas as fases de trabalho."""
        return (self.hours_learn + self.hours_earn + self.hours_train +
                self.hours_share + self.hours_review)
```

---

## 8. Fluxo de Dados End-to-End

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    🔄  FLUXO COMPLETO DE DADOS                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  MANHA (04:30) — INPUT MANUAL                                           │
│  ──────────────────────────────────────────────────────────────────     │
│  daily_qhe: sleep_hours, energy_level, mood_score, day_type             │
│       │                                                                 │
│       ▼                                                                 │
│  HYPERVISOR — CALCULA SETPOINTS                                         │
│  ──────────────────────────────────────────────────────────────────     │
│  policy_decisions: ajusta phase_distribution baseado em energy_level    │
│       │                                                                 │
│       ▼                                                                 │
│  DIA — EXECUCAO                                                         │
│  ──────────────────────────────────────────────────────────────────     │
│  TW: task start/stop/done                                               │
│  Timew: timew start phase.learn @vscode energy.high                     │
│       │                                                                 │
│       ▼                                                                 │
│  NOITE (Cron) — REVERSE SYNC                                            │
│  ──────────────────────────────────────────────────────────────────     │
│  1. task export → TaskSnapshot                                          │
│  2. timew export → TimewarriorInterval                                  │
│  3. JOIN com Planning via upstream_id + tags                            │
│  4. INSERT/UPDATE: habit_states, wave_progress, study_sessions          │
│  5. UPDATE: daily_qhe com horas por phase, habit compliance             │
│       │                                                                 │
│       ▼                                                                 │
│  DOMINGO — AGREGACAO                                                    │
│  ──────────────────────────────────────────────────────────────────     │
│  1. cycle_metrics: agrega wave_progress por cycle                       │
│  2. fin_ops sync: envia time_investment por vetor                       │
│  3. Dashboard: renderiza IKIGAi balance, burndown, streaks              │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 9. Anti-Patterns (O Que NAO Fazer)

| Anti-Pattern | Exemplo Ruim | Correcao |
|:-------------|:-------------|:---------|
| Wave sem Cycle | `wave: W2_Jul_2026` sem `cycle: C1` | Toda Wave DEVE ter um Cycle pai |
| Phase tag duplicada | `+phase.learn +phase.earn` no mesmo intervalo | Maximo UMA phase tag por intervalo |
| Habit sem tw_tags | `tw_tags: []` | tw_tags deve ter pelo menos a tag principal |
| Cycle com end_date no passado e status active | `end_date: 2026-01-01, status: active` | Status deve refletir o estado temporal |
| Meta.wave referenciando Wave inexistente | `wave: W99_Dez_2099` | Validar FK no pipeline |
| custom_days fora de 0-6 | `custom_days: [1, 8]` | Validar range no Pydantic |
| scheduled_time sem trigger_context=scheduled | `scheduled_time: 05:00, trigger_context: after_wakeup` | scheduled_time so quando trigger=scheduled |
| Computar streak no Frontmatter | `streak_current: 15` no YAML | Streak e COMPUTADO pelo pipeline |

---

> NOTA: Este documento e um **living spec** e deve ser atualizado quando:
> - Novos campos forem adicionados a qualquer entidade
> - O pipeline mudar sua logica de JOIN ou agregacao
> - Novas tags forem introduzidas no Timewarrior
> - O schema SQLite for alterado
>
> Alteracoes devem ser refletidas em `CHANGELOG.md` e versionadas.

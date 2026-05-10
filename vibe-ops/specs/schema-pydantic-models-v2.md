# Schema: Pydantic Models v2 (Temporal + Behavioral Entities)

**Versao:** 0.2.0
**Ultima Atualizacao:** 2026-05-09
**Referencia:** `architecture/ADR-001-data-flow-topology.md`, `doc/03-data-mesh-enrichment.md`, `schema-frontmatter-contract-v2.md`, `life-ops/planner/Points_of_premisses-task-habits.md`, `life-ops/planner/81d33ec8-c354-44c4-b846-575f26cb7ca3_time-lenghts_reviews.md`

Este documento estende os modelos Pydantic v1 (`schema-pydantic-models.md`) com as entidades temporais (Wave, Cycle, Phase) e comportamentais (Habit, StudyPlan, HabitState, PolicyDecision, QHEMetrics) necessarias para integrar o modelo matematico WAVE/CYCLE/PHASE ao Data-Mesh.

---

## 1. Modelos de Entidade (Planning Domain) — Novos

### 1.1. Enums Estendidos

```python
from enum import Enum

class EntityType(str, Enum):
    """Tipos de entidade do dominio de planejamento."""
    DREAM = "dream"
    OBJECTIVE = "objective"
    META = "meta"
    PROJECT = "project"
    TASK = "task"
    # Novas entidades temporais
    WAVE = "wave"
    CYCLE = "cycle"
    PHASE = "phase"
    # Novas entidades comportamentais
    HABIT = "habit"
    STUDY_PLAN = "study_plan"


class HabitCategory(str, Enum):
    """Categorias de habito segundo o substrato biologico."""
    PHYSIOLOGICAL = "physiological"   # Sono, alimentacao, exercicio
    COGNITIVE = "cognitive"           # Meditacao, leitura, estudo
    SOCIAL = "social"                 # Networking, comunicacao
    CREATIVE = "creative"             # Escrita, codificacao livre


class TrackingType(str, Enum):
    """Tipo de rastreamento para habitos."""
    BINARY = "binary"       # Executou / nao executou
    DURATION = "duration"   # Minutos, horas
    COUNT = "count"         # Paginas, repeticoes


class PolicyState(str, Enum):
    """
    Estados da politica operacional do Hypervisor.
    Derivado da matriz pi(s_t) em Points_of_premisses.
    """
    PUSH = "PUSH"           # Verde: maximizar hardwork (9h)
    MAINTAIN = "MAINTAIN"   # Amarelo: orcamento padrao
    REDUCE = "REDUCE"       # Laranja: -25% hardwork, pausas 15min
    RECOVER = "RECOVER"     # Vermelho: cancelar hardwork, sono 9h, review


class HabitIKIGAiVector(str, Enum):
    """Qual vetor IKIGAi o habito primariamente alimenta."""
    PASSION = "passion"
    SKILL = "skill"
    MARKET = "market"
    REVENUE = "revenue"


class ReviewType(str, Enum):
    """Tipo de revisao no operador Rn."""
    MID = "mid"
    END = "end"
```

---

### 1.2. WaveEntity — Onda de 15 dias

```python
from datetime import date
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator
import math


class HabitTarget(BaseModel):
    """Meta de streak para um habito dentro de uma wave."""
    habit_id: str = Field(pattern=r'^hab_[a-z0-9_]+$')
    target_streak: int = Field(ge=1, le=30)


class WaveEntity(BaseModel):
    """
    Nivel 3.5: Wave — Container temporal de 15 dias para consolidacao de habitos.
    Horizonte: Quinzenal. Cross-cuta entidades Meta.
    
    Matematica subjacente:
    - WAVE = 15 dias (constante estrutural)
    - H(t) = 1 - e^(-lambda * t)  (curva de consolidacao)
    - E(t) = t * e^(-k * t)       (curva de energia/fadiga)
    """
    id: str = Field(
        pattern=r'^W\d+_[A-Za-z]{3}_\d{4}$',
        description="Ex: W3_Jul_2026"
    )
    title: str = Field(min_length=5, max_length=200)
    entity_type: EntityType = EntityType.WAVE
    status: str = Field(
        default="active",
        pattern=r'^(active|paused|completed|aborted)$'
    )
    created: date
    started: date
    expected_end: date

    # Posicionamento temporal
    wave_number: int = Field(ge=1, le=12, description="Sequencial dentro do ciclo")
    parent_cycle: str = Field(
        pattern=r'^C\d+_\d{4}$',
        description="FK -> CycleEntity.id"
    )
    parent_objective: str = Field(
        pattern=r'^O\d+$',
        description="FK -> ObjectiveEntity.id"
    )

    # Metas comportamentais
    habit_targets: List[HabitTarget] = Field(default_factory=list)

    # Checkpoints de revisao
    mid_wave_review: date
    wave_end_review: date

    # Campos computados (populados pelo pipeline, nao editar manualmente)
    c_comp: Optional[float] = Field(
        default=None, ge=0.0, le=1.0,
        description="Consistency score: dias_estudados / dias_totais"
    )
    ic: Optional[float] = Field(
        default=None, ge=0.0, le=1.0,
        description="Index of Consistency: days_completed / days_planned"
    )

    tags: List[str] = Field(default_factory=list)

    # ============================================================
    # VALIDADORES
    # ============================================================
    @field_validator('expected_end')
    @classmethod
    def validate_wave_duration(cls, v: date, info) -> date:
        """
        Wave deve ter exatamente 15 dias corridos.
        started -> expected_end = 14 dias de delta.
        """
        started = info.data.get('started')
        if started:
            delta = (v - started).days
            if delta != 14:
                raise ValueError(
                    f"Wave deve ter exatamente 15 dias (delta=14). "
                    f"Got started={started}, expected_end={v}, delta={delta}"
                )
        return v

    @field_validator('mid_wave_review')
    @classmethod
    def validate_mid_wave(cls, v: date, info) -> date:
        """Mid-wave review deve ser no dia 8 (delta=7 desde started)."""
        started = info.data.get('started')
        if started:
            delta = (v - started).days
            if delta != 7:
                raise ValueError(f"Mid-wave review deve ser no dia 8 (delta=7). Got {delta}")
        return v

    @field_validator('wave_end_review')
    @classmethod
    def validate_wave_end(cls, v: date, info) -> date:
        """Wave end review deve coincidir com expected_end."""
        expected = info.data.get('expected_end')
        if expected and v != expected:
            raise ValueError(f"wave_end_review deve igualar expected_end")
        return v

    # ============================================================
    # PROPRIEDADES COMPUTADAS
    # ============================================================
    @property
    def elapsed_days(self) -> Optional[int]:
        """Dias decorridos desde o inicio da wave."""
        if self.started:
            return (date.today() - self.started).days
        return None

    @property
    def remaining_days(self) -> Optional[int]:
        """Dias restantes na wave."""
        if self.expected_end:
            return (self.expected_end - date.today()).days
        return None

    @property
    def progress_pct(self) -> Optional[float]:
        """Progresso percentual da wave (0-100)."""
        elapsed = self.elapsed_days
        if elapsed is not None:
            return min((elapsed / 14.0) * 100, 100.0)
        return None

    @property
    def is_mid_wave(self) -> bool:
        """True se estamos no dia do mid-wave review."""
        return date.today() == self.mid_wave_review

    @property
    def is_wave_end(self) -> bool:
        """True se estamos no dia do wave end review."""
        return date.today() == self.wave_end_review
```

---

### 1.3. CycleEntity — Ciclo de 45 dias

```python
class CycleEntity(BaseModel):
    """
    Nivel 3.6: Cycle — Estabilizacao de performance em 45 dias.
    Alinha com HALF_QUARTER. Contem 3 Waves.
    
    Constantes estruturais (imutaveis):
    - wave_count = 3
    - wave_duration_days = 15
    - total_duration_days = 45
    """
    id: str = Field(pattern=r'^C\d+_\d{4}$', description="Ex: C1_2026")
    title: str = Field(min_length=5, max_length=200)
    entity_type: EntityType = EntityType.CYCLE
    status: str = Field(default="active")
    created: date
    started: date
    expected_end: date

    cycle_number: int = Field(ge=1, le=8)
    parent_phase: str = Field(
        pattern=r'^P\d+_\d{4}$',
        description="FK -> PhaseEntity.id"
    )
    parent_objective: str = Field(
        pattern=r'^O\d+$',
        description="FK -> ObjectiveEntity.id"
    )

    # Constantes estruturais (valores padrao imutaveis)
    wave_count: int = Field(default=3)
    wave_duration_days: int = Field(default=15)
    total_duration_days: int = Field(default=45)

    mid_cycle_review: date
    cycle_end_review: date
    aligned_half_quarter: str = Field(
        pattern=r'^HQ\d+_Q[1-4]_\d{4}$',
        description="Ex: HQ1_Q3_2026"
    )

    tags: List[str] = Field(default_factory=list)

    @field_validator('expected_end')
    @classmethod
    def validate_cycle_duration(cls, v: date, info) -> date:
        """Cycle deve ter exatamente 45 dias (delta=44)."""
        started = info.data.get('started')
        if started:
            delta = (v - started).days
            if delta != 44:
                raise ValueError(f"Cycle deve ter exatamente 45 dias (delta=44). Got {delta}")
        return v

    @property
    def wave_ids(self) -> List[str]:
        """
        Gera IDs esperados das waves deste ciclo.
        Ex: C1_2026 -> [W1_2026, W2_2026, W3_2026] (simplificado)
        Na pratica, usa mes/ano do started.
        """
        # Implementacao real usaria o mes do started para nomear
        base_year = self.started.year
        return [
            f"W{i}_{base_year}"
            for i in range(1, self.wave_count + 1)
        ]

    @property
    def elapsed_days(self) -> Optional[int]:
        if self.started:
            return (date.today() - self.started).days
        return None

    @property
    def progress_pct(self) -> Optional[float]:
        elapsed = self.elapsed_days
        if elapsed is not None:
            return min((elapsed / 44.0) * 100, 100.0)
        return None
```

---

### 1.4. PhaseEntity — Fase de 180 dias

```python
class PhaseEntity(BaseModel):
    """
    Nivel 3.7: Phase — Maestria de competencia em 180 dias.
    Spans 4 Cycles = 2 Quarters. Alinha com Dream horizon.
    
    Constantes estruturais:
    - cycle_count = 4
    - cycle_duration_days = 45
    - total_duration_days = 180
    """
    id: str = Field(pattern=r'^P\d+_\d{4}$', description="Ex: P1_2026")
    title: str = Field(min_length=5, max_length=200)
    entity_type: EntityType = EntityType.PHASE
    status: str = Field(default="active")
    created: date
    started: date
    expected_end: date

    phase_number: int = Field(ge=1, le=4)
    parent_dream: str = Field(
        pattern=r'^S\d+$',
        description="FK -> DreamEntity.id"
    )

    cycle_count: int = Field(default=4)
    cycle_duration_days: int = Field(default=45)
    total_duration_days: int = Field(default=180)

    mid_phase_review: date
    phase_end_review: date

    aligned_quarter_start: str = Field(pattern=r'^Q[1-4]_\d{4}$')
    aligned_quarter_end: str = Field(pattern=r'^Q[1-4]_\d{4}$')

    tags: List[str] = Field(default_factory=list)

    @field_validator('expected_end')
    @classmethod
    def validate_phase_duration(cls, v: date, info) -> date:
        """Phase deve ter exatamente 180 dias (delta=179)."""
        started = info.data.get('started')
        if started:
            delta = (v - started).days
            if delta != 179:
                raise ValueError(f"Phase deve ter exatamente 180 dias (delta=179). Got {delta}")
        return v

    @property
    def elapsed_days(self) -> Optional[int]:
        if self.started:
            return (date.today() - self.started).days
        return None

    @property
    def progress_pct(self) -> Optional[float]:
        elapsed = self.elapsed_days
        if elapsed is not None:
            return min((elapsed / 179.0) * 100, 100.0)
        return None
```

---

### 1.5. HabitEntity — Entidade Comportamental

```python
class HabitEntity(BaseModel):
    """
    Entidade ortogonal: Hábito comportamental.
    Alimenta o Q_HE via H(t) = 1 - e^(-lambda * streak).
    
    Parametros matematicos:
    - resistance (R): dificuldade inerente 1-10
    - lambda_learning (λ): taxa de aprendizado
    - energy_cost: custo energético normalizado
    - qhe_weight (w_i): peso no quociente Q_HE
    """
    id: str = Field(pattern=r'^hab_[a-z0-9_]+$', description="Ex: hab_sleep")
    title: str = Field(min_length=3, max_length=200)
    entity_type: EntityType = EntityType.HABIT
    status: str = Field(default="active")
    created: date

    habit_category: HabitCategory
    resistance: int = Field(
        ge=1, le=10,
        description="Dificuldade inerente R (1=fácil, 10=muito difícil)"
    )
    lambda_learning: float = Field(
        ge=0.01, le=1.0,
        description="Taxa de aprendizado λ para H(t)"
    )
    energy_cost: float = Field(
        ge=0.0, le=1.0,
        description="Custo energético normalizado"
    )

    anchor_wave: str = Field(
        pattern=r'^W\d+_[A-Za-z]{3}_\d{4}$',
        description="FK -> WaveEntity.id (wave atual de consolidação)"
    )
    target_streak: int = Field(ge=1, le=45, description="Meta de streak para wave atual")

    qhe_weight: float = Field(
        ge=0.0, le=1.0,
        description="Peso w_i na fórmula Q_HE"
    )

    tracking_type: TrackingType
    target_value: float = Field(ge=0, description="Meta diária")
    unit: str = Field(description="completion | minutes | pages | reps")

    ikigai_vector: HabitIKIGAiVector

    tags: List[str] = Field(default_factory=list)

    # ============================================================
    # METODOS MATEMATICOS
    # ============================================================
    def habit_level(self, streak: int) -> float:
        """
        H(t) = 1 - e^(-λ * s)
        Nível de automatização dado streak atual.
        """
        return 1.0 - math.exp(-self.lambda_learning * streak)

    def energy_required(self, streak: int) -> float:
        """
        E_req = R * (1 - H(s))
        Energia necessária para executar o hábito hoje.
        Quanto mais consolidado, menos energia requer.
        """
        return self.resistance * (1.0 - self.habit_level(streak))

    def efficiency_index(self, streak: int, streak_prev: int) -> float:
        """
        I = (H(s) * Δs) / (R * (1 - H(s)))
        Índice de eficiência do hábito (core decision index).
        """
        h = self.habit_level(streak)
        delta_s = streak - streak_prev
        denom = self.resistance * (1.0 - h)
        if denom == 0:
            return float('inf')
        return (h * delta_s) / denom

    @property
    def qhe_component(self, streak: int = 0) -> float:
        """
        Componente w_i * H_i(t) para o Q_HE.
        """
        return self.qhe_weight * self.habit_level(streak)
```

---

### 1.6. StudyPlanEntity — Plano de Estudo Continuo

```python
class StudyTopic(BaseModel):
    """Topico dentro de um plano de estudo."""
    topic_id: str = Field(pattern=r'^tp_[a-z0-9_]+$', description="Ex: tp_python")
    title: str = Field(min_length=3, max_length=200)
    status: str = Field(
        default="pending",
        pattern=r'^(pending|in_progress|completed|deferred)$'
    )
    target_hours: float = Field(ge=0.5)


class StudyPlanEntity(BaseModel):
    """
    Plano de estudo contínuo (7/7 cadência).
    Especialização de Project com tracking de tópicos e CLR.
    
    O estudo é a "âncora" do sistema: mantém tração mental estável
    mesmo quando demandas externas flutuam.
    """
    id: str = Field(
        pattern=r'^study_[a-z0-9_]+$',
        description="Ex: study_backend_01"
    )
    title: str = Field(min_length=5, max_length=200)
    entity_type: EntityType = EntityType.STUDY_PLAN
    status: str = Field(default="active")
    created: date

    parent_dream: str = Field(
        pattern=r'^S\d+$',
        description="FK -> DreamEntity.id"
    )
    parent_objective: str = Field(
        pattern=r'^O\d+$',
        description="FK -> ObjectiveEntity.id"
    )

    anchor_wave: str = Field(
        pattern=r'^W\d+_[A-Za-z]{3}_\d{4}$',
        description="FK -> WaveEntity.id"
    )
    anchor_cycle: str = Field(
        pattern=r'^C\d+_\d{4}$',
        description="FK -> CycleEntity.id"
    )

    study_cadence: str = Field(
        default="daily",
        pattern=r'^(daily|wave_based)$'
    )
    work_ratio_override: float = Field(
        default=1.0, ge=0.0, le=1.0,
        description="1.0 = 7/7 (sem filtro de workday)"
    )
    daily_target_minutes: int = Field(ge=15, le=480, default=120)

    topics: List[StudyTopic] = Field(default_factory=list)
    target_clr: float = Field(
        ge=0.0, le=1.0, default=0.4,
        description="Cognitive Load Ratio target (study_hours / work_hours)"
    )

    tags: List[str] = Field(
        default_factory=list,
        default=["study", "phase:learn", "study_anchor"]
    )

    @property
    def total_target_hours(self) -> float:
        """Soma de horas-alvo de todos os tópicos."""
        return sum(t.target_hours for t in self.topics)

    @property
    def completed_hours(self) -> float:
        """Soma de horas completadas (de topics com status=completed)."""
        return sum(
            t.target_hours for t in self.topics
            if t.status == "completed"
        )

    @property
    def progress_pct(self) -> float:
        """Progresso percentual do plano de estudo."""
        total = self.total_target_hours
        if total > 0:
            return min((self.completed_hours / total) * 100, 100.0)
        return 0.0

    @property
    def tw_project_key(self) -> str:
        """
        Chave hierárquica para Taskwarrior.
        Formato: S1.O2.study_backend_01
        """
        return f"{self.parent_dream}.{self.parent_objective}.{self.id}"

    @property
    def is_anchor(self) -> bool:
        """StudyPlan é sempre âncora (7/7)."""
        return True
```

---

## 2. Modelos de Telemetria (Habit + Q_HE)

### 2.1. HabitState — Estado Diario de Hábito

```python
from datetime import date

class HabitState(BaseModel):
    """
    Estado diário de um hábito.
    Registrado pelo pipeline de tracking (input matinal + reverse sync).
    
    Fontes de dados:
    - executed: formulário matinal (manual) ou task done (reverse sync)
    - value: quantidade (minutos, páginas) se tracking_type != binary
    - streak_current: computado pelo pipeline comparando com yesterday
    """
    date: date
    habit_id: str = Field(pattern=r'^hab_[a-z0-9_]+$')

    # Input
    executed: bool = False
    value: Optional[float] = None
    notes: Optional[str] = None

    # Computado pelo pipeline
    streak_current: int = Field(ge=0, default=0)
    streak_previous: int = Field(ge=0, default=0)
    habit_level: float = Field(ge=0.0, le=1.0, default=0.0)  # H(s)
    energy_required: float = Field(ge=0.0, default=0.0)  # E_req

    @property
    def delta_streak(self) -> int:
        """Δs = s - s_prev. Negativo indica quebra de streak."""
        return self.streak_current - self.streak_previous

    @property
    def streak_broken(self) -> bool:
        """True se o streak foi quebrado hoje."""
        return self.delta_streak < 0

    @property
    def streak_maintained(self) -> bool:
        """True se o streak foi mantido ou aumentado."""
        return self.delta_streak >= 0
```

---

### 2.2. QHEMetrics — Quociente de Eficiência Habitual

```python
from typing import Dict

class QHEMetrics(BaseModel):
    """
    Agregação diária do Quociente de Eficiência Habitual.
    Computado pelo habit_engine a cada reverse sync.
    
    Formula:
    Q_HE(t) = (Σ w_i * H_i(t) / Σ w_i) * (E(t)/E_max) * (1 + η * S/S_max)
    
    Thresholds:
    - Q_HE >= 0.85: Regime de Alta Eficiência (PUSH)
    - Q_HE < 0.60: Política de Recuperação (RECOVER)
    """
    date: date

    # Componentes individuais de H(t) por hábito
    h_sono: float = Field(ge=0.0, le=1.0, default=0.0)
    h_meditation: float = Field(ge=0.0, le=1.0, default=0.0)
    h_workout: float = Field(ge=0.0, le=1.0, default=0.0)
    h_lunch: float = Field(ge=0.0, le=1.0, default=0.0)

    # Pesos aplicados (serializado como JSON no SQLite)
    weights: Dict[str, float] = Field(default_factory=dict)

    # Fatores multiplicativos
    energy_ratio: float = Field(
        ge=0.0, le=1.0, default=1.0,
        description="E(t)/E_max — razão de energia disponível"
    )
    streak_bonus: float = Field(
        ge=0.0, default=0.0,
        description="η * S/S_max — bônus de streak"
    )

    # Resultados
    qhe_raw: float = Field(
        ge=0.0, le=1.0, default=0.0,
        description="Q_HE antes do fator energia"
    )
    qhe_adjusted: float = Field(
        ge=0.0, le=1.0, default=0.0,
        description="Q_HE final ajustado"
    )

    # Regime derivado
    regime: PolicyState = Field(
        default=PolicyState.MAINTAIN,
        description="Regime operacional derivado do Q_HE"
    )

    # Metadados
    computed_at: Optional[datetime] = None

    # ============================================================
    # CLASSIFICACAO DE REGIME
    # ============================================================
    @field_validator('regime', mode='before')
    @classmethod
    def derive_regime(cls, v, info) -> PolicyState:
        """Deriva regime do qhe_adjusted se nao explicitamente setado."""
        if isinstance(v, PolicyState):
            return v
        qhe = info.data.get('qhe_adjusted', 0.0)
        if qhe >= 0.85:
            return PolicyState.PUSH
        elif qhe >= 0.70:
            return PolicyState.MAINTAIN
        elif qhe >= 0.60:
            return PolicyState.REDUCE
        else:
            return PolicyState.RECOVER

    @property
    def is_high_efficiency(self) -> bool:
        """True se Q_HE >= 0.85 (regime PUSH)."""
        return self.qhe_adjusted >= 0.85

    @property
    def is_critical(self) -> bool:
        """True se Q_HE < 0.60 (regime RECOVER)."""
        return self.qhe_adjusted < 0.60

    @property
    def weighted_habit_average(self) -> float:
        """Componente (Σ w_i * H_i) / Σ w_i do Q_HE."""
        habits = {
            'sono': self.h_sono,
            'meditation': self.h_meditation,
            'workout': self.h_workout,
            'lunch': self.h_lunch,
        }
        total_weighted = sum(
            self.weights.get(k, 0.0) * v
            for k, v in habits.items()
        )
        total_weight = sum(self.weights.values())
        if total_weight > 0:
            return total_weighted / total_weight
        return 0.0
```

---

### 2.3. PolicyDecision — Output do Hypervisor

```python
from datetime import datetime

class PolicyDecision(BaseModel):
    """
    Decisão do Hypervisor — output do policy_engine.
    Determina o regime operacional do dia baseado em Q_HE, consistencia,
    infrações e tipo de dia.
    
    Matriz de decisao (de Points_of_premisses):
    Q_HE >= 0.85, C_comp >= 0.90, 0 infrações, Livre -> PUSH
    Q_HE >= 0.85, C_comp >= 0.90, 0 infrações, Curso -> PUSH
    Q_HE [0.70, 0.85), C_comp [0.80, 0.90), <=1 infração, Qualquer -> MAINTAIN
    Q_HE [0.60, 0.70), C_comp [0.70, 0.80), <=2 infrações, Qualquer -> REDUCE
    Q_HE < 0.60, C_comp < 0.70, >=2 infrações, Qualquer -> RECOVER
    """
    date: date
    policy: PolicyState

    # Inputs que geraram a decisão
    qhe: float = Field(ge=0.0, le=1.0, description="Quociente de Eficiência Habitual")
    c_comp: float = Field(ge=0.0, le=1.0, description="Consistência comportamental")
    infrações_24h: int = Field(ge=0, default=0)
    tipo_dia: str = Field(
        pattern=r'^(livre|curso|workday|feriado)$',
        description="Classificação do dia"
    )

    # Setpoints computados
    hardwork_budget_hours: float = Field(ge=0.0, le=16.0)
    pause_duration_minutes: int = Field(ge=5, le=60)
    sleep_target_hours: float = Field(ge=4.0, le=12.0)

    # Recomendações narrativas
    recomendacoes: List[str] = Field(default_factory=list)
    alertas: List[str] = Field(default_factory=list)

    # Histerese (evita oscilação)
    days_in_current_policy: int = Field(ge=0, default=1)
    policy_prev: Optional[PolicyState] = None

    # Metadados
    computed_at: Optional[datetime] = None

    # ============================================================
    # LOGICA DE HISTERese
    # ============================================================
    def should_transition(self, new_policy: PolicyState) -> bool:
        """
        Determina se a transição de política deve ocorrer,
        respeitando as janelas de histerese:
        - UPGRADE: Q_HE >= θ_up por 3 dias
        - DOWNGRADE: Q_HE <= θ_down por 2 dias
        """
        if new_policy == self.policy:
            return False

        # Mapeamento de thresholds por direção
        upgrade_thresholds = {
            PolicyState.RECOVER: (PolicyState.REDUCE, 0.65, 3),
            PolicyState.REDUCE: (PolicyState.MAINTAIN, 0.75, 3),
            PolicyState.MAINTAIN: (PolicyState.PUSH, 0.85, 3),
        }
        downgrade_thresholds = {
            PolicyState.PUSH: (PolicyState.MAINTAIN, 0.80, 2),
            PolicyState.MAINTAIN: (PolicyState.REDUCE, 0.70, 2),
            PolicyState.REDUCE: (PolicyState.RECOVER, 0.60, 2),
        }

        # Verifica se transição é válida
        if self.policy in upgrade_thresholds:
            target, threshold, days = upgrade_thresholds[self.policy]
            if new_policy == target and self.days_in_current_policy >= days:
                return True

        if self.policy in downgrade_thresholds:
            target, threshold, days = downgrade_thresholds[self.policy]
            if new_policy == target and self.days_in_current_policy >= days:
                return True

        return False

    @property
    def is_push(self) -> bool:
        return self.policy == PolicyState.PUSH

    @property
    def is_recover(self) -> bool:
        return self.policy == PolicyState.RECOVER
```

---

## 3. Modelos de Transporte (Middleware -> Taskwarrior) — Atualizados

### 3.1. TaskPayload — Extensao com UDAs Temporais

```python
class TaskPayload(BaseModel):
    """
    Payload validado para injeção no Taskwarrior via tasklib.
    Versao estendida com UDAs temporais e comportamentais.
    """
    description: str = Field(min_length=3, max_length=500)
    project: str = Field(description="tw_project_key hierarquico")
    tags: List[str] = Field(default_factory=list)
    priority: Optional[str] = Field(default=None, pattern=r'^(H|M|L)$')
    due: Optional[date] = None
    depends: Optional[List[str]] = Field(default=None, description="UUIDs de dependencias")
    recur: Optional[str] = Field(default=None, description="Frequencia de recorrencia (daily, weekly)")

    # UDAs existentes
    upstream_id: str = Field(description="Hash SHA-256 truncado (12 chars)")
    size: Optional[str] = Field(default=None, description="Estimativa: '1h', '4h', '2d'")
    revenue_impact: Optional[RevenueImpact] = None

    # NOVOS UDAs temporais/comportamentais
    habit_id: Optional[str] = Field(
        default=None, pattern=r'^hab_[a-z0-9_]+$',
        description="FK para HabitEntity (se task for habito)"
    )
    wave_id: Optional[str] = Field(
        default=None, pattern=r'^W\d+_[A-Za-z]{3}_\d{4}$',
        description="FK para WaveEntity"
    )
    cycle_id: Optional[str] = Field(
        default=None, pattern=r'^C\d+_\d{4}$',
        description="FK para CycleEntity"
    )
    phase_id: Optional[str] = Field(
        default=None, pattern=r'^P\d+_\d{4}$',
        description="FK para PhaseEntity"
    )
    study_plan_id: Optional[str] = Field(
        default=None, pattern=r'^study_[a-z0-9_]+$',
        description="FK para StudyPlanEntity"
    )
    policy_state: Optional[PolicyState] = Field(
        default=None,
        description="Estado da politica quando a task foi criada"
    )

    @field_validator('upstream_id')
    @classmethod
    def validate_upstream_id(cls, v: str) -> str:
        if len(v) != 12:
            raise ValueError(f"upstream_id deve ter 12 chars: {v}")
        return v
```

---

## 4. Diagrama de Dependencias (Modelos v1 + v2)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    DIAGRAMA DE DEPENDENCIAS v2                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  NIVEL ESTRATEGICO (v1)                                                │
│  ┌───────────────┐                                                      │
│  │ IKIGAiVectors │                                                      │
│  └───────┬───────┘                                                      │
│          │                                                              │
│  ┌───────▼───────┐     ┌───────────────┐     ┌───────────────┐         │
│  │  DreamEntity  │────>│ObjectiveEntity│────>│   MetaEntity  │         │
│  │     (S1)      │     │     (O2)      │     │     (M3)      │         │
│  └───────────────┘     └───────────────┘     └───────┬───────┘         │
│                                                      │ wave (FK)       │
│  NIVEL TEMPORAL (v2)                                 ▼                 │
│  ┌───────────────┐     ┌───────────────┐     ┌───────────────┐         │
│  │  PhaseEntity  │◄────│  CycleEntity  │◄────│   WaveEntity  │◄────────┘
│  │    (P1)       │     │    (C1)       │     │   (W3_Jul)    │
│  └───────┬───────┘     └───────────────┘     └───────┬───────┘
│          │ parent_dream                             │
│          │                                          │ anchor_wave
│  ┌───────▼───────┐                                  │
│  │  HabitEntity  │◄─────────────────────────────────┘
│  │  (hab_sleep)  │
│  └───────┬───────┘
│          │
│  ┌───────▼───────┐
│  │  HabitState   │──────> Q_HE computation
│  │  (diario)     │
│  └───────────────┘
│
│  ┌───────────────────┐
│  │  StudyPlanEntity  │◄──── anchor_wave
│  │ (study_backend_01)│
│  └─────────┬─────────┘
│            │
│  ┌─────────▼─────────┐     ┌─────────────────┐
│  │   StudyTopic      │     │  StudySession   │
│  │   (tp_python)     │     │  (timew sync)   │
│  └───────────────────┘     └─────────────────┘
│
│  ANALYTICS OUTPUTS
│  ┌───────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  │  QHEMetrics   │────>│ PolicyDecision  │────>│  DailyMetrics   │
│  │   (diario)    │     │   (diario)      │     │   (v1 + cols)   │
│  └───────────────┘     └─────────────────┘     └─────────────────┘
│
│  TW INJECTION
│  ┌───────────────┐
│  │  TaskPayload  │────> tasklib.inject() -> .task DB
│  │  (v2 + UDAs)  │
│  └───────────────┘
│
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Modelos de Analytics (Agregacoes) — Novos

### 5.1. WaveMetrics

```python
class WaveMetrics(BaseModel):
    """Metricas agregadas por wave (atualizadas no reverse sync noturno)."""
    wave_id: str
    
    # Consolidacao
    habit_consolidation_pct: Optional[float] = Field(ge=0.0, le=1.0)
    avg_qhe: Optional[float] = Field(ge=0.0, le=1.0)
    min_qhe: Optional[float] = Field(ge=0.0, le=1.0)
    max_qhe: Optional[float] = Field(ge=0.0, le=1.0)
    
    # Execucao
    study_days_count: int = Field(ge=0, default=0)
    work_days_count: int = Field(ge=0, default=0)
    rest_days_count: int = Field(ge=0, default=0)
    
    # Performance
    tasks_completed: int = Field(ge=0, default=0)
    tasks_created: int = Field(ge=0, default=0)
    total_hours_logged: float = Field(ge=0.0, default=0.0)
    
    computed_at: Optional[datetime] = None
```

### 5.2. ReviewTrigger

```python
class ReviewTrigger(BaseModel):
    """
    Gatilho de revisao espacada (Operador Rn).
    Executado nos dias: 7 (mid_wave), 15 (wave_end), 30 (mid_cycle), 45 (cycle_end).
    """
    entity_type: str = Field(pattern=r'^(wave|cycle|phase)$')
    entity_id: str
    review_type: ReviewType
    scheduled_date: date
    completed_date: Optional[date] = None
    status: str = Field(default="pending", pattern=r'^(pending|completed|skipped)$')
    notes: Optional[str] = None

    @property
    def is_overdue(self) -> bool:
        return self.status == "pending" and date.today() > self.scheduled_date

    @property
    def days_until(self) -> Optional[int]:
        if self.status == "pending":
            return (self.scheduled_date - date.today()).days
        return None
```

---

> NOTA: Estes modelos sao **extensao append-only** do v1. Todos os modelos v1 (DreamEntity, ObjectiveEntity, MetaEntity, ProjectEntity, TaskPayload, TaskSnapshot, TimewarriorInterval, DailyMetrics) permanecem validos. As novas entidades operam em paralelo, cross-cutting a hierarquia estrategica existente.

# Schema: Pydantic Models para Validação do Pipeline

**Versão:** 0.1.0
**Última Atualização:** 2026-05-03
**Referência:** `architecture/ADR-001-data-flow-topology.md`, `doc/03-data-mesh-enrichment.md`

Este documento define os **modelos Pydantic** que serão implementados no Middleware Python para validar todos os dados que transitam entre o Planning Domain (Markdown) e o Execution Domain (Taskwarrior/Timewarrior).

---

## 1. Modelos de Entidade (Planning Domain)

### 1.1. IKIGAiVectors — Vetores de Alinhamento Estratégico

```python
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from enum import Enum

class IKIGAiVectors(BaseModel):
    """
    Vetores do modelo IKIGAi (0.0 a 1.0).
    Representam o alinhamento de uma entidade com os 4 pilares.
    """
    passion: float = Field(ge=0.0, le=1.0, description="❤️ Paixão: quanto você ama fazer isso")
    skill: float = Field(ge=0.0, le=1.0, description="💼 Habilidade: quanto você é bom nisso")
    market: float = Field(ge=0.0, le=1.0, description="🎯 Mercado: quanto o mundo precisa disso")
    revenue: float = Field(ge=0.0, le=1.0, description="💰 Renda: quanto te pagam por isso")

    @property
    def composite_score(self) -> float:
        """Score IKIGAi ponderado igualmente entre os 4 vetores."""
        return (self.passion + self.skill + self.market + self.revenue) / 4

    @property
    def is_sweet_spot(self) -> bool:
        """Retorna True se todos os vetores estão acima de 0.7 (zona IKIGAi)."""
        return all(v >= 0.7 for v in [self.passion, self.skill, self.market, self.revenue])
```

### 1.2. EntityType — Enum de Tipos de Entidade

```python
class EntityType(str, Enum):
    DREAM = "dream"           # Nível 1: Sonho (Anual/Plurianual)
    OBJECTIVE = "objective"   # Nível 2: Objetivo (Trimestral)
    META = "meta"             # Nível 3: Meta/Sprint (Quinzenal)
    PROJECT = "project"       # Nível 4: Projeto/Épico (Semanal)
    TASK = "task"             # Nível 5: Tarefa (Atômico/Diário)
```

### 1.3. RevenueImpact — Impacto Financeiro

```python
class RevenueImpact(str, Enum):
    CRITICAL = "CRITICAL"   # Bloqueante para receita imediata
    HIGH = "HIGH"           # Impacto direto significativo
    MEDIUM = "MEDIUM"       # Impacto indireto ou de longo prazo
    LOW = "LOW"             # Sem impacto financeiro direto
    NONE = "NONE"           # Puramente pessoal/hobby
```

### 1.4. ReviewCycle — Ciclo de Revisão

```python
class ReviewCycle(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"
```

### 1.5. DreamEntity — Sonho (Nível 1)

```python
from datetime import date
from typing import List, Optional

class DreamEntity(BaseModel):
    """
    Nível 1 da hierarquia: Sonho.
    Horizonte: Anual/Plurianual.
    Exemplo: 'Fonte de Renda com Programação'
    """
    id: str = Field(pattern=r'^S\d+$', description="ID único: S1, S2, etc.")
    title: str = Field(min_length=5, max_length=200)
    entity_type: EntityType = EntityType.DREAM
    horizon: str = Field(default="annual", pattern=r'^(annual|multi_year)$')
    ikigai_vectors: IKIGAiVectors
    status: str = Field(default="active", pattern=r'^(active|paused|completed|archived)$')
    created: date
    review_cycle: ReviewCycle = ReviewCycle.QUARTERLY
    tags: List[str] = Field(default_factory=list)

    # Validação customizada
    @field_validator('id')
    @classmethod
    def validate_dream_id(cls, v: str) -> str:
        if not v.startswith('S'):
            raise ValueError(f"Dream ID deve começar com 'S': {v}")
        return v
```

### 1.6. ObjectiveEntity — Objetivo (Nível 2)

```python
class KeyResult(BaseModel):
    """Key Result dentro de um Objective (OKR parcial)."""
    kr_id: str = Field(pattern=r'^KR\d+$')
    description: str = Field(min_length=10, max_length=300)
    target: float = Field(gt=0)
    current: float = Field(ge=0, default=0)

    @property
    def progress_pct(self) -> float:
        return min((self.current / self.target) * 100, 100.0) if self.target > 0 else 0.0


class ObjectiveEntity(BaseModel):
    """
    Nível 2: Objetivo.
    Horizonte: Trimestral (Quarter).
    Referencia obrigatoriamente um Dream pai via FK.
    """
    id: str = Field(pattern=r'^O\d+$')
    title: str = Field(min_length=5, max_length=200)
    entity_type: EntityType = EntityType.OBJECTIVE
    parent_dream: str = Field(pattern=r'^S\d+$', description="FK → DreamEntity.id")
    quarter: str = Field(pattern=r'^Q[1-4]_\d{4}$', description="Ex: Q3_2026")
    key_results: List[KeyResult] = Field(default_factory=list)
    revenue_impact: RevenueImpact = RevenueImpact.MEDIUM
    status: str = Field(default="in_progress")
    created: date
    review_cycle: ReviewCycle = ReviewCycle.MONTHLY
    tags: List[str] = Field(default_factory=list)
```

### 1.7. MetaEntity — Meta/Sprint (Nível 3)

```python
class MetaEntity(BaseModel):
    """
    Nível 3: Meta/Sprint.
    Horizonte: Quinzenal (Onda/Wave).
    """
    id: str = Field(pattern=r'^M\d+$')
    title: str = Field(min_length=5, max_length=200)
    entity_type: EntityType = EntityType.META
    parent_objective: str = Field(pattern=r'^O\d+$', description="FK → ObjectiveEntity.id")
    wave: str = Field(description="Identificador da onda: W2_Jul_2026")
    duration_days: int = Field(ge=1, le=30, default=15)
    estimated_hours: float = Field(ge=0.5, le=200)
    priority: str = Field(default="P2", pattern=r'^P[1-4]$')
    status: str = Field(default="active")
    created: date
    review_cycle: ReviewCycle = ReviewCycle.WEEKLY
    tags: List[str] = Field(default_factory=list)
```

### 1.8. ProjectEntity — Projeto/Épico (Nível 4)

```python
class ProjectEntity(BaseModel):
    """
    Nível 4: Projeto/Épico.
    Horizonte: Semanal.
    Gera o tw_project_key determinístico usado no Taskwarrior.
    """
    id: str = Field(pattern=r'^proj_[a-z0-9_]+$')
    title: str = Field(min_length=3, max_length=200)
    entity_type: EntityType = EntityType.PROJECT
    parent_meta: str = Field(pattern=r'^M\d+$', description="FK → MetaEntity.id")
    parent_objective: str = Field(pattern=r'^O\d+$', description="FK → ObjectiveEntity.id")
    parent_dream: str = Field(pattern=r'^S\d+$', description="FK → DreamEntity.id")
    revenue_impact: RevenueImpact = RevenueImpact.MEDIUM
    estimated_size: str = Field(description="Estimativa: '4h', '2d', '1w'")
    status: str = Field(default="active")
    created: date
    tags: List[str] = Field(default_factory=list)

    @property
    def tw_project_key(self) -> str:
        """
        Gera a chave de projeto hierárquica para o Taskwarrior.
        Formato: S1.O2.M3.proj_alfa_01
        """
        return f"{self.parent_dream}.{self.parent_objective}.{self.parent_meta}.{self.id}"
```

---

## 2. Modelos de Transporte (Middleware → Taskwarrior)

### 2.1. TaskPayload — Payload de Injeção no TW

```python
import hashlib
from typing import Optional, List

class TaskPayload(BaseModel):
    """
    Payload validado que será injetado no Taskwarrior via tasklib.
    Cada campo mapeia 1:1 para um atributo TW (built-in ou UDA).
    """
    description: str = Field(min_length=3, max_length=500)
    project: str = Field(description="tw_project_key: S1.O2.M3.proj_alfa_01")
    tags: List[str] = Field(default_factory=list)
    priority: Optional[str] = Field(default=None, pattern=r'^(H|M|L)$')
    due: Optional[date] = None
    depends: Optional[List[str]] = Field(default=None, description="UUIDs de dependências no TW")

    # UDAs customizados (injetados como atributos extras)
    upstream_id: str = Field(description="Hash SHA-256 truncado: FK para o Planning")
    size: Optional[str] = Field(default=None, description="Estimativa: '1h', '4h', '2d'")
    revenue_impact: Optional[RevenueImpact] = None

    @field_validator('upstream_id')
    @classmethod
    def validate_upstream_id(cls, v: str) -> str:
        if len(v) != 12:
            raise ValueError(f"upstream_id deve ter 12 chars (SHA-256 truncado): {v}")
        return v

    @staticmethod
    def generate_upstream_id(project_id: str, task_index: int) -> str:
        """
        Gera um upstream_id determinístico a partir do project_id + index.
        Garante idempotência: re-executar o pipeline não cria duplicatas.
        """
        raw = f"{project_id}::{task_index}"
        return hashlib.sha256(raw.encode()).hexdigest()[:12]
```

---

## 3. Modelos de Telemetria (Taskwarrior/Timewarrior → Analytics)

### 3.1. TaskSnapshot — Snapshot de uma Task Exportada

```python
from datetime import datetime

class TaskSnapshot(BaseModel):
    """
    Representa uma task exportada do TW (via task export).
    Usado para o Reverse Sync e cálculos analíticos.
    """
    uuid: str
    description: str
    status: str = Field(pattern=r'^(pending|completed|deleted|waiting|recurring)$')
    project: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    priority: Optional[str] = None
    entry: datetime
    end: Optional[datetime] = None
    due: Optional[date] = None
    upstream_id: Optional[str] = None
    urgency: Optional[float] = None

    @property
    def is_orphan(self) -> bool:
        """Task é órfã se não tem upstream_id (criada ad-hoc no CLI)."""
        return self.upstream_id is None

    @property
    def duration_hours(self) -> Optional[float]:
        """Duração em horas (entry → end), se completada."""
        if self.end and self.entry:
            delta = self.end - self.entry
            return delta.total_seconds() / 3600
        return None
```

### 3.2. TimewarriorInterval — Intervalo de Tempo

```python
class TimewarriorInterval(BaseModel):
    """
    Um intervalo de tracking do Timewarrior (timew export).
    """
    id: int
    start: datetime
    end: Optional[datetime] = None
    tags: List[str] = Field(default_factory=list)

    @property
    def duration_minutes(self) -> Optional[float]:
        if self.end:
            return (self.end - self.start).total_seconds() / 60
        return None

    @property
    def ikigai_phase(self) -> Optional[str]:
        """Infere a fase IKIGAi pelas tags do intervalo."""
        phase_map = {
            "deepwork": "phase:learn",
            "laborative": "phase:earn",
            "training": "phase:train",
            "content": "phase:share",
            "review": "phase:review",
        }
        for tag in self.tags:
            normalized = tag.lower().replace(" ", "")
            if normalized in phase_map:
                return phase_map[normalized]
        return None
```

---

## 4. Modelos de Analytics (Agregações e Métricas)

### 4.1. DailyMetrics — Métricas Consolidadas do Dia

```python
class DailyMetrics(BaseModel):
    """
    Agregação diária de todas as métricas do Hypervisor.
    Armazenado como uma row no SQLite (analytics store).
    """
    date: date
    # Inputs manuais (Morning Survey)
    sleep_hours: Optional[float] = Field(ge=0, le=24, default=None)
    energy_level: Optional[int] = Field(ge=1, le=10, default=None)

    # Métricas computadas (Reverse Sync)
    pomodoros_completed: int = Field(ge=0, default=0)
    tasks_completed: int = Field(ge=0, default=0)
    tasks_created: int = Field(ge=0, default=0)
    orphan_tasks_detected: int = Field(ge=0, default=0)

    # Horas por fase IKIGAi
    hours_learn: float = Field(ge=0, default=0.0)
    hours_earn: float = Field(ge=0, default=0.0)
    hours_train: float = Field(ge=0, default=0.0)
    hours_share: float = Field(ge=0, default=0.0)
    hours_review: float = Field(ge=0, default=0.0)

    # Métricas derivadas
    @property
    def total_hardwork_hours(self) -> float:
        return self.hours_learn + self.hours_earn + self.hours_train + self.hours_share + self.hours_review

    @property
    def efficiency_ratio(self) -> Optional[float]:
        """η = hardwork_real / setpoint_previsto"""
        # O setpoint depende do estado do dia (Concorrência vs Dedicação)
        # Será injetado em runtime pelo Hypervisor
        return None
```

---

## 5. Diagrama de Dependências entre Modelos

```
┌───────────────┐
│ IKIGAiVectors │ ← Usado por DreamEntity
└───────┬───────┘
        │
┌───────▼───────┐
│  DreamEntity  │ ← Raiz da hierarquia (Nível 1)
│  id: S1       │
└───────┬───────┘
        │ parent_dream (FK)
┌───────▼───────────┐
│ ObjectiveEntity   │ ← Nível 2
│ id: O2            │
│ key_results: [KR] │
└───────┬───────────┘
        │ parent_objective (FK)
┌───────▼───────────┐
│   MetaEntity      │ ← Nível 3
│   id: M3          │
└───────┬───────────┘
        │ parent_meta (FK)
┌───────▼───────────┐
│  ProjectEntity    │ ← Nível 4 (gera tw_project_key)
│  id: proj_alfa_01 │
└───────┬───────────┘
        │ tw_project_key
┌───────▼───────────┐
│   TaskPayload     │ ← Injetado no TW (Nível 5)
│   upstream_id     │
└───────┬───────────┘
        │ reverse sync
┌───────▼───────────┐    ┌──────────────────┐
│  TaskSnapshot     │───►│  DailyMetrics    │
│  (TW export)      │    │  (Agregado)      │
└───────────────────┘    └──────────────────┘
        ▲
        │ JOIN via tags
┌───────┴───────────────┐
│ TimewarriorInterval   │
│ (timew export)        │
└───────────────────────┘
```

---

> 💡 **NOTA:** Estes modelos são **especificações** — o código Python real será implementado em `life/vibe-ops/src/` seguindo esta spec como contrato. Alterações nos modelos devem ser refletidas em `CHANGELOG.md`.

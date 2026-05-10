# PRD-04: Project Execution Engine
**Versão:** 1.0.0 | **Status:** Draft | **Data:** 2026-05-10

> **Standalone Memory Machine** — Especificação autônoma do subgrafo de execução de projetos. Cobre: SoftwareProject → Epic → Sprint → Task → Taskwarrior. Um agente CLI pode ler apenas este PRD e operar o domínio completamente.

---

## 1. Hierarquia de Entidades

```
IKIGAi Vectors
    └── SoftwareProject / StudyProject
            └── Epic
                    └── Sprint
                            └── Task ←→ Taskwarrior (sync bidirecional)
                                    └── TimewarriorEntry (tracking)
```

---

## 2. Modelos Pydantic

### SoftwareProject
```python
class SoftwareProject(BaseModel):
    id: UUID
    slug: str                        # kebab-case único
    title: str
    description: str
    status: ProjectStatus            # BACKLOG|ACTIVE|PAUSED|COMPLETED|ARCHIVED
    vector_tags: list[IKIGAiVector]  # passion|skill|market|revenue
    tech_stack: list[str]
    repo_url: Optional[str]
    target_revenue: Optional[float]  # R$/mês esperado
    actual_revenue: float = 0.0
    created_at: datetime
    deadline: Optional[date]
    priority: int = Field(ge=1, le=10)
    tags: list[str] = []
```

### Epic + Sprint
```python
class Epic(BaseModel):
    id: UUID
    project_id: UUID
    title: str
    status: EpicStatus               # PLANNED|IN_PROGRESS|DONE|CANCELLED
    acceptance_criteria: list[str]
    estimated_hours: float
    actual_hours: float = 0.0
    weight: float = 1.0

class Sprint(BaseModel):
    id: UUID
    epic_id: UUID
    name: str
    goal: str
    start_date: date
    end_date: date
    status: SprintStatus             # PLANNED|ACTIVE|REVIEW|DONE
    velocity_target: Optional[int]
    velocity_actual: int = 0
    retrospective: Optional[str]
```

### Task (central)
```python
class Task(BaseModel):
    id: UUID
    tw_uuid: Optional[str]           # UUID Taskwarrior (sync)
    sprint_id: Optional[UUID]
    title: str
    status: TaskStatus               # TODO|IN_PROGRESS|DONE|BLOCKED|CANCELLED
    priority: TaskPriority           # H|M|L
    tags: list[str] = []
    project_tag: str                 # campo project: do Taskwarrior
    due: Optional[datetime]
    estimate_hours: Optional[float]
    actual_hours: float = 0.0
    depends_on: list[UUID] = []
    # UDAs Taskwarrior
    uda_energy: Optional[EnergyLevel]     # H|M|L
    uda_context: Optional[str]            # work|study|life
    uda_ikigai: Optional[IKIGAiVector]
    uda_wave: Optional[str]
```

### TimewarriorEntry
```python
class TimewarriorEntry(BaseModel):
    id: str
    task_id: Optional[UUID]
    tw_uuid: Optional[str]
    tags: list[str]
    start: datetime
    end: Optional[datetime]
    duration_minutes: Optional[float]
    date: date
```

---

## 3. Frontmatter YAML (Tasks em Markdown)

```yaml
---
type: task
id: "uuid"
title: "Implementar JWT auth"
sprint: "sprint-01-auth"
project: "petroshield"
status: in_progress
priority: H
energy: H
due: "2026-05-20"
estimate_hours: 4
tags: [backend, security]
ikigai: revenue
wave: "wave-2026-q2"
---
```

---

## 4. Mapeamento Taskwarrior ↔ vibe-ops

| vibe-ops | Taskwarrior | Tipo |
|:---|:---|:---|
| `title` | `description` | string |
| `status` | `status` | pending/completed |
| `priority` | `priority` | H/M/L |
| `due` | `due` | date |
| `tags` | `tags` | list |
| `project_tag` | `project` | string |
| `uda_energy` | `energy` (UDA) | H/M/L |
| `uda_ikigai` | `ikigai` (UDA) | string |
| `uda_wave` | `wave` (UDA) | string |

### UDAs Requeridas (taskrc)
```ini
uda.energy.type=string
uda.energy.label=Energy
uda.energy.values=H,M,L

uda.ikigai.type=string
uda.ikigai.label=IKIGAi Vector
uda.ikigai.values=passion,skill,market,revenue

uda.wave.type=string
uda.wave.label=Wave
```

---

## 5. Eventos Data-Mesh

| Evento Emitido | Trigger |
|:---|:---|
| `task.completed` | task → DONE |
| `sprint.closed` | sprint → DONE com velocity |
| `epic.completed` | epic → DONE |
| `project.milestone` | flag manual |

| Evento Consumido | Origem | Ação |
|:---|:---|:---|
| `wave.phase_changed` | TemporalEngine | reordena sprint ativo |
| `policy.alert` | PolicyEngine | pausa tasks baixa prioridade |
| `metric.energy_low` | MetricsEngine | reagenda tasks H-energy |

---

## 6. Algoritmos

### Sprint Velocity
```
velocity_actual = Σ(story_points tasks concluídas)
velocity_avg = média das últimas 3 sprints
```

### Epic Burndown + ETA
```
remaining = Σ(estimate_hours) - Σ(actual_hours tasks done)
burn_rate = done_work / dias_decorridos
eta = remaining / burn_rate
```

### ROI de Tempo
```
time_invested = Σ(TimewarriorEntry.duration_minutes) / 60
roi = actual_revenue / time_invested  # R$/hora
```

---

## 7. CLI Interface

```bash
vibe-ops projects list --status active
vibe-ops projects burndown --epic <id>
vibe-ops projects roi --month 2026-05
vibe-ops tasks create --sprint <id> --title "..." --priority H
vibe-ops sprints close --sprint <id>
vibe-ops tw sync --direction both
```

---

## 8. Módulos

| Arquivo | Responsabilidade |
|:---|:---|
| `src/models/project_entities.py` | Modelos Pydantic (expandir) |
| `src/pipeline/tw_sync.py` | Sync bidirecional Taskwarrior |
| `src/pipeline/burndown.py` | Velocity + ETA |
| `src/pipeline/time_roi.py` | ROI R$/hora |

---

*PRD-04 — Project Execution Engine | vibe-ops v1.0.0 | 2026-05-10*

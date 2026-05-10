# PRD-06: Policy & Governance Engine
**Versão:** 1.0.0 | **Status:** Draft | **Data:** 2026-05-10

> **Standalone Memory Machine** — Especificação autônoma do subgrafo de políticas e governança. Cobre: PolicyRule → PolicyAlert → PolicyAction → GovernanceLog. Implementa a lógica PUSH/MAINTAIN/REDUCE/RECOVER do sistema.

---

## 1. Propósito

O **PolicyEngine** é o sistema nervoso autônomo do Data-Mesh — o "piloto automático" que ajusta comportamentos baseado em sinais agregados. Ele:

- Avalia regras sobre métricas consolidadas e emite ações automatizadas
- Implementa os 4 modos operacionais: PUSH, MAINTAIN, REDUCE, RECOVER
- Gera recomendações táticas baseadas no estado atual do sistema
- Registra toda tomada de decisão em log auditável (GovernanceLog)
- Serve como "guardião de limites" para evitar burnout e garantir sustentabilidade

---

## 2. Modos Operacionais

### PUSH Mode
**Quando:** energy_score > 80, habit_compliance > 80%, sleep_debt < 2h
**Ação:** Aumentar carga de trabalho, adicionar tarefas de alto impacto, estender sessões de foco
```
sprint_velocity_target *= 1.2
allow_tasks.priority = [H, M]
study_sessions_target += 1
```

### MAINTAIN Mode
**Quando:** condições normais, sem alertas críticos
**Ação:** Manter ritmo atual, não adicionar nem remover
```
sprint_velocity_target = velocity_avg_7d
allow_tasks.priority = [H, M, L]
```

### REDUCE Mode
**Quando:** energy_score < 50, OU habit_compliance < 60%, OU sleep_debt > 4h
**Ação:** Reduzir carga, focar apenas em tarefas críticas
```
sprint_velocity_target *= 0.7
allow_tasks.priority = [H]  # apenas urgentes
study_sessions_target = max(1, study_target - 1)
```

### RECOVER Mode
**Quando:** energy_score < 30, OU sleep_debt > 8h, OU streak_broken_critical
**Ação:** Modo mínimo — apenas hábitos essenciais e descanso
```
sprint_velocity_target *= 0.4
allow_tasks.priority = []   # apenas manutenção
enforce_bedtime = True
cancel_optional_habits = True
```

---

## 3. Modelos Pydantic

### PolicyRule
```python
class PolicyRule(BaseModel):
    id: UUID
    name: str
    description: str
    category: PolicyCategory         # ENERGY|SLEEP|HABITS|PRODUCTIVITY|FINANCE
    trigger_conditions: list[PolicyCondition]
    actions: list[PolicyAction]
    severity: PolicySeverity         # INFO|WARNING|CRITICAL|OVERRIDE
    active: bool = True
    cooldown_hours: int = 24         # horas antes de re-disparar
    last_triggered: Optional[datetime]

class PolicyCategory(str, Enum):
    ENERGY = "energy"
    SLEEP = "sleep"
    HABITS = "habits"
    PRODUCTIVITY = "productivity"
    FINANCE = "finance"
    TEMPORAL = "temporal"

class PolicySeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    OVERRIDE = "override"            # bloqueia ações incompatíveis
```

### PolicyCondition
```python
class PolicyCondition(BaseModel):
    metric: str                      # ex: "energy_score", "sleep_debt_hours"
    operator: ConditionOperator      # GT|LT|GTE|LTE|EQ|NEQ
    threshold: float
    window_days: int = 1             # janela de avaliação

class ConditionOperator(str, Enum):
    GT = "gt"
    LT = "lt"
    GTE = "gte"
    LTE = "lte"
    EQ = "eq"
    NEQ = "neq"
```

### PolicyAction
```python
class PolicyAction(BaseModel):
    action_type: ActionType
    params: dict[str, Any] = {}
    notification_message: Optional[str]
    auto_execute: bool = False       # True = executa sem aprovação humana

class ActionType(str, Enum):
    SET_MODE = "set_mode"                    # mudar modo operacional
    PAUSE_PROJECT = "pause_project"          # pausar projeto
    RESCHEDULE_TASKS = "reschedule_tasks"    # reagendar tasks
    SEND_ALERT = "send_alert"                # notificação
    ADJUST_SPRINT = "adjust_sprint"          # ajustar sprint target
    ENFORCE_HABIT = "enforce_habit"          # marcar hábito como crítico
    BLOCK_NEW_TASKS = "block_new_tasks"      # bloquear criação de tasks
    TRIGGER_REVIEW = "trigger_review"        # pedir revisão manual
```

### PolicyAlert
```python
class PolicyAlert(BaseModel):
    id: UUID
    rule_id: UUID
    triggered_at: datetime
    severity: PolicySeverity
    message: str
    metric_snapshot: dict[str, float]    # valores no momento do trigger
    actions_taken: list[str]
    resolved: bool = False
    resolved_at: Optional[datetime]
    resolution_notes: Optional[str]
```

### OperationalMode (estado atual)
```python
class OperationalMode(BaseModel):
    mode: ModeType                   # PUSH|MAINTAIN|REDUCE|RECOVER
    activated_at: datetime
    reason: str
    triggered_by_rule: Optional[UUID]
    expires_at: Optional[datetime]   # None = indefinido até nova avaliação
    constraints: ModeConstraints

class ModeType(str, Enum):
    PUSH = "push"
    MAINTAIN = "maintain"
    REDUCE = "reduce"
    RECOVER = "recover"

class ModeConstraints(BaseModel):
    max_daily_tasks: Optional[int]
    allowed_priorities: list[str]    # ["H"] no REDUCE
    sprint_velocity_multiplier: float = 1.0
    enforce_bedtime: bool = False
    block_new_projects: bool = False
    study_sessions_delta: int = 0    # +1 no PUSH, -1 no REDUCE
```

### GovernanceLog
```python
class GovernanceLog(BaseModel):
    id: UUID
    timestamp: datetime
    event_type: GovernanceEvent
    rule_id: Optional[UUID]
    mode_before: Optional[ModeType]
    mode_after: Optional[ModeType]
    metrics_snapshot: dict[str, float]
    decision: str                    # descrição da decisão tomada
    actions_executed: list[str]
    auto_executed: bool
    human_override: bool = False
    notes: Optional[str]

class GovernanceEvent(str, Enum):
    MODE_CHANGED = "mode_changed"
    RULE_TRIGGERED = "rule_triggered"
    ALERT_SENT = "alert_sent"
    HUMAN_OVERRIDE = "human_override"
    REVIEW_REQUESTED = "review_requested"
    COOLDOWN_RESET = "cooldown_reset"
```

---

## 4. Regras Pré-definidas (Defaults)

```python
DEFAULT_RULES = [
    PolicyRule(
        name="energy_critical_recover",
        description="Ativa RECOVER quando energia crítica por 2 dias",
        category=PolicyCategory.ENERGY,
        trigger_conditions=[
            PolicyCondition(metric="avg_energy_score", operator="lt", threshold=30, window_days=2)
        ],
        actions=[PolicyAction(action_type=ActionType.SET_MODE, params={"mode": "recover"})],
        severity=PolicySeverity.CRITICAL,
    ),
    PolicyRule(
        name="sleep_debt_warning",
        description="WARNING quando dívida de sono > 4h",
        category=PolicyCategory.SLEEP,
        trigger_conditions=[
            PolicyCondition(metric="sleep_debt_hours", operator="gt", threshold=4)
        ],
        actions=[
            PolicyAction(action_type=ActionType.SET_MODE, params={"mode": "reduce"}),
            PolicyAction(action_type=ActionType.SEND_ALERT, notification_message="Dívida de sono crítica!")
        ],
        severity=PolicySeverity.WARNING,
    ),
    PolicyRule(
        name="high_performance_push",
        description="Ativa PUSH quando tudo está ótimo",
        category=PolicyCategory.PRODUCTIVITY,
        trigger_conditions=[
            PolicyCondition(metric="avg_energy_score", operator="gte", threshold=80, window_days=3),
            PolicyCondition(metric="habit_compliance_pct", operator="gte", threshold=80, window_days=3),
        ],
        actions=[PolicyAction(action_type=ActionType.SET_MODE, params={"mode": "push"})],
        severity=PolicySeverity.INFO,
    ),
]
```

---

## 5. Fluxo de Avaliação

```
1. [Trigger] Evento recebido (daily_consolidated, task.completed, etc.)
2. [Evaluate] Para cada PolicyRule ativa:
   a. Checar cooldown (last_triggered + cooldown_hours)
   b. Avaliar todas conditions (AND lógico por padrão)
   c. Se condições satisfeitas → coletar actions
3. [Priority] Ordenar actions por severity (OVERRIDE > CRITICAL > WARNING > INFO)
4. [Execute] Para cada action:
   a. auto_execute=True → executar imediatamente
   b. auto_execute=False → adicionar à fila de aprovação humana
5. [Log] Registrar tudo no GovernanceLog
6. [Emit] Emitir evento policy.action para demais subgrafos
```

---

## 6. Eventos Data-Mesh

| Evento Emitido | Dados |
|:---|:---|
| `policy.mode_changed` | mode_before, mode_after, reason |
| `policy.alert` | alert_id, severity, message |
| `policy.action.reschedule` | tasks afetadas |
| `policy.review_requested` | snapshot de métricas |

| Evento Consumido | Origem |
|:---|:---|
| `metric.daily_consolidated` | MetricsEngine |
| `metric.energy_low` | MetricsEngine |
| `habit.streak_broken` | HabitTracker |
| `wave.phase_changed` | TemporalEngine |

---

## 7. CLI Interface

```bash
# Status do modo atual
vibe-ops policy status

# Listar regras ativas
vibe-ops policy rules list

# Forçar avaliação agora
vibe-ops policy evaluate --metrics-date today

# Ver alertas pendentes
vibe-ops policy alerts --unresolved

# Override manual de modo
vibe-ops policy mode set --mode reduce --reason "Semana de provas"

# Histórico de decisões
vibe-ops policy log --last 7d
```

---

## 8. Módulos

| Arquivo | Responsabilidade |
|:---|:---|
| `src/models/policy_entities.py` | Modelos Pydantic (expandir) |
| `src/pipeline/policy_engine.py` | Avaliador de regras (novo) |
| `src/pipeline/governance_log.py` | Registro auditável (novo) |

---

*PRD-06 — Policy & Governance Engine | vibe-ops v1.0.0 | 2026-05-10*

# LangGraph Patterns Research — Always-On Planning Agent (PAE System)

**Date:** 2026-06-30
**Context:** agentic-markdown-system plan — dual-channel, PAE hierarchy, Q_HE hysteresis, swarm dispatch
**Sources:** LangGraph Official Docs · langchain-ai/langgraph (v1.0.8, 0.4.8)

---

## 1. Recommended Graph Topology

### 1.1 Core State Schema (Pydantic v2)

```python
from pydantic import BaseModel, Field
from typing import Annotated, Literal
from enum import Enum
import operator

class PolicyState(str, Enum):
    PUSH = "push"; MAINTAIN = "maintain"; REDUCE = "reduce"; RECOVER = "recover"

class PAEPhase(str, Enum):
    PLANEJAMENTO = "planejamento"
    AVALIACAO = "avaliacao"
    EXECUCAO = "execucao"

class CorrectionSignal(BaseModel):
    kill_switch: bool = False
    test_de_fogo_drift: float = 0.0
    sustained_recover: bool = False
    severity: Literal["critical", "high", "medium", "low"] = "low"

class PAEState(BaseModel):
    phase: PAEPhase = PAEPhase.PLANEJAMENTO
    prospective_buffer: Annotated[list[str], operator.add] = Field(default_factory=list)
    retrospective_log: Annotated[list[str], operator.add] = Field(default_factory=list)
    q_he_score: float = 0.5
    policy_state: PolicyState = PolicyState.MAINTAIN
    streak: int = 0
    corrections: Annotated[list[CorrectionSignal], operator.add] = Field(default_factory=list)
    swarm_dispatch: bool = False
    swarm_trigger: Literal["kill_switch", "drift", "recover", None] = None
    depth: int = 0
    pending_tasks: Annotated[list[str], operator.add] = Field(default_factory=list)
```

### 1.2 Node Architecture (5 Core Nodes)

```
PROSPECTIVE CHANNEL (observe -> plan -> commit)

OBSERVE ---> PLAN ---> COMMIT
                    |
                    v
              BALANCE (hysteresis + 5x3x3)
                    |
RETROSPECTIVE <-----+-----> (balance -> reflect -> observe)
```

### 1.3 Dual-Channel Edge Routing

```python
from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

def route_retrospective(state: PAEState) -> Literal["reflect", "__end__"]:
    if state.phase == PAEPhase.EXECUCAO:
        return "reflect"
    return "__end__"

def route_corrections(state: PAEState) -> Literal["swarm_dispatch", "__end__"]:
    if state.corrections and any([c.kill_switch for c in state.corrections]):
        return "swarm_dispatch"
    return "__end__"
```

---

## 2. Key Patterns to Apply

### 2.1 Checkpoint + Persistence (for always-on)

```python
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.postgres import PostgresSaver

checkpointer = InMemorySaver()  # dev
checkpointer = PostgresSaver.from_conn_string("postgresql://...")  # prod

app = workflow.compile(checkpointer=checkpointer)
result = app.invoke(
    input={"phase": "continue"},
    config={"configurable": {"thread_id": "pae-agent-001"}}
)
```

**Evidence:** [InMemorySaver source](https://github.com/langchain-ai/langgraph/blob/main/langgraph/libs/checkpoint/langgraph/checkpoint/memory/__init__.py)

### 2.2 Conditional Edge Dispatch (for swarm triggers)

```python
from langgraph.types import Send

def swarm_dispatcher(state: PAEState) -> list[Send]:
    sends = []
    for corr in state.corrections:
        if corr.kill_switch:
            sends.append(Send("kill_switch_agent", {"signal": corr}))
        if corr.test_de_fogo_drift > 0.7:
            sends.append(Send("drift_correction_agent", {"drift": corr.test_de_fogo_drift}))
        if corr.sustained_recover:
            sends.append(Send("recover_agent", {"policy": state.policy_state}))
    return sends
```

**Evidence:** [Multi-Agent Spawning with Send](https://github.com/langchain-ai/langgraph/blob/main/langgraph/libs/langgraph/tests/test_pregel.py#L1710-L1744)

### 2.3 Human-in-the-Loop (for kill-switch approval)

```python
from langgraph.types import interrupt

def kill_switch_node(state: dict) -> dict:
    response = interrupt([{
        "action_request": {"action": "emergency_stop", "args": {"reason": state.get("reason")}},
        "config": {"allow_ignore": False, "allow_respond": True, "allow_edit": False},
        "description": f"EMERGENCY STOP. Q_HE={state[ q_he_score]}"
    }])
    return {"approved": response[0]["type"] == "response"}
```

**Evidence:** [Human Interrupt in LangGraph](https://github.com/langchain-ai/langgraph/blob/main/libs/prebuilt/README.md)

### 2.4 Memory Store (cross-thread persistence)

```python
from langgraph.store.memory import MemoryStore

store = MemoryStore()

def reflect_node(state: PAEState) -> dict:
    past_entries = store.get(
        namespace=("pae", state.get("thread_id", "default")),
        key="retrospective_log"
    )
    return {"insights": synthesize(past_entries, state.retrospective_log)}
```

**Evidence:** [Persistent Cross-Thread Memory with Store](https://github.com/langchain-ai/langgraph/blob/main/langgraph/libs/checkpoint/langgraph/store/base/__init__.py)

### 2.5 Pydantic v2 State (native support)

```python
class PAEState(BaseModel):
    prospective_buffer: Annotated[list[str], operator.add] = Field(default_factory=list)
    corrections: Annotated[list[CorrectionSignal], operator.add] = Field(default_factory=list)
    q_he_score: Annotated[float, Field(ge=0.0, le=1.0)]
```

**Evidence:** [Advanced Pydantic State](https://github.com/langchain-ai/langgraph/blob/main/langgraph/libs/langgraph/tests/test_pydantic.py)

---

## 3. Code Snippets for 5 Core Nodes

### 3.1 OBSERVE Node

```python
def observe_node(state: PAEState) -> dict:
    current_habits = read_habit_sensors()
    current_tasks = read_task_sensors()
    observation = format_observation(
        habits=current_habits, tasks=current_tasks, policy=state.policy_state
    )
    return {
        "prospective_buffer": [f"[OBSERVE] {observation}"],
        "phase": PAEPhase.PLANEJAMENTO,
        "depth": state.depth + 1
    }
```

### 3.2 PLAN Node

```python
def plan_node(state: PAEState) -> dict:
    plan = generate_prospective_plan(
        buffer=state.prospective_buffer,
        q_he_target=get_q_he_target(state.policy_state),
        hardwork_budget=get_budget(state.policy_state)
    )
    return {
        "prospective_buffer": [f"[PLAN] {plan}"],
        "pending_tasks": plan.task_list,
        "phase": PAEPhase.EXECUCAO
    }
```

### 3.3 COMMIT Node

```python
def commit_node(state: PAEState) -> dict:
    results = execute_tasks(state.pending_tasks)
    return {
        "retrospective_log": [
            f"[COMMIT] Executed {len(results)} tasks",
            *[f"  -> {r}" for r in results]
        ],
        "phase": PAEPhase.AVALIACAO,
        "pending_tasks": []
    }
```

### 3.4 BALANCE Node (Hysteresis + 5x3x3)

```python
def balance_node(state: PAEState) -> dict:
    q_he = compute_q_he(state)
    new_policy = apply_hysteresis(
        state.policy_state, q_he, state.streak,
        deviation_threshold=0.15, streak_threshold=3
    )
    proportionality = check_5x3x3(
        state.policy_state, len(state.pending_tasks), get_budget(new_policy)
    )
    corrections = []
    if not proportionality.valid:
        corrections.append(CorrectionSignal(
            test_de_fogo_drift=proportionality.drift_score, severity="medium"
        ))
    if q_he < 0.2 and state.streak > 7:
        corrections.append(CorrectionSignal(kill_switch=True, severity="critical"))
    return {
        "q_he_score": q_he,
        "policy_state": new_policy,
        "corrections": corrections,
        "phase": PAEPhase.EXECUCAO
    }
```

### 3.5 REFLECT Node

```python
def reflect_node(state: PAEState) -> dict:
    delta = compute_delta(
        planned=state.prospective_buffer,
        executed=state.retrospective_log
    )
    new_streak = update_streak(current=state.streak, delta=delta.execution_ratio)
    return {
        "retrospective_log": [f"[REFLECT] delta={delta.summary}"],
        "streak": new_streak,
        "phase": PAEPhase.PLANEJAMENTO
    }
```

---

## 4. Library Recommendations

| Component | Recommendation | Version |
|-----------|---------------|---------|
| Core LangGraph | langgraph (langchain-ai) | v1.0.8 |
| Checkpoint dev | langgraph.checkpoint.memory.InMemorySaver | bundled |
| Checkpoint prod | langgraph-checkpoint-postgres | latest |
| Store prod | langgraph-store + langgraph-checkpoint-redis | latest |
| Pydantic | pydantic>=2.0 | bundled |

---

## 5. Anti-Patterns to Avoid

| Anti-Pattern | Problem | Correct |
|--------------|---------|---------|
| Using interrupt without checkpointer | State lost on restart | Always pair with PostgresSaver |
| Returning None from node | State channel gets None | Always return dict |
| Mutable default arguments | Shared state across invocations | Use Field(default_factory=...) |
| Blocking LLM calls in hot path | Graph hangs | Use async or subprocess |
| Single large node | No checkpoint granularity | Split into smaller nodes |
| Hardcoding thread_id | No multi-user sessions | Use configurable thread_id |

---

## 6. Complexity Estimates

| Node | Complexity | Reasoning |
|------|-----------|-----------|
| OBSERVE | Medium | I/O bound (sensors) |
| PLAN | High | LLM/algorithm bottleneck |
| COMMIT | Medium | Task execution |
| BALANCE | Low | Pure arithmetic <10ms |
| REFLECT | Medium | Log aggregation |
| swarm_dispatch | High | Parallel fan-out |

---

## 7. Key GitHub References

| Pattern | URL |
|---------|-----|
| Checkpoint saver | https://github.com/langchain-ai/langgraph/blob/main/libs/checkpoint/README.md |
| InMemorySaver | https://github.com/langchain-ai/langgraph/blob/main/langgraph/libs/checkpoint/langgraph/checkpoint/memory/__init__.py |
| Send fan-out | https://github.com/langchain-ai/langgraph/blob/main/langgraph/libs/langgraph/tests/test_pregel.py#L1710 |
| Human interrupt | https://github.com/langchain-ai/langgraph/blob/main/libs/prebuilt/README.md |
| Pydantic state | https://github.com/langchain-ai/langgraph/blob/main/langgraph/libs/langgraph/tests/test_pydantic.py |
| Store base | https://github.com/langchain-ai/langgraph/blob/main/langgraph/libs/checkpoint/langgraph/store/base/__init__.py |

---

*Research compiled from LangGraph v1.0.8 source and official documentation.*

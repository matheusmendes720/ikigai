"""Execution state store — persists workflow runs to JSON files.

Per /workflow-orchestrator skill: ExecutionState, execution history,
state serialization to ~/.time-tasker/agent_harness/executions/.
"""

from __future__ import annotations

import json
import threading
from datetime import datetime, UTC
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class ExecutionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskExecution(BaseModel):
    task_id: str
    task_name: str = ""
    status: ExecutionStatus = ExecutionStatus.PENDING
    start_time: str | None = None
    end_time: str | None = None
    duration_ms: int | None = None
    exit_code: int | None = None
    stdout_preview: str = ""
    stderr_preview: str = ""
    result: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    attempt: int = Field(default=1)
    retries: int = Field(default=0)

    def duration_s(self) -> float | None:
        if self.duration_ms is not None:
            return self.duration_ms / 1000
        return None


class ExecutionState(BaseModel):
    execution_id: str = Field(description="Unique execution ID, e.g. 'exec_abc123'")
    workflow_name: str
    workflow_path: str
    status: ExecutionStatus = ExecutionStatus.PENDING
    start_time: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    end_time: str | None = None
    duration_ms: int | None = None
    trigger: str = "manual"
    tasks: dict[str, TaskExecution] = Field(default_factory=dict)
    task_order: list[str] = Field(default_factory=list)
    completed_tasks: list[str] = Field(default_factory=list)
    failed_tasks: list[str] = Field(default_factory=list)
    context: dict[str, Any] = Field(default_factory=dict, description="Shared execution context / variables")

    def duration_s(self) -> float | None:
        if self.duration_ms is not None:
            return self.duration_ms / 1000
        return None


class ExecutionStore:
    """File-backed execution history — one JSON file per execution run.

    Stored in: ~/.time-tasker/agent_harness/executions/{workflow_name}/{execution_id}.json
    """

    def __init__(self, base_dir: Path | None = None):
        if base_dir is None:
            base_dir = Path.home() / ".time-tasker" / "agent_harness" / "executions"
        self.base_dir = base_dir
        self._lock = threading.RLock()

    def _exec_dir(self, workflow_name: str) -> Path:
        d = self.base_dir / workflow_name.replace(" ", "_")
        d.mkdir(parents=True, exist_ok=True)
        return d

    def save(self, state: ExecutionState) -> None:
        path = self._exec_dir(state.workflow_name) / f"{state.execution_id}.json"
        with self._lock:
            path.write_text(state.model_dump_json(indent=2), encoding="utf-8")

    def load(self, workflow_name: str, execution_id: str) -> ExecutionState | None:
        path = self._exec_dir(workflow_name) / f"{execution_id}.json"
        if not path.exists():
            return None
        return ExecutionState.model_validate_json(path.read_text(encoding="utf-8"))

    def list_executions(
        self,
        workflow_name: str,
        limit: int = 20,
        status: ExecutionStatus | None = None,
    ) -> list[ExecutionState]:
        exec_dir = self._exec_dir(workflow_name)
        if not exec_dir.exists():
            return []
        states: list[ExecutionState] = []
        for path in sorted(exec_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:limit]:
            try:
                state = ExecutionState.model_validate_json(path.read_text(encoding="utf-8"))
                if status is None or state.status == status:
                    states.append(state)
            except Exception:
                continue
        return states

    def latest(self, workflow_name: str) -> ExecutionState | None:
        states = self.list_executions(workflow_name, limit=1)
        return states[0] if states else None

    def update_task(self, workflow_name: str, execution_id: str, task_id: str, **kwargs) -> None:
        state = self.load(workflow_name, execution_id)
        if state is None:
            return
        if task_id not in state.tasks:
            state.tasks[task_id] = TaskExecution(task_id=task_id, task_name=kwargs.get("task_name", task_id))
        for k, v in kwargs.items():
            setattr(state.tasks[task_id], k, v)
        self.save(state)

    def summary(self, workflow_name: str) -> dict[str, Any]:
        states = self.list_executions(workflow_name, limit=100)
        if not states:
            return {"total": 0, "completed": 0, "failed": 0, "avg_duration_s": 0}
        completed = [s for s in states if s.status == ExecutionStatus.COMPLETED]
        failed = [s for s in states if s.status == ExecutionStatus.FAILED]
        durations = [s.duration_s() for s in completed if s.duration_s() is not None]
        return {
            "total": len(states),
            "completed": len(completed),
            "failed": len(failed),
            "running": sum(1 for s in states if s.status == ExecutionStatus.RUNNING),
            "avg_duration_s": round(sum(durations) / len(durations), 1) if durations else 0,
            "last_execution": states[0].execution_id if states else None,
            "last_status": states[0].status.value if states else None,
        }

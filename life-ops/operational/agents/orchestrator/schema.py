"""Workflow schema — JSON-serializable Pydantic models for workflow definitions.

Per /workflow-orchestrator skill: Full JSON schema for all task types,
triggers, environment, notifications, retry policies, and conditions.
"""

from __future__ import annotations

import json
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Annotated

from pydantic import BaseModel, Field


# ── Enums ────────────────────────────────────────────────────────────────────

class TaskType(str, Enum):
    SHELL = "shell"
    PYTHON = "python"
    HTTP = "http"
    DOCKER = "docker"
    CONDITIONAL = "conditional"
    PARALLEL = "parallel"
    LOOP = "loop"
    DATA_PROCESSOR = "data_processor"
    NOTIFY = "notify"


class TriggerType(str, Enum):
    MANUAL = "manual"
    SCHEDULE = "schedule"
    WEBHOOK = "webhook"
    FILE_CHANGE = "file_change"


class NotificationChannel(str, Enum):
    SLACK = "slack"
    EMAIL = "email"
    WEBHOOK_URL = "webhook_url"


# ── Trigger ─────────────────────────────────────────────────────────────────

class RetryConfig(BaseModel):
    attempts: int = Field(default=1, ge=1, le=10)
    delay_ms: int = Field(default=1000, ge=0)
    backoff_multiplier: float = Field(default=2.0, ge=1.0)
    max_delay_ms: int = Field(default=30000)


class TriggerConfig(BaseModel):
    type: TriggerType = Field(default=TriggerType.MANUAL)
    schedule: str | None = Field(default=None, description="Cron expression, e.g. '0 2 * * *'")
    webhook_path: str | None = Field(default=None)
    watch_files: list[str] = Field(default_factory=list)
    webhook_secret: str | None = Field(default=None)


# ── Base Task ────────────────────────────────────────────────────────────────

class BaseTaskFields(BaseModel):
    id: str = Field(description="Unique task ID within the workflow")
    name: str = Field(default="", description="Human-readable name")
    enabled: bool = Field(default=True)
    depends_on: list[str] = Field(default_factory=list)
    parallel: bool = Field(default=False, description="Run concurrently with siblings in same parallel group")
    parallel_group: str | None = Field(default=None)
    timeout_s: int = Field(default=300, ge=1)
    retry: RetryConfig = Field(default_factory=RetryConfig)
    condition: str | None = Field(
        default=None,
        description="JS-like expression, e.g. ${tasks.build.exit_code} == 0",
    )
    environment: dict[str, str] = Field(default_factory=dict)
    on_success: list[str] = Field(default_factory=list, description="Callback task IDs on success")
    on_failure: list[str] = Field(default_factory=list, description="Callback task IDs on failure")
    live_output: bool = Field(default=False, description="Stream stdout in real-time")
    cwd: str | None = Field(default=None)


# ── Shell Task ───────────────────────────────────────────────────────────────

class ShellTask(BaseTaskFields):
    type: Literal["shell"] = Field(default="shell", alias="type")
    command: str = Field(description="Shell command to execute")
    shell: bool = Field(default=True)


# ── Python Task ─────────────────────────────────────────────────────────────

class PythonTask(BaseTaskFields):
    type: Literal["python"] = Field(default="python", alias="type")
    script_path: str = Field(description="Path to Python script")
    args: list[str] = Field(default_factory=list)
    interpreter: str = Field(default="python")


# ── HTTP Task ────────────────────────────────────────────────────────────────

class HttpAuth(BaseModel):
    username: str | None = None
    password: str | None = None
    bearer_token: str | None = None


class HttpTask(BaseTaskFields):
    type: Literal["http"] = Field(default="http", alias="type")
    method: str = Field(default="GET")
    url: str = Field()
    headers: dict[str, str] = Field(default_factory=dict)
    data: Any = Field(default=None)
    auth: HttpAuth | None = None
    timeout_s: int = Field(default=30)


# ── Docker Task ─────────────────────────────────────────────────────────────

class DockerTask(BaseTaskFields):
    type: Literal["docker"] = Field(default="docker", alias="type")
    command: str = Field(description="Docker command (run/build/exec)")
    image: str | None = None
    container_name: str | None = None
    detach: bool = Field(default=False)
    environment: dict[str, str] = Field(default_factory=dict)


# ── Conditional Task ────────────────────────────────────────────────────────

class ConditionalTask(BaseTaskFields):
    type: Literal["conditional"] = Field(default="conditional", alias="type")
    condition: str = Field(description="JS expression evaluated at runtime")
    then_command: str | None = None
    then_script_path: str | None = None
    else_command: str | None = None
    else_script_path: str | None = None


# ── Parallel Task ───────────────────────────────────────────────────────────

class ParallelTask(BaseTaskFields):
    type: Literal["parallel"] = Field(default="parallel", alias="type")
    tasks: list[dict[str, Any]] = Field(default_factory=list, description="List of task dicts")
    wait_for: str = Field(default="all")
    max_parallel: int = Field(default=1, ge=1)


# ── Loop Task ───────────────────────────────────────────────────────────────

class LoopTask(BaseTaskFields):
    type: Literal["loop"] = Field(default="loop", alias="type")
    items: list[Any] = Field(default_factory=list)
    items_from_file: str | None = None
    item_variable: str = Field(default="item")
    index_variable: str = Field(default="index")
    task: dict[str, Any] = Field(description="Task template — ${item} and ${index} substituted")
    stop_on_failure: bool = Field(default=True)
    max_parallel: int = Field(default=1, ge=1)


# ── Data Processor Task ─────────────────────────────────────────────────────

class DataProcessorInput(BaseModel):
    type: str = Field(default="file")  # file | http | inline
    path: str | None = None
    url: str | None = None
    data: Any = None


class DataProcessorOutput(BaseModel):
    type: str = Field(default="file")
    path: str | None = None


class DataProcessorTask(BaseTaskFields):
    type: Literal["data_processor"] = Field(default="data_processor", alias="type")
    input: DataProcessorInput = Field(default_factory=DataProcessorInput)
    processor: dict[str, Any] = Field(
        default_factory=dict,
        description="{type: 'python'|'javascript', script_path: str, fn: str}",
    )
    output: DataProcessorOutput = Field(default_factory=DataProcessorOutput)


# ── Notify Task ─────────────────────────────────────────────────────────────

class NotifyTask(BaseTaskFields):
    type: Literal["notify"] = Field(default="notify", alias="type")
    channel: NotificationChannel = Field(default=NotificationChannel.SLACK)
    message_template: str = Field(description="Message template with ${...} interpolation")
    webhook_url: str | None = None


# ── Task Union ─────────────────────────────────────────────────────────────

TaskConfig = Annotated[
    ShellTask
    | PythonTask
    | HttpTask
    | DockerTask
    | ConditionalTask
    | ParallelTask
    | LoopTask
    | DataProcessorTask
    | NotifyTask,
    Field(discriminator="type"),
]


# ── Notifications ────────────────────────────────────────────────────────────

class NotificationConfig(BaseModel):
    channels: list[NotificationChannel] = Field(default_factory=lambda: [NotificationChannel.SLACK])
    on_completion: bool = Field(default=False)
    on_failure: bool = Field(default=True)
    on_start: bool = Field(default=False)
    slack_webhook: str | None = None
    email_to: list[str] = Field(default_factory=list)


# ── Workflow Schema ─────────────────────────────────────────────────────────

class WorkflowMetadata(BaseModel):
    name: str
    version: str = Field(default="1.0.0")
    description: str = ""
    author: str | None = None
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    tags: list[str] = Field(default_factory=list)
    expected_duration_s: int | None = Field(default=None)
    environment: dict[str, str] = Field(default_factory=dict)


class WorkflowSchema(BaseModel):
    metadata: WorkflowMetadata
    trigger: TriggerConfig = Field(default_factory=TriggerConfig)
    tasks: list[dict[str, Any]] = Field(default_factory=list)
    notifications: NotificationConfig = Field(default_factory=NotificationConfig)

    @classmethod
    def from_json(cls, path: str | Path) -> WorkflowSchema:
        text = Path(path).read_text(encoding="utf-8")
        return cls.model_validate_json(text)

    @classmethod
    def from_yaml(cls, path: str | Path) -> WorkflowSchema:
        import yaml
        text = Path(path).read_text(encoding="utf-8")
        return cls.model_validate(yaml.safe_load(text))

    def to_json(self, path: str | Path) -> None:
        Path(path).write_text(self.model_dump_json(indent=2, exclude_none=True), encoding="utf-8")

    def get_task(self, task_id: str) -> dict[str, Any] | None:
        return next((t for t in self.tasks if t.get("id") == task_id), None)

    def topological_order(self) -> list[str]:
        """Kahn's algorithm — task IDs in execution order."""
        in_degree: dict[str, int] = {t["id"]: 0 for t in self.tasks}
        adj: dict[str, list[str]] = {t["id"]: [] for t in self.tasks}
        for t in self.tasks:
            for dep in t.get("depends_on", []):
                adj[dep].append(t["id"])
                in_degree[t["id"]] += 1
        queue = [tid for tid, deg in in_degree.items() if deg == 0]
        order: list[str] = []
        while queue:
            tid = queue.pop(0)
            order.append(tid)
            for nb in adj[tid]:
                in_degree[nb] -= 1
                if in_degree[nb] == 0:
                    queue.append(nb)
        return order

    def get_ready_tasks(self, completed: set[str], failed: set[str]) -> list[dict[str, Any]]:
        """Return tasks whose dependencies are all satisfied."""
        ready: list[dict[str, Any]] = []
        for t in self.tasks:
            if t.get("id") in completed or t.get("id") in failed:
                continue
            deps = t.get("depends_on", [])
            if all(d in completed for d in deps) and not any(d in failed for d in deps):
                ready.append(t)
        return ready

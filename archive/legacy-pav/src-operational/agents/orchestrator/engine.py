"""WorkflowOrchestrator — core execution engine.

Per /workflow-orchestrator skill: dependency graph execution,
task dispatch, retry logic, callbacks, context passing.
"""

from __future__ import annotations

import concurrent.futures
import threading
import time
import uuid
from datetime import datetime, UTC
from pathlib import Path
from typing import Any

from agents.orchestrator.schema import WorkflowSchema, TaskType
from agents.orchestrator.state import ExecutionState, ExecutionStore, ExecutionStatus, TaskExecution
from agents.orchestrator.task_types import get_runner, TaskResult


class WorkflowOrchestrator:
    """Main execution engine for a single workflow.

    Loads WorkflowSchema → builds dependency graph → executes tasks
    respecting depends_on, retry, conditions, and callbacks.
    Thread-safe: can run multiple workflows concurrently.
    """

    def __init__(
        self,
        workflow: WorkflowSchema | Path | str,
        execution_store: ExecutionStore | None = None,
        trigger: str = "manual",
        max_parallel: int = 4,
    ):
        if isinstance(workflow, (Path, str)):
            p = Path(workflow)
            workflow = WorkflowSchema.from_yaml(p) if p.suffix in (".yaml", ".yml") else WorkflowSchema.from_json(p)

        self.workflow = workflow
        self.store = execution_store or ExecutionStore()
        self.trigger = trigger
        self.max_parallel = max_parallel

        # Generate execution ID
        self.execution_id = f"exec_{uuid.uuid4().hex[:12]}"
        self.state = ExecutionState(
            execution_id=self.execution_id,
            workflow_name=self.workflow.metadata.name,
            workflow_path="",
            status=ExecutionStatus.PENDING,
            trigger=trigger,
            task_order=self.workflow.topological_order(),
        )

        # Runtime
        self._lock = threading.RLock()
        self._task_results: dict[str, Any] = {}
        self._running_threads: dict[str, threading.Thread] = {}
        self._stop_requested = False

    # ── Public API ─────────────────────────────────────────────────────────

    def run(self) -> ExecutionState:
        """Execute the full workflow. Returns final ExecutionState."""
        print(f"🚀 [{self.workflow.metadata.name}] Starting execution {self.execution_id}")

        self.state.status = ExecutionStatus.RUNNING
        self.state.start_time = datetime.now(UTC).isoformat()
        self.store.save(self.state)

        try:
            self._execute_workflow()
        except Exception as e:
            self.state.status = ExecutionStatus.FAILED
            self.state.end_time = datetime.now(UTC).isoformat()
            print(f"   ❌ Workflow failed: {e}")

        # Finalize
        self.state.end_time = datetime.now(UTC).isoformat()
        if self.state.start_time:
            t_start = datetime.fromisoformat(self.state.start_time)
            t_end = datetime.fromisoformat(self.state.end_time)
            self.state.duration_ms = int((t_end - t_start).total_seconds() * 1000)

        if all(t in self.state.completed_tasks for t in self.state.task_order):
            self.state.status = ExecutionStatus.COMPLETED
        elif self.state.failed_tasks:
            self.state.status = ExecutionStatus.FAILED

        self.store.save(self.state)
        self._notify(self.state)

        status_icon = "✅" if self.state.status == ExecutionStatus.COMPLETED else "❌"
        print(f"{status_icon} [{self.workflow.metadata.name}] {self.state.status.value} — {len(self.state.completed_tasks)}/{len(self.state.task_order)} tasks")

        return self.state

    def cancel(self) -> None:
        """Request graceful cancellation of the running workflow."""
        self._stop_requested = True
        with self._lock:
            for tid, thread in self._running_threads.items():
                thread.join(timeout=2)

    # ── Core execution loop ────────────────────────────────────────────────

    def _execute_workflow(self) -> None:
        completed: set[str] = set()
        failed: set[str] = set()
        in_flight: set[str] = set()

        while True:
            if self._stop_requested:
                self.state.status = ExecutionStatus.CANCELLED
                break

            # Check if done
            pending = set(self.state.task_order) - completed - failed
            if not pending and not in_flight:
                break

            # Get newly ready tasks
            ready = [
                t for t in self.workflow.tasks
                if t["id"] in pending
                and all(dep in completed for dep in t.get("depends_on", []))
                and t["id"] not in in_flight
            ]

            # Launch up to max_parallel
            batch = ready[: self.max_parallel - len(in_flight)]
            for task_def in batch:
                in_flight.add(task_def["id"])
                t = threading.Thread(
                    target=self._execute_task,
                    args=(task_def, completed, failed, in_flight),
                    daemon=True,
                )
                with self._lock:
                    self._running_threads[task_def["id"]] = t
                t.start()

            time.sleep(0.05)

        # Wait for stragglers
        for tid in list(in_flight):
            if tid not in completed and tid not in failed:
                pass  # Will be handled by thread completion

    def _execute_task(
        self,
        task_def: dict[str, Any],
        completed: set[str],
        failed: set[str],
        in_flight: set[str],
    ) -> None:
        task_id = task_def["id"]
        task_name = task_def.get("name", task_id)

        # Update state: running
        self._update_task_state(task_id, task_name, ExecutionStatus.RUNNING, start_time=datetime.now(UTC).isoformat())

        # Condition check
        condition = task_def.get("condition")
        if condition:
            try:
                # Build condition context
                ctx = {"task_results": self._task_results, "env": dict(__import__("os").environ)}
                cond_interp = condition
                import re
                def repl(m):
                    path = m.group(1)
                    if path.startswith("tasks."):
                        parts = path.split(".")
                        tid = parts[1]
                        field = parts[2] if len(parts) > 2 else "exit_code"
                        return str(self._task_results.get(tid, {}).get(field, ""))
                    if path.startswith("env."):
                        return __import__("os").getenv(path[4:], "")
                    return m.group(0)
                cond_safe = re.sub(r"\$\{([^}]+)\}", repl, cond_interp)
                cond_safe = cond_safe.replace("&&", " and ").replace("||", " or ")
                if not eval(cond_safe, {"__builtins__": {}}):
                    with self._lock:
                        completed.add(task_id)
                        in_flight.discard(task_id)
                    self._update_task_state(task_id, task_name, ExecutionStatus.COMPLETED, result={"skipped": True})
                    print(f"   ⊘ {task_name} (condition false)")
                    return
            except Exception as e:
                print(f"   ⚠️  {task_name} condition eval error: {e}")

        # Retry loop
        retry_cfg = task_def.get("retry", {})
        max_retries = retry_cfg.get("attempts", 1)
        delay_ms = retry_cfg.get("delay_ms", 1000)
        backoff = retry_cfg.get("backoff_multiplier", 2.0)
        max_delay = retry_cfg.get("max_delay_ms", 30000)

        attempt = 0
        last_result: TaskResult | None = None
        for attempt in range(max_retries):
            result = self._run_task_once(task_def)
            last_result = result

            if result.success:
                break

            if attempt < max_retries - 1:
                wait_ms = min(int(delay_ms * (backoff ** attempt)), max_delay)
                print(f"   ↺ {task_name} retry {attempt + 1}/{max_retries - 1} after {wait_ms}ms — {result.error}")
                time.sleep(wait_ms / 1000)

        # Update completion state
        with self._lock:
            in_flight.discard(task_id)
            if last_result and last_result.success:
                completed.add(task_id)
                self.state.completed_tasks.append(task_id)
                status = ExecutionStatus.COMPLETED
            else:
                failed.add(task_id)
                self.state.failed_tasks.append(task_id)
                status = ExecutionStatus.FAILED

            self._task_results[task_id] = {
                "exit_code": last_result.exit_code if last_result else -1,
                "stdout": last_result.stdout[:500] if last_result else "",
                "stderr": last_result.stderr[:200] if last_result else "",
                "result": last_result.result if last_result else {},
            }

        self._update_task_state(
            task_id,
            task_name,
            status,
            end_time=datetime.now(UTC).isoformat(),
            exit_code=last_result.exit_code if last_result else -1,
            stdout_preview=last_result.stdout[:200] if last_result else "",
            stderr_preview=last_result.stderr[:200] if last_result else "",
            result=last_result.result if last_result else {},
            error=last_result.error if last_result and not last_result.success else None,
            attempt=attempt + 1,
        )

        # Callbacks
        if status == ExecutionStatus.COMPLETED:
            for cb_id in task_def.get("on_success", []):
                self._trigger_callback(cb_id, task_def, last_result)
        elif status == ExecutionStatus.FAILED:
            for cb_id in task_def.get("on_failure", []):
                self._trigger_callback(cb_id, task_def, last_result)

        # Enqueue dependent tasks that are now ready
        icon = "✅" if status == ExecutionStatus.COMPLETED else "❌"
        print(f"   {icon} {task_name} ({status.value})" + (f" — {last_result.exit_code}" if last_result else ""))

    def _run_task_once(self, task_def: dict[str, Any]) -> TaskResult:
        """Run a single task (no retry — retry is handled by _execute_task)."""
        task_type = task_def.get("type", "shell")
        context = dict(self._task_results)

        runner = get_runner(task_def, context)
        return runner._run()

    def _update_task_state(self, task_id: str, task_name: str, status: ExecutionStatus, **kwargs) -> None:
        if task_id not in self.state.tasks:
            self.state.tasks[task_id] = TaskExecution(task_id=task_id, task_name=task_name)
        ts = self.state.tasks[task_id]
        ts.status = status
        for k, v in kwargs.items():
            setattr(ts, k, v)
        self.store.save(self.state)

    def _trigger_callback(self, cb_id: str, source_task: dict[str, Any], result: TaskResult | None) -> None:
        cb_task = self.workflow.get_task(cb_id)
        if not cb_task:
            return
        # Add context about the triggering task
        cb_context = dict(self._task_results)
        cb_context["callback_of"] = source_task["id"]
        cb_context["callback_result"] = result.model_dump() if result else {}
        try:
            runner = get_runner(cb_task, cb_context)
            cb_result = runner._run()
            icon = "✅" if cb_result.success else "❌"
            print(f"   {icon} callback: {cb_task.get('name', cb_id)} ({cb_task.get('type', 'shell')})")
        except Exception as e:
            print(f"   ⚠️  callback {cb_id} failed: {e}")

    def _notify(self, state: ExecutionState) -> None:
        cfg = self.workflow.notifications
        if state.status == ExecutionStatus.COMPLETED and not cfg.on_completion:
            return
        if state.status == ExecutionStatus.FAILED and not cfg.on_failure:
            return

        webhook_url = cfg.slack_webhook
        if not webhook_url:
            return

        status_emoji = "✅" if state.status == ExecutionStatus.COMPLETED else "❌"
        msg = f"{status_emoji} *{self.workflow.metadata.name}* — {state.status.value}\n"
        msg += f"Execution: `{state.execution_id}`\n"
        msg += f"Tasks: {len(state.completed_tasks)}/{len(state.task_order)} completed"
        if state.duration_s():
            msg += f" • Duration: {state.duration_s():.1f}s"

        try:
            import requests
            requests.post(webhook_url, json={"text": msg}, timeout=5)
        except Exception:
            pass

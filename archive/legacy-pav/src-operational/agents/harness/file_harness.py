"""FileBasedHarness — the core execution engine for file-based agent workflows.

Orchestrates:
    1. Load WorkflowSchema from YAML
    2. Initialize SharedMessageBus + TaskQueue
    3. Execute nodes respecting dependency graph (parallel where possible)
    4. Agents run via CLI subprocess calls (pav CLI commands)
    5. State persisted as JSON checkpoints between nodes

Inspired by LangGraph's:
    - StateGraph (shared state dict, checkpointed)
    - Checkpoint (persistence between node runs)
    - Workflow compilation (graph → executor)

Usage:
    harness = FileBasedHarness(
        workflow_path="agents/workflows/qa_swarm.yaml",
        dataset_path="datasets/6month/synthetic_180d.csv",
    )
    result = harness.run()
"""

from __future__ import annotations

import concurrent.futures
import json
import subprocess
import threading
import time
from datetime import datetime, UTC
from pathlib import Path
from typing import Any

from agents.harness.workflow_schema import (
    AgentNode,
    AgentStatus,
    TaskEdge,
    TriggerType,
    WorkflowSchema,
)
from agents.harness.message_bus import MessageBus, MessageType
from agents.harness.task_queue import TaskQueue, Task, TaskPriority, TaskStatus
from agents.harness.node_registry import NodeRegistry


# ── Paths ─────────────────────────────────────────────────────────────────────

_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_DATASETS = _ROOT / "datasets"
_STATE_DIR = Path.home() / ".time-tasker"


# ── Checkpoint ───────────────────────────────────────────────────────────────

class CheckpointStore:
    """JSON file-backed state store — the "LangGraph checkpointer"."""

    def __init__(self, workflow_id: str):
        self.path = _STATE_DIR / "agent_harness" / f"{workflow_id}_state.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._cache: dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        if self.path.exists():
            try:
                self._cache = json.loads(self.path.read_text(encoding="utf-8"))
            except Exception:
                self._cache = {}

    def get(self, key: str, default: Any = None) -> Any:
        return self._cache.get(key, default)

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._cache[key] = value
            self.path.write_text(json.dumps(self._cache, indent=2, ensure_ascii=False), encoding="utf-8")

    def merge(self, updates: dict[str, Any]) -> None:
        with self._lock:
            self._cache.update(updates)
            self.path.write_text(json.dumps(self._cache, indent=2, ensure_ascii=False), encoding="utf-8")

    def get_all(self) -> dict[str, Any]:
        return dict(self._cache)

    def snapshot(self, label: str) -> None:
        """Named snapshot for replay/debug."""
        snap_path = self.path.with_suffix(f".snap_{label}.json")
        snap_path.write_text(json.dumps(self._cache, indent=2, ensure_ascii=False), encoding="utf-8")


# ── CLI Runner ────────────────────────────────────────────────────────────────

class CLIRunner:
    """Execute pav CLI commands as subprocess — the agent's actuator."""

    def __init__(self, root: Path = _ROOT):
        self.root = root

    def run(
        self,
        command: str,
        cwd: Path | None = None,
        env: dict[str, str] | None = None,
        timeout_s: int = 60,
        input_text: str = "",
    ) -> tuple[int, str, str]:
        cmd = ["uv", "run", "--directory", str(self.root), "pav", *command.split()]
        env_full = {**dict(__import__("os").environ), **(env or {})}
        try:
            r = subprocess.run(
                cmd,
                input=input_text,
                capture_output=True,
                text=True,
                cwd=str(cwd or self.root),
                env=env_full,
                timeout=timeout_s,
            )
            return r.returncode, r.stdout or "", r.stderr or ""
        except subprocess.TimeoutExpired:
            return -1, "", f"Timeout after {timeout_s}s"
        except Exception as e:
            return -1, "", str(e)


# ── FileBasedHarness ─────────────────────────────────────────────────────────

class FileBasedHarness:
    """LangGraph-style file-based workflow executor.

    Key idea: Workflow is defined in YAML → loaded as WorkflowSchema →
    executed by this harness → agents communicate via shared JSON state +
    message bus → each node is checkpointed after execution.
    """

    def __init__(
        self,
        workflow_path: str | Path,
        dataset_path: str | Path | None = None,
        workflow_id: str | None = None,
        registry: NodeRegistry | None = None,
        max_parallel: int = 4,
    ):
        self.workflow_path = Path(workflow_path)
        self.workflow: WorkflowSchema = WorkflowSchema.from_yaml(self.workflow_path)
        self.workflow_id = workflow_id or self.workflow.metadata.name

        self.dataset_path = Path(dataset_path) if dataset_path else None
        self.max_parallel = max_parallel

        # Subsystems
        self.bus = SharedMessageBus(self.workflow_id)
        self.queue = TaskQueue(self.workflow_id)
        self.checkpoint = CheckpointStore(self.workflow_id)
        self.runner = CLIRunner(root=_ROOT)
        self.registry = registry or NodeRegistry()

        # Runtime state
        self._running: dict[str, threading.Thread] = {}
        self._results: dict[str, dict[str, Any]] = {}
        self._errors: dict[str, str] = {}
        self._lock = threading.RLock()

        # Bootstrap: seed dataset info into state
        self._seed_state()

    # ── Bootstrap ──────────────────────────────────────────────────────────

    def _seed_state(self) -> None:
        """Pre-populate workflow state with known context."""
        self.checkpoint.set("workflow_id", self.workflow_id)
        self.checkpoint.set("started_at", datetime.now(UTC).isoformat())
        self.checkpoint.set("dataset_path", str(self.dataset_path) if self.dataset_path else None)
        self.checkpoint.set("completed_nodes", [])
        self.checkpoint.set("failed_nodes", [])

        if self.dataset_path and self.dataset_path.exists():
            # Load CSV metadata
            import csv
            try:
                with open(self.dataset_path, newline="", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    rows = list(reader)
                    self.checkpoint.set("dataset_rows", len(rows))
                    if rows:
                        self.checkpoint.set("dataset_columns", list(rows[0].keys()))
                        self.checkpoint.set("dataset_sample", rows[0])
            except Exception as e:
                self.checkpoint.set("dataset_error", str(e))

    # ── Main run ───────────────────────────────────────────────────────────

    def run(self) -> dict[str, Any]:
        """Execute the workflow. Returns final state."""
        print(f"🚀 Starting workflow: {self.workflow_id}")
        print(f"   Nodes: {len(self.workflow.nodes)} | Edges: {len(self.workflow.edges)}")
        print(f"   Dataset: {self.dataset_path}")
        print()

        # Enqueue all nodes that have no dependencies
        for node in self.workflow.nodes:
            if not node.depends_on:
                self.queue.enqueue(Task(
                    name=node.name,
                    description=node.description,
                    agent_id=node.id,
                    priority=TaskPriority.NORMAL,
                    payload={"node_id": node.id},
                ))

        self._run_loop()

        state = self.checkpoint.get_all()
        print(f"\n✅ Workflow complete: {self.workflow_id}")
        print(f"   Completed: {len(state.get('completed_nodes', []))}")
        print(f"   Failed: {len(state.get('failed_nodes', []))}")
        return state

    def _run_loop(self) -> None:
        """Main event loop — drains queue, spawns parallel nodes, watches for completion."""
        completed: set[str] = set()
        failed: set[str] = set()

        while True:
            # 1. Grab up to max_parallel pending tasks
            batch: list[Task] = []
            while len(batch) < self.max_parallel:
                task = self.queue.dequeue()
                if task is None:
                    break
                if task.agent_id in completed or task.agent_id in failed:
                    # Node already done, skip
                    continue
                batch.append(task)

            if not batch:
                # No more tasks in queue — check if workflow is done
                if self.queue.stats()[TaskStatus.PENDING.value] == 0 and self.queue.stats()[TaskStatus.RUNNING.value] == 0:
                    break
                time.sleep(0.2)
                continue

            # 2. Execute batch in parallel threads
            threads: list[threading.Thread] = []
            for task in batch:
                t = threading.Thread(target=self._execute_node, args=(task, completed, failed), daemon=True)
                threads.append(t)
                t.start()

            for t in threads:
                t.join(timeout=120)

            # 3. Check for new tasks that became unblocked
            time.sleep(0.1)

    def _execute_node(self, task: Task, completed: set[str], failed: set[str]) -> None:
        """Execute a single agent node."""
        node_id = task.payload["node_id"]
        node = self.workflow.get_node(node_id)
        if node is None:
            return

        print(f"   ▶ {node.name}")
        self.bus.publish(node_id, "*", MessageType.EVENT, {"event": "started", "node": node_id})

        try:
            # Build input state for this agent
            input_state = self.checkpoint.get_all()

            # Execute agent
            if node.script_path:
                result = self._run_script_agent(node, input_state)
            elif node.tools:
                result = self._run_cli_agent(node, input_state)
            else:
                result = {}

            # Handle None returns (agent chose to skip)
            if result is None:
                result = {"skipped": True}

            # Write to state
            if node.state_key:
                self.checkpoint.set(node.state_key, result)
            self.checkpoint.merge({node.state_key: result, f"{node_id}_status": "complete"})

            # Update completed set
            with self._lock:
                completed.add(node_id)
                self._results[node_id] = result

            self.queue.complete(task.id, result)
            self.bus.publish(node_id, "*", MessageType.RESULT, {"node": node_id, "result": result})

            # Enqueue downstream nodes whose dependencies are now satisfied
            self._enqueue_ready_nodes(completed, failed)

            print(f"   ✅ {node.name}")

        except Exception as e:
            error_msg = f"{type(e).__name__}: {e}"
            self.node_status(node_id, AgentStatus.FAILED, error=error_msg)
            with self._lock:
                failed.add(node_id)
            self.queue.fail(task.id, error_msg)
            self.bus.publish(node_id, "*", MessageType.ERROR, {"node": node_id, "error": error_msg})
            print(f"   ❌ {node.name}: {error_msg}")

    # ── Agent executors ────────────────────────────────────────────────────

    def _run_cli_agent(self, node: AgentNode, input_state: dict[str, Any]) -> dict[str, Any]:
        """Run a CLI-based agent: execute all tools sequentially, aggregate results."""
        results: dict[str, Any] = {"tool_results": []}

        for tool in node.tools:
            exit_code, stdout, stderr = self.runner.run(
                command=tool.command,
                cwd=Path(tool.cwd) if tool.cwd else None,
                env=tool.env_vars,
                timeout_s=tool.timeout_s,
            )

            tool_result = {
                "command": tool.command,
                "exit_code": exit_code,
                "stdout_preview": stdout[:500] if stdout else "",
                "stderr_preview": stderr[:200] if stderr else "",
            }

            # Try parsing stdout as JSON
            try:
                tool_result["parsed"] = json.loads(stdout) if stdout.strip().startswith(("[", "{")) else None
            except Exception:
                tool_result["parsed"] = None

            # Retry logic
            retries = 0
            while exit_code != tool.expected_exit and retries < (1 if tool.retry_on_fail else 0):
                retries += 1
                exit_code, stdout, stderr = self.runner.run(
                    command=tool.command,
                    timeout_s=tool.timeout_s,
                )
                tool_result[f"retry_{retries}"] = {"exit_code": exit_code, "stdout": stdout[:200]}

            results["tool_results"].append(tool_result)

        # Aggregate: last parsed result or summary
        parsed = [tr["parsed"] for tr in results["tool_results"] if tr["parsed"]]
        if parsed:
            results["aggregated"] = parsed[-1]

        return results

    def _run_script_agent(self, node: AgentNode, input_state: dict[str, Any]) -> dict[str, Any]:
        """Run a Python-script-based agent as a subprocess."""
        script_path = _ROOT / node.script_path
        if not script_path.exists():
            raise FileNotFoundError(f"Agent script not found: {script_path}")

        state_file = _STATE_DIR / "agent_harness" / f"{self.workflow_id}_{node.id}_state.json"
        state_file.parent.mkdir(parents=True, exist_ok=True)
        state_file.write_text(json.dumps(input_state, indent=2, ensure_ascii=False), encoding="utf-8")

        cmd = ["python", str(script_path), "--state", str(state_file), "--workflow-id", self.workflow_id]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=node.tools[0].timeout_s if node.tools else 60)

        if r.returncode != 0:
            raise RuntimeError(f"Script agent failed: {r.stderr[:300]}")

        try:
            return json.loads(r.stdout)
        except json.JSONDecodeError:
            return {"raw_output": r.stdout[:1000]}

    def _enqueue_ready_nodes(self, completed: set[str], failed: set[str]) -> None:
        """Enqueue nodes whose dependencies are now all satisfied."""
        for node in self.workflow.nodes:
            if node.status != AgentStatus.PENDING:
                continue
            if not node.depends_on:
                continue  # Already enqueued at start
            if any(d in failed for d in node.depends_on):
                node.status = AgentStatus.SKIPPED
                continue
            if all(d in completed for d in node.depends_on):
                self.queue.enqueue(Task(
                    name=node.name,
                    description=node.description,
                    agent_id=node.id,
                    priority=TaskPriority.NORMAL,
                    payload={"node_id": node.id},
                ))

    # ── Utilities ──────────────────────────────────────────────────────────

    def node_status(self, node_id: str, status: AgentStatus, error: str | None = None) -> None:
        self.checkpoint.merge({f"{node_id}_status": status.value, **{f"{node_id}_error": error} if error else {}})

    def get_results(self) -> dict[str, dict[str, Any]]:
        return dict(self._results)

    def get_errors(self) -> dict[str, str]:
        return dict(self._errors)

    def report(self) -> dict[str, Any]:
        """Return a summary report of the workflow execution."""
        state = self.checkpoint.get_all()
        return {
            "workflow_id": self.workflow_id,
            "workflow_path": str(self.workflow_path),
            "dataset_path": str(self.dataset_path) if self.dataset_path else None,
            "total_nodes": len(self.workflow.nodes),
            "completed_nodes": state.get("completed_nodes", []),
            "failed_nodes": state.get("failed_nodes", []),
            "node_results": self._results,
            "errors": self._errors,
            "started_at": state.get("started_at"),
            "finished_at": datetime.now(UTC).isoformat(),
        }

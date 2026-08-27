"""WorkflowMonitor — health reports, metrics, and alerting.

Per /workflow-orchestrator skill: tracks workflow metrics across runs,
computes success rates, average duration, task-level health, and alerts.
"""

from __future__ import annotations

import json
import threading
import time
from datetime import datetime, UTC
from pathlib import Path
from typing import Any

from agents.orchestrator.state import ExecutionStore, ExecutionState, ExecutionStatus


class WorkflowMonitor:
    """Aggregates metrics across all executions of a workflow.

    Thread-safe. Persists alert state to JSON file.
    """

    def __init__(self, execution_store: ExecutionStore | None = None, alerts_path: Path | None = None):
        self.store = execution_store or ExecutionStore()
        self.alerts_path = alerts_path or Path.home() / ".time-tasker" / "agent_harness" / "alerts.json"
        self.alerts_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._alert_state: dict[str, Any] = self._load_alert_state()

    def _load_alert_state(self) -> dict[str, Any]:
        if self.alerts_path.exists():
            try:
                return json.loads(self.alerts_path.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {}

    def _save_alert_state(self) -> None:
        with self._lock:
            self.alerts_path.write_text(json.dumps(self._alert_state, indent=2), encoding="utf-8")

    # ── Health Report ────────────────────────────────────────────────────

    def get_health_report(self, workflow_name: str) -> dict[str, Any]:
        """Return full health report for a workflow."""
        executions = self.store.list_executions(workflow_name, limit=100)
        if not executions:
            return {"status": "no_runs", "workflow": workflow_name}

        completed = [e for e in executions if e.status == ExecutionStatus.COMPLETED]
        failed = [e for e in executions if e.status == ExecutionStatus.FAILED]
        running = [e for e in executions if e.status == ExecutionStatus.RUNNING]

        durations = [e.duration_s() for e in completed if e.duration_s() is not None]
        avg_duration = round(sum(durations) / len(durations), 1) if durations else 0

        # Task-level metrics
        task_metrics: dict[str, dict[str, Any]] = {}
        for e in executions:
            for tid, task in e.tasks.items():
                if tid not in task_metrics:
                    task_metrics[tid] = {"runs": 0, "failures": 0, "total_duration_ms": 0}
                m = task_metrics[tid]
                m["runs"] += 1
                if task.status == ExecutionStatus.FAILED:
                    m["failures"] += 1
                if task.duration_ms:
                    m["total_duration_ms"] += task.duration_ms

        task_health = {}
        for tid, m in task_metrics.items():
            runs = m["runs"]
            failures = m["failures"]
            avg_ms = m["total_duration_ms"] / runs if runs else 0
            task_health[tid] = {
                "runs": runs,
                "success_rate": round(100 * (runs - failures) / runs, 1) if runs else 0,
                "avg_duration_ms": round(avg_ms, 1),
                "total_failures": failures,
            }

        # Slowest tasks
        slowest = sorted(task_health.items(), key=lambda x: x[1]["avg_duration_ms"], reverse=True)[:5]

        success_rate = round(100 * len(completed) / len(executions), 1) if executions else 0

        return {
            "workflow": workflow_name,
            "status": "healthy" if success_rate >= 90 else ("degraded" if success_rate >= 70 else "unhealthy"),
            "overall": {
                "total_runs": len(executions),
                "completed": len(completed),
                "failed": len(failed),
                "running": len(running),
                "success_rate": f"{success_rate}%",
                "avg_duration_s": avg_duration,
                "last_execution_id": executions[0].execution_id if executions else None,
                "last_status": executions[0].status.value if executions else None,
            },
            "task_health": task_health,
            "slowest_tasks": [{"task_id": tid, "avg_ms": m["avg_duration_ms"]} for tid, m in slowest],
            "alerts": self._get_active_alerts(workflow_name),
        }

    def get_global_summary(self) -> dict[str, Any]:
        """Return summary across all known workflows."""
        from pathlib import Path
        exec_base = Path.home() / ".time-tasker" / "agent_harness" / "executions"
        if not exec_base.exists():
            return {"workflows": 0, "total_executions": 0}

        workflows: list[str] = []
        total = 0
        for d in exec_base.iterdir():
            if d.is_dir():
                workflows.append(d.name)
                total += len(list(d.glob("*.json")))

        return {"workflows": len(workflows), "workflow_names": workflows[:10], "total_executions": total}

    # ── Alerts ────────────────────────────────────────────────────────────

    def _get_active_alerts(self, workflow_name: str) -> list[dict[str, Any]]:
        state = self._alert_state.get(workflow_name, {})
        return state.get("active_alerts", [])

    def check_and_fire_alerts(self, execution: ExecutionState) -> list[dict[str, Any]]:
        """Evaluate alert conditions and fire if triggered. Returns fired alerts."""
        fired: list[dict[str, Any]] = []
        alerts = self._alert_state.get(execution.workflow_name, {}).get("alert_rules", [])

        for rule in alerts:
            name = rule.get("name", "unnamed")
            condition = rule.get("condition", "")
            channels = rule.get("channels", [])

            triggered = False
            if "success_rate" in condition:
                threshold = float(condition.split("<")[1].strip().rstrip("%"))
                success_rate = self._calc_success_rate(execution.workflow_name)
                triggered = success_rate < threshold

            elif execution.status == ExecutionStatus.FAILED:
                triggered = True

            if triggered:
                fired.append({"rule": name, "channels": channels, "execution_id": execution.execution_id})
                self._fire_alert(name, execution, channels)

        return fired

    def _calc_success_rate(self, workflow_name: str) -> float:
        executions = self.store.list_executions(workflow_name, limit=50)
        if not executions:
            return 100.0
        completed = sum(1 for e in executions if e.status == ExecutionStatus.COMPLETED)
        return 100 * completed / len(executions)

    def _fire_alert(self, name: str, execution: ExecutionState, channels: list[str]) -> None:
        import requests
        msg = f"🚨 Alert: *{name}* triggered for `{execution.workflow_name}`\n"
        msg += f"Execution: `{execution.execution_id}`\nStatus: {execution.status.value}"

        for channel in channels:
            if channel == "slack":
                # Read webhook from alerts state
                webhook = self._alert_state.get("slack_webhook")
                if webhook:
                    try:
                        requests.post(webhook, json={"text": msg}, timeout=5)
                    except Exception:
                        pass
            elif channel == "email":
                # Could add SMTP here
                pass

    def register_alert_rule(self, workflow_name: str, rule: dict[str, Any]) -> None:
        if workflow_name not in self._alert_state:
            self._alert_state[workflow_name] = {"alert_rules": [], "active_alerts": []}
        self._alert_state[workflow_name].setdefault("alert_rules", []).append(rule)
        self._save_alert_state()

    def configure_slack(self, webhook_url: str) -> None:
        self._alert_state["slack_webhook"] = webhook_url
        self._save_alert_state()

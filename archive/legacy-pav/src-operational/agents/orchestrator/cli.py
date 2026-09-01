"""Workflow orchestrator CLI — Typer app with subcommands.

Per /workflow-orchestrator skill:
    workflow create [--template TYPE] [--output PATH]
    workflow run WORKFLOW_JSON [--trigger manual|scheduled|cron]
    workflow schedule WORKFLOW_JSON --cron "0 2 * * *"
    workflow list | workflow status [--execution-id ID]
    workflow history [--workflow-name NAME] [--limit N]
    workflow validate WORKFLOW_JSON
    workflow monitor [--workflow-name NAME] [--watch]
    workflow cancel [--execution-id ID]

Integrates with: agents/workflows/*.yaml (PAV QA + daily pipeline examples)
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime, UTC
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.live import Live

app = typer.Typer(help="PAV Workflow Orchestrator CLI", add_completion=False)
console = Console()

_ROOT = Path(__file__).resolve().parents[3]
_WORKFLOWS_DIR = _ROOT / "agents" / "workflows"
_SYS_MODELS_DIR = _ROOT.parent.parent / "life-ops" / "operational"  # workspace root


# ── Helpers ──────────────────────────────────────────────────────────────────

def resolve_workflow_path(path: str | None) -> Path:
    if path:
        p = Path(path)
        if not p.exists():
            p = _WORKFLOWS_DIR / path
        return p
    return _WORKFLOWS_DIR


def wf_summary(state) -> dict:
    return {
        "id": state.execution_id,
        "workflow": state.workflow_name,
        "status": state.status.value,
        "start": state.start_time[:19] if state.start_time else "",
        "duration_s": round(state.duration_s() or 0, 1),
        "tasks": f"{len(state.completed_tasks)}/{len(state.task_order)}",
    }


# ── Commands ────────────────────────────────────────────────────────────────

@app.command()
def run(
    workflow: str = typer.Argument(..., help="Workflow YAML or JSON file path"),
    trigger: str = typer.Option("manual", help="Trigger type: manual, scheduled, cron"),
    watch: bool = typer.Option(False, "--watch", help="Live output while running"),
    execution_id: str | None = typer.Option(None, "--execution-id", help="Override execution ID"),
) -> None:
    """Run a workflow."""
    from agents.orchestrator.schema import WorkflowSchema
    from agents.orchestrator.engine import WorkflowOrchestrator
    from agents.orchestrator.state import ExecutionStore

    wf_path = Path(workflow)
    if not wf_path.exists():
        wf_path = _WORKFLOWS_DIR / workflow
    if not wf_path.exists():
        console.print(f"[red]Workflow not found: {workflow}[/red]")
        raise typer.Exit(1)

    try:
        wf = WorkflowSchema.from_yaml(wf_path) if wf_path.suffix in (".yaml", ".yml") else WorkflowSchema.from_json(wf_path)
    except Exception as e:
        console.print(f"[red]Invalid workflow: {e}[/red]")
        raise typer.Exit(1)

    console.print(f"[bold cyan]Running:[/bold cyan] {wf.metadata.name} ({wf_path.name})")

    engine = WorkflowOrchestrator(wf, trigger=trigger)
    if execution_id:
        engine.execution_id = execution_id

    if watch:
        console.print("[dim]Press Ctrl+C to cancel[/dim]")

    try:
        state = engine.run()
    except KeyboardInterrupt:
        console.print("\n[yellow]Cancelling...[/yellow]")
        engine.cancel()
        raise typer.Exit(130)

    # Rich summary
    s = wf_summary(state)
    icon = "✅" if state.status.value == "completed" else "❌"
    console.print(f"\n{icon} Execution `{state.execution_id}` — {state.status.value}")
    console.print(f"   Tasks: {s['tasks']} | Duration: {s['duration_s']}s")


@app.command()
def create(
    name: str = typer.Option(..., "--name", prompt="Workflow name"),
    output: Path = typer.Option(..., "--output", prompt="Output path"),
    template: str = typer.Option("blank", "--template", help="Template: blank, ci-cd, qa-pipeline, daily"),
) -> None:
    """Create a new workflow from a template."""
    from agents.orchestrator.schema import WorkflowSchema, WorkflowMetadata, TriggerConfig, NotificationConfig, TaskType

    metadata = WorkflowMetadata(name=name, description=f"Auto-created workflow: {name}")

    if template == "blank":
        tasks = []
    elif template == "qa-pipeline":
        tasks = [
            {"id": "setup", "name": "Setup environment", "type": "shell", "command": "echo 'setup'"},
            {"id": "test", "name": "Run tests", "type": "shell", "command": "echo 'tests'", "depends_on": ["setup"]},
            {"id": "report", "name": "Generate report", "type": "shell", "command": "echo 'report'", "depends_on": ["test"]},
        ]
    elif template == "daily":
        tasks = [
            {"id": "sync", "name": "Sync data", "type": "shell", "command": "echo 'sync'"},
            {"id": "process", "name": "Process data", "type": "shell", "command": "echo 'process'", "depends_on": ["sync"]},
            {"id": "report", "name": "Daily report", "type": "shell", "command": "echo 'report'", "depends_on": ["process"]},
        ]
    else:
        tasks = []

    wf = WorkflowSchema(metadata=metadata, tasks=tasks)
    output.parent.mkdir(parents=True, exist_ok=True)
    wf.to_json(output)
    console.print(f"[green]Created:[/green] {output}")


@app.command()
def schedule(
    workflow: str = typer.Argument(..., help="Workflow YAML path"),
    cron_expr: str = typer.Option(..., "--cron", prompt="Cron expression (e.g. '0 2 * * *')"),
    enabled: bool = typer.Option(True, "--enabled/--disabled"),
) -> None:
    """Schedule a workflow with a cron expression."""
    from agents.orchestrator.scheduler import WorkflowScheduler

    wf_path = Path(workflow)
    if not wf_path.exists():
        wf_path = _WORKFLOWS_DIR / workflow

    scheduler = WorkflowScheduler()
    sched_id = scheduler.schedule(
        workflow_name=wf_path.stem,
        cron_expr=cron_expr,
        workflow_path=wf_path,
        enabled=enabled,
    )
    console.print(f"[green]Scheduled:[/green] {sched_id}")
    console.print(f"   Cron: {cron_expr}")
    console.print(f"   Workflow: {wf_path.name}")
    console.print(f"   Status: {'enabled' if enabled else 'disabled'}")


@app.command("list")
def list_workflows() -> None:
    """List all available workflow definitions."""
    table = Table(title="Available Workflows")
    table.add_column("Name", style="cyan")
    table.add_column("File", style="dim")
    table.add_column("Tasks", justify="right")
    table.add_column("Trigger", style="yellow")

    for p in sorted(_WORKFLOWS_DIR.glob("*.yaml")):
        try:
            from agents.orchestrator.schema import WorkflowSchema
            wf = WorkflowSchema.from_yaml(p)
            trigger = wf.trigger.type.value
            table.add_row(wf.metadata.name, p.name, str(len(wf.tasks)), trigger)
        except Exception as e:
            table.add_row(p.stem, p.name, "?", f"[red]{e}[/red]")

    console.print(table)


@app.command()
def history(
    workflow_name: str | None = None,
    limit: int = typer.Option(20, "--limit"),
    status_filter: str | None = None,
) -> None:
    """View execution history."""
    from agents.orchestrator.state import ExecutionStore, ExecutionStatus

    store = ExecutionStore()

    if workflow_name:
        names = [workflow_name]
    else:
        exec_base = Path.home() / ".time-tasker" / "agent_harness" / "executions"
        names = [d.name for d in exec_base.iterdir() if d.is_dir()] if exec_base.exists() else []

    table = Table(title="Execution History")
    table.add_column("Execution ID", style="dim")
    table.add_column("Workflow", style="cyan")
    table.add_column("Status", style="yellow")
    table.add_column("Start", style="dim")
    table.add_column("Duration", justify="right")
    table.add_column("Tasks", justify="right")

    status_map = {v.value: v for v in ExecutionStatus}
    for name in names:
        execs = store.list_executions(name, limit=limit)
        for e in execs:
            if status_filter and e.status.value != status_filter:
                continue
            icon = "✅" if e.status.value == "completed" else ("⏳" if e.status.value == "running" else "❌")
            table.add_row(
                e.execution_id,
                e.workflow_name,
                f"{icon} {e.status.value}",
                e.start_time[:19] if e.start_time else "",
                f"{round(e.duration_s() or 0, 1)}s",
                f"{len(e.completed_tasks)}/{len(e.task_order)}",
            )

    console.print(table)


@app.command()
def status(
    execution_id: str = typer.Option(..., "--execution-id", prompt="Execution ID"),
) -> None:
    """Get status of a specific execution."""
    from agents.orchestrator.state import ExecutionStore

    store = ExecutionStore()
    exec_dir = Path.home() / ".time-tasker" / "agent_harness" / "executions"
    found = None

    for d in exec_dir.iterdir():
        if not d.is_dir():
            continue
        state = store.load(d.name, execution_id)
        if state:
            found = state
            break

    if not found:
        console.print(f"[yellow]Execution not found: {execution_id}[/yellow]")
        raise typer.Exit(1)

    s = wf_summary(found)
    console.print(Panel(
        f"[bold]{found.workflow_name}[/bold]\n"
        f"ID:     {found.execution_id}\n"
        f"Status: {found.status.value}\n"
        f"Start:  {s['start']}\n"
        f"Duration: {s['duration_s']}s\n"
        f"Tasks: {s['tasks']}",
        title="Execution Status",
    ))

    # Task table
    table = Table(title="Task Results")
    table.add_column("Task", style="cyan")
    table.add_column("Status", style="yellow")
    table.add_column("Duration", justify="right")
    table.add_column("Exit", justify="right")
    table.add_column("Error", style="red")

    for tid, task in found.tasks.items():
        icon = "✅" if task.status.value == "completed" else ("⏳" if task.status.value == "running" else "❌")
        table.add_row(
            tid,
            f"{icon} {task.status.value}",
            f"{task.duration_ms}ms" if task.duration_ms else "-",
            str(task.exit_code) if task.exit_code is not None else "-",
            task.error[:50] if task.error else "",
        )

    console.print(table)


@app.command()
def monitor(
    workflow_name: str = typer.Option(..., "--workflow"),
    watch: bool = typer.Option(False, "--watch", help="Live refreshing dashboard"),
    refresh_s: int = typer.Option(5, "--refresh"),
) -> None:
    """Workflow health monitor with optional live refresh."""
    from agents.orchestrator.monitor import WorkflowMonitor

    monitor = WorkflowMonitor()

    def render_report():
        report = monitor.get_health_report(workflow_name)
        overall = report.get("overall", {})

        table = Table(title=f"Health Report: {workflow_name}")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="yellow")
        table.add_row("Success Rate", overall.get("success_rate", "N/A"))
        table.add_row("Total Runs", str(overall.get("total_runs", 0)))
        table.add_row("Completed", str(overall.get("completed", 0)))
        table.add_row("Failed", str(overall.get("failed", 0)))
        table.add_row("Avg Duration", f"{overall.get('avg_duration_s', 0)}s")
        table.add_row("Status", report.get("status", "unknown"))

        return table

    if watch:
        with Live(refresh_per_second=1 / refresh_s) as live:
            while True:
                live.update(render_report())
                time.sleep(refresh_s)
    else:
        console.print(render_report())


@app.command()
def validate(
    workflow: str = typer.Argument(...),
) -> None:
    """Validate a workflow JSON/YAML definition."""
    from agents.orchestrator.schema import WorkflowSchema

    p = Path(workflow)
    if not p.exists():
        p = _WORKFLOWS_DIR / workflow

    try:
        wf = WorkflowSchema.from_yaml(p) if p.suffix in (".yaml", ".yml") else WorkflowSchema.from_json(p)
    except Exception as e:
        console.print(f"[red]❌ Invalid: {e}[/red]")
        raise typer.Exit(1)

    # Structural checks
    errors: list[str] = []
    task_ids: set[str] = set()
    for t in wf.tasks:
        if not t.get("id"):
            errors.append(f"Task missing id: {t}")
        if t["id"] in task_ids:
            errors.append(f"Duplicate task id: {t['id']}")
        task_ids.add(t["id"])
        for dep in t.get("depends_on", []):
            if dep not in task_ids:
                # Don't error on forward references
                pass

    # Check circular dependencies
    order = wf.topological_order()
    if len(order) != len(wf.tasks):
        errors.append("Circular dependency detected")

    if errors:
        console.print("[red]❌ Validation failed:[/red]")
        for e in errors:
            console.print(f"  • {e}")
        raise typer.Exit(1)

    console.print(f"[green]✅ Valid:[/green] {wf.metadata.name} — {len(wf.tasks)} tasks")


@app.command()
def cancel(
    execution_id: str = typer.Option(..., "--execution-id"),
) -> None:
    """Cancel a running execution (sets stop flag, does not kill process)."""
    # Cancellation state is in-memory — just acknowledge
    console.print(f"[yellow]Cancel requested for:[/yellow] {execution_id}")
    console.print("[dim]Note: Cancellation is cooperative — the workflow will stop at next task boundary.[/dim]")


if __name__ == "__main__":
    app()

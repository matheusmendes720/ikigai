"""Paperclip CLI — ``paperclip`` console-script entry point.

Registered in ``src/ikigai/pyproject.toml`` as::

    [tool.poetry.scripts]
    paperclip = "agents.paperclip.cli:main"

Subcommands:

* ``paperclip status`` — print graph topology + adapter health + gate snapshot
* ``paperclip run --spec "..." [--dry-run] [--task-id ...]`` — invoke the graph
* ``paperclip spec validate <path>`` — stub for future spec schema validation

Dashboard note: the FastAPI dashboard (``scripts/paperclip-dashboard.py``)
lives outside the pip-installable package. Run it directly::

    python scripts/paperclip-dashboard.py
    # then open http://127.0.0.1:8765

Implementation notes:

* Pure stdlib + Typer (already in ``pyproject.toml`` dependencies). The
  ``run`` subcommand invokes Paperclip via the package's factory; status
  reads from the live policy/router state.
* Uses ``agents.paperclip.cli.main`` as the package's primary surface,
  matching the dotted-prefix import convention from M102.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

import typer

# ---------------------------------------------------------------------------
# Path setup — make paperclip package importable when invoked via the
# console script. Poetry's `pip install -e .` should already expose
# ``agents.paperclip.*`` via the editable install, but we add a safety net
# so the CLI also works from a checkout where ``agents.paperclip`` is NOT
# on sys.path (e.g. running directly from the repo with ``python -m``).
# ---------------------------------------------------------------------------
_THIS = Path(__file__).resolve()
_REPO_SRC = _THIS.parents[3]  # .../src
_REPO_ROOT = _THIS.parents[4]
for _p in (str(_REPO_SRC), str(_REPO_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# Now imports work. Import lazily so the CLI loads fast on --help.
log = logging.getLogger("paperclip.cli")

app = typer.Typer(
    name="paperclip",
    help="Paperclip meta-orchestrator CLI (M169+). Drives the 4th LangGraph graph.",
    no_args_is_help=True,
    add_completion=False,
)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo("paperclip 0.1.0 (MVP — M169/M170-M176)")
        raise typer.Exit()


@app.callback()
def main(
    version: bool | None = typer.Option(
        None,
        "--version",
        callback=_version_callback,
        is_eager=True,
        help="Print version and exit.",
    ),
) -> None:
    """Paperclip meta-orchestrator — orchestrating Claude / Pi / omo / openclaw / stubs."""


# ---------------------------------------------------------------------------
# paperclip status
# ---------------------------------------------------------------------------
@app.command(name="status", help="Print graph topology + adapter health + gate snapshot.")
def status_cmd(
    json_output: bool = typer.Option(False, "--json", help="Emit JSON instead of pretty text."),
) -> None:
    # Adapter health snapshot
    import shutil

    from agents.paperclip.agents.claude import ClaudeAdapter
    from agents.paperclip.agents.omo import OmoAdapter
    from agents.paperclip.agents.openclaw import OpenClawAdapter
    from agents.paperclip.agents.pi import PiAdapter
    from agents.paperclip.graph import NODES
    from agents.paperclip.policy import (
        DEFAULT_RISK_KEYWORDS,
        DEFAULT_THRESHOLD_S,
        DEFAULT_THRESHOLD_USD,
    )
    from agents.paperclip.policy import (
        ENV_THRESHOLD as COST_ENV,
    )
    from agents.paperclip.router import ADAPTER_PRIORITY

    adapters = []
    for name, cls in (
        ("claude", ClaudeAdapter),
        ("pi", PiAdapter),
        ("omo", OmoAdapter),
        ("openclaw", OpenClawAdapter),
    ):
        on_path = shutil.which(name) is not None
        adapters.append(
            {"name": name, "type": "real", "on_path": on_path, "timeout_s": cls.timeout_s}
        )
    adapters.append({"name": "mcode", "type": "stub", "on_path": False, "timeout_s": 180})
    adapters.append({"name": "hermes", "type": "stub", "on_path": False, "timeout_s": 180})

    snapshot: dict[str, Any] = {
        "graph_nodes": list(NODES),
        "adapter_priority": list(ADAPTER_PRIORITY),
        "adapters": adapters,
        "gates": {
            "cost": {
                "threshold_usd": float(os.environ.get(COST_ENV, DEFAULT_THRESHOLD_USD)),
                "env_var": COST_ENV,
                "semantics": "fail-OPEN",
                "milestone": "M173",
            },
            "wall_clock": {
                "threshold_s": int(
                    os.environ.get("PAPERCLIP_WALL_CLOCK_THRESHOLD_S", DEFAULT_THRESHOLD_S)
                ),
                "env_var": "PAPERCLIP_WALL_CLOCK_THRESHOLD_S",
                "semantics": "fail-OPEN",
                "milestone": "M175",
            },
            "risk": {
                "keywords_count": len(DEFAULT_RISK_KEYWORDS),
                "env_var": "PAPERCLIP_RISK_KEYWORDS",
                "semantics": "fail-CLOSED",
                "milestone": "M176",
            },
        },
    }

    if json_output:
        typer.echo(json.dumps(snapshot, indent=2))
    else:
        typer.echo(f"Paperclip — graph topology ({len(snapshot['graph_nodes'])} nodes):")
        for n in snapshot["graph_nodes"]:
            typer.echo(f"  • {n}")
        typer.echo("")
        typer.echo(f"Adapter priority: {' → '.join(snapshot['adapter_priority'])}")
        typer.echo()
        typer.echo(
            f"Adapters ({sum(1 for a in adapters if a['on_path'])}/{len(adapters)} on PATH):"
        )
        for a in adapters:
            mark = "✓" if a["on_path"] else "✗"
            typer.echo(f"  [{mark}] {a['name']:<10} {a['type']:<6} timeout={a['timeout_s']}s")
        typer.echo("")
        typer.echo("Throttle gates:")
        typer.echo(
            f"  CostGate      M173  ${snapshot['gates']['cost']['threshold_usd']:.2f}/day   fail-OPEN"
        )
        typer.echo(
            f"  WallClockGate M175  {snapshot['gates']['wall_clock']['threshold_s']}s          fail-OPEN"
        )
        typer.echo(
            f"  RiskGate      M176  {snapshot['gates']['risk']['keywords_count']} keywords    fail-CLOSED"
        )


# ---------------------------------------------------------------------------
# paperclip run
# ---------------------------------------------------------------------------
@app.command(name="run", help="Invoke the Paperclip meta-orchestrator on a spec.")
def run_cmd(
    spec: str = typer.Option(..., "--spec", "-s", help="Spec text (the task to perform)."),
    task_id: str | None = typer.Option(None, "--task-id", help="Override auto-generated task_id."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Use mock adapter instead of real CLIs."),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON instead of pretty text."),
) -> None:
    """Invoke Paperclip on a spec. With --dry-run, uses a mock adapter (no subprocess)."""
    from agents.paperclip.agents.base import AgentResult
    from agents.paperclip.graph import _build_paperclip_graph
    from agents.paperclip.policy import CostGate, RiskGate, WallClockGate

    run_task_id = task_id or f"cli-{os.urandom(4).hex()}"

    # Pick adapter (skip if dry_run)
    adapter = None
    if dry_run:

        class _DryRunAdapter:
            name = "dry-run"
            timeout_s = 1

            def run(
                self,
                prompt: str,
                cwd: Path,
                *,
                timeout_s: int | None = None,
            ) -> AgentResult:
                return AgentResult(
                    success=True,
                    output=f"[dry-run] would invoke AI on {len(prompt)} chars in {cwd}",
                    duration_s=0.0,
                )

        adapter = _DryRunAdapter()
    else:
        import shutil

        from agents.paperclip.agents.claude import ClaudeAdapter
        from agents.paperclip.agents.omo import OmoAdapter
        from agents.paperclip.agents.openclaw import OpenClawAdapter
        from agents.paperclip.agents.pi import PiAdapter
        from agents.paperclip.router import (
            AdapterHealth,
            SpecContext,
            pick_adapter,
        )

        health = {
            n: AdapterHealth(
                name=n, on_path=shutil.which(n) is not None, last_invoked_at=None, last_success=None
            )
            for n in ("claude", "pi", "omo", "openclaw")
        }
        try:
            decision = pick_adapter(
                SpecContext(task_id=run_task_id, spec_text=spec, cost_today_usd=0.0), health
            )
        except Exception as exc:
            typer.echo(f"router failed: {exc}", err=True)
            raise typer.Exit(2) from exc
        adapter_map = {
            "claude": ClaudeAdapter,
            "pi": PiAdapter,
            "omo": OmoAdapter,
            "openclaw": OpenClawAdapter,
        }
        adapter = adapter_map[decision.adapter]()

    # Build the graph
    ckpt = Path(os.environ.get("PAPERCLIP_CHECKPOINT_DB", "data/paperclip.db")).resolve()
    graph = _build_paperclip_graph(checkpoint_db=str(ckpt), entry_point="read_spec")

    # Wire adapter into implement_node via state["spec_text"] + adapter injection.
    # The implement_node reads `(state, *, adapter=None)` and uses the passed adapter.
    initial_state = {"task_id": run_task_id, "spec_text": spec, "messages": []}
    config = {"configurable": {"thread_id": run_task_id}}

    # Run gates before invoking
    gates_consulted = []
    cost_gate = CostGate()
    cost_ok, cost_reason = cost_gate.check()
    gates_consulted.append({"gate": "CostGate", "allowed": cost_ok, "reason": cost_reason})
    if not cost_ok:
        if json_output:
            typer.echo(
                json.dumps(
                    {"task_id": run_task_id, "gates": gates_consulted, "result": "blocked_by_cost"},
                    indent=2,
                )
            )
        else:
            typer.echo(f"❌ Cost gate blocked: {cost_reason}", err=True)
        raise typer.Exit(3)

    # WallClockGate
    import time as _time

    wall_gate = WallClockGate(
        task_started_at=_time.strftime("%Y-%m-%dT%H:%M:%SZ", _time.gmtime()),
        now_iso=_time.strftime("%Y-%m-%dT%H:%M:%SZ", _time.gmtime()),
        threshold_seconds=None,
    )
    wall_ok, wall_reason = wall_gate.check()
    gates_consulted.append({"gate": "WallClockGate", "allowed": wall_ok, "reason": wall_reason})
    if not wall_ok:
        if json_output:
            typer.echo(
                json.dumps(
                    {"task_id": run_task_id, "gates": gates_consulted, "result": "blocked_by_wall"},
                    indent=2,
                )
            )
        else:
            typer.echo(f"❌ Wall-clock gate blocked: {wall_reason}", err=True)
        raise typer.Exit(3)

    # RiskGate
    risk_gate = RiskGate(text_to_check=spec)
    risk_ok, risk_reason = risk_gate.check()
    gates_consulted.append({"gate": "RiskGate", "allowed": risk_ok, "reason": risk_reason})
    if not risk_ok:
        if json_output:
            typer.echo(
                json.dumps(
                    {"task_id": run_task_id, "gates": gates_consulted, "result": "blocked_by_risk"},
                    indent=2,
                )
            )
        else:
            typer.echo(f"❌ Risk gate blocked: {risk_reason}", err=True)
        raise typer.Exit(3)

    # Invoke the graph (use graph.stream to capture per-node progress)
    typer.echo(
        f"Invoking Paperclip (task_id={run_task_id}, dry_run={dry_run}, adapter={adapter.name})"
    )
    import time as _time

    started_at_iso = _time.strftime("%Y-%m-%dT%H:%M:%SZ", _time.gmtime())
    run_started_mono = _time.monotonic()
    steps = []
    final_values = {}
    graph_error: str | None = None
    try:
        for event in graph.stream(initial_state, config=config):
            for node_name, partial in event.items():
                if node_name.startswith("__"):
                    continue
                step = {
                    "node": node_name,
                    "ts": _time.strftime("%Y-%m-%dT%H:%M:%SZ", _time.gmtime()),
                }
                if isinstance(partial, dict):
                    err_type = partial.get("error_type")
                    if err_type:
                        step["error_type"] = err_type
                        step["error_message"] = partial.get("error_message", "")
                steps.append(step)
                typer.echo(
                    f"  → {node_name}"
                    + (f" [error: {step.get('error_type')}]" if step.get("error_type") else "")
                )
                if partial.get("error_type"):
                    final_values = partial
                    # Don't continue past error in node
                    break
        try:
            final = graph.get_state(config)
            if final and final.values:
                final_values = final.values
        except Exception:
            pass
    except Exception as exc:
        graph_error = f"{type(exc).__name__}: {exc}"
        typer.echo(f"graph invocation failed: {exc}", err=True)

    finished_at_iso = _time.strftime("%Y-%m-%dT%H:%M:%SZ", _time.gmtime())
    duration_s = round(_time.monotonic() - run_started_mono, 3)

    # ---- Persist run snapshot (M183) ----------------------------------
    # Always persists — post-mortem is most valuable when things go wrong.
    # Wrapped in try/except so a broken persistence layer never masks the
    # real graph outcome (e.g. the user wants to see the test failure, not
    # the JSON-write error).
    persisted_path = None
    try:
        from agents.paperclip.persistence import build_record_from_state, persist_run

        # Filter final_values to JSON-safe subset (mirrors the JSON output below).
        safe_final_state = {
            k: v
            for k, v in (final_values or {}).items()
            if k
            in (
                "commit_sha",
                "worktree_path",
                "branch_name",
                "error_type",
                "error_message",
                "last_step",
                "implement_iteration",
                "tests_ok",
            )
            and isinstance(v, (str, int, float, bool, list, dict, type(None)))
        }

        record = build_record_from_state(
            task_id=run_task_id,
            adapter=adapter.name,
            started_at=started_at_iso,
            finished_at=finished_at_iso,
            steps=steps,
            final_state=safe_final_state,
            gates_consulted=gates_consulted,
            error=graph_error,
        )
        record.duration_s = duration_s
        persisted_path = persist_run(record)
    except Exception as exc:
        log.warning("persist_run failed (non-fatal): %s", exc)

    if json_output:
        payload = {
            "task_id": run_task_id,
            "adapter": adapter.name,
            "dry_run": dry_run,
            "gates": gates_consulted,
            "steps": steps,
            "final_state": {
                k: v
                for k, v in (final_values or {}).items()
                if k
                in (
                    "commit_sha",
                    "worktree_path",
                    "branch_name",
                    "error_type",
                    "error_message",
                    "last_step",
                    "implement_iteration",
                    "tests_ok",
                )
                and isinstance(v, (str, int, float, bool, list, dict, type(None)))
            },
            "started_at": started_at_iso,
            "finished_at": finished_at_iso,
            "duration_s": duration_s,
            "persisted": str(persisted_path) if persisted_path else None,
        }
        typer.echo(json.dumps(payload, indent=2, default=str))
    else:
        typer.echo("")
        typer.echo("=" * 60)
        typer.echo(f"task_id:   {run_task_id}")
        typer.echo(f"adapter:   {adapter.name}")
        typer.echo(f"dry_run:   {dry_run}")
        typer.echo(f"steps:     {len(steps)}")
        typer.echo(f"duration:  {duration_s}s")
        if persisted_path:
            typer.echo(f"persisted: {persisted_path}")
        if final_values.get("commit_sha"):
            typer.echo(f"commit:    {final_values['commit_sha']}")
        if final_values.get("error_type") or graph_error:
            err_type = final_values.get("error_type", "GraphError")
            err_msg = final_values.get("error_message", "") or graph_error or ""
            typer.echo(f"error:     {err_type}: {err_msg}", err=True)
            raise typer.Exit(5)
        typer.echo("done.")


# ---------------------------------------------------------------------------
# paperclip runs — list recent persisted run snapshots
# ---------------------------------------------------------------------------
@app.command(name="runs", help="List recent persisted Paperclip run snapshots.")
def runs_cmd(
    limit: int = typer.Option(20, "--limit", "-n", help="How many runs to show (newest first)."),
    runs_dir: Path = typer.Option(
        Path("data/paperclip/runs"),
        "--runs-dir",
        help="Directory to scan (default: data/paperclip/runs).",
    ),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON instead of pretty text."),
) -> None:
    """Show the most recent run snapshots persisted by ``paperclip run``.

    Each row comes from a single JSON file in ``data/paperclip/runs/`` —
    these are the post-mortem snapshots written at the end of every
    ``paperclip run`` invocation (success or failure).
    """
    from agents.paperclip.persistence import list_recent_runs, load_run

    paths = list_recent_runs(runs_dir=runs_dir, limit=limit)
    if not paths:
        if json_output:
            typer.echo(json.dumps({"runs": [], "runs_dir": str(runs_dir)}, indent=2))
        else:
            typer.echo(f"no runs found in {runs_dir} — invoke `paperclip run --spec ...` first")
        return

    rows: list[dict[str, Any]] = []
    summaries: list[dict[str, Any]] = []
    for p in paths:
        try:
            payload = load_run(p)
        except Exception as exc:
            summaries.append({"path": str(p), "error": f"{type(exc).__name__}: {exc}"})
            continue
        rows.append(payload)
        summaries.append(
            {
                "path": str(p),
                "run_id": payload.get("run_id"),
                "task_id": payload.get("task_id"),
                "started_at": payload.get("started_at"),
                "finished_at": payload.get("finished_at"),
                "duration_s": payload.get("duration_s"),
                "adapter": payload.get("adapter"),
                "status": payload.get("status"),
                "steps": len(payload.get("steps") or []),
                "error": payload.get("error"),
            }
        )

    if json_output:
        typer.echo(
            json.dumps({"runs": summaries, "runs_dir": str(runs_dir)}, indent=2, default=str)
        )
        return

    # Pretty table.
    typer.echo(f"Recent runs (most recent first) — dir: {runs_dir}")
    typer.echo("-" * 80)
    # Fixed-width columns; truncate fields beyond their column width.
    fmt = "{:<12}  {:<22}  {:<7}  {:<8}  {:>5}  {}"
    typer.echo(fmt.format("TASK", "STARTED", "STATUS", "ADAPTER", "STEPS", "PATH"))
    for s in summaries:
        if "error" in s and "run_id" not in s:
            typer.echo(fmt.format("?", "?", "?", "?", "?", s["path"]))
            continue
        started = (s.get("started_at") or "")[:19].replace("T", " ")
        typer.echo(
            fmt.format(
                (s.get("task_id") or "")[:12],
                started,
                s.get("status") or "?",
                s.get("adapter") or "?",
                str(s.get("steps", "?")),
                s.get("path", ""),
            )
        )


# ---------------------------------------------------------------------------
# paperclip spec validate
# ---------------------------------------------------------------------------
@app.command(name="spec", help="Spec utilities.", no_args_is_help=True)
def spec_cmd() -> None:
    pass


@app.command(name="validate")
def spec_validate_cmd(
    path: Path = typer.Argument(..., help="Path to a .md spec file."),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON instead of pretty text."),
) -> None:
    """Stub: validate a spec file. Full implementation in a future wave."""
    if not path.exists():
        typer.echo(f"file not found: {path}", err=True)
        raise typer.Exit(1) from None
    text = path.read_text(encoding="utf-8")
    result = {
        "path": str(path),
        "size_chars": len(text),
        "lines": text.count("\n") + 1,
        "valid": True,  # Stub: always passes
        "note": "stub implementation — full schema validation in N+3",
    }
    if json_output:
        typer.echo(json.dumps(result, indent=2))
    else:
        typer.echo(
            f"✓ {path} — {result['size_chars']} chars, {result['lines']} lines (stub validation)"
        )


if __name__ == "__main__":
    app()

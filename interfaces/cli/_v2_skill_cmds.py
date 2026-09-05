"""v2 — Per-skill Typer command bodies (daily/weekly/monthly/quarterly).

Bound to v2.app via `register_skill(app, console)` from v2.py. Each command
is a thin orchestrator over `_run_<period>` from `_v2_skills.py`.

Per-skill orchestrators stay strictly read-only on vault/ (per ADR-012 +
skill frontmatter constraints):
  - Writes go through `vault_write` MCP tool (called by the v2 graph's
    commit node when invoked via `v2 cycle`).
  - These commands ORCHESTRATE — they do NOT execute math (per ADR-013).

Why a separate file from _v2_skills.py: keeping _v2_skills.py focused on
the orchestrator/core logic keeps each module under the CLAUDE.md 500-line
guideline (W6.X item 2b hygiene item).
"""

from __future__ import annotations

import json
from datetime import date

import typer

from ._v2_skills import _run_daily, _run_monthly, _run_quarterly, _run_weekly


def register_skill(app: typer.Typer, console) -> None:
    """Bind 4 per-skill typer commands to `app` (W2.3 / W6.X item 2).

    daily / weekly / monthly / quarterly → ikigai-<period> skill.

    Each command is a thin orchestrator over `_run_<period>` (in
    _v2_skills.py) which routes through invoke_skill(). The skill files at
    src/ikigai/src/agents/v2/skills/<name>.md declare entry_point + outputs.
    """

    @app.command(name="daily")
    def daily(
        date_arg: str = typer.Argument(
            "",
            help="Date to surface daily intentions for (YYYY-MM-DD). Defaults to today.",
        ),
        json_output: bool = typer.Option(False, "--json", help="Machine-readable output"),
    ) -> None:
        """Run ikigai-daily skill — surface PAV intentions (3-5 pt-BR suggestions).

        Orchestrates render_surface_pav_intentions prompt chain. Reads PAV-written
        cycle_state + last 3 daily reports. Strictly read-only on vault/.
        Reference: src/ikigai/src/agents/v2/skills/daily.md
        """
        date_str = date_arg or date.today().isoformat()
        try:
            result = _run_daily(date_str)
        except Exception as exc:
            console.print(f"[red]Daily skill error:[/red] {exc}")
            raise typer.Exit(1)

        if json_output:
            console.print_json(json.dumps(result, default=str))
        else:
            surface = result.get("surface", {})
            suggestions = surface.get("suggestions", [])
            lang = surface.get("language", "pt-BR")
            console.print(f"[green]ikigai-daily for {date_str} [{lang}]:[/green]")
            if not suggestions:
                console.print("  [dim](no suggestions surfaced)[/dim]")
            for i, s in enumerate(suggestions, 1):
                console.print(f"  {i}. {s}")

    @app.command(name="weekly")
    def weekly(
        date_arg: str = typer.Argument(
            "",
            help="Date for weekly review (YYYY-MM-DD). Defaults to today.",
        ),
        json_output: bool = typer.Option(False, "--json", help="Machine-readable output"),
    ) -> None:
        """Run ikigai-weekly skill — score vectors + regime check.

        Orchestrates score_passion_observation + heuristics_regime_observation prompt
        chains. Aggregates last 7 daily reports. Strictly read-only on vault/.
        Reference: src/ikigai/src/agents/v2/skills/weekly.md
        """
        date_str = date_arg or date.today().isoformat()
        try:
            result = _run_weekly(date_str)
        except Exception as exc:
            console.print(f"[red]Weekly skill error:[/red] {exc}")
            raise typer.Exit(1)

        if json_output:
            console.print_json(json.dumps(result, default=str))
        else:
            score = result.get("score", {})
            regime = result.get("regime", {})
            console.print(f"[green]ikigai-weekly for {date_str}:[/green]")
            # Score line
            if "error" in score:
                console.print(f"  [yellow]Score: error — {score.get('error')}[/yellow]")
            else:
                ps = score.get(
                    "passion_score", score.get("vector_scores", {}).get("passion", "?")
                )
                console.print(f"  passion_score: {ps}")
            # Regime line
            if "error" in regime:
                console.print(f"  [yellow]Regime: error — {regime.get('error')}[/yellow]")
            else:
                rg = regime.get("regime", "?")
                console.print(f"  regime: {rg}")

    @app.command(name="monthly")
    def monthly(
        date_arg: str = typer.Argument(
            "",
            help="Date for monthly review (YYYY-MM-DD). Defaults to today.",
        ),
        json_output: bool = typer.Option(False, "--json", help="Machine-readable output"),
    ) -> None:
        """Run ikigai-monthly skill — full cycle (dry-run) + score + regime.

        Orchestrates cycle (dry-run) + score + regime. Aggregates last 4 weekly
        reviews. Strictly read-only on vault/ (cycle is dry-run only).
        Reference: src/ikigai/src/agents/v2/skills/monthly.md
        """
        date_str = date_arg or date.today().isoformat()
        try:
            result = _run_monthly(date_str)
        except Exception as exc:
            console.print(f"[red]Monthly skill error:[/red] {exc}")
            raise typer.Exit(1)

        if json_output:
            console.print_json(json.dumps(result, default=str))
        else:
            cycle = result.get("cycle", {})
            score = result.get("score", {})
            regime = result.get("regime", {})
            console.print(f"[green]ikigai-monthly for {date_str}:[/green]")
            # Cycle line
            if "error_type" in cycle and cycle["error_type"]:
                console.print(f"  [yellow]Cycle: error — {cycle['error_type']}[/yellow]")
            else:
                console.print(
                    f"  cycle: {cycle.get('graph', '?')} "
                    f"(entry_point={cycle.get('entry_point', '?')}, "
                    f"dry_run={cycle.get('dry_run', '?')})"
                )
            # Score line
            if "error" in score:
                console.print(f"  [yellow]Score: error — {score.get('error')}[/yellow]")
            else:
                ps = score.get(
                    "passion_score", score.get("vector_scores", {}).get("passion", "?")
                )
                console.print(f"  passion_score: {ps}")
            # Regime line
            if "error" in regime:
                console.print(f"  [yellow]Regime: error — {regime.get('error')}[/yellow]")
            else:
                rg = regime.get("regime", "?")
                console.print(f"  regime: {rg}")

    @app.command(name="quarterly")
    def quarterly(
        date_arg: str = typer.Argument(
            "",
            help="Date for quarterly review (YYYY-MM-DD). Defaults to today.",
        ),
        json_output: bool = typer.Option(False, "--json", help="Machine-readable output"),
    ) -> None:
        """Run ikigai-quarterly skill — strategic realignment (cycle dry-run + score + regime).

        Orchestrates cycle (dry-run) + score + regime. Reads last 3 monthly + last
        13 weekly reviews. Strictly read-only on vault/ (cycle is dry-run only).
        Reference: src/ikigai/src/agents/v2/skills/quarterly.md
        """
        date_str = date_arg or date.today().isoformat()
        try:
            result = _run_quarterly(date_str)
        except Exception as exc:
            console.print(f"[red]Quarterly skill error:[/red] {exc}")
            raise typer.Exit(1)

        if json_output:
            console.print_json(json.dumps(result, default=str))
        else:
            cycle = result.get("cycle", {})
            score = result.get("score", {})
            regime = result.get("regime", {})
            console.print(f"[green]ikigai-quarterly for {date_str}:[/green]")
            if "error_type" in cycle and cycle["error_type"]:
                console.print(f"  [yellow]Cycle: error — {cycle['error_type']}[/yellow]")
            else:
                console.print(
                    f"  cycle: {cycle.get('graph', '?')} "
                    f"(entry_point={cycle.get('entry_point', '?')}, "
                    f"dry_run={cycle.get('dry_run', '?')})"
                )
            if "error" in score:
                console.print(f"  [yellow]Score: error — {score.get('error')}[/yellow]")
            else:
                ps = score.get(
                    "passion_score", score.get("vector_scores", {}).get("passion", "?")
                )
                console.print(f"  passion_score: {ps}")
            if "error" in regime:
                console.print(f"  [yellow]Regime: error — {regime.get('error')}[/yellow]")
            else:
                rg = regime.get("regime", "?")
                console.print(f"  regime: {rg}")

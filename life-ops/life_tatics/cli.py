import json
import typer
from life_tatics.domain.time_blocks import manage_block
from life_tatics.domain.screentime import log_screentime

app = typer.Typer(
    help="Standalone Time Allocation and Routine Tracker (@life-tatics).",
    no_args_is_help=True,
)


@app.command()
def block(
    action: str = typer.Argument(..., help="'start' or 'stop'"),
    name: str = typer.Option("unknown", "--name", "-n"),
    json_out: bool = typer.Option(False, "--json", help="Output in JSON format"),
):
    """Start or stop a time allocation block."""
    result = manage_block(action, name)
    if json_out:
        print(json.dumps(result))
    else:
        typer.echo(f"Block action '{action}' on '{name}' recorded successfully.")


@app.command()
def screentime(
    mode: str = typer.Argument(..., help="'dev' or 'rest'"),
    duration: int = typer.Option(0, "--duration", "-d", help="Minutes spent"),
    json_out: bool = typer.Option(False, "--json"),
):
    """Log development vs testing/resting screentime."""
    result = log_screentime(mode, duration)
    if json_out:
        print(json.dumps(result))
    else:
        typer.echo(f"Logged {duration} minutes of '{mode}' screentime.")


@app.command()
def routine(
    kind: str = typer.Argument(..., help="'morning' or 'evening'"),
    json_out: bool = typer.Option(False, "--json"),
):
    """Run routine checklists."""
    result = {"routine": kind, "status": "pending_implementation"}
    if json_out:
        print(json.dumps(result))
    else:
        typer.echo(f"Routine '{kind}' invoked. (Checklist feature pending).")


if __name__ == "__main__":
    app()

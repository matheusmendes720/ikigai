"""notify_cli.py - life notify subcommand (M75).

Tiny Typer sub-app exposing the notify router to the CLI surface.
Lets you test the notification pipeline end-to-end and broadcast
ad-hoc messages to your channels.

Usage:
    life notify "M75 done" "749 PASS + 95 SKIP"
    life notify "ALERT" "taskdog health failed" --level error
    life notify --status
    life notify test --channel telegram
"""

from __future__ import annotations

import json
from pathlib import Path

import typer

from .notify import health, notify

app = typer.Typer(help="Send notifications via the router (M75).")


@app.command()
def send(
    title: str = typer.Argument(..., help="Notification title."),
    body: str = typer.Argument("", help="Notification body."),
    level: str = typer.Option("info", "--level", "-l"),
    payload_json: str = typer.Option("", "--payload", "-p"),
    file: Path = typer.Option(None, "--file"),
):
    payload = None
    if payload_json:
        try:
            payload = json.loads(payload_json)
        except json.JSONDecodeError as exc:
            typer.echo(f"ERROR: invalid JSON: {exc}", err=True)
            raise typer.Exit(code=2)
    result = notify(title, body, level=level, payload=payload, file_path=file)
    typer.echo(json.dumps(result, indent=2))


@app.command("status")
def status_cmd():
    info = health()
    typer.echo(json.dumps(info, indent=2))


@app.command("test")
def test_cmd(
    channel: str = typer.Option("file", "--channel"),
):
    if channel in ("file", "both"):
        result = notify(
            "TEST notify ping",
            "If you see this in notifications.log, file channel works.",
            level="success",
        )
        typer.echo("file: " + str(result["channels"]))
    if channel in ("telegram", "both"):
        result = notify(
            "TEST notify ping",
            "If you receive this on Telegram, the bot is wired.",
            level="success",
        )
        typer.echo("telegram: " + str(result.get("channels", [])))
        if "telegram_error" in result:
            typer.echo("telegram error: " + result["telegram_error"], err=True)
            raise typer.Exit(code=1)


if __name__ == "__main__":
    app()

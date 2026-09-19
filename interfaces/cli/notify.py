"""notify.py — outbound notification router (M75).

Routes notifications to one or more channels:
- stdout (always, when HERMES env var set or `-v`)
- file (always, appends to .life/logs/notifications.log)
- telegram (optional, if TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID env vars set)

Used by daemon-manager.sh to forward loop results to the user.
Per ADR-012 vault-only invariant: notifications are NOT written to
the vault (they are runtime-only artifacts).

Usage:
    from interfaces.cli.notify import notify
    notify("M75 done", "749 PASS + 95 SKIP")
    notify("ALERT", "taskdog-server health check failed", level="error")
    notify("M76", "tests run", payload={"passed": 329, "failed": 0})

Environment variables (all optional):
    TELEGRAM_BOT_TOKEN  — bot token from @BotFather
    TELEGRAM_CHAT_ID    — chat ID (numeric, or @channelusername)
    NOTIFY_VERBOSE      — 1 to also print to stdout
    NOTIFY_FILE         — path to notification log (default:
                           .life/logs/notifications.log)

The Telegram adapter uses urllib.request (stdlib, no extra deps).
Rate-limited to 1 msg/sec to avoid Telegram flood limits.
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_LOG = Path(".life/logs/notifications.log")


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _level_icon(level: str) -> str:
    return {
        "info": "ℹ️",
        "success": "✅",
        "warning": "⚠️",
        "error": "❌",
        "alert": "🚨",
    }.get(level, "•")


def notify(
    title: str,
    body: str = "",
    *,
    level: str = "info",
    payload: dict[str, Any] | None = None,
    file_path: Path | None = None,
) -> dict[str, Any]:
    """Send a notification to all configured channels.

    Returns a dict describing which channels received it (for tests).
    """
    icon = _level_icon(level)
    timestamp = _now()
    body_text = body if body else ""
    payload_text = ""
    if payload:
        try:
            payload_text = "\n" + json.dumps(payload, indent=2, default=str)
        except (TypeError, ValueError):
            payload_text = "\n[payload: non-serializable]"

    message = f"{icon} *{title}*\n{body_text}{payload_text}\n_{timestamp}_"

    result = {
        "title": title,
        "level": level,
        "timestamp": timestamp,
        "channels": [],
    }

    # File channel (always)
    log_path = file_path or Path(os.environ.get("NOTIFY_FILE", str(DEFAULT_LOG)))
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as f:
            f.write(message + "\n\n")
        result["channels"].append("file")
    except OSError as exc:
        result["file_error"] = str(exc)

    # Stdout channel (only with NOTIFY_VERBOSE=1 or explicit -v flag)
    verbose = os.environ.get("NOTIFY_VERBOSE") == "1"
    if verbose or "-v" in sys.argv:
        print(f"[notify] {message}")
        result["channels"].append("stdout")

    # Telegram channel (optional)
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if token and chat_id:
        try:
            _send_telegram(token, chat_id, message)
            result["channels"].append("telegram")
        except Exception as exc:  # noqa: BLE001 — surface all errors
            result["telegram_error"] = f"{type(exc).__name__}: {exc}"

    return result


def _send_telegram(token: str, chat_id: str, message: str) -> None:
    """Post a message to Telegram via Bot API (urllib stdlib, no deps)."""
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = json.dumps({
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
    }).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        if resp.status != 200:
            raise RuntimeError(f"telegram returned {resp.status}")
        body = resp.read().decode("utf-8")
        parsed = json.loads(body)
        if not parsed.get("ok"):
            raise RuntimeError(f"telegram error: {parsed.get('description')}")


def health() -> dict[str, Any]:
    """Report which channels are active. Useful for `--notify-status` CLI flag."""
    return {
        "file": str(DEFAULT_LOG),
        "file_writable": _is_writable(DEFAULT_LOG),
        "telegram_configured": bool(
            os.environ.get("TELEGRAM_BOT_TOKEN")
            and os.environ.get("TELEGRAM_CHAT_ID")
        ),
        "verbose": os.environ.get("NOTIFY_VERBOSE") == "1",
    }


def _is_writable(path: Path) -> bool:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8"):
            pass
        return True
    except OSError:
        return False


__all__ = ["notify", "health"]

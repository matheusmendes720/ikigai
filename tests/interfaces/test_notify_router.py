"""Smoke test for the notify router (M75).

Verifies file channel works (always-on, no external deps) and that
telegram channel is correctly gated on TELEGRAM_BOT_TOKEN env var.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest


@pytest.fixture
def tmp_log(tmp_path, monkeypatch):
    """Point NOTIFY_FILE at a tmp file for the duration of the test."""
    log = tmp_path / "notifications.log"
    monkeypatch.setenv("NOTIFY_FILE", str(log))
    # Ensure no TELEGRAM vars leak from the host env
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    return log


def test_notify_writes_to_file(tmp_log):
    """File channel appends the message with title, body, and timestamp."""
    from interfaces.cli.notify import notify

    result = notify("M75 done", "749 PASS + 95 SKIP")
    assert "file" in result["channels"]
    assert result["title"] == "M75 done"
    assert result["level"] == "info"

    text = tmp_log.read_text(encoding="utf-8")
    assert "M75 done" in text
    assert "749 PASS" in text
    # Markdown-style bold + timestamp marker
    assert "*M75 done*" in text
    assert "_20" in text  # year prefix of ISO timestamp


def test_notify_supports_all_levels(tmp_log):
    """Each level gets a distinct icon in the rendered message."""
    from interfaces.cli.notify import notify

    for level in ("info", "success", "warning", "error", "alert"):
        result = notify(f"title-{level}", f"body-{level}", level=level)
        assert "file" in result["channels"]

    text = tmp_log.read_text(encoding="utf-8")
    # Spot-check the iconography (one per level)
    assert "ℹ️" in text
    assert "✅" in text
    assert "⚠️" in text
    assert "❌" in text
    assert "🚨" in text


def test_notify_with_payload(tmp_log):
    """Payload dict is JSON-serialized into the message body."""
    from interfaces.cli.notify import notify

    notify(
        "M76",
        "tests run",
        payload={"passed": 329, "failed": 0},
    )
    text = tmp_log.read_text(encoding="utf-8")
    assert '"passed": 329' in text or "passed" in text
    assert '"failed": 0' in text or "failed" in text


def test_notify_skips_telegram_when_no_token(tmp_log):
    """Without TELEGRAM_BOT_TOKEN, telegram channel is not attempted."""
    from interfaces.cli.notify import notify

    result = notify("M77", "")
    assert "telegram" not in result["channels"]
    assert "telegram_error" not in result


def test_notify_with_telegram_token_marks_channel(tmp_log, monkeypatch):
    """When TELEGRAM_BOT_TOKEN + CHAT_ID set, channel is attempted.

    We don't actually post (would hit real API). The urllib.request call
    would fail with a non-telegram error since the token is fake; we
    assert the channel appears in result.channels OR telegram_error
    surfaces the failure (proving the attempt was made).
    """
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "0000000000:FAKE_TOKEN_FOR_TEST")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "000000000")
    from interfaces.cli.notify import notify

    result = notify("M78", "telegram path")
    # Either channel succeeded, or telegram_error was recorded
    assert "telegram" in result["channels"] or "telegram_error" in result


def test_health_reports_channel_state(tmp_log, monkeypatch):
    """health() inspects env vars to report which channels are wired."""
    from interfaces.cli.notify import health

    info = health()
    assert "file" in info
    assert "telegram_configured" in info
    assert info["telegram_configured"] is False  # monkeypatch cleared

    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "x")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "y")
    info2 = health()
    assert info2["telegram_configured"] is True

"""OpenClaw adapter — REAL implementation (MVP).

Subprocess invocation of the ``openclaw`` CLI inside the worktree. Mirrors the
``run_taskdog`` pattern at ``src/ikigai/tools/vault_taskdog_sync.py:61-75``
(Path 1 taskdog pattern from M-series memory) and the ``ClaudeAdapter`` shape
at ``paperclip/agents/claude.py`` (same one-shot subprocess design).

CLI signature discovery (run ``openclaw --help`` + ``openclaw agent --help``
on 2026-10-11 — OpenClaw 2026.7.1-2 0790d9f):

* ``openclaw [options] [command]`` is subcommand-style — there is NO
  ``openclaw run <prompt>`` (the binary errors with ``Unknown command:
  openclaw run``) and no positional prompt arg.
* The agent turn is invoked via ``openclaw agent [options]`` and the
  prompt body is passed via the ``--message`` / ``-m`` flag (NOT
  positional).
* ``openclaw agent`` defaults to running through the Gateway; the
  ``--local`` flag switches to the embedded agent (requires model-provider
  API keys in the shell env, but no Gateway daemon).
* ``--no-color`` is the canonical way to disable ANSI escape codes so
  ``capture_output=True, text=True`` returns clean text on stdout.

Failure semantics:
* Non-zero return code → ``success=False``, ``error="<stderr>"``.
* TimeoutExpired → ``success=False``, ``error="timeout after Ns"``.
* Agent never crashes the graph; ``implement_node`` reads ``success`` and
  either retries (test fail) or proceeds to commit.
"""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

from .base import AgentResult


class OpenClawAdapter:
    """Subprocess wrapper for the OpenClaw agent CLI.

    Tested implicitly via
    ``test_graph_smoke.py::test_openclaw_adapter_protocol`` — must satisfy
    the ``AgentAdapter`` protocol structurally (``runtime_checkable``
    Protocol in ``base.py``).
    """

    name = "openclaw"
    timeout_s = 180  # 3 minutes; can be overridden per-call

    def run(
        self,
        prompt: str,
        cwd: Path,
        *,
        timeout_s: int | None = None,
    ) -> AgentResult:
        """Invoke ``openclaw agent --local --no-color --message <prompt>`` in ``cwd``.

        Args:
            prompt: text to pass to the CLI via ``--message``. Paperclip's
                ``implement_node`` builds this from the resolved spec.
            cwd: worktree directory the agent should write to. Implementation
                does NOT chdir-validate; the caller is trusted.
            timeout_s: optional per-call override of ``self.timeout_s``.

        Returns:
            ``AgentResult(success, output, duration_s, error)`` — never raises.
        """
        effective_timeout = timeout_s or self.timeout_s
        env = os.environ.copy()
        # Defensive env fix from ``run_taskdog`` pattern — harmless for openclaw
        env["COLUMNS"] = "200"
        env["LINES"] = "50"

        start = time.monotonic()
        try:
            proc = subprocess.run(
                [
                    "openclaw",
                    "agent",
                    "--local",
                    "--no-color",
                    "--message",
                    prompt,
                ],
                cwd=str(cwd),
                capture_output=True,
                text=True,
                timeout=effective_timeout,
                env=env,
                check=False,  # we read returncode + report success ourselves
            )
            duration = time.monotonic() - start
            if proc.returncode == 0:
                return AgentResult(
                    success=True,
                    output=proc.stdout,
                    duration_s=duration,
                )
            return AgentResult(
                success=False,
                output=proc.stdout,
                duration_s=duration,
                error=f"openclaw exit={proc.returncode}: {proc.stderr.strip()}",
            )
        except subprocess.TimeoutExpired:
            duration = time.monotonic() - start
            return AgentResult(
                success=False,
                output="",
                duration_s=duration,
                error=f"timeout after {effective_timeout}s",
            )
        except FileNotFoundError as exc:
            # ``openclaw`` binary not on PATH — treat as adapter-not-ready,
            # not a graph error. Caller decides what to do.
            return AgentResult(
                success=False,
                output="",
                duration_s=0.0,
                error=f"openclaw CLI not found on PATH: {exc}",
            )

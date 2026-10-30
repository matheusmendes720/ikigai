"""Claude Code adapter — REAL implementation (MVP).

Subprocess invocation of the ``claude`` CLI inside the worktree. Mirrors the
``run_taskdog`` pattern at ``src/ikigai/tools/vault_taskdog_sync.py:61-75``
(Path 1 taskdog pattern from M-series memory):

* ``subprocess.run`` with ``capture_output=True`` + ``text=True`` + a hard
  ``timeout``.
* ``COLUMNS=200 LINES=50`` env fix to dodge paginated-table issues on some
  CLIs (defensive — harmless for ``claude``).
* No Popen / no JSON-RPC framing — ``claude`` CLI is one-shot text-in /
  text-out, so ``run`` is sufficient (the JSON-RPC-framed ``StdioAdapter``
  in ``sys_ikigai/gateway/stdio_adapter.py`` is for binary MCP servers).

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


class ClaudeAdapter:
    """Subprocess wrapper for the Claude Code CLI.

    Tested implicitly via ``test_graph_smoke.py::test_claude_adapter_contract``
    — must satisfy the ``AgentAdapter`` protocol structurally
    (``runtime_checkable`` Protocol in ``base.py``).
    """

    name = "claude"
    timeout_s = 180  # 3 minutes; can be overridden per-call

    def run(
        self,
        prompt: str,
        cwd: Path,
        *,
        timeout_s: int | None = None,
    ) -> AgentResult:
        """Invoke ``claude <prompt>`` in ``cwd`` and capture stdout/stderr.

        Args:
            prompt: text to pass to the CLI as a positional arg. Paperclip's
                ``implement_node`` builds this from the resolved spec.
            cwd: worktree directory the agent should write to. Implementation
                does NOT chdir-validate; the caller is trusted.
            timeout_s: optional per-call override of ``self.timeout_s``.

        Returns:
            ``AgentResult(success, output, duration_s, error)`` — never raises.
        """
        effective_timeout = timeout_s or self.timeout_s
        env = os.environ.copy()
        # Defensive env fix from ``run_taskdog`` pattern — harmless for claude
        env["COLUMNS"] = "200"
        env["LINES"] = "50"

        start = time.monotonic()
        try:
            proc = subprocess.run(
                ["claude", prompt],
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
                error=f"claude exit={proc.returncode}: {proc.stderr.strip()}",
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
            # ``claude`` binary not on PATH — treat as adapter-not-ready,
            # not a graph error. Caller decides what to do.
            return AgentResult(
                success=False,
                output="",
                duration_s=0.0,
                error=f"claude CLI not found on PATH: {exc}",
            )

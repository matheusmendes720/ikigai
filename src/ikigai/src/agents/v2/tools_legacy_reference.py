"""READ-ONLY legacy reference — DO NOT IMPORT.

Kept per ADR-013 scope discipline for inspection during Phase 8 refactor.
The entire module body is wrapped in `if False:` so this file is never executed
and never participates in the runtime module graph.

Drift detector: this file is scanned by test_canonical_scope.py (agents/ is in scope).
The if False: wrapper prevents any top-level FunctionDef/Import from being detected
as live definitions. The code is preserved verbatim as a historical artifact.
"""

# ---------------------------------------------------------------------------
# SOURCE FILE: tools_PRE_STRIP_8992e0c.py (1020 lines)
# Original commit: 8992e0c
# See archive/recovered-agentic-2026-09-01/ for the canonical source.
# ---------------------------------------------------------------------------

if False:
    import json
    import os
    import sqlite3
    import subprocess
    from pathlib import Path
    from typing import Any, Literal, cast

    from langchain_core.tools import tool

    from .reliability import (
        CircuitBreakerConfig,
        RetryConfig,
        _set_cache_ref,
        circuit_breaker,
        invalidate_session_cache,
        retry_with_backoff,
    )

    # ---------------------------------------------------------------------------
    # MCP Session Cache (for connection state tracking)
    # ---------------------------------------------------------------------------

    _MCP_SESSION_CACHE: dict[str, bool] = {}
    _set_cache_ref(_MCP_SESSION_CACHE)

    # ---------------------------------------------------------------------------
    # External tool configurations
    # ---------------------------------------------------------------------------

    _SOLVERFORGE_CLI = os.environ.get("SOLVERFORGE_CLI", "solverforge-calendar-cli.exe")
    _TUIBOARD_CLI = os.environ.get("TUIBOARD_CLI", "bun")
    _TUIBOARD_MCP = os.environ.get("TUIBOARD_MCP", "tuiboard-mcp.ts")
    _TASKDOG_CLI = os.environ.get("TASKDOG_CLI", "taskdog.exe")

    # ---------------------------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------------------------

    _PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
    _CHECKPOINT_DB = str(_PROJECT_ROOT / "data" / "ikigai_checkpoints.db")
    _VAULT_DIR = _PROJECT_ROOT / "vault"

    def _get_checkpoint_path() -> Path:
        p = Path(_CHECKPOINT_DB)
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    def _read_checkpoint_data(thread_id: str = "default") -> dict[str, Any]:
        """Read latest checkpoint for a thread."""
        p = _get_checkpoint_path()
        if not p.exists():
            return {}
        import msgpack

        conn = sqlite3.connect(str(p))
        cur = conn.cursor()
        cur.execute(
            "SELECT checkpoint FROM checkpoints WHERE thread_id = ? ORDER BY checkpoint_id DESC LIMIT 1",
            (thread_id,),
        )
        row = cur.fetchone()
        conn.close()
        if row and row[0]:
            try:
                data = cast(dict[str, Any], msgpack.unpackb(row[0]))
                channel_values = data.get("channel_values")
                if isinstance(channel_values, dict):
                    return channel_values
                return data
            except Exception:
                return {}
        return {}

    # ---------------------------------------------------------------------------
    # Tool 1: score
    # ---------------------------------------------------------------------------

    @tool
    def ikigai_score(thread_id: str = "default") -> str:
        """Get current IKIGAi 5-vector scores and meta-vector composite score."""
        d = _read_checkpoint_data(thread_id)
        vs = d.get("vector_scores", {})
        mv = d.get("meta_vector_score", 0.0)
        qhe = d.get("q_he_score", 0.0)
        if not vs:
            return "No vector scores found in checkpoint. Run `plan` first."
        lines = [f"**IKIGAi Scores**  (meta: {mv:.4f}  Q_HE: {qhe:.4f})", ""]
        for vec in ("passion", "skill", "market", "revenue", "course"):
            v = vs.get(vec, 0.0)
            bar = "█" * int(v / 10) + "░" * (10 - int(v / 10))
            lines.append(f"  {vec.capitalize():12s} [{bar}] {v:.1f}")
        return "\n".join(lines)

    # ---------------------------------------------------------------------------
    # Tool 2: regime
    # ---------------------------------------------------------------------------

    @tool
    def ikigai_regime(thread_id: str = "default") -> str:
        """Get current regime state (PUSH/MAINTAIN/REDUCE/RECOVER), Q_HE, days-in-regime."""
        d = _read_checkpoint_data(thread_id)
        regime = d.get("regime_state", "MAINTAIN")
        days = d.get("days_in_regime", 0)
        qhe = d.get("q_he_score", 0.65)
        emoji = {"PUSH": "🔴", "MAINTAIN": "🟡", "REDUCE": "🟠", "RECOVER": "🟢"}.get(regime, "⚪")
        return f"{emoji} **Regime: {regime}**  |  Q_HE: {qhe:.4f}  |  Days: {days}"

    # ---------------------------------------------------------------------------
    # Tool 3: phase
    # ---------------------------------------------------------------------------

    @tool
    def ikigai_phase(thread_id: str = "default") -> str:
        """Get current phase and 5-vector weight distribution."""
        d = _read_checkpoint_data(thread_id)
        phase = d.get("phase", "BUSCA")
        pi = d.get("phase_iteration", 0)
        converged = d.get("phase_converged", False)
        pw = d.get("phase_weights", {})
        emoji = {
            "FUNDAÇÃO": "🏗️",
            "BUSCA": "🔍",
            "HACKATHON": "⚡",
            "RECUPERACAO": "🔧",
            "OVERCLOCK": "🔥",
        }.get(phase, "❓")
        lines = [f"{emoji} **Phase: {phase}**  iter={pi}  converged={converged}", "", "Weights:"]
        for k, v in pw.items():
            lines.append(f"  {k.capitalize():12s}: {v:.2f}")
        return "\n".join(lines)

    # ---------------------------------------------------------------------------
    # Tool 4: corrections
    # ---------------------------------------------------------------------------

    @tool
    def ikigai_corrections(thread_id: str = "default") -> str:
        """Get active correction signals from H1-H6 heuristics."""
        d = _read_checkpoint_data(thread_id)
        corrs = d.get("corrections", [])
        if not corrs:
            return "No corrections — system is balanced."
        lines = [f"**Corrections ({len(corrs)})**", ""]
        for c in corrs[-5:]:
            lines.append(f"  [{c.get('heuristic', '?')}] {c.get('description', '')}")
        return "\n".join(lines)

    # ---------------------------------------------------------------------------
    # Tool 5: decompose
    # ---------------------------------------------------------------------------

    @tool
    def ikigai_decompose(ueid: str, thread_id: str = "default") -> str:
        """Decompose a UEID into its full hierarchy: Dream → Objectives → Projects → Tasks."""
        if not ueid:
            return "Provide a UEID, e.g. ikigai_decompose(ueid='ikigai:dream:vaga-remota-2026')"
        try:
            from mcp_server.server import _decompose_ueid

            result = _decompose_ueid(ueid)
            dream = result.get("dream", {})
            objectives = result.get("objectives", [])
            projects = result.get("projects", [])
            lines = [
                f"**Dream:** {dream.get('title', dream.get('slug', ueid))}  [{dream.get('status', '?')}]",
                "",
            ]
            if objectives:
                lines.append(f"  Objectives ({len(objectives)}):")
                for o in objectives:
                    lines.append(f"    • {o.get('title', '?')}  [{o.get('status', '?')}]")
            if projects:
                lines.append(f"  Projects ({len(projects)}):")
                for p in projects:
                    lines.append(f"    • {p.get('title', '?')}  [{p.get('status', '?')}]")
            return "\n".join(lines)
        except Exception as e:
            return f"Could not decompose UEID: {e}"

    # ---------------------------------------------------------------------------
    # Tool 6: plan_cycle — REMOVED from legacy reference
    # Original function had: from agents.ikigai_maintainer import make_ikigai_graph
    # (FORBIDDEN_IMPORT per ADR-013). Full source in archive at:
    # archive/recovered-agentic-2026-09-01/src_ikigai_src_agents/tools_PRE_STRIP_8992e0c.py
    # ---------------------------------------------------------------------------

    # Stub to preserve list length without the forbidden import
    def ikigai_plan_cycle(thread_id: str = "default") -> str:
        """Run one full IKIGAi strategic planning cycle (DEPRECATED — see archive)."""
        return "[DEPRECATED] ikigai_plan_cycle removed from legacy reference per ADR-013"

    # ---------------------------------------------------------------------------
    # Tool 7: sync_vault
    # ---------------------------------------------------------------------------

    def _format_corrections(corrections: list[dict[str, Any]]) -> str:
        if not corrections:
            return "_None_"
        lines = [
            f"- [{c.get('heuristic', '?')}] {c.get('description', '')}\n" for c in corrections[-5:]
        ]
        return "".join(lines)

    @tool
    def ikigai_sync_vault(thread_id: str = "default") -> str:
        """Sync the latest checkpoint to a vault markdown file."""
        import datetime as _dt

        from ikigai.vault.vault_write import vault_write as _vault_write_impl

        d = _read_checkpoint_data(thread_id)
        cycle_id = d.get("cycle_id", _dt.date.today().isoformat())
        vs = d.get("vector_scores", {})
        regime = d.get("regime_state", "UNKNOWN")
        qhe = d.get("q_he_score", 0.0)
        mv = d.get("meta_vector_score", 0.0)
        phase = d.get("phase", "BUSCA")
        corrections = d.get("corrections", [])
        vault_root = _VAULT_DIR
        vault_root.mkdir(parents=True, exist_ok=True)
        relative_path = f"cycle-{cycle_id}.md"
        frontmatter_fields: dict[str, Any] = {
            "ueid": f"ikigai:cycle:{cycle_id}",
            "cycle_id": cycle_id,
            "date": _dt.date.today().isoformat(),
            "regime": regime,
            "q_he": qhe,
            "meta_vector": mv,
            "phase": phase,
            "corrections_count": len(corrections),
            "vector_scores": json.dumps(vs),
        }
        body = (
            f"# IKIGAi Cycle — {cycle_id}\n\n"
            f"## Regime: {regime}  |  Q_HE: {qhe:.4f}  |  Meta: {mv:.4f}\n\n"
            f"## Vector Scores\n"
            f"| Vector | Score |\n|--------|-------|\n"
            f"| Passion | {vs.get('passion', 0.0)} |\n"
            f"| Skill | {vs.get('skill', 0.0)} |\n"
            f"| Market | {vs.get('market', 0.0)} |\n"
            f"| Revenue | {vs.get('revenue', 0.0)} |\n"
            f"| Course | {vs.get('course', 0.0)} |\n\n"
            f"## Phase: {phase}\n\n"
            f"## Corrections: {len(corrections)}\n"
            f"{_format_corrections(corrections)}\n"
        )
        result = _vault_write_impl(
            vault_root=vault_root,
            vault_path=relative_path,
            frontmatter_fields=frontmatter_fields,
            body=body,
        )
        return f"Synced to vault: {vault_root / relative_path} (sha256={result['sha256'][:8]}...)"

    # ---------------------------------------------------------------------------
    # Tool 8: checkpoint
    # ---------------------------------------------------------------------------

    @tool
    def ikigai_checkpoint(
        action: Literal["list", "get", "state"] = "list",
        thread_id: str = "default",
    ) -> str:
        """Manage IKIGAi checkpoint state."""
        p = _get_checkpoint_path()
        if not p.exists():
            return "No checkpoint DB found. Run `plan_cycle` first."
        conn = sqlite3.connect(str(p))
        cur = conn.cursor()
        if action == "list":
            cur.execute(
                "SELECT thread_id, checkpoint_ns, checkpoint_id FROM checkpoints "
                "ORDER BY checkpoint_id DESC LIMIT 20"
            )
            rows = cur.fetchall()
            conn.close()
            if not rows:
                return "No checkpoints found."
            lines = [f"**Checkpoints ({len(rows)}):**", ""]
            for r in rows:
                lines.append(f"  • {r[0]}  [{r[1]}]  {r[2]}")
            return "\n".join(lines)
        if action in ("get", "state"):
            cur.execute(
                "SELECT checkpoint FROM checkpoints WHERE thread_id = ? ORDER BY checkpoint_id DESC LIMIT 1",
                (thread_id,),
            )
            row = cur.fetchone()
            conn.close()
            if not row or not row[0]:
                return f"No checkpoint found for thread '{thread_id}'."
            try:
                import msgpack

                data = msgpack.unpackb(row[0])
                data = data.get("channel_values", data)
            except Exception:
                data = {}
            if action == "get":
                summary = [
                    f"cycle_id:    {data.get('cycle_id', '?')}",
                    f"regime:      {data.get('regime_state', '?')}  Q_HE={data.get('q_he_score', 0):.4f}",
                    f"phase:       {data.get('phase', '?')}  iter={data.get('phase_iteration', 0)}",
                    f"verdict:     {data.get('balancer_verdict', '?')}",
                    f"meta-vector: {data.get('meta_vector_score', 0):.4f}",
                    f"corrections: {len(data.get('corrections', []))}",
                ]
                return "\n".join(summary)
            serializable = {}
            for k, v in data.items():
                try:
                    json.dumps(v)
                    serializable[k] = v
                except (TypeError, ValueError):
                    serializable[k] = str(v)
            return json.dumps(serializable, indent=2)
        conn.close()
        return f"Unknown action: {action}"

    # ---------------------------------------------------------------------------
    # External Tools: Solverforge, Tuiboard, Taskdog
    # ---------------------------------------------------------------------------

    _solverforge_retry_config = RetryConfig(
        max_attempts=3,
        initial_backoff_s=0.5,
        max_backoff_s=8.0,
        backoff_multiplier=2.0,
        jitter=True,
    )
    _solverforge_cb_config = CircuitBreakerConfig(failure_threshold=5, reset_timeout_s=30.0)

    @tool
    @circuit_breaker("solverforge", _solverforge_cb_config)
    @retry_with_backoff(
        name="solverforge_list_events",
        retryable_exceptions=(
            subprocess.TimeoutExpired,
            FileNotFoundError,
            ConnectionError,
            OSError,
        ),
        config=_solverforge_retry_config,
    )
    def solverforge_list_events(days: int = 7) -> str:
        try:
            result = subprocess.run(
                [_SOLVERFORGE_CLI, "events", "list", "--days", str(days)],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                raise ConnectionError(f"solverforge error: {result.stderr}")
            return result.stdout
        except (subprocess.TimeoutExpired, FileNotFoundError, ConnectionError, OSError):
            invalidate_session_cache("solverforge")
            raise
        except Exception as e:
            return f"solverforge unavailable: {e}"

    @tool
    @circuit_breaker("solverforge", _solverforge_cb_config)
    @retry_with_backoff(
        name="solverforge_create_event",
        retryable_exceptions=(
            subprocess.TimeoutExpired,
            FileNotFoundError,
            ConnectionError,
            OSError,
        ),
        config=_solverforge_retry_config,
    )
    def solverforge_create_event(title: str, date: str, time: str = "09:00") -> str:
        try:
            result = subprocess.run(
                [
                    _SOLVERFORGE_CLI,
                    "events",
                    "create",
                    "--title",
                    title,
                    "--date",
                    date,
                    "--time",
                    time,
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                raise ConnectionError(f"solverforge error: {result.stderr}")
            return result.stdout
        except (subprocess.TimeoutExpired, FileNotFoundError, ConnectionError, OSError):
            invalidate_session_cache("solverforge")
            raise
        except Exception as e:
            return f"solverforge unavailable: {e}"

    _tuiboard_retry_config = RetryConfig(
        max_attempts=3,
        initial_backoff_s=0.5,
        max_backoff_s=8.0,
        backoff_multiplier=2.0,
        jitter=True,
    )
    _tuiboard_cb_config = CircuitBreakerConfig(failure_threshold=5, reset_timeout_s=30.0)

    def _tuiboard_rpc(method: str, params: dict[str, Any] | None = None) -> Any:
        import json

        request = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}}
        result = subprocess.run(
            [_TUIBOARD_CLI, "run", _TUIBOARD_MCP],
            input=json.dumps(request),
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            raise ConnectionError(f"tuiboard error: {result.stderr}")
        try:
            response = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise ConnectionError(f"tuiboard invalid response: {result.stdout}") from exc
        if "error" in response:
            raise ConnectionError(f"tuiboard RPC error: {response['error']}")
        return response.get("result", {})

    @tool
    @circuit_breaker("tuiboard", _tuiboard_cb_config)
    @retry_with_backoff(
        name="tuiboard_list_boards",
        retryable_exceptions=(
            subprocess.TimeoutExpired,
            FileNotFoundError,
            ConnectionError,
            OSError,
        ),
        config=_tuiboard_retry_config,
    )
    def tuiboard_list_boards() -> str:
        try:
            result = _tuiboard_rpc("list_boards", {})
            if not result:
                return "No boards found"
            lines = ["**Tuiboard Boards:**", ""]
            for board in result:
                lines.append(f"  • {board.get('name', 'unnamed')} ({board.get('path', '')})")
            return "\n".join(lines)
        except (subprocess.TimeoutExpired, FileNotFoundError, ConnectionError, OSError):
            invalidate_session_cache("tuiboard")
            raise
        except Exception as e:
            return f"tuiboard unavailable: {e}"

    @tool
    @circuit_breaker("tuiboard", _tuiboard_cb_config)
    @retry_with_backoff(
        name="tuiboard_get_tasks",
        retryable_exceptions=(
            subprocess.TimeoutExpired,
            FileNotFoundError,
            ConnectionError,
            OSError,
        ),
        config=_tuiboard_retry_config,
    )
    def tuiboard_get_tasks(board_path: str, column: int | None = None, filter_: str = "all") -> str:
        try:
            result = _tuiboard_rpc(
                "get_tasks", {"board_path": board_path, "column": column, "filter": filter_}
            )
            if not result:
                return "No tasks found"
            lines = [f"**Tasks from {board_path}:**", ""]
            for task in result:
                status = "✅" if task.get("done") else "⬜"
                lines.append(
                    f"  {status} {task.get('title', 'untitled')} [{task.get('priority', '?')}]"
                )
            return "\n".join(lines)
        except (subprocess.TimeoutExpired, FileNotFoundError, ConnectionError, OSError):
            invalidate_session_cache("tuiboard")
            raise
        except Exception as e:
            return f"tuiboard unavailable: {e}"

    @tool
    @circuit_breaker("tuiboard", _tuiboard_cb_config)
    @retry_with_backoff(
        name="tuiboard_create_task",
        retryable_exceptions=(
            subprocess.TimeoutExpired,
            FileNotFoundError,
            ConnectionError,
            OSError,
        ),
        config=_tuiboard_retry_config,
    )
    def tuiboard_create_task(board_path: str, title: str, column: int = 0) -> str:
        try:
            result = _tuiboard_rpc(
                "create_task", {"board_path": board_path, "title": title, "column": column}
            )
            return f"Task created: {result.get('id', 'unknown')}"
        except (subprocess.TimeoutExpired, FileNotFoundError, ConnectionError, OSError):
            invalidate_session_cache("tuiboard")
            raise
        except Exception as e:
            return f"tuiboard unavailable: {e}"

    @tool
    @circuit_breaker("tuiboard", _tuiboard_cb_config)
    @retry_with_backoff(
        name="tuiboard_update_task",
        retryable_exceptions=(
            subprocess.TimeoutExpired,
            FileNotFoundError,
            ConnectionError,
            OSError,
        ),
        config=_tuiboard_retry_config,
    )
    def tuiboard_update_task(
        board_path: str,
        task_id: str,
        done: bool | None = None,
        priority: str | None = None,
        tags: list[str] | None = None,
    ) -> str:
        try:
            params: dict[str, Any] = {"board_path": board_path, "task_id": task_id}
            if done is not None:
                params["done"] = done
            if priority is not None:
                params["priority"] = priority
            if tags is not None:
                params["tags"] = tags
            _ = _tuiboard_rpc("update_task", params)
            return f"Task updated: {task_id}"
        except (subprocess.TimeoutExpired, FileNotFoundError, ConnectionError, OSError):
            invalidate_session_cache("tuiboard")
            raise
        except Exception as e:
            return f"tuiboard unavailable: {e}"

    _taskdog_retry_config = RetryConfig(
        max_attempts=3,
        initial_backoff_s=0.5,
        max_backoff_s=8.0,
        backoff_multiplier=2.0,
        jitter=True,
    )
    _taskdog_cb_config = CircuitBreakerConfig(failure_threshold=5, reset_timeout_s=30.0)

    @tool
    @circuit_breaker("taskdog", _taskdog_cb_config)
    @retry_with_backoff(
        name="taskdog_list_tasks",
        retryable_exceptions=(
            subprocess.TimeoutExpired,
            FileNotFoundError,
            ConnectionError,
            OSError,
        ),
        config=_taskdog_retry_config,
    )
    def taskdog_list_tasks(status: str | None = None, include_archived: bool = False) -> str:
        try:
            args = [_TASKDOG_CLI, "list"]
            if status:
                args.extend(["--status", status])
            if include_archived:
                args.append("--include-archived")
            result = subprocess.run(args, capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                raise ConnectionError(f"taskdog error: {result.stderr}")
            return result.stdout
        except (subprocess.TimeoutExpired, FileNotFoundError, ConnectionError, OSError):
            invalidate_session_cache("taskdog")
            raise
        except Exception as e:
            return f"taskdog unavailable: {e}"

    @tool
    @circuit_breaker("taskdog", _taskdog_cb_config)
    @retry_with_backoff(
        name="taskdog_create_task",
        retryable_exceptions=(
            subprocess.TimeoutExpired,
            FileNotFoundError,
            ConnectionError,
            OSError,
        ),
        config=_taskdog_retry_config,
    )
    def taskdog_create_task(name: str) -> str:
        try:
            result = subprocess.run(
                [_TASKDOG_CLI, "create", "--name", name],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                raise ConnectionError(f"taskdog error: {result.stderr}")
            return result.stdout
        except (subprocess.TimeoutExpired, FileNotFoundError, ConnectionError, OSError):
            invalidate_session_cache("taskdog")
            raise
        except Exception as e:
            return f"taskdog unavailable: {e}"

    @tool
    @circuit_breaker("taskdog", _taskdog_cb_config)
    @retry_with_backoff(
        name="taskdog_complete_task",
        retryable_exceptions=(
            subprocess.TimeoutExpired,
            FileNotFoundError,
            ConnectionError,
            OSError,
        ),
        config=_taskdog_retry_config,
    )
    def taskdog_complete_task(task_id: int) -> str:
        try:
            result = subprocess.run(
                [_TASKDOG_CLI, "complete", str(task_id)],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                raise ConnectionError(f"taskdog error: {result.stderr}")
            return result.stdout
        except (subprocess.TimeoutExpired, FileNotFoundError, ConnectionError, OSError):
            invalidate_session_cache("taskdog")
            raise
        except Exception as e:
            return f"taskdog unavailable: {e}"

    @tool
    @circuit_breaker("taskdog", _taskdog_cb_config)
    @retry_with_backoff(
        name="taskdog_get_task",
        retryable_exceptions=(
            subprocess.TimeoutExpired,
            FileNotFoundError,
            ConnectionError,
            OSError,
        ),
        config=_taskdog_retry_config,
    )
    def taskdog_get_task(task_id: int) -> str:
        try:
            result = subprocess.run(
                [_TASKDOG_CLI, "get", str(task_id)],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                raise ConnectionError(f"taskdog error: {result.stderr}")
            return result.stdout
        except (subprocess.TimeoutExpired, FileNotFoundError, ConnectionError, OSError):
            invalidate_session_cache("taskdog")
            raise
        except Exception as e:
            return f"taskdog unavailable: {e}"

    # ---------------------------------------------------------------------------
    # All tools as list
    # ---------------------------------------------------------------------------
    IKIGAI_TOOLS = [
        ikigai_score,
        ikigai_regime,
        ikigai_phase,
        ikigai_corrections,
        ikigai_decompose,
        ikigai_plan_cycle,
        ikigai_sync_vault,
        ikigai_checkpoint,
        solverforge_list_events,
        solverforge_create_event,
        tuiboard_list_boards,
        tuiboard_get_tasks,
        tuiboard_update_task,
        tuiboard_create_task,
        taskdog_list_tasks,
        taskdog_create_task,
        taskdog_complete_task,
        taskdog_get_task,
    ]

    # ---------------------------------------------------------------------------
    # B7.3 vault-grounded agent tools (appended)
    # ---------------------------------------------------------------------------
    from .ikigai_read_strategics import ikigai_read_strategics
    from .ikigai_read_vault import ikigai_read_vault

    IKIGAI_TOOLS.extend([ikigai_read_strategics, ikigai_read_vault])

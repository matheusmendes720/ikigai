"""IKIGAi tools — wrapped as LangChain @tool for deepagents.

Each tool is a clean function with docstring + TypedDict return type.
These are the 8 operations the conversational agent can call.
"""
from __future__ import annotations

import datetime as dt
import json
import sqlite3
from pathlib import Path
from typing import Any, Literal

from langchain_core.tools import tool

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_CHECKPOINT_DB = str(Path.home() / ".ikigai" / "ikigai_checkpoints.db")
_VAULT_DIR = Path.home() / ".ikigai" / "vault"


def _get_checkpoint_path() -> Path:
    p = Path(_CHECKPOINT_DB)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _read_checkpoint_data(thread_id: str = "default") -> dict[str, Any]:
    """Read latest checkpoint for a thread.

    langgraph stores state in checkpoint['channel_values'].
    """
    p = _get_checkpoint_path()
    if not p.exists():
        return {}
    import msgpack

    conn = sqlite3.connect(str(p))
    cur = conn.cursor()
    cur.execute(
        """
        SELECT checkpoint FROM checkpoints
        WHERE thread_id = ?
        ORDER BY checkpoint_id DESC LIMIT 1
        """,
        (thread_id,),
    )
    row = cur.fetchone()
    conn.close()
    if row and row[0]:
        try:
            data = msgpack.unpackb(row[0])
            # langgraph wraps state in channel_values
            return data.get("channel_values", data)
        except Exception:
            return {}
    return {}


# ---------------------------------------------------------------------------
# Tool 1: score — 5-vector scores + meta-vector
# ---------------------------------------------------------------------------


@tool
def ikigai_score(thread_id: str = "default") -> str:
    """Get current IKIGAi 5-vector scores (passion, skill, market, revenue, course)
    and the meta-vector composite score.

    Args:
        thread_id: Checkpoint thread to read from. Defaults to "default".

    Returns:
        Formatted table of vector scores with ASCII bar charts.
    """
    d = _read_checkpoint_data(thread_id)
    vs = d.get("vector_scores", {})
    mv = d.get("meta_vector_score", 0.0)
    qhe = d.get("q_he_score", 0.0)

    if not vs:
        return "⚠️ No vector scores found in checkpoint. Run `plan` first."

    lines = [f"**IKIGAi Scores**  (meta: {mv:.4f}  Q_HE: {qhe:.4f})", ""]
    for vec in ("passion", "skill", "market", "revenue", "course"):
        v = vs.get(vec, 0.0)
        bar = "█" * int(v / 10) + "░" * (10 - int(v / 10))
        lines.append(f"  {vec.capitalize():12s} [{bar}] {v:.1f}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tool 2: regime — regime state, Q_HE, days in regime
# ---------------------------------------------------------------------------


@tool
def ikigai_regime(thread_id: str = "default") -> str:
    """Get current IKIGAi regime state (PUSH / MAINTAIN / REDUCE / RECOVER),
    Q_HE score, and days-in-regime counter.

    Args:
        thread_id: Checkpoint thread to read from. Defaults to "default".

    Returns:
        One-line regime status with emoji indicator.
    """
    d = _read_checkpoint_data(thread_id)
    regime = d.get("regime_state", "MAINTAIN")
    days = d.get("days_in_regime", 0)
    qhe = d.get("q_he_score", 0.65)

    emoji = {
        "PUSH": "🔴",
        "MAINTAIN": "🟡",
        "REDUCE": "🟠",
        "RECOVER": "🟢",
    }.get(regime, "⚪")

    return f"{emoji} **Regime: {regime}**  |  Q_HE: {qhe:.4f}  |  Days: {days}"


# ---------------------------------------------------------------------------
# Tool 3: phase — current phase and weight distribution
# ---------------------------------------------------------------------------


@tool
def ikigai_phase(thread_id: str = "default") -> str:
    """Get current IKIGAi phase (FUNDAÇÃO / BUSCA / HACKATHON / RECUPERACAO / OVERCLOCK)
    and the 5-vector weight distribution.

    Args:
        thread_id: Checkpoint thread to read from. Defaults to "default".

    Returns:
        Phase name with iteration count and weight table.
    """
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

    lines = [
        f"{emoji} **Phase: {phase}**  iter={pi}  converged={converged}",
        "",
        "Weights:",
    ]
    for k, v in pw.items():
        lines.append(f"  {k.capitalize():12s}: {v:.2f}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tool 4: corrections — H1-H6 heuristic signals
# ---------------------------------------------------------------------------


@tool
def ikigai_corrections(thread_id: str = "default") -> str:
    """Get active IKIGAi correction signals from H1-H6 heuristics.

    Returns the most recent correction signals emitted by the regime FSM,
    phase FSM, and balance heuristics.

    Args:
        thread_id: Checkpoint thread to read from. Defaults to "default".

    Returns:
        List of correction signals with heuristic tags and descriptions.
    """
    d = _read_checkpoint_data(thread_id)
    corrs = d.get("corrections", [])

    if not corrs:
        return "✅ No corrections — system is balanced."

    lines = [f"**Corrections ({len(corrs)})**", ""]
    for c in corrs[-5:]:
        lines.append(f"  [{c.get('heuristic', '?')}] {c.get('description', '')}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tool 5: decompose — UEID hierarchy (dream → goal → objective → project)
# ---------------------------------------------------------------------------


@tool
def ikigai_decompose(ueid: str, thread_id: str = "default") -> str:
    """Decompose a UEID into its full hierarchy:
    Dream → Objectives → Projects → Tasks.

    Args:
        ueid: Full UEID to decompose (e.g. "ikigai:dream:vaga-remota-2026").
        thread_id: Checkpoint thread to read from. Defaults to "default".

    Returns:
        Formatted hierarchy tree with status for each level.
    """
    if not ueid:
        return "⚠️ Provide a UEID, e.g. `ikigai_decompose(ueid='ikigai:dream:vaga-remota-2026')`"

    # Try to decompose via the existing mcp_server helper
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
        return f"⚠️ Could not decompose UEID: {e}"


# ---------------------------------------------------------------------------
# Tool 6: plan_cycle — run full IKIGAi agent cycle
# ---------------------------------------------------------------------------


@tool
def ikigai_plan_cycle(thread_id: str = "default") -> str:
    """Run one full IKIGAi strategic planning cycle.

    Executes the 8-node LangGraph: observe → score_vectors → heuristics
    → balance → decompose → plan → reflect → commit.

    Uses SqliteSaver checkpointing. Results are persisted and resumable.

    Args:
        thread_id: Thread ID for checkpointing. Defaults to "default".

    Returns:
        Summary of the completed cycle: regime, Q_HE, corrections, buffers.
    """
    import datetime as _dt
    import sys
    from pathlib import Path as _P

    sys.path.insert(0, str(_P(__file__).parent.parent.parent / "src"))
    from agents.ikigai_maintainer import make_ikigai_graph

    today = _dt.date.today()
    graph = make_ikigai_graph(checkpoint_db=_CHECKPOINT_DB)
    config = {"configurable": {"thread_id": thread_id}}

    initial = {
        "cycle_id": today.isoformat(),
        "cycle_start": today.isoformat(),
        "cycle_end": (today + _dt.timedelta(days=45)).isoformat(),
        "iteration": 0,
        "last_step": "",
        "regime_state": "MAINTAIN",
        "q_he_score": 0.65,
        "days_in_regime": 1,
        "is_hysteresis_active": False,
        "phase": "BUSCA",
        "phase_iteration": 0,
        "phase_converged": False,
        "phase_weights": {
            "passion": 0.15,
            "skill": 0.25,
            "market": 0.25,
            "revenue": 0.20,
            "course": 0.15,
        },
        "vector_scores": {},
        "meta_vector_score": 0.0,
        "active_dream_ueid": None,
        "active_goal_ueids": [],
        "active_objective_ueids": [],
        "active_project_ueids": [],
        "active_task_ueids": [],
        "workload_estimate": 2.0,
        "capacity_estimate": 8.0,
        "balancer_verdict": "OK",
        "prospective_buffer": [],
        "retrospective_log": [],
        "corrections": [],
        "kill_switch_triggered": False,
        "terminated": False,
    }

    final = graph.invoke(initial, config)
    vs = final.get("vector_scores", {})
    mv = final.get("meta_vector_score", 0.0)
    regime = final.get("regime_state", "?")
    qhe = final.get("q_he_score", 0.0)
    corrections = final.get("corrections", [])
    prospective = final.get("prospective_buffer", [])
    retrospective = final.get("retrospective_log", [])

    return (
        f"✅ Plan cycle complete\n"
        f"   Regime: {regime}  |  Q_HE: {qhe:.4f}  |  Meta: {mv:.4f}\n"
        f"   Vectors: {len(vs)} scored\n"
        f"   Corrections: {len(corrections)}  |  Prospective: {len(prospective)}  |  Retrospective: {len(retrospective)}"
    )


# ---------------------------------------------------------------------------
# Tool 7: sync_vault — write cycle checkpoint to vault markdown
# ---------------------------------------------------------------------------


@tool
def ikigai_sync_vault(thread_id: str = "default") -> str:
    """Sync the latest checkpoint to a vault markdown file.

    Writes a cycle log to ~/.ikigai/vault/cycle-YYYY-MM-DD.md
    with current vector scores, regime, phase, and corrections.

    Args:
        thread_id: Checkpoint thread to read from. Defaults to "default".

    Returns:
        Path to the written vault file.
    """
    import datetime as _dt

    d = _read_checkpoint_data(thread_id)
    cycle_id = d.get("cycle_id", _dt.date.today().isoformat())
    vs = d.get("vector_scores", {})
    regime = d.get("regime_state", "UNKNOWN")
    qhe = d.get("q_he_score", 0.0)
    mv = d.get("meta_vector_score", 0.0)
    phase = d.get("phase", "BUSCA")
    corrections = d.get("corrections", [])

    vault_dir = _VAULT_DIR
    vault_dir.mkdir(parents=True, exist_ok=True)
    log_file = vault_dir / f"cycle-{cycle_id}.md"

    content = f"""---
ueid: ikigai:cycle:{cycle_id}
cycle_id: {cycle_id}
date: {_dt.date.today().isoformat()}
regime: {regime}
q_he: {qhe}
meta_vector: {mv}
phase: {phase}
corrections_count: {len(corrections)}
vector_scores: {json.dumps(vs)}
---

# IKIGAi Cycle — {cycle_id}

## Regime: {regime}  |  Q_HE: {qhe:.4f}  |  Meta: {mv:.4f}

## Vector Scores
| Vector | Score |
|--------|-------|
| Passion | {vs.get('passion', 0.0)} |
| Skill | {vs.get('skill', 0.0)} |
| Market | {vs.get('market', 0.0)} |
| Revenue | {vs.get('revenue', 0.0)} |
| Course | {vs.get('course', 0.0)} |

## Phase: {phase}

## Corrections: {len(corrections)}
{''.join(f"- [{c.get('heuristic','?')}] {c.get('description','')}\n" for c in corrections[-5:]) if corrections else '_None_'}
"""
    log_file.write_text(content, encoding="utf-8")
    return f"✅ Synced to vault: {log_file}"


# ---------------------------------------------------------------------------
# Tool 8: checkpoint — list / get / set checkpoint state
# ---------------------------------------------------------------------------


@tool
def ikigai_checkpoint(
    action: Literal["list", "get", "state"] = "list",
    thread_id: str = "default",
) -> str:
    """Manage IKIGAi checkpoint state.

    - list: Show all recent checkpoint threads
    - get: Show current state for a thread
    - state: Return full state dict as JSON string

    Args:
        action: One of "list", "get", or "state". Defaults to "list".
        thread_id: Thread to operate on. Defaults to "default".

    Returns:
        Checkpoint info in requested format.
    """
    p = _get_checkpoint_path()
    if not p.exists():
        return "⚠️ No checkpoint DB found. Run `plan_cycle` first."

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
            "SELECT checkpoint FROM checkpoints "
            "WHERE thread_id = ? ORDER BY checkpoint_id DESC LIMIT 1",
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
        # state — return JSON
        import copy

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
# All tools as list (for create_deep_agent)
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
]

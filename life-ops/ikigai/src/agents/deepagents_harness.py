"""Deep agents harness for IKIGAi-Maintainer.

Wraps the ikigai_maintainer LangGraph with deep-agent capabilities:
- Checkpoint persistence across restarts (SqliteSaver)
- Human-in-the-loop pause/approve
- Memory accumulation between cycles
- Thread-based conversation context

Run with:
    python -m agents.deepagents_harness
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sys
from pathlib import Path
from typing import Any

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from agents.ikigai_maintainer import make_ikigai_graph

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
CHECKPOINT_DB = os.environ.get(
    "IKIGAI_CHECKPOINT_DB",
    str(Path.home() / ".ikigai" / "ikigai_checkpoints.db"),
)
THREAD_ID = os.environ.get("IKIGAI_THREAD_ID", "default")


# ---------------------------------------------------------------------------
# DeepAgent wrapper
# ---------------------------------------------------------------------------
class IKIGAiDeepAgent:
    """Thin wrapper that gives a deep-agent interface to the ikigai_maintainer graph.

    Provides:
    - invoke(input_state) → output_state  (like an agent)
    - checkpoint / resume via SqliteSaver
    - human_in_the_loop pause before commit
    """

    def __init__(
        self,
        checkpoint_db: str | None = None,
        thread_id: str | None = None,
        human_in_the_loop: bool = False,
    ):
        self.checkpoint_db = checkpoint_db or CHECKPOINT_DB
        self.thread_id = thread_id or THREAD_ID
        self.human_in_the_loop = human_in_the_loop

        # Ensure checkpoint dir
        Path(self.checkpoint_db).parent.mkdir(parents=True, exist_ok=True)

        self.graph = make_ikigai_graph(checkpoint_db=self.checkpoint_db)
        self.config = {"configurable": {"thread_id": self.thread_id}}

    def invoke(self, input_state: dict[str, Any] | None = None) -> dict[str, Any]:
        """Run one cycle of the IKIGAi agent.

        Args:
            input_state: Optional initial state override. Defaults to sensible defaults.

        Returns:
            Final state after the full graph run.
        """
        if input_state is None:
            input_state = self._default_state()

        # Human-in-the-loop pause before commit
        if self.human_in_the_loop:
            self._confirm_pre_commit(input_state)

        result = self.graph.invoke(input_state, self.config)
        return result

    def resume(self, checkpoint_id: str | None = None) -> dict[str, Any]:
        """Resume from a named checkpoint or latest.

        Args:
            checkpoint_id: Specific thread/checkpoint ID. Defaults to self.thread_id.

        Returns:
            State at that checkpoint.
        """
        tid = checkpoint_id or self.thread_id
        config = {"configurable": {"thread_id": tid}}
        # Get the checkpointed state from the store
        if hasattr(self.graph, "get_state"):
            state = self.graph.get_state(config)
            return state
        # Fallback: return current state
        return self.graph.get_state(self.config)

    def list_checkpoints(self) -> list[dict[str, str]]:
        """List all checkpoints in the DB (LangGraph schema: thread_id, checkpoint_id, checkpoint_ns)."""
        import sqlite3
        path = Path(self.checkpoint_db)
        if not path.exists():
            return []
        conn = sqlite3.connect(str(path))
        cur = conn.cursor()
        cur.execute(
            "SELECT DISTINCT thread_id, checkpoint_ns FROM checkpoints ORDER BY checkpoint_id DESC LIMIT 50"
        )
        rows = cur.fetchall()
        conn.close()
        return [{"thread_id": r[0], "checkpoint_ns": r[1]} for r in rows]

    def _default_state(self) -> dict[str, Any]:
        """Build a sensible default initial state."""
        today = dt.date.today()
        return {
            "cycle_id": today.isoformat(),
            "cycle_start": today.isoformat(),
            "cycle_end": (today + dt.timedelta(days=45)).isoformat(),
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

    def _confirm_pre_commit(self, state: dict[str, Any]) -> None:
        """Print a summary and wait for human confirmation before commit."""
        print("\n" + "=" * 60)
        print("IKIGAi DEEP AGENT — PRE-COMMIT PAUSE")
        print("=" * 60)
        print(f"  Cycle:    {state.get('cycle_id')}")
        print(f"  Regime:   {state.get('regime_state')}")
        print(f"  Q_HE:     {state.get('q_he_score', 0):.4f}")
        print(f"  Phase:    {state.get('phase')}")
        print(f"  Corrections: {len(state.get('corrections', []))}")
        print("=" * 60)
        try:
            confirm = input("Proceed with commit? [Y/n]: ").strip().lower()
            if confirm == "n":
                print("Commit aborted by user.")
                sys.exit(0)
        except (EOFError, KeyboardInterrupt):
            print("\nCommit skipped.")
            sys.exit(0)


# ---------------------------------------------------------------------------
# CLI entrypoint
# ---------------------------------------------------------------------------
def main():
    """Run the deep agent interactively."""
    import argparse

    parser = argparse.ArgumentParser(description="IKIGAi Deep Agent")
    parser.add_argument("--thread", default=THREAD_ID, help="Thread ID for checkpointing")
    parser.add_argument("--checkpoint-db", default=CHECKPOINT_DB, help="SQLite checkpoint DB path")
    parser.add_argument(
        "--human-in-the-loop", action="store_true", help="Pause before each commit"
    )
    parser.add_argument("--list-checkpoints", action="store_true", help="List checkpoints and exit")
    parser.add_argument("--resume", metavar="THREAD_ID", help="Resume from a specific checkpoint")
    parser.add_argument(
        "--chat", action="store_true", help="Start interactive REPL chat mode"
    )
    args = parser.parse_args()

    agent = IKIGAiDeepAgent(
        checkpoint_db=args.checkpoint_db,
        thread_id=args.thread,
        human_in_the_loop=args.human_in_the_loop,
    )

    if args.list_checkpoints:
        checkpoints = agent.list_checkpoints()
        print(f"\nCheckpoints ({len(checkpoints)}):")
        for cp in checkpoints:
            print(f"  {cp['thread_id']}  —  {cp.get('checkpoint_ns', '')}")
        return

    if args.resume:
        state = agent.resume(args.resume)
        print("\nResumed state:")
        print(f"  Cycle: {state.get('cycle_id')}")
        print(f"  Regime: {state.get('regime_state')}")
        print(f"  Phase: {state.get('phase')}")
        return

    if args.chat:
        run_chat(agent)
        return

    # Run one cycle
    print(f"\nIKIGAi Deep Agent — thread: {args.thread}")
    print(f"Checkpoint DB: {args.checkpoint_db}")
    result = agent.invoke()
    print("\nCycle complete:")
    print(f"  Cycle:   {result.get('cycle_id')}")
    print(f"  Regime:  {result.get('regime_state')}")
    print(f"  Q_HE:    {result.get('q_he_score', 0):.4f}")
    print(f"  Meta:    {result.get('meta_vector_score', 0):.4f}")
    print(f"  Corrections: {len(result.get('corrections', []))}")
    print(f"  Prospective: {len(result.get('prospective_buffer', []))} items")
    print(f"  Retrospective: {len(result.get('retrospective_log', []))} items")


def run_chat(agent: IKIGAiDeepAgent) -> None:
    """Conversational agent: routes natural language to IKIGAI operations.

    Tools available:
    - ikigai_score       → 5-vector scores + meta-vector
    - ikigai_regime      → regime + Q_HE + days
    - ikigai_phase       → phase + weights
    - ikigai_decompose   → UEID hierarchy (dream→project)
    - ikigai_corrections → H1-H6 signals
    - ikigai_plan_cycle  → run full LangGraph agent
    - ikigai_checkpoint  → get/set/list checkpoints
    - ikigai_sync_vault  → write cycle to vault markdown
    """
    import httpx

    print("IKIGAi Conversational Agent — Ctrl+C to exit\n")
    print("Commands: score | regime | phase | decompose <ueid> | corrections | plan | sync | checkpoint\n")

    # Bootstrap IKIGAi state
    result = agent.invoke()
    current_state = _build_state_summary(result)

    # Build system prompt with available operations
    system_prompt = (
        "You are the IKIGAi Strategic Agent. The user talks to you in natural language.\n"
        "You have 8 tools. Route the user's intent to the right operation.\n\n"
        "Operations:\n"
        "  score         → ikigai_score       — 5-vector scores + meta-vector\n"
        "  regime        → ikigai_regime      — regime + Q_HE + days_in_regime\n"
        "  phase         → ikigai_phase       — phase + weights\n"
        "  decompose <ueid> → ikigai_decompose — full UEID hierarchy\n"
        "  corrections   → ikigai_corrections — H1-H6 heuristic signals\n"
        "  plan          → ikigai_plan_cycle  — run full IKIGAI cycle\n"
        "  sync          → ikigai_sync_vault  — write cycle to vault markdown\n"
        "  checkpoint    → ikigai_checkpoint  — list checkpoints\n"
        "  vault         → read vault files directly\n\n"
        f"Current IKIGAi state:\n{current_state}\n\n"
        "When the user asks about their scores, regime, phase, or corrections — "
        "call the corresponding tool and show the raw result formatted nicely.\n"
        "When they ask to run a plan_cycle — call ikigai_plan_cycle.\n"
        "When they ask about a specific dream/objective/project — decompose that UEID.\n"
        "Be concise. Format tables nicely. Use emoji for vectors."
    )

    # LLM client — use existing env
    api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("MINIMAX_API_KEY", "")
    base_url = os.environ.get("ANTHROPIC_BASE_URL", "https://api.minimax.io/anthropic")
    model = os.environ.get("ANTHROPIC_DEFAULT_OPUS_MODEL", "MiniMax-M3")

    client = httpx.Client(base_url=base_url, headers={
        "x-api-key": api_key,
        "anthropic-version": "2025-11-25",
        "content-type": "application/json",
    }, timeout=120.0)

    messages: list[dict] = [{"role": "system", "content": system_prompt}]

    def call_llm(user_msg: str) -> str:
        msgs = messages + [{"role": "user", "content": user_msg}]
        try:
            resp = client.post("/v1/messages", json={
                "model": model,
                "max_tokens": 1024,
                "messages": msgs,
            })
            resp.raise_for_status()
            data = resp.json()
            text = "".join(b.get("text","") for b in data.get("content", []) if b.get("type")=="text")
            usage = data.get("usage", {})
            print(f"  [tokens: {usage.get('input_tokens',0)} in / {usage.get('output_tokens',0)} out]")
            return text
        except Exception as e:
            return f"[LLM error: {e}]"

    def do_score() -> str:
        import json as _json
        try:
            from mcp_server.server import _read_checkpoint, _read_entity
            d = _read_checkpoint()
            vs = d.get("vector_scores", {})
            mv = d.get("meta_vector_score", 0.0)
            qhe = d.get("q_he_score")
            if not vs:
                row = _read_entity("plan_entities")
                if row:
                    vs = {k: row.get(k, 0.0) for k in ("passion","skill","market","revenue","course")}
                    mv = row.get("meta_vector", 0.0)
                    qhe = row.get("q_he")
            lines = [f"**IKIGAi Scores**  (meta-vector: {mv:.4f})"]
            for vec in ("passion","skill","market","revenue","course"):
                v = vs.get(vec, 0.0)
                bar = "█" * int(v/10) + "░" * (10 - int(v/10))
                lines.append(f"  {vec.capitalize():12s} [{bar}] {v:.1f}")
            lines.append(f"\nQ_HE: {qhe}")
            return "\n".join(lines)
        except Exception as e:
            return f"[error: {e}]"

    def do_regime() -> str:
        try:
            from mcp_server.server import _read_checkpoint, _read_entity
            d = _read_checkpoint()
            regime = d.get("regime_state","MAINTAIN")
            days = d.get("days_in_regime", 0)
            qhe = d.get("q_he_score", 0.65)
            if not d:
                row = _read_entity("plan_entities")
                if row:
                    regime = row.get("regime", regime)
                    qhe = row.get("q_he", qhe)
            emoji = {"PUSH":"🔴","MAINTAIN":"🟡","REDUCE":"🟠","RECOVER":"🟢"}.get(regime,"⚪")
            return f"{emoji} **Regime: {regime}**  |  Q_HE: {qhe:.4f}  |  Days in regime: {days}"
        except Exception as e:
            return f"[error: {e}]"

    def do_corrections() -> str:
        try:
            from mcp_server.server import _read_checkpoint, _read_entity
            import json as _json
            d = _read_checkpoint()
            corrs = d.get("corrections", [])
            if not corrs:
                row = _read_entity("plan_entities")
                if row:
                    try:
                        corrs = _json.loads(row.get("corrections","[]"))
                    except: pass
            if not corrs:
                return "✅ No corrections — system is balanced."
            lines = [f"**Corrections ({len(corrs)})**"]
            for c in corrs[-5:]:
                lines.append(f"  [{c.get('heuristic')}] {c.get('description','')}")
            return "\n".join(lines)
        except Exception as e:
            return f"[error: {e}]"

    def do_decompose(ueid: str) -> str:
        if not ueid:
            return "Provide a UEID, e.g. `decompose ikigai:dream:vaga-remota-2026:...`"
        try:
            from mcp_server.server import _decompose_ueid
            result = _decompose_ueid(ueid)
            dream = result.get("dream", {})
            objectives = result.get("objectives", [])
            projects = result.get("projects", [])
            lines = [f"**Dream:** {dream.get('title', dream.get('slug','?'))}  [{dream.get('status','?')}]"]
            if objectives:
                lines.append(f"  Objectives ({len(objectives)}):")
                for o in objectives:
                    lines.append(f"    • {o.get('title','?')}  [{o.get('status','?')}]")
            if projects:
                lines.append(f"  Projects ({len(projects)}):")
                for p in projects:
                    lines.append(f"    • {p.get('title','?')}  [{p.get('status','?')}]")
            return "\n".join(lines)
        except Exception as e:
            return f"[error: {e}]"

    def do_plan() -> str:
        try:
            import sys as _sys, datetime as _dt
            from pathlib import Path as _P
            _sys.path.insert(0, str(_P(__file__).parent.parent.parent / "src"))
            from agents.ikigai_maintainer import make_ikigai_graph
            today = _dt.date.today()
            graph = make_ikigai_graph()
            initial = {
                "cycle_id": today.isoformat(), "cycle_start": today.isoformat(),
                "cycle_end": (today + _dt.timedelta(days=45)).isoformat(),
                "iteration": 0, "last_step": "",
                "regime_state": "MAINTAIN", "q_he_score": 0.65,
                "days_in_regime": 1, "is_hysteresis_active": False,
                "phase": "BUSCA", "phase_iteration": 0, "phase_converged": False,
                "phase_weights": {"passion":0.15,"skill":0.25,"market":0.25,"revenue":0.20,"course":0.15},
                "vector_scores": {}, "meta_vector_score": 0.0,
                "active_dream_ueid": None,
                "active_goal_ueids": [], "active_objective_ueids": [],
                "active_project_ueids": [], "active_task_ueids": [],
                "workload_estimate": 2.0, "capacity_estimate": 8.0, "balancer_verdict": "OK",
                "prospective_buffer": [], "retrospective_log": [],
                "corrections": [], "kill_switch_triggered": False, "terminated": False,
            }
            config = {"configurable": {"thread_id": f"cycle_{today.isoformat()}"}}
            final = graph.invoke(initial, config)
            vs = final.get("vector_scores", {})
            return (
                f"✅ Plan cycle complete\n"
                f"   Regime: {final.get('regime_state')}  |  Q_HE: {final.get('q_he_score',0):.4f}\n"
                f"   Meta: {final.get('meta_vector_score',0):.4f}  |  Corrections: {len(final.get('corrections',[]))}\n"
                f"   Prospective: {len(final.get('prospective_buffer',[]))}  |  Retrospective: {len(final.get('retrospective_log',[]))}"
            )
        except Exception as e:
            return f"[error: {e}]"

    def do_sync() -> str:
        try:
            import datetime as _dt
            from pathlib import Path as _P
            from mcp_server.server import _read_plan_entity
            cycle_id = _dt.date.today().isoformat()
            row = _read_plan_entity(cycle_id)
            if not row:
                return f"No cycle '{cycle_id}' found — run `plan` first."
            repo_root = _P(__file__).parent.parent.parent
            vault_dir = repo_root / "data" / "matheus" / "ikigai_state"
            vault_dir.mkdir(parents=True, exist_ok=True)
            log_file = vault_dir / f"cycle-{cycle_id}.md"
            import json as _json
            vs = {k: row.get(k) for k in ("passion","skill","market","revenue","course")}
            content = f"""---
ueid: ikigai:cycle:{cycle_id}
cycle_id: {cycle_id}
date: {_dt.date.today().isoformat()}
regime: {row.get('regime','UNKNOWN')}
q_he: {row.get('q_he')}
meta_vector: {row.get('meta_vector')}
vector_scores: {_json.dumps(vs)}
phase: BUSCA
corrections_count: 0
---

# IKIGAi Cycle — {cycle_id}

## Vector Scores
| Vector | Score |
|--------|-------|
| Passion | {row.get('passion')} |
| Skill | {row.get('skill')} |
| Market | {row.get('market')} |
| Revenue | {row.get('revenue')} |
| Course | {row.get('course')} |

**Meta-vector:** {row.get('meta_vector')}
"""
            log_file.write_text(content, encoding="utf-8")
            return f"✅ Synced to vault: {log_file}"
        except Exception as e:
            return f"[error: {e}]"

    def do_checkpoint(action: str = "list") -> str:
        try:
            import sqlite3 as _sqlite3
            path = agent.checkpoint_db
            if not _P(path).exists():
                return "No checkpoint DB found."
            conn = _sqlite3.connect(str(path))
            cur = conn.cursor()
            if action == "list":
                cur.execute("SELECT thread_id, checkpoint_ns FROM checkpoints ORDER BY checkpoint_id DESC LIMIT 20")
                rows = cur.fetchall()
                conn.close()
                if not rows:
                    return "No checkpoints found."
                lines = ["**Checkpoints:**"]
                for r in rows:
                    lines.append(f"  • {r[0]}  [{r[1]}]")
                return "\n".join(lines)
            conn.close()
            return f"Unknown checkpoint action: {action}"
        except Exception as e:
            return f"[error: {e}]"

    def handle_command(text: str) -> str:
        t = text.strip().lower()
        if t in ("score", "scores", "vector", "vectors"):
            return do_score()
        if t in ("regime", "state", "status"):
            return do_regime()
        if t in ("phase", "phases", "weights"):
            return do_phase()
        if t in ("corrections", "correction", "signals"):
            return do_corrections()
        if t.startswith("decompose ") or t.startswith("decomp "):
            parts = text.strip().split(None, 1)
            return do_decompose(parts[1]) if len(parts) > 1 else do_decompose("")
        if t in ("plan", "plan_cycle", "cycle", "run"):
            return do_plan()
        if t in ("sync", "sync_vault", "vault"):
            return do_sync()
        if t.startswith("checkpoint"):
            parts = text.strip().split(None, 1)
            return do_checkpoint(parts[1] if len(parts) > 1 else "list")
        if t in ("help", "?"):
            return ("Commands: **score** | **regime** | **phase** | **decompose <ueid>** | "
                    "**corrections** | **plan** | **sync** | **checkpoint**\n"
                    "Or just chat naturally — I'll route it.")
        return None  # not a command, let LLM handle it

    def do_phase() -> str:
        try:
            from mcp_server.server import _read_checkpoint
            d = _read_checkpoint()
            phase = d.get("phase","BUSCA")
            pw = d.get("phase_weights",{})
            pi = d.get("phase_iteration",0)
            converged = d.get("phase_converged",False)
            emoji = {"FUNDAÇÃO":"🏗️","BUSCA":"🔍","HACKATHON":"⚡","RECUPERACAO":"🔧","OVERCLOCK":"🔥"}.get(phase,"❓")
            lines = [f"{emoji} **Phase: {phase}**  iter={pi}  converged={converged}", "Weights:"]
            for k,v in pw.items():
                lines.append(f"  {k.capitalize():12s}: {v:.2f}")
            return "\n".join(lines)
        except Exception as e:
            return f"[error: {e}]"

    try:
        while True:
            try:
                user_input = input("\n🧑 > ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n\nGoodbye.")
                break
            if not user_input:
                continue

            # Direct command routing
            cmd_result = handle_command(user_input)
            if cmd_result is not None:
                print(f"\n🤖 IKIGAi:\n{cmd_result}")
                messages.append({"role": "user", "content": user_input})
                messages.append({"role": "assistant", "content": cmd_result})
                continue

            # Natural language → LLM
            print()
            response = call_llm(user_input)
            if response:
                print(f"\n🤖 IKIGAi:\n{response}")
                messages.append({"role": "user", "content": user_input})
                messages.append({"role": "assistant", "content": response})
    except KeyboardInterrupt:
        print("\n\nGoodbye.")
    finally:
        client.close()


def _build_state_summary(state: dict) -> str:
    """Build a compact state summary for the LLM system prompt."""
    vs = state.get("vector_scores", {})
    lines = [
        f"cycle_id:    {state.get('cycle_id', '?')}",
        f"regime:      {state.get('regime_state', '?')}  (Q_HE={state.get('q_he_score', 0):.4f})",
        f"phase:       {state.get('phase', '?')}  iter={state.get('phase_iteration', 0)}",
        f"verdict:     {state.get('balancer_verdict', '?')}",
        f"workload:    {state.get('workload_estimate', 0):.1f}h  capacity={state.get('capacity_estimate', 0):.1f}h",
        f"meta-vector: {state.get('meta_vector_score', 0):.4f}",
        "vectors:",
    ]
    for vec, score in sorted(vs.items()):
        lines.append(f"  {vec:12s}: {score:.1f}")
    corrections = state.get("corrections", [])
    if corrections:
        lines.append(f"corrections: {len(corrections)} pending")
        for c in corrections[-2:]:
            lines.append(f"  [{c.get('heuristic')}] {c.get('description', '')}")
    prospective = state.get("prospective_buffer", [])
    if prospective:
        lines.append(f"prospective_buffer: {len(prospective)} items")
    retrospective = state.get("retrospective_log", [])
    if retrospective:
        lines.append(f"retrospective_log: {len(retrospective)} items")
    return "\n".join(lines)


def _print_agent_response(state: dict) -> None:
    """Print the agent's response from a chat turn."""
    response = state.get("agent_response", "")
    if response:
        print(f"\n🤖 IKIGAi:\n{response}")
    else:
        # Fallback: print computed state summary
        print(f"\n🤖 IKIGAi:")
        print(f"   Regime:  {state.get('regime_state', '?')}")
        print(f"   Q_HE:    {state.get('q_he_score', 0):.4f}")
        print(f"   Meta:    {state.get('meta_vector_score', 0):.4f}")
        vs = state.get("vector_scores", {})
        for vec, score in vs.items():
            print(f"   {vec.capitalize():12s}: {score:.1f}")


if __name__ == "__main__":
    main()

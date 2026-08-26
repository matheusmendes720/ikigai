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
    """Interactive REPL: accumulate messages, run graph, print agent response."""
    print("IKIGAi Chat REPL — Ctrl+C to exit\n")

    # Bootstrap: run one cycle to populate initial state
    result = agent.invoke()
    _print_agent_response(result)

    try:
        while True:
            try:
                user_input = input("\n🧑 > ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n\nGoodbye.")
                break

            if not user_input:
                continue

            # Inject user message and run graph
            result = agent.invoke({"user_input": user_input})
            _print_agent_response(result)
    except KeyboardInterrupt:
        print("\n\nGoodbye.")


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

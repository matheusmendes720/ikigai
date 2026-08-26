"""Deep agents harness for IKIGAi-Maintainer — powered by deepagents.

Refactored to use create_deep_agent with:
- 8 IKIGAi tools (ikigai_score, ikigai_regime, ikigai_phase,
  ikigai_corrections, ikigai_decompose, ikigai_plan_cycle,
  ikigai_sync_vault, ikigai_checkpoint)
- SqliteSaver checkpointer (persistent across restarts)
- Human-in-the-loop pause before commit (interrupt_on)
- Thread-based conversation via thread_id
- deepagents built-in chat REPL

Run with:
    python -m agents.deepagents_harness --chat --thread default
    python -m agents.deepagents_harness --chat --thread default --human-in-the-loop
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
_CHECKPOINT_DB = os.environ.get(
    "IKIGAI_CHECKPOINT_DB",
    str(Path.home() / ".ikigai" / "ikigai_checkpoints.db"),
)
_THREAD_ID = os.environ.get("IKIGAI_THREAD_ID", "default")


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------
_SYSTEM_PROMPT = """You are the **IKIGAi Strategic Agent** — an expert in personal strategy
and career planning. You have 8 specialized tools at your disposal.

You help the user understand their IKIGAi vector scores (passion, skill, market,
revenue, course), manage their strategic regime (PUSH / MAINTAIN / REDUCE / RECOVER),
track phase transitions, and run planning cycles.

Be concise. Use emoji for vectors and regimes. Format tables nicely.

When the user asks about their scores, regime, phase, or corrections — call the
corresponding tool and show the result formatted nicely.
When they ask to run a plan cycle — call ikigai_plan_cycle.
When they ask about a specific dream/project — call ikigai_decompose.
When they ask to persist/sync their state — call ikigai_sync_vault.

Available tools:
  ikigai_score        — 5-vector scores + meta-vector + Q_HE
  ikigai_regime       — regime + Q_HE + days_in_regime
  ikigai_phase        — phase + iteration + weight distribution
  ikigai_corrections  — H1-H6 heuristic signals
  ikigai_decompose    — full UEID hierarchy (dream → project)
  ikigai_plan_cycle   — run full 8-node strategic planning cycle
  ikigai_sync_vault   — write checkpoint to vault markdown
  ikigai_checkpoint   — list / get checkpoint threads

Be conversational. Offer insights when scores change or regime transitions occur."""


# ---------------------------------------------------------------------------
# Agent factory
# ---------------------------------------------------------------------------

def _make_agent(
    thread_id: str = _THREAD_ID,
    checkpoint_db: str = _CHECKPOINT_DB,
    human_in_the_loop: bool = False,
):
    """Build a deep-agent-wrapped IKIGAi agent.

    Uses deepagents' create_deep_agent with:
    - 8 IKIGAi tools (langchain @tool decorators)
    - SqliteSaver checkpointer
    - interrupt_on={"write_file": True} for HITL before writes
    - thread_id as configurable thread
    """
    from deepagents import create_deep_agent
    from langgraph.checkpoint.sqlite import SqliteSaver
    from langchain_anthropic import ChatAnthropic

    # Ensure checkpoint dir
    Path(checkpoint_db).parent.mkdir(parents=True, exist_ok=True)

    # Checkpointer
    import sqlite3

    conn = sqlite3.connect(checkpoint_db, check_same_thread=False)
    checkpointer = SqliteSaver(conn)

    # Human-in-the-loop: pause before any tool that writes
    interrupt_on = None
    if human_in_the_loop:
        interrupt_on = {"write_file": True}

    # Load IKIGAi tools
    from .tools import IKIGAI_TOOLS

    # LLM — initialize ChatAnthropic with MiniMax API credentials
    api_key = os.environ.get("MINIMAX_API_KEY", os.environ.get("ANTHROPIC_API_KEY", ""))
    base_url = os.environ.get("ANTHROPIC_BASE_URL", "https://api.minimax.io/anthropic")
    model_name = os.environ.get("ANTHROPIC_MODEL", "MiniMax-M2.7-highspeed")

    llm = ChatAnthropic(
        model=model_name,
        api_key=api_key,
        base_url=base_url,
        default_headers={"x-api-key": api_key},
    )

    agent = create_deep_agent(
        model=llm,
        tools=IKIGAI_TOOLS,
        system_prompt=_SYSTEM_PROMPT,
        checkpointer=checkpointer,
        interrupt_on=interrupt_on,
        name="ikigai-maintainer",
    )
    return agent, thread_id


# ---------------------------------------------------------------------------
# CLI entrypoint
# ---------------------------------------------------------------------------

def main():
    import argparse

    parser = argparse.ArgumentParser(description="IKIGAi Deep Agent (deepagents-powered)")
    parser.add_argument("--thread", default=_THREAD_ID, help="Thread ID for checkpointing")
    parser.add_argument("--checkpoint-db", default=_CHECKPOINT_DB, help="SQLite checkpoint DB path")
    parser.add_argument(
        "--human-in-the-loop",
        action="store_true",
        help="Pause before each tool write (human-in-the-loop)",
    )
    parser.add_argument(
        "--list-checkpoints",
        action="store_true",
        help="List checkpoints and exit",
    )
    parser.add_argument(
        "--run-cycle",
        action="store_true",
        help="Run one plan cycle and exit",
    )
    parser.add_argument(
        "--chat",
        action="store_true",
        help="Start interactive REPL chat mode",
    )
    args = parser.parse_args()

    agent, thread_id = _make_agent(
        thread_id=args.thread,
        checkpoint_db=args.checkpoint_db,
        human_in_the_loop=args.human_in_the_loop,
    )

    if args.list_checkpoints:
        from .tools import ikigai_checkpoint

        result = ikigai_checkpoint.invoke({"action": "list", "thread_id": thread_id})
        print(result)
        return

    if args.run_cycle:
        from .tools import ikigai_plan_cycle

        result = ikigai_plan_cycle.invoke({"thread_id": thread_id})
        print(result)
        return

    if args.chat:
        run_chat(agent, thread_id)
        return

    # Default: run one cycle
    print(f"\nIKIGAi Deep Agent — thread: {thread_id}")
    print(f"Checkpoint DB: {args.checkpoint_db}")
    from .tools import ikigai_plan_cycle

    result = ikigai_plan_cycle.invoke({"thread_id": thread_id})
    print(result)


def run_chat(agent, thread_id: str):
    """Run the deep agent in interactive chat mode.

    deepagents provides a built-in REPL via the graph's stream or invoke.
    We wrap it with conversation history accumulation.
    """
    from deepagents.graph import DeepAgentState

    print("IKIGAi Conversational Agent — powered by deepagents")
    print("Ctrl+C to exit\n")
    print("Commands: score | regime | phase | corrections | decompose <ueid> | plan | sync | checkpoint\n")

    # Bootstrap: run one plan cycle first to get initial state
    from .tools import ikigai_plan_cycle

    print("Bootstrapping IKIGAi state...")
    init_result = ikigai_plan_cycle.invoke({"thread_id": thread_id})
    print(f"  {init_result}\n")

    config = {"configurable": {"thread_id": thread_id}}

    messages: list[dict] = []

    def show_state():
        """Print current checkpointed state."""
        from .tools import ikigai_regime, ikigai_phase, ikigai_score

        print("\n📊 Current State:")
        print("  " + ikigai_regime.invoke({"thread_id": thread_id}))
        print("  " + ikigai_phase.invoke({"thread_id": thread_id}))
        score_result = ikigai_score.invoke({"thread_id": thread_id})
        for line in score_result.split("\n"):
            print(f"  {line}")

    try:
        while True:
            try:
                user_input = input("\n🧑 > ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n\nGoodbye.")
                break
            if not user_input:
                continue

            # Built-in direct commands
            t = user_input.lower().strip()
            if t in ("score", "scores"):
                from .tools import ikigai_score

                print("\n" + ikigai_score.invoke({"thread_id": thread_id}))
                continue
            if t in ("regime", "state", "status"):
                from .tools import ikigai_regime

                print("\n" + ikigai_regime.invoke({"thread_id": thread_id}))
                continue
            if t in ("phase", "phases", "weights"):
                from .tools import ikigai_phase

                print("\n" + ikigai_phase.invoke({"thread_id": thread_id}))
                continue
            if t in ("corrections", "signals"):
                from .tools import ikigai_corrections

                print("\n" + ikigai_corrections.invoke({"thread_id": thread_id}))
                continue
            if t in ("sync", "vault"):
                from .tools import ikigai_sync_vault

                print("\n" + ikigai_sync_vault.invoke({"thread_id": thread_id}))
                continue
            if t.startswith("decompose ") or t.startswith("decomp "):
                parts = user_input.strip().split(None, 1)
                ueid = parts[1] if len(parts) > 1 else ""
                from .tools import ikigai_decompose

                print("\n" + ikigai_decompose.invoke({"ueid": ueid, "thread_id": thread_id}))
                continue
            if t.startswith("checkpoint"):
                parts = user_input.strip().split(None, 1)
                action = parts[1] if len(parts) > 1 else "list"
                from .tools import ikigai_checkpoint

                print("\n" + ikigai_checkpoint.invoke({"action": action, "thread_id": thread_id}))
                continue
            if t in ("plan", "plan_cycle", "cycle", "run"):
                print()
                print(ikigai_plan_cycle.invoke({"thread_id": thread_id}))
                continue
            if t in ("state", "show"):
                show_state()
                continue
            if t in ("help", "?"):
                print(
                    "\nCommands:\n"
                    "  score              — 5-vector scores\n"
                    "  regime            — regime + Q_HE\n"
                    "  phase             — phase + weights\n"
                    "  corrections       — H1-H6 signals\n"
                    "  decompose <ueid>  — UEID hierarchy\n"
                    "  plan              — run full cycle\n"
                    "  sync              — write vault file\n"
                    "  checkpoint        — list checkpoints\n"
                    "  state             — show current state\n"
                    "\nOr just chat naturally."
                )
                continue

            # Natural language → deep agent
            print()
            messages.append({"role": "user", "content": user_input})

            try:
                # Stream response
                response_content = ""
                for event in agent.stream(
                    {"messages": messages},
                    config=config,
                ):
                    # deepagents streams message deltas
                    if hasattr(event, "get"):
                        for node_name, node_output in event.items():
                            if isinstance(node_output, dict) and "messages" in node_output:
                                for msg in node_output["messages"]:
                                    if isinstance(msg, dict) and msg.get("role") == "assistant":
                                        text = msg.get("content", "")
                                        if text:
                                            print(text, end="", flush=True)
                                            response_content += text
                print()  # newline after stream

                messages.append({"role": "assistant", "content": response_content})

            except Exception as e:
                print(f"\n[Agent error: {e}]")
                # Fallback: try plan cycle
                print("Falling back to plan cycle...")
                try:
                    print(ikigai_plan_cycle.invoke({"thread_id": thread_id}))
                except Exception as e2:
                    print(f"  [Fallback failed: {e2}]")

    except KeyboardInterrupt:
        print("\n\nGoodbye.")


# ---------------------------------------------------------------------------
# Compat shim for old module-level imports
# ---------------------------------------------------------------------------
IKIGAiDeepAgent = None  # removed — use create_deep_agent via _make_agent


if __name__ == "__main__":
    main()

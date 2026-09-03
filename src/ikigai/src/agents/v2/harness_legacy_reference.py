"""READ-ONLY legacy reference — DO NOT IMPORT.

Kept per ADR-013 scope discipline for inspection during Phase 8 refactor.
The entire module body is wrapped in `if False:` so this file is never executed
and never participates in the runtime module graph.

Drift detector: this file is scanned by test_canonical_scope.py (agents/ is in scope).
The if False: wrapper prevents any top-level FunctionDef/Import from being detected
as live definitions. The code is preserved verbatim as a historical artifact.
"""

# ---------------------------------------------------------------------------
# SOURCE FILE: deepagents_harness_PRE_STRIP_8992e0c.py (566 lines)
# Original commit: 8992e0c
# See archive/recovered-agentic-2026-09-01/ for the canonical source.
# ---------------------------------------------------------------------------

if False:
    import os
    from pathlib import Path
    from typing import Any, cast

    # Observability — NOT a real package; stubbed at v2/graph.py level
    from observability import get_tracer, init_tracing, shutdown_tracing

    init_tracing()
    _tracer = get_tracer("ikigai.harness")

    # ---------------------------------------------------------------------------
    # Config
    # ---------------------------------------------------------------------------
    _CHECKPOINT_DB = os.environ.get(
        "IKIGAI_CHECKPOINT_DB",
        str(Path.cwd() / "data" / "ikigai_checkpoints.db"),
    )
    _THREAD_ID = os.environ.get("IKIGAI_THREAD_ID", "default")

    _PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
    _FS_ROOT = _PROJECT_ROOT / "data"
    _VAULT_ROOT = _PROJECT_ROOT / "vault"
    _FS_ALLOWED_ROOTS: tuple[Path, ...] = (_FS_ROOT, _VAULT_ROOT)

    # ---------------------------------------------------------------------------
    # System prompt (full constitutional + IKIGAI + PAV context)
    # ---------------------------------------------------------------------------
    _SYSTEM_PROMPT = """You are the **IKIGAi Strategic Agent** — a cross-functional analyst who operates
across three layers: constitutional intent (strategics/), strategic planning (IKIGAI),
and operational execution (PAV).

You have 18 specialized tools. You help the user understand their IKIGAi vector scores
(passion, skill, market, revenue, course), manage their strategic regime
(PUSH / MAINTAIN / REDUCE / RECOVER), track phase transitions, check project status
anywhere on the filesystem, and run planning cycles that persist to the vault.

Be conversational. Use emoji for vectors and regimes. Format tables nicely.
Offer insights when regime transitions occur or scores change significantly.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LAYER 1 — CONSTITUTIONAL (strategics/ — read-only reference)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The strategics/ directory is the constitutional layer: it NEVER changes and is the
foundation for all decisions. Key concepts:
- Tensão → Comportamento → Solução: tension drives behavior drives solution
- 5 tensões (tensions) that shape strategy
- 4 regimes that govern workload envelopes

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LAYER 2 — IKIGAI STRATEGIC
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

5 VECTORS (passion, skill, market, revenue, course)
  Each vector is scored 0.0-1.0. Until 5+ SONHO logs are captured, all vectors
  are weighted equally (0.20 each). The meta-vector is a hybrid geometric/harmonic
  mean (60/40 blend).

5 PHASES
  FUNDAÇÃO    (foundation)   — building infrastructure, low speed
  BUSCA       (search)       — exploring options, medium speed
  HACKATHON   (build)         — rapid execution, high speed
  RECUPERAÇÃO  (recovery)     — healing, very low speed
  OVERCLOCK   (sprint)       — maximum output, short duration

4 REGIMES (with asymmetric hysteresis)
  PUSH      Q_HE ≥ 0.85  | 8h hard work · 10 pomodoros · 7h sleep
  MAINTAIN  0.70-0.85   | 6h hard work · 8 pomodoros · 8h sleep
  REDUCE    0.60-0.70   | 4h hard work · 5 pomodoros · 8h sleep
  RECOVER   < 0.60       | 2h hard work · 2 pomodoros · 9h sleep

  Hysteresis rules (asymmetric — down is faster than up):
    Upgrade to PUSH:      3 consecutive days at Q_HE ≥ 0.85
    Downgrade to RECOVER:  2 consecutive days at Q_HE < 0.60
    RECOVER → REDUCE:      3 consecutive days at Q_HE ≥ 0.60
    Emergency RECOVER:     Q_HE < 0.30 OR infractions ≥ 3 (immediate, no hysteresis)
    PUSH early warning:    infractions ≥ 2 → drops to REDUCE immediately

Q_HE FORMULA (quality of life execution)
  H(t) = 1 - e^(-λ · streak)         [habit consolidation, 0 ≤ H < 1]
  E = R · (1 - H(t))                  [energy required, 0-10]
  Q_HE = H_avg · (E(t)/E_max) · (1 + η · S_bonus)
  Where:
    H_avg = weighted average habit level across all active habits
    E(t)/E_max = energy ratio (high=1.0, medium=0.6, low=0.3)
    S_bonus = min(current_streak / max_streak, 1.0)  [streak bonus, 0-1]
    η = 0.5 (streak bonus multiplier, configurable)
  Typical Q_HE operational range: 0.0-1.0. Theoretical max: 2.0.

H1-H6 HEURISTIC SIGNALS
  H1: Regime consistency (deviation from expected Q_HE for current regime)
  H2: Phase convergence (are vector weights converging toward phase targets?)
  H3: Passion decay (is passion vector drifting from its baseline?)
  H4: Velocity gap (is actual progress matching planned velocity?)
  H5: Strategic friction (are external blockers accumulating?)
  H6: Recovery signals (is RECOVER phase producing expected rest benefits?)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LAYER 3 — PAV OPERATIONAL
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PAV (Operational Layer) measures habit consistency, energy, and policy decisions.
IKIGAI consumes PAV outputs as substrate for the 5-vector scores.

What PAV produces:
  QHEMetrics      — daily habit quality composite (H_avg, consistency, streak_bonus, energy_ratio)
  PolicyDecision   — regime assignment + workload envelope for the day
  PolicySetpoints  — hardwork_budget, pause_min, sleep_target, Q_HE target
  HabitState       — per-habit daily records (streak, effort_minutes, completed)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
VAULT HIERARCHY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Vault root: data/matheus/
  dreams/           — SONHOS root objectives (547d horizon)
  objectives/       — TRIMESTRE goals (90d)
  projects/         — ONDA deliverables (30d)
  deliverables/     — CYCLE outputs (7d)
  ikigai_state/     — cycle logs, profile snapshots

UEID format: ikigai:<entity_type>:<slug>:<8-hex-uuid>:<8-hex-content-hash>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
IDIOMA — Idioma mandatory:
  Você DEVE responder SEMPRE em português brasileiro (pt-BR).
  Toda resposta deve ser em português, sem exceção.
  Não responda em inglês, mesmo que a pergunta seja em inglês.
  Use português brasileiro natural, com expressões comuns do Brasil.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""

    # ---------------------------------------------------------------------------
    # Agent factory
    # ---------------------------------------------------------------------------

    def _make_agent(
        thread_id: str = _THREAD_ID,
        checkpoint_db: str = _CHECKPOINT_DB,
        human_in_the_loop: bool = False,
    ) -> Any:
        """Build a deep-agent-wrapped IKIGAi agent."""
        from deepagents import create_deep_agent
        from deepagents.backends import FilesystemBackend
        from langchain_anthropic import ChatAnthropic
        from langgraph.checkpoint.sqlite import SqliteSaver

        Path(checkpoint_db).parent.mkdir(parents=True, exist_ok=True)
        import sqlite3

        conn = sqlite3.connect(checkpoint_db, check_same_thread=False)
        checkpointer = SqliteSaver(conn)

        interrupt_on = None
        if human_in_the_loop:
            interrupt_on = {"write_file": True}

        backend = FilesystemBackend(
            root_dir=_FS_ROOT,
            virtual_mode=True,
        )

        from .tools import IKIGAI_TOOLS

        api_key = os.environ.get("MINIMAX_API_KEY", os.environ.get("ANTHROPIC_API_KEY", ""))
        base_url = os.environ.get("ANTHROPIC_BASE_URL", "https://api.minimax.io/anthropic")
        model_name = os.environ.get("ANTHROPIC_MODEL", "MiniMax-M2.7-highspeed")

        llm = ChatAnthropic(
            model=model_name,
            api_key=api_key,
            base_url=base_url,
            default_headers={"x-api-key": api_key},
        )

        with _tracer.start_as_current_span("ikigai.make_agent") as span:
            span.set_attribute("thread_id", thread_id)
            span.set_attribute("human_in_the_loop", human_in_the_loop)
            span.set_attribute("model", os.environ.get("ANTHROPIC_MODEL", "MiniMax-M2.7-highspeed"))
            agent = create_deep_agent(
                model=llm,
                tools=IKIGAI_TOOLS,
                system_prompt=_SYSTEM_PROMPT,
                checkpointer=checkpointer,
                interrupt_on=interrupt_on,
                name="ikigai-maintainer",
                backend=backend,
            )
        return agent, thread_id

    # ---------------------------------------------------------------------------
    # CLI entrypoint
    # ---------------------------------------------------------------------------

    def main() -> None:
        import argparse

        parser = argparse.ArgumentParser(description="IKIGAi Deep Agent (deepagents-powered)")
        parser.add_argument("--thread", default=_THREAD_ID, help="Thread ID for checkpointing")
        parser.add_argument(
            "--checkpoint-db", default=_CHECKPOINT_DB, help="SQLite checkpoint DB path"
        )
        parser.add_argument(
            "--human-in-the-loop", action="store_true", help="Pause before each tool write"
        )
        parser.add_argument(
            "--list-checkpoints", action="store_true", help="List checkpoints and exit"
        )
        parser.add_argument("--run-cycle", action="store_true", help="Run one plan cycle and exit")
        parser.add_argument("--chat", action="store_true", help="Start interactive REPL chat mode")
        args = parser.parse_args()
        thread_id = args.thread

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

        if not args.chat:
            from .tools import ikigai_plan_cycle

            print(f"\nIKIGAi Deep Agent — thread: {thread_id}")
            print(f"Checkpoint DB: {args.checkpoint_db}")
            result = ikigai_plan_cycle.invoke({"thread_id": thread_id})
            print(result)
            return

        agent, agent_thread_id = _make_agent(
            thread_id=args.thread,
            checkpoint_db=args.checkpoint_db,
            human_in_the_loop=args.human_in_the_loop,
        )
        run_chat(agent, agent_thread_id)

    # ---------------------------------------------------------------------------
    # F11 helpers
    # ---------------------------------------------------------------------------

    def _msg_role(msg: Any) -> str | None:
        if isinstance(msg, dict):
            return msg.get("role") or msg.get("type")
        return getattr(msg, "type", None) or getattr(msg, "role", None)

    def _msg_content(msg: Any) -> Any:
        if isinstance(msg, dict):
            return msg.get("content", "")
        return getattr(msg, "content", "")

    def _extract_assistant_text(result: dict[str, Any]) -> str:
        messages = result.get("messages", [])
        for msg in reversed(messages):
            role = _msg_role(msg)
            if role in ("assistant", "ai"):
                content = _msg_content(msg)
                return content if isinstance(content, str) else str(content)
        return ""

    def _register_builtin_commands() -> dict[str, Any]:
        from .tools import (
            ikigai_checkpoint,
            ikigai_corrections,
            ikigai_phase,
            ikigai_plan_cycle,
            ikigai_regime,
            ikigai_score,
            ikigai_sync_vault,
        )

        def _call(tool: Any, thread_id: str) -> str:
            return cast(str, tool.invoke({"thread_id": thread_id}))

        return {
            "score": lambda tid: _call(ikigai_score, tid),
            "scores": lambda tid: _call(ikigai_score, tid),
            "regime": lambda tid: _call(ikigai_regime, tid),
            "phase": lambda tid: _call(ikigai_phase, tid),
            "corrections": lambda tid: _call(ikigai_corrections, tid),
            "plan": lambda tid: _call(ikigai_plan_cycle, tid),
            "sync": lambda tid: _call(ikigai_sync_vault, tid),
            "checkpoint": lambda tid: _call(ikigai_checkpoint, tid),
        }

    def _route_command(user_input: str, thread_id: str, registry: dict[str, Any]) -> str | None:
        key = user_input.lower().strip()
        handler = registry.get(key)
        if handler is None:
            return None
        return cast(str | None, handler(thread_id))

    def _invoke_agent_or_fallback(
        agent: Any,
        messages: list[dict[str, Any]],
        config: dict[str, Any],
        thread_id: str,
    ) -> dict[str, Any] | None:
        _ = thread_id
        try:
            return cast(dict[str, Any], agent.invoke({"messages": messages}, config=config))
        except (RuntimeError, ValueError, KeyError, TypeError, AttributeError, OSError) as exc:
            if isinstance(exc, (KeyboardInterrupt, SystemExit, GeneratorExit)):
                raise
            return None

    def run_chat(agent: Any, thread_id: str) -> None:
        from .tools import ikigai_plan_cycle

        print("IKIGAi Conversational Agent — powered by deepagents")
        print("Ctrl+C to exit\n")
        print("Commands: score | regime | phase | corrections | plan | sync | checkpoint\n")
        print("Bootstrapping IKIGAi state...")
        init_result = ikigai_plan_cycle.invoke({"thread_id": thread_id})
        print(f"  {init_result}\n")
        config: dict[str, Any] = {"configurable": {"thread_id": thread_id}}
        messages: list[dict[str, Any]] = []
        registry = _register_builtin_commands()
        while True:
            try:
                user_input = input("\n🧑 > ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n\nGoodbye.")
                break
            if not user_input:
                continue
            cmd_result = _route_command(user_input, thread_id, registry)
            if cmd_result is not None:
                print(cmd_result)
                continue
            messages.append({"role": "user", "content": user_input})
            result = _invoke_agent_or_fallback(agent, messages, config, thread_id)
            if result is None:
                print("(agent unavailable; please use a built-in command)")
                continue
            assistant_text = _extract_assistant_text(result)
            messages = result.get("messages", messages)
            print(assistant_text)
        shutdown_tracing()

    # ---------------------------------------------------------------------------
    # Compat shim
    # ---------------------------------------------------------------------------
    IKIGAiDeepAgent = None  # removed — use create_deep_agent via _make_agent

    if __name__ == "__main__":
        main()

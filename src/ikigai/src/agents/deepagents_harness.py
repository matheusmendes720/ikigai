"""Deep agents harness for IKIGAi-Maintainer — powered by deepagents.

Refactored to use create_deep_agent with:
- 18 tools (8 IKIGAi + 3 solverforge + 4 tuiboard + 3 taskdog)
- FilesystemBackend for free directory access anywhere on the system
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
# Observability — initialize tracing once at module load.
# init_tracing() is idempotent and best-effort: missing OTel libs or empty
# env vars mean no exporters are added, but the host code still runs.
# ---------------------------------------------------------------------------
from observability import init_tracing, get_tracer, shutdown_tracing
from opentelemetry import trace as _otel_trace

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

# Filesystem backend root — scope to project data/ + vault/ directories only.
# This prevents the agent from reading or writing outside the project sandbox.
# Per audit B5.0-F9: previous default was Path.home() with virtual_mode=False,
# which granted unrestricted system access (security blast radius risk).
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
_FS_ROOT = _PROJECT_ROOT / "data"
_VAULT_ROOT = _PROJECT_ROOT / "vault"
_FS_ALLOWED_ROOTS: tuple[Path, ...] = (_FS_ROOT, _VAULT_ROOT)


# ---------------------------------------------------------------------------
# System prompt
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

When reasoning about strategic decisions, ground them in these constitutional principles.
Never contradict or rewrite strategics/ content.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LAYER 2 — IKIGAI STRATEGIC
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

5 VECTORS (passion, skill, market, revenue, course)
  Each vector is scored 0.0–1.0. Until 5+ SONHO logs are captured, all vectors
  are weighted equally (0.20 each). The meta-vector is a hybrid geometric/harmonic
  mean (60/40 blend).

5 PHASES
  FUNDAÇÃO    (foundation)   — building infrastructure, low speed
  BUSCA       (search)       — exploring options, medium speed
  HACKATHON   (build)         — rapid execution, high speed
  RECUPERAÇÃO  (recovery)     — healing, very low speed
  OVERCLOCK   (sprint)       — maximum output, short duration

  Phase weights (vector distribution per phase):
    FUNDAÇÃO:    passion=0.35, skill=0.30, market=0.15, revenue=0.10, course=0.10
    BUSCA:       passion=0.25, skill=0.25, market=0.25, revenue=0.15, course=0.10
    HACKATHON:   passion=0.20, skill=0.15, market=0.20, revenue=0.30, course=0.15
    RECUPERAÇÃO: passion=0.30, skill=0.30, market=0.15, revenue=0.10, course=0.15
    OVERCLOCK:   passion=0.25, skill=0.15, market=0.15, revenue=0.30, course=0.15

4 REGIMES (with asymmetric hysteresis)
  PUSH      Q_HE ≥ 0.85  | 8h hard work · 10 pomodoros · 7h sleep
  MAINTAIN  0.70–0.85   | 6h hard work · 8 pomodoros · 8h sleep
  REDUCE    0.60–0.70   | 4h hard work · 5 pomodoros · 8h sleep
  RECOVER   < 0.60       | 2h hard work · 2 pomodoros · 9h sleep

  Hysteresis rules (asymmetric — down is faster than up):
    Upgrade to PUSH:      3 consecutive days at Q_HE ≥ 0.85
    Downgrade to RECOVER:  2 consecutive days at Q_HE < 0.60
    RECOVER → REDUCE:      3 consecutive days at Q_HE ≥ 0.60
    Emergency RECOVER:     Q_HE < 0.30 OR infractions ≥ 3 (immediate, no hysteresis)
    PUSH early warning:    infractions ≥ 2 → drops to REDUCE immediately

TIME HORIZONS
  SONHOS   = 547 days  (lifetime dream — root of all hierarchy)
  PHASE    = 180 days  (semester planning window)
  TRIMESTRE =  90 days (quarterly objective)
  ONDA     =  15 days  (wave — standard project window)
  CYCLE    =  45 days  (planning cycle within a TRIMESTRE)
  WEEKLY   =   7 days  (operational horizon)

Q_HE FORMULA (quality of life execution)
  H(t) = 1 − e^(−λ · streak)         [habit consolidation, 0 ≤ H < 1]
  E = R · (1 − H(t))                  [energy required, 0–10]
  Q_HE = H_avg · (E(t)/E_max) · (1 + η · S_bonus)
  Where:
    H_avg = weighted average habit level across all active habits
    E(t)/E_max = energy ratio (high=1.0, medium=0.6, low=0.3)
    S_bonus = min(current_streak / max_streak, 1.0)  [streak bonus, 0–1]
    η = 0.5 (streak bonus multiplier, configurable)
  Typical Q_HE operational range: 0.0–1.0. Theoretical max: 2.0.

H1–H6 HEURISTIC SIGNALS
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

What IKIGAI reads from PAV:
  q_he_score      — QHE composite from most recent QHEMetrics
  regime_state    — PUSH | MAINTAIN | REDUCE | RECOVER from PolicyDecision
  days_in_regime  — consecutive days in current regime
  corrections      — H1–H6 heuristic signals (ikigai_corrections tool)

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
  entity_type: dream | objective | project | deliverable | profile | cycle

Use ikigai_decompose(ueid) to walk the hierarchy:
  ikigai_decompose("ikigai:dream:vaga-remota-2026:...")
  → returns full tree: dream → objectives → projects → tasks

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TOOLS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

IKIGAi core (8 tools):
  ikigai_score        — 5-vector scores + meta-vector + Q_HE
  ikigai_regime       — regime + Q_HE + days_in_regime + hysteresis status
  ikigai_phase        — phase + iteration + weight distribution
  ikigai_corrections  — H1–H6 heuristic signals
  ikigai_decompose    — full UEID hierarchy (dream → deliverable)
  ikigai_plan_cycle   — run full 8-node planning cycle
  ikigai_sync_vault   — write checkpoint to vault markdown
  ikigai_checkpoint   — list / get checkpoint threads

Filesystem (built-in via FilesystemBackend — scoped to project data/):
  ls <path>             — list directory contents under data/
  read_file <path>      — read file contents (data/ only)
  write_file <path>     — write content to file (data/ only, HITL-required)
  edit_file <path>      — edit file (shows diff, data/ only)
  glob <pattern>        — glob pattern search under data/
  grep <pattern> <path> — search for pattern under data/

  ⚠️ Scope: agent can ONLY access files under <project_root>/data/.
  Vault/ files are accessed via ikigai_decompose / ikigai_sync_vault tools,
  not via filesystem tools. The root_dir is enforced by FilesystemBackend.

Solverforge Calendar (Rust CLI):
  solverforge_list_events  — list upcoming events (default 7 days)
  solverforge_create_event — create calendar event

Tuiboard Kanban (SolidJS MCP):
  tuiboard_list_boards   — list all markdown kanban boards
  tuiboard_get_tasks     — get tasks from a board
  tuiboard_update_task   — update task (done/priority/tags/dates)
  tuiboard_create_task   — create new task

Taskdog (Python MCP):
  taskdog_list_tasks      — list tasks with filtering
  taskdog_create_task     — create task
  taskdog_complete_task   — mark task completed
  taskdog_get_task        — get full task details

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
INTERACTION PATTERNS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

When the user asks about scores, regime, phase, or corrections:
  → Call the corresponding IKIGAi tool immediately, format as table with emoji.

When the user asks to check project status anywhere on the filesystem:
  → Use ls/read_file to navigate the directory and read relevant files.
  Example: "check the vibe-ops project" → ls ~/code_space/life-oss/vibe-ops/

When the user asks about the vault hierarchy or a specific dream/project:
  → Use ikigai_decompose with the appropriate UEID, or ls the vault directories.

When the user asks to run a plan cycle:
  → Call ikigai_plan_cycle.

When the user asks to persist or sync state:
  → Call ikigai_sync_vault.

When regime transitions occur:
  → Explain: what changed, why (hysteresis rule triggered), and what it means
    for workload envelope going forward.

When scores change significantly (>0.1 on any vector):
  → Surface which habit or external factor likely drove the change.

Be concise. Format tables nicely. Use emoji for vectors (🔥 passion, ⚡ skill,
💰 market, 📊 revenue, 📚 course) and regimes (🚀 PUSH, 🔧 MAINTAIN,
📉 REDUCE, 🛌 RECOVER).

IDIOMA — Idioma mandatory:
  Você DEVE responder SEMPRE em português brasileiro (pt-BR).
  Toda resposta deve ser em português, sem exceção.
  Não responda em inglês, mesmo que a pergunta seja em inglês.
  Use português brasileiro natural, com expressões comuns do Brasil.
  Formate tabelas, listas e estruturas em português.
  Quando usar emoji junto com texto, use o português ao redor do emoji."""


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
    from deepagents.backends import FilesystemBackend
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

    # Filesystem backend — scoped to project data/ + vault/ only.
    # Per audit B5.0-F9: previous default was Path.home() with virtual_mode=False,
    # which granted unrestricted system access (blast radius). Now scoped.
    backend = FilesystemBackend(
        root_dir=_FS_ROOT,  # data/ is primary working area
        virtual_mode=True,  # virtual paths relative to root_dir
        # NOTE: vault/ is a sibling, not under data/. If the agent needs to
        # read vault, the REPL shortcut (ls/cat in run_chat) handles it
        # outside the LLM tool surface. LLM tools are scoped to data/ only.
    )

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
            backend=backend,  # enables built-in ls/read_file/write_file/edit_file/glob/grep
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
                    "  IKIGAi:   score | regime | phase | corrections | decompose <ueid>\n"
                    "            plan | sync | checkpoint | state\n"
                    "  Calendar:  cal <days> | new-event <title> <date> [time]\n"
                    "  Kanban:    boards | board <path> [col] [filter]\n"
                    "  Tasks:     tasks [status] | new-task <name> | done <id> | task <id>\n"
                    "  Filesystem: ls <path> | cat <file> | find <pattern>\n"
                    "\nOr just chat naturally."
                )
                continue

            # Calendar shortcuts
            if t.startswith("cal "):
                days = int(t.split()[1]) if len(t.split()) > 1 else 7
                from .tools import solverforge_list_events
                print("\n" + solverforge_list_events.invoke({"days": days}))
                continue

            if t.startswith("new-event "):
                parts = user_input.strip().split(None, 3)
                if len(parts) < 3:
                    print("Usage: new-event <title> <date> [time]")
                    continue
                title, date = parts[1], parts[2]
                time = parts[3] if len(parts) > 3 else "09:00"
                from .tools import solverforge_create_event
                print("\n" + solverforge_create_event.invoke(
                    {"title": title, "date": date, "time": time}))
                continue

            # Kanban shortcuts
            if t == "boards":
                from .tools import tuiboard_list_boards
                print("\n" + tuiboard_list_boards.invoke({}))
                continue

            if t.startswith("board "):
                parts = user_input.strip().split(None, 4)
                if len(parts) < 2:
                    print("Usage: board <path> [col] [filter]")
                    continue
                bp = parts[1]
                col = int(parts[2]) if len(parts) > 2 else None
                flt = parts[3] if len(parts) > 3 else "all"
                from .tools import tuiboard_get_tasks
                print("\n" + tuiboard_get_tasks.invoke(
                    {"board_path": bp, "column": col, "filter": flt}))
                continue

            # Task shortcuts
            if t.startswith("tasks"):
                parts = user_input.strip().split(None, 2)
                status = parts[1].upper() if len(parts) > 1 else None
                from .tools import taskdog_list_tasks
                print("\n" + taskdog_list_tasks.invoke(
                    {"status": status, "include_archived": False}))
                continue

            if t.startswith("new-task ") or t.startswith("newtask "):
                name = user_input.strip().split(None, 1)[1] if " " in user_input.strip() else ""
                if not name:
                    print("Usage: new-task <name>")
                    continue
                from .tools import taskdog_create_task
                print("\n" + taskdog_create_task.invoke({"name": name}))
                continue

            if t.startswith("done "):
                try:
                    tid = int(t.split()[1])
                    from .tools import taskdog_complete_task
                    print("\n" + taskdog_complete_task.invoke({"task_id": tid}))
                except (ValueError, IndexError):
                    print("Usage: done <task_id>")
                continue

            if t.startswith("task "):
                try:
                    tid = int(t.split()[1])
                    from .tools import taskdog_get_task
                    print("\n" + taskdog_get_task.invoke({"task_id": tid}))
                except (ValueError, IndexError):
                    print("Usage: task <task_id>")
                continue

            # Filesystem shortcuts
            if t.startswith("ls "):
                path = t.split(None, 1)[1]
                p = Path(path).expanduser()
                if p.is_dir():
                    for item in sorted(p.iterdir()):
                        tag = "[DIR]" if item.is_dir() else "[FILE]"
                        print(f"  {tag}  {item.name}")
                else:
                    print(f"  Not a directory: {path}")
                continue

            if t.startswith("cat "):
                path = t.split(None, 1)[1]
                p = Path(path).expanduser()
                if p.is_file():
                    print(p.read_text(encoding="utf-8", errors="replace"))
                else:
                    print(f"  File not found: {path}")
                continue

            if t.startswith("find "):
                pattern = t.split(None, 1)[1] if " " in t else ""
                import glob as _glob
                matches = _glob.glob(str(Path.home() / pattern), recursive=True)[:20]
                for m in matches:
                    print(f"  {m}")
                if not matches:
                    print("  (no matches)")
                continue

            # Natural language → deep agent
            print()
            messages.append({"role": "user", "content": user_input})

            try:
                # Use invoke() for reliable full-response retrieval
                result = agent.invoke(
                    {"messages": messages},
                    config=config,
                )
                # Result is the final state dict; extract assistant text from messages
                response_content = ""
                if isinstance(result, dict):
                    for msg in result.get("messages", []):
                        # Handle both plain dicts and LangChain message objects
                        if isinstance(msg, dict):
                            role = msg.get("role", "")
                            content = msg.get("content", "")
                        else:
                            # LangChain message: HumanMessage, AIMessage, SystemMessage, etc.
                            role = getattr(msg, "type", getattr(msg, "role", ""))
                            content = getattr(msg, "content", "")

                        if role == "ai" and content:
                            # deepagents returns structured content: [{type, text, ...}, ...]
                            # Extract readable text, skipping 'thinking' blocks
                            if isinstance(content, list):
                                for block in content:
                                    if isinstance(block, dict) and block.get("type") == "text":
                                        text = block.get("text", "")
                                        if text:
                                            print(text, end="", flush=True)
                                            response_content += text + "\n"
                            elif isinstance(content, str) and content:
                                print(content, end="", flush=True)
                                response_content += content + "\n"
                elif isinstance(result, str):
                    print(result, end="")
                    response_content = result
                print()  # newline after response

                if response_content:
                    messages.append({"role": "assistant", "content": response_content.strip()})

            except Exception as e:
                # Record the exception in the active trace so Langfuse shows
                # the full stack trace alongside the LLM span that triggered it.
                with _tracer.start_as_current_span("ikigai.run_chat.error") as span:
                    span.set_status(_otel_trace.Status(_otel_trace.StatusCode.ERROR, str(e)))
                    span.record_exception(e)
                print(f"\n[Agent error: {e}]")
                # Fallback: try plan cycle
                print("Falling back to plan cycle...")
                try:
                    print(ikigai_plan_cycle.invoke({"thread_id": thread_id}))
                except Exception as e2:
                    print(f"  [Fallback failed: {e2}]")

    except KeyboardInterrupt:
        print("\n\nGoodbye.")

    finally:
        # Flush any pending spans to both exporters before the process exits.
        shutdown_tracing()


# ---------------------------------------------------------------------------
# Compat shim for old module-level imports
# ---------------------------------------------------------------------------
IKIGAiDeepAgent = None  # removed — use create_deep_agent via _make_agent


if __name__ == "__main__":
    main()

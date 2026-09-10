"""Deep agents harness for IKIGAi — planning assistant ONLY.

Per user scope (2026-08-31):
  "o ikigai agent nao cuida de algoritmos matematicos como regas de negocios,
   politicas" — IKIGAi agent is a PLANNING ASSISTANT ONLY at the level of
   "prompt chains e workflows definidos entre as tools com o mcp da interface".

The agent layer binds 12 tools (10 external data + 2 vault reads). It does
NOT bind math/policy/business-rule tools. Those live behind the MCP
interface (`src/mcp_server/server.py`).

Tools:
- 2 solverforge (calendar events)
- 4 tuiboard (kanban read/write)
- 4 taskdog (task management)
- 2 vault reads (ikigai_read_vault, ikigai_read_strategics)

Run with:
    python -m agents.deepagents_harness --chat --thread default
    python -m agents.deepagents_harness --chat --thread default --human-in-the-loop
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, cast

# ---------------------------------------------------------------------------
# Observability — initialize tracing once at module load.
# init_tracing() is idempotent and best-effort: missing OTel libs or empty
# env vars mean no exporters are added, but the host code still runs.
# ---------------------------------------------------------------------------
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
_SYSTEM_PROMPT = """Você é o **Agente de Planejamento IKIGAi** — um assistente que opera via
"prompt chains e workflows definidos entre as tools com o mcp da interface".

Você é um PLANEJADOR, não um executor de algoritmos. Sua função é ajudar o
usuário a organizar, decompor e priorizar trabalho. Você NÃO executa:
  - Cálculo de vetores IKIGAi (passion/skill/market/revenue/course)
  - Decisões de regime (PUSH/MAINTAIN/REDUCE/RECOVER)
  - Transições de fase (FUNDAÇÃO/BUSCA/HACKATHON/RECUPERAÇÃO/OVERCLOCK)
  - Cálculo de Q_HE
  - Heurísticas H1-H6
  - Ciclo de planejamento completo (8-node LangGraph)

Essas capacidades vivem atrás da interface MCP (`src/mcp_server/server.py`).
Quando o usuário pedir um cálculo ou estado algorítmico, instrua-o a usar a
interface MCP — você não tem essas tools vinculadas.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CAMADA CONSTITUCIONAL (strategics/ — read-only reference)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

O diretório `strategics/` é a camada constitucional: NUNCA muda e é a
fundamentação para todas as decisões. Use `ikigai_read_strategics` para ler.
Conceitos-chave:
- Tensão → Comportamento → Solução: tensão dirige comportamento dirige solução
- 5 tensões que moldam estratégia
- 4 regimes que governam envelopes de carga

Quando raciocinar sobre decisões estratégicas, aterris-as nesses princípios
constitucionais. Nunca contradiga ou reescreva conteúdo de `strategics/`.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HIERARQUIA VAULT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Vault root: project_root/vault/
  ikigai/closing-2026/   — ciclos de planejamento (Q3, Q4, archive)
  ikigai/meta/           — MOCs, indexes, dashboards
  ikigai/mock-datasets/  — fixtures
  drafts/evidence/       — PAE coverage, evidence trail
  plans/                 — plan specs
  run-continuation/      — session resumption JSON

UEID format: ikigai:<entity_type>:<slug>:<8-hex>:<8-hex>
  entity_type: dream | objective | project | deliverable | profile | cycle | regime

Use `ikigai_read_vault(path)` para ler arquivos do vault.
Vault writes vão exclusivamente via MCP `vault_write` (você não escreve
diretamente no vault — não há tool de write vinculada neste agente).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TOOLS VINCULADAS (12 total — apenas leitura de dados externos + vault)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Vault reads:
  ikigai_read_vault(path)     — read any file under vault/ (read-only)
  ikigai_read_strategics(...) — read strategics/ constitutional layer

Solverforge Calendar (Rust CLI):
  solverforge_list_events(days)  — list upcoming events
  solverforge_create_event(t,d,t) — create calendar event

Tuiboard Kanban:
  tuiboard_list_boards()                — list markdown kanban boards
  tuiboard_get_tasks(board_path)         — get tasks from a board
  tuiboard_update_task(task_id, ...)     — update task
  tuiboard_create_task(board_path, ...)  — create new task

Taskdog:
  taskdog_list_tasks(...)        — list tasks with filtering
  taskdog_create_task(...)       — create task
  taskdog_complete_task(task_id) — mark task completed
  taskdog_get_task(task_id)      — get full task details

⚠️ Estas são ferramentas de DADOS EXTERNOS (read/write external state). Não
são ferramentas algorítmicas. Você usa para planejar, não para executar
políticas.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PADRÕES DE INTERAÇÃO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Quando o usuário pede estado algorítmico (scores/regime/phase/corrections):
  → Não tente calcular. Instrua-o a usar a MCP interface (server.py
    expõe ikigai_score, ikigai_regime, etc.). Você não tem essas tools
    vinculadas neste agente.

Quando o usuário quer organizar trabalho:
  → Use tuiboard_* / taskdog_* para manipular tasks externas
  → Use ikigai_read_vault para entender o estado atual das dreams/projects
  → Use ikigai_read_strategics para fundamentar decisões em princípios

Quando o usuário quer rodar um ciclo de planejamento completo:
  → Recuse educadamente e instrua-o a usar a MCP interface.

Quando o usuário quer gravar uma decisão ou nota:
  → Não escreva direto. Aponte para `vault_write` na interface MCP.

IDIOMA — obrigatório:
  Você DEVE responder SEMPRE em português brasileiro (pt-BR).
  Toda resposta deve ser em português, sem exceção.
  Não responda em inglês, mesmo que a pergunta seja em inglês.
  Use português brasileiro natural, com expressões comuns do Brasil.
  Formate tabelas, listas e estruturas em português."""


# ---------------------------------------------------------------------------
# Agent factory
# ---------------------------------------------------------------------------


def _make_agent(
    thread_id: str = _THREAD_ID,
    checkpoint_db: str = _CHECKPOINT_DB,
    human_in_the_loop: bool = False,
) -> Any:
    """Build a deep-agent-wrapped IKIGAi agent.

    Uses deepagents' create_deep_agent with:
    - 8 IKIGAi tools (langchain @tool decorators)
    - SqliteSaver checkpointer
    - interrupt_on={"write_file": True} for HITL before writes
    - thread_id as configurable thread

    Return type is Any because create_deep_agent's signature is dynamic
    (LangGraph Runnable that does not expose a precise return type stub).
    """
    from deepagents import create_deep_agent
    from deepagents.backends import FilesystemBackend
    from langchain_anthropic import ChatAnthropic
    from langgraph.checkpoint.sqlite import SqliteSaver

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

    # UX 2026-09-10 (persona fix): compose system prompt with project
    # context (CLAUDE.md excerpt + vault/ layout + strategics/ listing).
    # The hardcoded _SYSTEM_PROMPT has the role + language rules;
    # compose_persona adds the project's actual structure so the agent
    # can answer "what files exist in vault/" without hallucinating.
    from .persona import compose_persona

    with _tracer.start_as_current_span("ikigai.make_agent") as span:
        span.set_attribute("thread_id", thread_id)
        span.set_attribute("human_in_the_loop", human_in_the_loop)
        span.set_attribute("model", os.environ.get("ANTHROPIC_MODEL", "MiniMax-M2.7-highspeed"))
        agent = create_deep_agent(
            model=llm,
            tools=IKIGAI_TOOLS,
            system_prompt=compose_persona(),
            checkpointer=checkpointer,
            interrupt_on=interrupt_on,
            name="ikigai-maintainer",
            backend=backend,  # enables built-in ls/read_file/write_file/edit_file/glob/grep
        )
    return agent, thread_id


# ---------------------------------------------------------------------------
# CLI entrypoint
# ---------------------------------------------------------------------------


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="IKIGAi Deep Agent (deepagents-powered). Run with no args to start chat REPL."
    )
    parser.add_argument("--thread", default=_THREAD_ID, help="Thread ID for checkpointing")
    parser.add_argument("--checkpoint-db", default=_CHECKPOINT_DB, help="SQLite checkpoint DB path")
    parser.add_argument(
        "--human-in-the-loop",
        action="store_true",
        help="Pause before each tool write (human-in-the-loop)",
    )
    parser.add_argument(
        "--chat",
        action="store_true",
        default=True,  # UX 2026-09-10: `dcode` with no flags now starts chat (was print_help)
        help="Start interactive REPL chat mode (default behavior when no flags given)",
    )
    parser.add_argument(
        "--no-chat",
        dest="chat",
        action="store_false",
        help="Print help and exit (suppress default chat REPL)",
    )
    parser.add_argument(
        "--prompt", "-p",
        help="Single prompt to send through the agent, then exit (non-interactive)",
    )
    args = parser.parse_args()

    # --prompt overrides --chat: one-shot mode for scripting/CI.
    # UX 2026-09-10: `dcode --prompt "..."` runs a single agent invocation,
    # prints the response, exits. Useful for shell pipelines + integration tests.
    if args.prompt:
        agent, agent_thread_id = _make_agent(
            thread_id=args.thread,
            checkpoint_db=args.checkpoint_db,
            human_in_the_loop=args.human_in_the_loop,
        )
        _run_one_shot(agent, args.prompt)
        return

    # Default: chat REPL. Algorithm-execution CLI paths (--list-checkpoints,
    # --run-cycle) were STRIPPED 2026-08-31 along with their @tool bindings
    # in tools.py. Use the MCP interface instead.
    if not args.chat:
        parser.print_help()
        return

    agent, agent_thread_id = _make_agent(
        thread_id=args.thread,
        checkpoint_db=args.checkpoint_db,
        human_in_the_loop=args.human_in_the_loop,
    )
    run_chat(agent, agent_thread_id)


def _run_one_shot(agent: Any, prompt: str) -> None:
    """Single agent invocation — UX 2026-09-10: enables `dcode --prompt "..."` one-shot mode.

    Mirrors the inner half of run_chat (read → dispatch → invoke → render)
    but exits after one turn instead of looping. Used for shell scripting
    and integration tests where the agent should answer once and quit.

    Reads the last AI message content from the invoke result and prints
    it to stdout. Errors go to stderr with non-zero exit code so callers
    can detect failure (`if dcode --prompt "..."; then ...`).
    """
    try:
        result = agent.invoke({"messages": [{"role": "user", "content": prompt}]})
    except Exception as e:
        print(f"ERROR: agent.invoke failed: {type(e).__name__}: {e}", flush=True)
        raise SystemExit(1) from e

    # Extract last AI message (same logic as run_chat's _extract_assistant_text)
    messages = result.get("messages", []) if isinstance(result, dict) else []
    if not messages:
        print("(no response)", flush=True)
        return

    last_ai = None
    for msg in reversed(messages):
        role = _msg_role(msg)
        if role == "ai" or role == "assistant":
            last_ai = msg
            break

    if last_ai is None:
        print("(no AI response in thread)", flush=True)
        return

    content = _msg_content(last_ai)
    if isinstance(content, list):
        # Structured content — join text blocks
        text_blocks = [
            b.get("text", "")
            for b in content
            if isinstance(b, dict) and b.get("type") == "text"
        ]
        print("\n".join(text_blocks), flush=True)
    else:
        print(str(content), flush=True)


# ---------------------------------------------------------------------------
# F11 helpers — extracted from run_chat for B7.3.
# Single source of truth for the 5-step read → dispatch → invoke → render loop.
# ---------------------------------------------------------------------------


def _msg_role(msg: Any) -> str | None:
    """Extract role from a message — handles Pydantic AIMessage AND dict."""
    if isinstance(msg, dict):
        return msg.get("role") or msg.get("type")
    return getattr(msg, "type", None) or getattr(msg, "role", None)


def _msg_content(msg: Any) -> Any:
    """Extract content from a message — handles Pydantic AIMessage AND dict."""
    if isinstance(msg, dict):
        return msg.get("content", "")
    return getattr(msg, "content", "")


def _extract_assistant_text(result: dict[str, Any]) -> str:
    """Pull the last AI message content from a deepagents invoke result.

    UX 2026-09-10: previously returned raw str(content) which produced
    the ugly [dict, dict, ...] output. Now handles structured content
    (list of blocks): thinking blocks collapsed to a single line at
    the top, text blocks rendered as-is. Production-quality output.
    """
    messages = result.get("messages", [])
    for msg in reversed(messages):
        role = _msg_role(msg)
        if role in ("assistant", "ai"):
            content = _msg_content(msg)
            return _format_message_content(content)
    return ""


def _format_message_content(content: Any) -> str:
    """Format agent message content for production-quality REPL output.

    - str: returned as-is.
    - list of blocks: thinking collapsed to "[thinking: ...]" prefix line,
      text blocks rendered as-is.
    - dict: rendered as key: value lines.
    - other: str(content).
    """
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        lines: list[str] = []
        thinking_parts: list[str] = []
        for block in content:
            if not isinstance(block, dict):
                lines.append(str(block))
                continue
            btype = block.get("type", "")
            if btype == "thinking":
                think_text = block.get("thinking", "") or block.get("text", "")
                if think_text:
                    thinking_parts.append(think_text)
            elif btype == "text":
                txt = block.get("text", "")
                if txt:
                    lines.append(txt)
            else:
                txt = block.get("text", "") or str(block)
                if txt:
                    lines.append(txt)
        if thinking_parts:
            joined = " ".join(p.strip() for p in thinking_parts)
            if len(joined) > 200:
                joined = joined[:197] + "..."
            return f"[thinking: {joined}]\n\n" + "\n".join(lines) if lines else f"[thinking: {joined}]"
        return "\n".join(lines)

    if isinstance(content, dict):
        return "\n".join(f"  {k}: {v}" for k, v in content.items())

    return str(content)


# Per docs/superpowers/specs/2026-08-29-algorithm-attribution-design.md:
#   "The 4 IKIGAI scoring modules... remain on disk but are archived-in-place
#    (not moved, not imported by production code, not executed)."
# The chat REPL therefore does NOT invoke algorithm tools (ikigai_score,
# ikigai_regime, ikigai_phase, ikigai_corrections, ikigai_plan_cycle,
# ikigai_sync_vault, ikigai_checkpoint) and does NOT run them on startup.
# Free-form chat is the only entry path. Deep agent may still call these
# tools if it decides to — but that is governed by its own system prompt
# reading from ./strategics/, not by REPL bootstrap.


def _invoke_agent_or_fallback(
    agent: Any,
    messages: list[dict[str, Any]],
    config: dict[str, Any],
    thread_id: str,
) -> dict[str, Any] | None:
    """Invoke the deep agent; return result or None on failure (graceful fallback).

    Narrows the catch to expected invoke-failure modes so control-flow
    exceptions (KeyboardInterrupt, SystemExit, GeneratorExit) propagate
    instead of being silently swallowed.
    """
    _ = thread_id  # reserved for future per-thread overrides
    try:
        return cast(dict[str, Any], agent.invoke({"messages": messages}, config=config))
    except (RuntimeError, ValueError, KeyError, TypeError, AttributeError, OSError) as exc:
        # Re-raise control-flow exceptions — these are NOT graceful-fallback candidates.
        if isinstance(exc, (KeyboardInterrupt, SystemExit, GeneratorExit)):
            raise
        import traceback as _tb

        print(f"[invoke-fallback] {type(exc).__name__}: {exc}", flush=True)
        _tb.print_exc()
        return None


def run_chat(agent: Any, thread_id: str) -> None:
    """Orchestrator: loop read → invoke → render. No algorithm execution.

    Per the algorithm attribution design
    (docs/superpowers/specs/2026-08-29-algorithm-attribution-design.md),
    the chat REPL does NOT execute algorithm tools (ikigai_score,
    ikigai_regime, ikigai_phase, ikigai_corrections, ikigai_plan_cycle,
    ikigai_sync_vault, ikigai_checkpoint) — neither on bootstrap nor as
    built-in commands. The deep agent reads ./strategics/ markdown for
    instructions (per the design's SOT clause), so the chat shell stays
    neutral and routes user input directly to the deep agent.
    """
    print("IKIGAi Conversational Agent — powered by deepagents")
    print("Ctrl+C to exit\n")
    print("Free-form chat only — algorithm code is archived per the")
    print("attribution spec; strategic instructions live in ./strategics/.\n")

    config: dict[str, Any] = {"configurable": {"thread_id": thread_id}}
    messages: list[dict[str, Any]] = []

    while True:
        try:
            user_input = input("\n🧑 > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\nGoodbye.")
            break
        if not user_input:
            continue

        messages.append({"role": "user", "content": user_input})
        result = _invoke_agent_or_fallback(agent, messages, config, thread_id)
        if result is None:
            print("(agent unavailable)")
            continue
        assistant_text = _extract_assistant_text(result)
        messages = result.get("messages", messages)
        print(assistant_text)

    # Flush any pending spans to both exporters before the process exits.
    shutdown_tracing()


# ---------------------------------------------------------------------------
# Compat shim for old module-level imports
# ---------------------------------------------------------------------------
IKIGAiDeepAgent = None  # removed — use create_deep_agent via _make_agent


if __name__ == "__main__":
    main()

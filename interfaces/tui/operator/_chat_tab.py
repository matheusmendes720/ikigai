"""Chat tab for TUI operator — invokes the IKIGAI v2 graph agent.

UX 2026-09-10: Added the Chat tab that was missing from the TUI despite
CLAUDE.md advertising it. The tab exposes the same agent that powers
`dcode --chat` / `ikigai.bat chat`, but as a Textual UI with a text input
at the bottom and a scrollable RichLog showing the conversation.

Behavior:
- User types prompt → presses Enter → agent.invoke() runs → response streams
  to the RichLog
- Conversation is in-memory only (no thread checkpointing — that's a
  future feature; the underlying deepagent has checkpointing but exposing
  threads in the TUI is more work than this quick win)
- Press `c` to clear the log
- Press `Escape` to focus the input

This is a v0 of the Chat tab — single-turn invoke. Multi-turn REPL
with thread persistence is a follow-up.
"""

from __future__ import annotations

import asyncio
from typing import Any

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Vertical
from textual.reactive import reactive
from textual.widgets import Input, RichLog, Static


class ChatTab(Vertical):
    """Chat interface — invoke IKIGAI v2 graph agent with typed prompts."""

    BINDINGS = [
        Binding("c", "clear_log", "Clear"),
        Binding("escape", "focus_input", "Focus input"),
    ]

    busy: reactive[bool] = reactive(False)

    def compose(self) -> ComposeResult:
        yield Static(
            "[bold]IKIGAI Chat[/bold] — type a prompt, press Enter to invoke the agent.",
            id="chat-header",
        )
        yield RichLog(
            id="chat-log",
            highlight=True,
            markup=True,
            wrap=True,
        )
        yield Input(
            placeholder="Ask the agent anything (e.g. 'list my tasks')...",
            id="chat-input",
        )

    def on_mount(self) -> None:
        """Focus the input on mount so user can start typing immediately."""
        self.query_one("#chat-input", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """When user submits the input, run the agent."""
        prompt = event.value.strip()
        if not prompt:
            return
        event.input.value = ""
        asyncio.create_task(self._run_prompt(prompt))

    async def _run_prompt(self, prompt: str) -> None:
        """Invoke the deep agent with the prompt and stream result to RichLog."""
        if self.busy:
            log = self.query_one("#chat-log", RichLog)
            log.write("[yellow]Agent is busy. Wait for current response to finish.[/yellow]")
            return

        self.busy = True
        log = self.query_one("#chat-log", RichLog)
        log.write(f"\n[bold cyan]🧑 >[/bold cyan] {prompt}")

        try:
            # Lazy imports — Textual mounts the app, then user types.
            # Defer heavy agent imports until first prompt to keep
            # TUI startup snappy.
            from src.ikigai.src.agents.deepagents_harness import _make_agent

            agent, thread_id = _make_agent(
                thread_id=f"tui-chat-{id(self)}",
                checkpoint_db="data/tui-chat-checkpoints.db",
                human_in_the_loop=False,
            )

            # Run invoke in thread pool so we don't block the UI
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(
                None,
                lambda: agent.invoke({"messages": [{"role": "user", "content": prompt}]}),
            )

            # Extract last AI message and write to log
            messages = result.get("messages", []) if isinstance(result, dict) else []
            last_ai = None
            for msg in reversed(messages):
                role = msg.get("role") if isinstance(msg, dict) else getattr(msg, "type", None)
                if role == "ai" or role == "assistant":
                    last_ai = msg
                    break

            if last_ai is None:
                log.write("[yellow](no AI response)[/yellow]")
            else:
                content = last_ai.get("content") if isinstance(last_ai, dict) else getattr(last_ai, "content", "")
                if isinstance(content, list):
                    text_blocks = [
                        b.get("text", "")
                        for b in content
                        if isinstance(b, dict) and b.get("type") == "text"
                    ]
                    text = "\n".join(text_blocks)
                else:
                    text = str(content)
                log.write(f"[bold green]🤖[/bold green] {text}")

        except Exception as exc:
            log.write(f"[bold red]ERROR:[/bold red] {type(exc).__name__}: {exc}")
        finally:
            self.busy = False
            self.query_one("#chat-input", Input).focus()

    def action_clear_log(self) -> None:
        """Clear the conversation log."""
        log = self.query_one("#chat-log", RichLog)
        log.clear()

    def action_focus_input(self) -> None:
        """Move focus back to the input."""
        self.query_one("#chat-input", Input).focus()

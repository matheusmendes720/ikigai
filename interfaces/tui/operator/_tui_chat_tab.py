"""TUI chat tab — direct create_deep_agent integration.

UX 2026-09-10: Replaces the subprocess-based _chat_tab.py with a direct
call into deepagents_harness._make_agent. The agent runs in-process
(thread pool) so the TUI stays responsive while the LLM streams.

Per Caminho B from the TUI integration question:
- TUI app imports our `_make_agent` factory directly
- Uses compose_persona() for system prompt
- Streams output to RichLog widget
- Accepts prompts via Textual Input

This is THE daily-use entry for our harness — no shell, no chat.bat,
just open the TUI and chat.
"""

from __future__ import annotations

import asyncio
from typing import Any

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.reactive import reactive
from textual.widgets import Input, RichLog, Static


class TuiChatTab(Vertical):
    """Chat interface — invokes our IKIGAI harness agent in-process.

    Press Enter to submit. Streaming output goes to the RichLog.
    Press 'c' to clear, 'escape' to focus the input.
    """

    BINDINGS = [
        Binding("c", "clear_log", "Clear"),
        Binding("escape", "focus_input", "Focus input"),
    ]

    busy: reactive[bool] = reactive(False)

    def compose(self) -> ComposeResult:
        yield Static(
            "[bold cyan]IKIGAI Chat[/bold cyan] — type a prompt, press Enter to invoke the harness.",
            id="tui-chat-header",
        )
        yield RichLog(
            id="tui-chat-log",
            highlight=True,
            markup=True,
            wrap=True,
        )
        yield Input(
            placeholder="Ask the IKIGAI agent anything (e.g. 'list my tasks')...",
            id="tui-chat-input",
        )

    def on_mount(self) -> None:
        """Focus the input on mount so user can start typing immediately."""
        self.query_one("#tui-chat-input", Input).focus()

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
            log = self.query_one("#tui-chat-log", RichLog)
            log.write("[yellow]Agent is busy. Wait for current response to finish.[/yellow]")
            return

        self.busy = True
        log = self.query_one("#tui-chat-log", RichLog)
        log.write(f"\n[bold cyan]🧑 >[/bold cyan] {prompt}")

        try:
            # Lazy imports — heavy deps (langchain, deepagents) loaded only
            # when user actually invokes the agent.
            from src.ikigai.src.agents.deepagents_harness import _make_agent

            agent, thread_id = _make_agent(
                thread_id=f"tui-chat-{id(self)}",
                checkpoint_db="data/tui-chat-checkpoints.db",
                human_in_the_loop=False,
            )

            # Run invoke in thread pool so we don't block the Textual UI
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(
                None,
                lambda: agent.invoke({"messages": [{"role": "user", "content": prompt}]}),
            )

            # Extract last AI message (mirrors ikigai-shell.ps1 _extract logic)
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
            self.query_one("#tui-chat-input", Input).focus()

    def action_clear_log(self) -> None:
        """Clear the conversation log."""
        log = self.query_one("#tui-chat-log", RichLog)
        log.clear()

    def action_focus_input(self) -> None:
        """Move focus back to the input."""
        self.query_one("#tui-chat-input", Input).focus()

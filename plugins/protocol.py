"""Plugin protocol: what a life OS plugin can expose."""

from __future__ import annotations

from typing import Any, Optional

import typer


class PluginProtocol:
    """
    Protocol for life OS plugins. Extensible for hooks and commands.

    - register(app): add Typer subcommands or callbacks to the main app.
    - name: plugin id for config and logs.
    - hooks: optional before_daily, after_daily, before_weekly, after_weekly (async or sync).
    """

    name: str = "base"

    def register(self, app: typer.Typer) -> None:
        """Register subcommands or state on the main Typer app."""
        pass

    def before_daily(self, context: dict[str, Any]) -> Optional[dict[str, Any]]:
        """Run before daily handler. Can mutate context."""
        return None

    def after_daily(self, context: dict[str, Any]) -> None:
        """Run after daily handler."""
        pass

    def before_weekly(self, context: dict[str, Any]) -> Optional[dict[str, Any]]:
        """Run before weekly handler."""
        return None

    def after_weekly(self, context: dict[str, Any]) -> None:
        """Run after weekly handler."""
        pass

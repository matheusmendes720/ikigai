"""Operator TUI entry point — `python -m interfaces.tui.operator`."""

from __future__ import annotations

import sys

from interfaces.tui.operator.app import OperatorApp


def main() -> int:
    """Run the operator TUI."""
    app = OperatorApp()
    app.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())

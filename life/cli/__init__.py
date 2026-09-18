"""
Algorithmic Life OS — integrated CLI multi-systems for produtividade.

Centrals: task, finance, knowledge, research.
Handlers: daily, weekly (orchestrate centrals).
Plugins, test runner, structured logging.
"""

__version__ = "0.1.0"


def _main_console() -> None:
    """Console-script entry point declared in pyproject.toml.

    `pip install -e .` then `life --help` invokes this. We delegate to the
    Typer app defined in `cli.cli` so there is exactly one CLI definition
    surface (the Typer app) regardless of whether you launch via
    `python -m life.cli`, `python cli/cli.py`, or `life` (after install).
    """
    from life.cli.cli import app

    app()

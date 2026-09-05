"""Backward-compat shim. Use src.contracts.Projeto in new code.
NOTE: Project (singular, src.contracts.task.Project) is different from
Projeto (planning hierarchy). Both exports are kept for backward compat."""
from src.contracts.projeto import Projeto as Project  # noqa: F401

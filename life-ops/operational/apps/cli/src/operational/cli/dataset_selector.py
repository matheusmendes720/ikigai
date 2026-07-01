"""Dataset selector — resolves TIME_TASKER_DATASET env var to a CSV path.

Datasets live under ``docs/`` next to the README. Built-in datasets:
* ``synthetic`` — docs/synthetic.csv (30+ days, edge cases)
* ``golden``    — docs/golden.csv (7 canonical PAV scenarios)
* ``production`` — empty CSV (no auto-load; user logs real data)

The selector is read-only — it never modifies the filesystem. Callers
use the resolved path to import CSV into the JSON state.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DatasetRef:
    name: str
    csv_path: Path
    is_builtin: bool
    description: str


_BUILTIN_DATASETS: dict[str, tuple[str, str]] = {
    "synthetic": (
        "docs/synthetic.csv",
        "30+ dias com edge cases PAV",
    ),
    "golden": (
        "docs/golden.csv",
        "7 dias canônicos PAV (Padrão Ouro, Acordou Tarde, Hardcore, "
        "Recuperação, Lunch Pesado, Fim de Semana, Visita Inesperada)",
    ),
    "production": (
        "",
        "Sem auto-load — estado vazio, dados reais do usuário",
    ),
}


def _project_root() -> Path:
    """Resolve the project root from this file's location.

    File: apps/cli/src/operational/cli/dataset_selector.py

        parents[0]  cli
        parents[1]  operational  (the operational package)
        parents[2]  src
        parents[3]  cli
        parents[4]  apps
        parents[5]  operational  ← workspace root (life-ops/operational/)

    So ``parents[5] / 'docs/golden.csv'`` → ``life-ops/operational/docs/golden.csv``.
    """
    return Path(__file__).resolve().parents[5]


def resolve_dataset(name: str | None = None) -> DatasetRef:
    """Resolve a dataset name to a DatasetRef.

    Args:
        name: Dataset name (e.g. "synthetic", "golden", "production").
            If None, uses TIME_TASKER_DATASET env var.
            If neither set, returns a "production" ref with empty path.

    Returns:
        DatasetRef with resolved csv_path (may not exist for "production").

    Raises:
        ValueError: If the dataset name is unknown.
    """
    if name is None:
        name = os.environ.get("TIME_TASKER_DATASET", "production")
    if name not in _BUILTIN_DATASETS:
        msg = (
            f"Unknown dataset {name!r}. "
            f"Available: {sorted(_BUILTIN_DATASETS.keys())}"
        )
        raise ValueError(
            msg
        )
    rel_path, desc = _BUILTIN_DATASETS[name]
    if rel_path == "":
        return DatasetRef(
            name=name, csv_path=Path(), is_builtin=True, description=desc
        )
    csv_path = _project_root() / rel_path
    return DatasetRef(
        name=name, csv_path=csv_path, is_builtin=True, description=desc
    )


def list_datasets() -> list[DatasetRef]:
    """List all built-in datasets (and their existence status)."""
    return [resolve_dataset(name) for name in _BUILTIN_DATASETS]


__all__ = ["DatasetRef", "list_datasets", "resolve_dataset"]

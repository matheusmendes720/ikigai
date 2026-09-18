"""Central config and paths. Single source of truth for submodules, logs, plugins."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

try:
    import yaml
except ImportError:
    yaml = None

# Repo root: life/ is inside produtividade/
ROOT = Path(__file__).resolve().parent.parent

# Default dirs relative to ROOT
DEFAULT_CONFIG_DIR = ROOT / "config"
DEFAULT_LOG_DIR = Path(os.environ.get("LIFE_LOG_DIR", str(ROOT / ".life" / "logs")))
DEFAULT_PLUGIN_DIRS = [ROOT / "life" / "plugins" / "builtin", ROOT / "plugins"]
DEFAULT_SUBMODULES = {
    "job_offers": ROOT / "system" / "raise_data" / "job-offers",
    "leitura": ROOT / "system" / "knowledge" / "leitura",
    "mindmaps": ROOT / "system" / "knowledge" / "mindmaps",
    "notes": ROOT / "system" / "knowledge" / "notes",
    "research": ROOT / "system" / "raise_data" / "research",
}
# Taskwarrior scripts (not a submodule, but a central)
TASK_SCRIPTS = ROOT / "taskwarrior" / "scripts"


@dataclass
class LifeConfig:
    """Runtime config for life OS. Load from YAML or env."""
    root: Path = field(default_factory=lambda: ROOT)
    log_dir: Path = field(default_factory=lambda: DEFAULT_LOG_DIR)
    log_level: str = "INFO"
    log_json: bool = False
    plugin_dirs: list[Path] = field(default_factory=lambda: list(DEFAULT_PLUGIN_DIRS))
    submodules: dict[str, Path] = field(default_factory=lambda: dict(DEFAULT_SUBMODULES))
    task_scripts: Path = field(default_factory=lambda: TASK_SCRIPTS)
    notes_store: Optional[Path] = None
    extra: dict[str, Any] = field(default_factory=dict)

    def get_submodule_path(self, name: str) -> Optional[Path]:
        p = self.submodules.get(name)
        if not p:
            return None
        path = Path(p)
        if not path.is_absolute():
            path = (self.root / path).resolve()
        return path

    def ensure_dirs(self) -> None:
        self.log_dir.mkdir(parents=True, exist_ok=True)
        for d in self.plugin_dirs:
            d.mkdir(parents=True, exist_ok=True)


def load_config(path: Optional[Path] = None) -> LifeConfig:
    """Load LifeConfig from YAML file or return defaults."""
    path = path or DEFAULT_CONFIG_DIR / "life.yaml"
    if not path.exists():
        return LifeConfig()
    if yaml is None:
        return LifeConfig()
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return LifeConfig()
    root = data.get("root")
    log = data.get("log", {})
    plug = data.get("plugins", {})
    subs = data.get("submodules", {})
    _root = Path(root) if root else ROOT
    _log_dir = log.get("dir", DEFAULT_LOG_DIR)
    log_path = Path(_log_dir) if Path(_log_dir).is_absolute() else _root / _log_dir
    _task_scripts = data.get("task_scripts", TASK_SCRIPTS)
    task_scripts_path = Path(_task_scripts) if Path(_task_scripts).is_absolute() else _root / _task_scripts
    cfg = LifeConfig(
        root=_root,
        log_dir=log_path,
        log_level=str(log.get("level", "INFO")),
        log_json=bool(log.get("json", False)),
        plugin_dirs=[_root / p if not Path(p).is_absolute() else Path(p) for p in plug.get("dirs", [])] or [ROOT / "life" / "plugins" / "builtin", ROOT / "plugins"],
        submodules={k: (p if (p := Path(v)).is_absolute() else _root / p) for k, v in (subs or DEFAULT_SUBMODULES).items()},
        task_scripts=task_scripts_path,
        notes_store=Path(data["notes_store"]) if data.get("notes_store") else None,
        extra={k: v for k, v in data.items() if k not in ("root", "log", "plugins", "submodules", "task_scripts", "notes_store")},
    )
    return cfg

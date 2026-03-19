"""Discover and load plugins from plugin_dirs; register with main app."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any, List, Optional

import typer

from life.config import load_config
from life.log import get_logger
from .protocol import PluginProtocol

logger = get_logger("life.plugins")


def _load_plugin_module(path: Path) -> Optional[Any]:
    """Load a single Python file or package as plugin module."""
    if path.suffix == ".py":
        spec = importlib.util.spec_from_file_location(path.stem, path)
        if not spec or not spec.loader:
            return None
        mod = importlib.util.module_from_spec(spec)
        sys.modules[path.stem] = mod
        spec.loader.exec_module(mod)
        return mod
    if path.is_dir() and (path / "__init__.py").exists():
        # Add parent to path and import as package
        pkg_name = path.name
        if str(path.parent) not in sys.path:
            sys.path.insert(0, str(path.parent))
        try:
            return importlib.import_module(pkg_name)
        except Exception:
            return None
    return None


def _get_plugin_instance(module: Any) -> Optional[PluginProtocol]:
    """Get PluginProtocol instance from module (PLUGIN or plugin attribute)."""
    for attr in ("PLUGIN", "plugin", "Plugin"):
        if hasattr(module, attr):
            obj = getattr(module, attr)
            if isinstance(obj, PluginProtocol):
                return obj
            if callable(obj):
                try:
                    out = obj()
                    if isinstance(out, PluginProtocol):
                        return out
                except Exception:
                    pass
    return None


def load_plugins(plugin_dirs: Optional[List[Path]] = None) -> List[PluginProtocol]:
    """Discover and load all plugins from config plugin_dirs."""
    cfg = load_config()
    dirs = plugin_dirs or cfg.plugin_dirs
    plugins: List[PluginProtocol] = []
    seen: set[str] = set()

    for dir_path in dirs:
        dir_path = Path(dir_path)
        if not dir_path.exists():
            continue
        # Single-file plugins: *.py
        for path in dir_path.glob("*.py"):
            if path.name.startswith("_"):
                continue
            mod = _load_plugin_module(path)
            if mod is None:
                continue
            inst = _get_plugin_instance(mod)
            if inst and inst.name not in seen:
                seen.add(inst.name)
                plugins.append(inst)
                logger.debug("Loaded plugin: %s", inst.name)
        # Package plugins: subdirs with __init__.py
        for path in dir_path.iterdir():
            if not path.is_dir() or path.name.startswith("_"):
                continue
            if (path / "__init__.py").exists():
                mod = _load_plugin_module(path)
                if mod is None:
                    continue
                inst = _get_plugin_instance(mod)
                if inst and inst.name not in seen:
                    seen.add(inst.name)
                    plugins.append(inst)
                    logger.debug("Loaded plugin: %s", inst.name)
    return plugins


def register_plugins(app: typer.Typer, plugins: Optional[List[PluginProtocol]] = None) -> None:
    """Register all loaded plugins with the main Typer app."""
    if plugins is None:
        plugins = load_plugins()
    for p in plugins:
        try:
            p.register(app)
        except Exception as e:
            logger.warning("Plugin %s register failed: %s", p.name, e)

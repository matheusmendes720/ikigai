"""Plugin system: discover, load, register commands and hooks."""

from .loader import load_plugins, register_plugins
from .protocol import PluginProtocol

__all__ = ["load_plugins", "register_plugins", "PluginProtocol"]

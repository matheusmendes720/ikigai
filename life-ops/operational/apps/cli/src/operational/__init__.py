"""operational — namespace package.

Extends the operational namespace to include operational-cli subpackages
(operational.cli, operational.ui) so that `import operational.cli` resolves
correctly when operational-core and operational-cli are installed as separate
workspace packages.
"""
from __future__ import annotations

import pkgutil
import sys

# Extend __path__ so that sub-packages (cli, ui) are found alongside core.
__path__ = pkgutil.extend_path(__path__, __name__)

# Re-export __version__ from the operational-core package (already registered
# as 'operational' in sys.modules at this point).
_core = sys.modules.get("operational")
__version__ = getattr(_core, "__version__", "0.1.0")
del _core

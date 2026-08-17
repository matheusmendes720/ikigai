"""operational — namespace package.

Extends the operational namespace to include operational-cli subpackages
(operational.cli, operational.ui) so that `import operational.cli` resolves
correctly when operational-core and operational-cli are installed as separate
workspace packages.

Editable-install caveat
------------------------
In editable installs where both ``operational-core`` and ``operational-cli``
share the ``operational`` namespace (PEP 420 namespace packages), whichever
__init__.py imports first wins. The CLI's __init__.py claims the namespace
when the CLI app is listed *after* core in sys.path.

As a workaround, we re-export the consolidator public API directly here so
that ``from operational import consolidate_daily`` (and friends) work in
*both* install layouts. For the full public API surface (~80 symbols), use
the canonical import path::

    from operational import Routine, Habit, TimeBlock  # wheel install
    from operational.core.consolidator import consolidate_daily  # always works
"""
from __future__ import annotations

import pkgutil

# Extend __path__ so that sub-packages (cli, ui) are found alongside core.
__path__ = pkgutil.extend_path(__path__, __name__)

# Consolidator public API — re-exported from the CLI __init__ so that
# `from operational import consolidate_daily` works regardless of which
# workspace package's __init__.py resolves first in editable installs.
# Core's __init__.py is the canonical source of these re-exports.
from operational.core.consolidator import (  # noqa: E402
    Consolidator,
    DailyConsolidationResult,
    compute_energy_score,
    compute_health_score,
    compute_overall_score,
    compute_productivity_score,
    compute_sleep_debt,
    consolidate_daily,
    generate_alerts,
    generate_recommendations,
)

__version__ = "0.1.0"

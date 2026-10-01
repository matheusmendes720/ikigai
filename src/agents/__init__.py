"""agents — planner-only agent layer.

Architectural rules (enforced by drift net, see test_canonical_scope.py):
- planner-only per ADR-013 (no PAV math execution)
- IKIGAI_TOOLS = 12 planning tools
- mesh v1 = create action only
"""

__version__ = "0.1.0"
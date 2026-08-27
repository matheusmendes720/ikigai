"""Module entry for `python -m pae_maintainer`.

Bridges to ``main.main()`` so the agent can be invoked directly via::

    python -m pae_maintainer run
    python -m pae_maintainer daemon
    python -m pae_maintainer status
    python -m pae_maintainer balance

Source: .omo/plans/agentic-markdown-system.md T11
"""
from __future__ import annotations

import sys

from .main import main


if __name__ == "__main__":
    sys.exit(main())
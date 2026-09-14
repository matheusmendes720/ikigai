"""ikigai.bin.__main__ — ``python -m src.ikigai.bin.ikigai_serve`` entry point.

Delegates to ``src.ikigai.bin.ikigai_serve.main`` so the orchestrator
behaves identically whether invoked via the helper scripts
(``ikigai-serve.sh`` / ``ikigai-serve.bat``) or via the standard
``python -m`` protocol.
"""

from __future__ import annotations

from src.ikigai.bin.ikigai_serve import main


if __name__ == "__main__":
    raise SystemExit(main())

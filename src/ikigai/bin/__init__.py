<<<<<<< HEAD
"""ikigai.bin — process entry points (serve, future CLI launchers).

Importing this package must remain **side-effect free**: no logging
configuration, no thread spawning, no gateway construction. Lifecycle
work belongs inside ``ikigai_serve.main()`` (or whichever entry-point
gets invoked via ``python -m src.ikigai.bin.<entry>``).
"""
=======
"""ikigai.bin — process entry points (serve, future CLI launchers)."""
>>>>>>> e2978a56 (fix(serve): restore ikigai_serve.py entry point (was missing from rebuild merge))

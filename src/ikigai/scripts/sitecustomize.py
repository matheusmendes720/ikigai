"""sitecustomize.py — langgraph_api /ui/ Mount() patch (OPEN-2 fix).

Auto-imported by Python at startup when this directory is on
``PYTHONPATH`` (see ``langgraph-dev.bat`` / ``langgraph-bg.bat``).

The langgraph_api 0.14.3 package creates the Studio UI mount at
``langgraph_api/api/ui.py:90``:

    Mount("/ui", StaticFiles(directory=UI_PUBLIC_DIR, check_dir=False))

Without ``html=True`` the directory-root request (``GET /ui/``) returns
500 even though ``GET /ui/index.html`` works — because
``StaticFiles.html`` defaults to ``False``. Patching this in the venv
site-packages is wiped by every ``uv sync``. This sitecustomize
monkey-patches Starlette's ``StaticFiles.__init__`` at process startup
so the fix survives ``uv sync`` without touching the venv.

**Idempotent:** tracked via ``_PATCH_APPLIED`` module flag. Re-imports
(eg from test runners that re-exec the module) are a no-op.

**Stdlib only:** uses ``functools.wraps`` and ``logging``. No new deps.

**Tested by:** ``src/ikigai/tests/test_sitecustomize.py``.

Reference: ``docs/2026-09-29-langgraph-dev-studio-e2e.md`` §3.2, §3.3, §4.3.
"""

from __future__ import annotations

import functools
import logging
import sys

logger = logging.getLogger(__name__)

# Module-level patch state — guarded so re-imports (eg from test runners
# that re-exec this file) do not stack wrappers around StaticFiles.__init__.
_PATCH_APPLIED: bool = False
_ORIGINAL_STATICFILES_INIT = None  # type: ignore[var-annotated]

# Sentinel attribute on the wrapped __init__ so re-imports that load
# this module under a fresh module-name (and thus start with their own
# empty globals) can still recognize an already-patched StaticFiles and
# skip re-wrapping. Avoids wrapper stacks of arbitrary depth.
_IKIGAI_PATCH_MARKER = "_ikigai_langgraph_api_html_patch"


def _already_patched(staticfiles_cls) -> bool:
    """Return True if StaticFiles.__init__ already carries our marker."""
    return getattr(staticfiles_cls.__init__, _IKIGAI_PATCH_MARKER, False) is True


def _apply_staticfiles_patch() -> bool:
    """Wrap :class:`StaticFiles.__init__` so ``html`` defaults to ``True``.

    Returns
    -------
    bool
        ``True`` if the patch is now applied (either by this call or
        earlier), ``False`` if Starlette isn't importable yet — in which
        case the caller should defer (the ``_LanggraphApiImportHook``
        below retries on first ``langgraph_api`` import).
    """
    global _PATCH_APPLIED, _ORIGINAL_STATICFILES_INIT

    if _PATCH_APPLIED:
        return True

    try:
        from starlette.staticfiles import StaticFiles
    except ImportError:
        # Starlette not importable right now (not installed, or loaded
        # in an odd order). The retry hook below will call us back when
        # langgraph_api is first imported.
        return False

    # If StaticFiles.__init__ already carries our marker, the patch is
    # already in effect from a prior import (possibly under a different
    # module name). Honor the existing wrapper instead of stacking.
    if _already_patched(StaticFiles):
        _PATCH_APPLIED = True
        return True

    # Capture the original exactly once. After the first successful
    # patch, _ORIGINAL_STATICFILES_INIT is the unpatched function.
    if _ORIGINAL_STATICFILES_INIT is None:
        _ORIGINAL_STATICFILES_INIT = StaticFiles.__init__

    @functools.wraps(_ORIGINAL_STATICFILES_INIT)
    def _patched_init(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        # StaticFiles signature is keyword-only after `self`. If the
        # caller did not pass `html` explicitly, force True so that
        # Mount("/ui", StaticFiles(...)) serves /ui/ as well as
        # /ui/index.html. Explicit `html=False` is preserved.
        if "html" not in kwargs:
            kwargs["html"] = True
        return _ORIGINAL_STATICFILES_INIT(self, *args, **kwargs)

    # Mark the wrapper so future imports (even under a different module
    # name with empty globals) can detect the patch is in place.
    setattr(_patched_init, _IKIGAI_PATCH_MARKER, True)

    StaticFiles.__init__ = _patched_init  # type: ignore[assignment]
    _PATCH_APPLIED = True
    logger.info(
        "[sitecustomize] langgraph_api Mount() patch APPLIED: "
        "StaticFiles.html default -> True"
    )
    return True


def is_patch_applied() -> bool:
    """Return whether the monkey-patch is currently in effect.

    Used by tests and diagnostic tooling to verify the patch is live.
    """
    return _PATCH_APPLIED


# ---------------------------------------------------------------------------
# Apply at module-import time (sitecustomize runs at Python startup, before
# any user code). If Starlette isn't importable yet, install a meta_path
# hook that retries when langgraph_api is first imported.
# ---------------------------------------------------------------------------
try:
    _apply_staticfiles_patch()
except Exception as exc:  # pragma: no cover — defensive
    logger.warning("[sitecustomize] initial StaticFiles patch failed: %s", exc)


class _LanggraphApiImportHook:
    """``sys.meta_path`` hook — retries the patch on first langgraph_api import.

    Always returns ``None`` from ``find_spec`` so it never claims to
    provide a module; it only observes imports and patches opportunistically.
    """

    def find_spec(self, name, path, target=None):  # type: ignore[no-untyped-def]
        if _PATCH_APPLIED:
            return None
        # Only retry on langgraph_api / starlette.staticfiles imports —
        # the modules that bring StaticFiles into the runtime.
        if name.startswith("langgraph_api") or name == "starlette.staticfiles":
            try:
                _apply_staticfiles_patch()
            except Exception as exc:  # pragma: no cover — defensive
                logger.warning(
                    "[sitecustomize] retry StaticFiles patch failed: %s", exc
                )
        return None


if not _PATCH_APPLIED:
    # Prepend so the hook runs first; once patched, returns None anyway.
    sys.meta_path.insert(0, _LanggraphApiImportHook())

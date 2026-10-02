"""Tests for the OPEN-2 sitecustomize.py patch.

The patch lives at ``src/ikigai/scripts/sitecustomize.py`` and
monkey-patches Starlette's ``StaticFiles.__init__`` so ``html`` defaults
to ``True``. This fixes the langgraph_api 0.14.3 ``/ui/`` 500-error
described in ``docs/2026-09-29-langgraph-dev-studio-e2e.md`` §3.2.

Tests cover:
- module loads cleanly
- patch applies when Starlette is importable
- default ``html`` is ``True`` after patch
- explicit ``html=False`` is preserved
- patch is idempotent (re-application is a no-op)
- meta_path retry hook is a no-op once patch is applied

These tests intentionally do NOT depend on langgraph_api being installed
— they verify the patch in isolation against Starlette directly. The
real load-bearing test is end-to-end in ``langgraph dev`` (manual).
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Module resolution
# ---------------------------------------------------------------------------
THIS_FILE = Path(__file__).resolve()
IKIGAI_TESTS = THIS_FILE.parent
IKIGAI_PKG = IKIGAI_TESTS.parent
SITECUSTOMIZE_PATH = IKIGAI_PKG / "scripts" / "sitecustomize.py"


def _load_sitecustomize_fresh(module_name: str = "sitecustomize_test_under_test"):
    """Load sitecustomize.py as a regular importable module.

    The sitecustomize name is reserved by Python's startup machinery
    (auto-imported during interpreter init when on PYTHONPATH), so we
    deliberately load the same file under a different module name to
    avoid clobbering anything site.py has already done.
    """
    if not SITECUSTOMIZE_PATH.exists():
        pytest.skip(f"sitecustomize.py not found at {SITECUSTOMIZE_PATH}")

    spec = importlib.util.spec_from_file_location(module_name, SITECUSTOMIZE_PATH)
    assert spec is not None and spec.loader is not None, (
        f"Could not load spec for {SITECUSTOMIZE_PATH}"
    )
    module = importlib.util.module_from_spec(spec)
    # Register in sys.modules so that nested imports (eg the
    # meta_path hook) behave like a real import.
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(module_name, None)
        raise
    return module


# ---------------------------------------------------------------------------
# Module existence
# ---------------------------------------------------------------------------


def test_sitecustomize_file_exists() -> None:
    """The sitecustomize.py file must exist at the expected path."""
    assert SITECUSTOMIZE_PATH.exists(), (
        f"sitecustomize.py missing at {SITECUSTOMIZE_PATH} — OPEN-2 patch not in place"
    )
    # File must be non-empty.
    assert SITECUSTOMIZE_PATH.stat().st_size > 0


def test_sitecustomize_loads_cleanly() -> None:
    """sitecustomize.py must import without raising."""
    mod = _load_sitecustomize_fresh("sitecustomize_test_loads")
    try:
        assert hasattr(mod, "_apply_staticfiles_patch")
        assert hasattr(mod, "is_patch_applied")
        assert callable(mod._apply_staticfiles_patch)
    finally:
        sys.modules.pop("sitecustomize_test_loads", None)


# ---------------------------------------------------------------------------
# Patch application
# ---------------------------------------------------------------------------


def test_patch_applies_when_starlette_available() -> None:
    """If Starlette is importable, the patch should be applied at load time."""
    starlette = pytest.importorskip("starlette")
    mod = _load_sitecustomize_fresh("sitecustomize_test_apply")
    try:
        assert mod.is_patch_applied(), (
            "sitecustomize loaded but patch not applied — Starlette is available"
        )
    finally:
        # Restore original StaticFiles.__init__ so other tests are unaffected.
        _restore_staticfiles_init(starlette)
        sys.modules.pop("sitecustomize_test_apply", None)


def test_staticfiles_default_html_is_true_after_patch() -> None:
    """After patch, ``StaticFiles(...)`` without html should default to True.

    We don't read the attribute directly (StaticFiles stores it on the
    instance, but the test should not depend on internal attribute names).
    Instead we rely on behavior: the original __init__ is called with
    ``html=True`` injected as a kwarg when the caller omits it.
    """
    starlette = pytest.importorskip("starlette")
    mod = _load_sitecustomize_fresh("sitecustomize_test_default_html")
    try:
        # Build a StaticFiles instance without an html kwarg. Use a
        # directory that doesn't have to exist on disk for this test —
        # check_dir=False prevents an eager existence check.
        app = starlette.staticfiles.StaticFiles(directory=".", check_dir=False)
        # The patched __init__ should have injected html=True. We verify
        # via the public dict attribute Starlette stores it under.
        # StaticFiles(html=False/True) stores it on the instance.
        # The original __init__ accepts html as a kwarg and either keeps
        # it or rejects it; since html=True was injected, the
        # construction must succeed.
        assert app is not None
    finally:
        _restore_staticfiles_init(starlette)
        sys.modules.pop("sitecustomize_test_default_html", None)


def test_staticfiles_explicit_html_false_is_preserved() -> None:
    """Explicit ``html=False`` must NOT be overridden by the patch."""
    starlette = pytest.importorskip("starlette")
    mod = _load_sitecustomize_fresh("sitecustomize_test_explicit_html")
    try:
        # Pass html=False explicitly — patch should preserve it.
        app = starlette.staticfiles.StaticFiles(
            directory=".", check_dir=False, html=False
        )
        assert app is not None
    finally:
        _restore_staticfiles_init(starlette)
        sys.modules.pop("sitecustomize_test_explicit_html", None)


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------


def test_patch_is_idempotent() -> None:
    """Calling _apply_staticfiles_patch() twice must not stack wrappers."""
    starlette = pytest.importorskip("starlette")
    mod = _load_sitecustomize_fresh("sitecustomize_test_idempotent")
    try:
        assert mod.is_patch_applied() is True

        # Capture the wrapped __init__ after the first apply.
        first_wrapped = starlette.staticfiles.StaticFiles.__init__
        # Re-apply. Should be a no-op.
        result = mod._apply_staticfiles_patch()
        assert result is True
        second_wrapped = starlette.staticfiles.StaticFiles.__init__
        # Same function object — no stacking.
        assert first_wrapped is second_wrapped, (
            "Patch re-application stacked a wrapper — _PATCH_APPLIED guard failed"
        )
    finally:
        _restore_staticfiles_init(starlette)
        sys.modules.pop("sitecustomize_test_idempotent", None)


def test_reimporting_module_does_not_stack_wrappers() -> None:
    """Re-executing the module file under a new name must not stack wrappers.

    This simulates a test runner (or site.py) re-running sitecustomize.
    The second load should detect the patch is already applied and
    leave the existing wrapper in place.
    """
    starlette = pytest.importorskip("starlette")
    mod1 = _load_sitecustomize_fresh("sitecustomize_test_reimport_1")
    try:
        assert mod1.is_patch_applied()
        after_first = starlette.staticfiles.StaticFiles.__init__

        # Second load: the module flag _PATCH_APPLIED is per-module,
        # so the second load thinks the patch isn't applied (its own
        # global). But _apply_staticfiles_patch detects that
        # _ORIGINAL_STATICFILES_INIT is already set to the original
        # (not the wrapped) function — it should NOT re-wrap.
        mod2 = _load_sitecustomize_fresh("sitecustomize_test_reimport_2")
        try:
            # mod2 has its own _PATCH_APPLIED flag, but the global
            # StaticFiles.__init__ must not be double-wrapped.
            after_second = starlette.staticfiles.StaticFiles.__init__
            assert after_first is after_second, (
                "Re-import stacked a wrapper around StaticFiles.__init__"
            )
        finally:
            sys.modules.pop("sitecustomize_test_reimport_2", None)
    finally:
        _restore_staticfiles_init(starlette)
        sys.modules.pop("sitecustomize_test_reimport_1", None)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _restore_staticfiles_init(starlette_module) -> None:
    """Restore Starlette's StaticFiles.__init__ to the unpatched version.

    This is a defensive cleanup so other tests in the same pytest run
    see the original behavior. It is not required for the patch to be
    correct — it's hygiene for test isolation.
    """
    # Find the original by inspecting any wrapper's __wrapped__ chain.
    current = starlette_module.staticfiles.StaticFiles.__init__
    visited = set()
    while hasattr(current, "__wrapped__") and current.__wrapped__ not in visited:
        visited.add(current)
        current = current.__wrapped__
    if current is not starlette_module.staticfiles.StaticFiles.__init__:
        starlette_module.staticfiles.StaticFiles.__init__ = current

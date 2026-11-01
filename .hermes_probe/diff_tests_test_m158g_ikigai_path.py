diff --git a/tests/test_m158g_ikigai_path.py b/tests/test_m158g_ikigai_path.py
new file mode 100644
index 00000000..b3321c09
--- /dev/null
+++ b/tests/test_m158g_ikigai_path.py
@@ -0,0 +1,162 @@
+"""M158g — drift net for ``_ensure_ikigai_path()``.
+
+The mesh CLI shim (scripts/td_shim_build/__main__.py) prepends
+``REPO_ROOT/src`` before ``REPO_ROOT/src/ikigai/src``. Both paths expose
+a top-level ``agents`` package. Python's importer picks whichever path
+comes FIRST for the ``agents`` name — so ``import agents`` resolves to
+the parent-level ``src/agents/`` (planner-only layer per ADR-013) and
+shadows ``src/ikigai/src/agents/v2/``, breaking ``td chat`` with
+``No module named 'agents.v2'``.
+
+The invariant guarded here: ``_ensure_ikigai_path()`` MUST promote
+``src/ikigai/src`` to sys.path position 0, regardless of where it was
+before. Presence is not enough — ordering is.
+"""
+from __future__ import annotations
+
+import importlib
+import sys
+from pathlib import Path
+
+# Make sure ``src.mesh`` resolves for the module under test.
+_REPO_ROOT = Path(__file__).resolve().parent.parent
+_SRC = _REPO_ROOT / "src"
+if str(_SRC) not in sys.path:
+    sys.path.insert(0, str(_SRC))
+
+
+def _load_chat_module():
+    """Import the module under test, reloading to reset state between tests."""
+    if "src.mesh.taskdog_chat" in sys.modules:
+        del sys.modules["src.mesh.taskdog_chat"]
+    return importlib.import_module("src.mesh.taskdog_chat")
+
+
+def _make_faulty_path() -> list[str]:
+    """Simulate the shim's sys.path: REPO_ROOT/src wins over IKIGAi src.
+
+    This is the path layout that caused ``No module named 'agents.v2'``.
+    The shim prepends ``src/`` before ``src/ikigai/src/``, so ``agents``
+    would resolve to the parent ``src/agents/`` (planner-only) and shadow
+    ``src/ikigai/src/agents/v2/``.
+    """
+    return [
+        str(_REPO_ROOT / "src"),  # ← parent src/ (has src/agents/)
+        str(_REPO_ROOT),  # ← for the bare ``scripts`` package
+        str(_REPO_ROOT / "src" / "ikigai" / "src"),  # ← has agents/v2
+    ]
+
+
+def test_ikigai_src_at_position_zero_after_call():
+    """After _ensure_ikigai_path(), IKIGAi src must be at sys.path[0]."""
+    chat = _load_chat_module()
+    ikigai_src = str(_REPO_ROOT / "src" / "ikigai" / "src")
+
+    saved_path = sys.path[:]
+    try:
+        sys.path[:] = _make_faulty_path()
+        # Sanity check: the IKIGAi src is in sys.path but NOT at position 0.
+        assert ikigai_src in sys.path
+        assert sys.path[0] != ikigai_src
+
+        chat._ensure_ikigai_path()
+
+        assert sys.path[0] == ikigai_src, (
+            f"expected IKIGAi src at sys.path[0], got {sys.path[0]!r}"
+        )
+    finally:
+        sys.path[:] = saved_path
+
+
+def test_call_is_idempotent():
+    """Calling _ensure_ikigai_path() twice keeps IKIGAi src at 0."""
+    chat = _load_chat_module()
+    ikigai_src = str(_REPO_ROOT / "src" / "ikigai" / "src")
+
+    saved_path = sys.path[:]
+    try:
+        sys.path[:] = _make_faulty_path()
+        chat._ensure_ikigai_path()
+        chat._ensure_ikigai_path()
+        assert sys.path[0] == ikigai_src
+        # And it appears only once in sys.path.
+        assert sys.path.count(ikigai_src) == 1
+    finally:
+        sys.path[:] = saved_path
+
+
+def test_call_when_path_already_at_zero_is_noop():
+    """If IKIGAi is already at 0, _ensure_ikigai_path() must not move other paths."""
+    chat = _load_chat_module()
+    ikigai_src = str(_REPO_ROOT / "src" / "ikigai" / "src")
+    src_root = str(_REPO_ROOT / "src")
+
+    saved_path = sys.path[:]
+    try:
+        # IKIGAi first (correct order). Then src/.
+        sys.path[:] = [ikigai_src, src_root, str(_REPO_ROOT)]
+        expected = sys.path[:]
+
+        chat._ensure_ikigai_path()
+
+        # Position 0 unchanged, relative ordering unchanged.
+        assert sys.path[0] == ikigai_src
+        assert sys.path == expected
+    finally:
+        sys.path[:] = saved_path
+
+
+def test_call_when_ikigai_src_absent_inserts_at_zero():
+    """If IKIGAi src isn't in sys.path at all, it must be inserted at 0."""
+    chat = _load_chat_module()
+    ikigai_src = str(_REPO_ROOT / "src" / "ikigai" / "src")
+    src_root = str(_REPO_ROOT / "src")
+
+    saved_path = sys.path[:]
+    try:
+        sys.path[:] = [src_root, str(_REPO_ROOT)]
+        chat._ensure_ikigai_path()
+        assert sys.path[0] == ikigai_src
+        assert ikigai_src in sys.path
+    finally:
+        sys.path[:] = saved_path
+
+
+def test_invariant_agents_resolves_to_ikigai_v2_after_call():
+    """Smoke test: post-call, ``import agents`` resolves to IKIGAi (has v2/)."""
+    chat = _load_chat_module()
+
+    saved_path = sys.path[:]
+    saved_modules = {k: v for k, v in sys.modules.items() if k == "agents" or k.startswith("agents.")}
+    try:
+        # Reset ``agents`` cache so the resolver hits sys.path afresh.
+        for k in list(sys.modules):
+            if k == "agents" or k.startswith("agents."):
+                del sys.modules[k]
+
+        sys.path[:] = _make_faulty_path()
+        chat._ensure_ikigai_path()
+
+        import agents  # noqa: F401 — smoke import, we only need the path resolution
+
+        assert agents.__file__ is not None
+        agents_path = Path(agents.__file__).resolve()
+        # Must resolve inside src/ikigai/src/agents/ (the IKIGAi agent layer),
+        # NOT inside src/agents/ (the parent planner-only layer).
+        agents_path_str = str(agents_path).replace("\\", "/")
+        assert "/ikigai/src/agents/" in agents_path_str, (
+            f"agents resolved to {agents_path!r} — expected under src/ikigai/src/agents/"
+        )
+        assert "/src/agents/" not in agents_path_str.replace("/ikigai/src/agents/", ""), (
+            f"agents resolved to the parent planner-only package at {agents_path!r}"
+        )
+        # And the v2 subpackage must exist on disk.
+        v2_file = (_REPO_ROOT / "src" / "ikigai" / "src" / "agents" / "v2" / "__init__.py")
+        assert v2_file.exists(), f"expected {v2_file} to exist"
+    finally:
+        sys.path[:] = saved_path
+        # Restore modules so we don't leak state into other tests.
+        for k in list(sys.modules):
+            if k == "agents" or k.startswith("agents."):
+                if k not in saved_modules:
+                    del sys.modules[k]
\ No newline at end of file

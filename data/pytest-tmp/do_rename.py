"""One-shot rename script: ikigai.X → sys_ikigai.X across all .py files.

Replaces 3 patterns:
1. sys_ikigai.X → sys_ikigai.X (long-form alias path)
2. from sys_ikigai.X → from sys_ikigai.X (start-of-line, possibly indented)
3. import sys_ikigai.X → import sys_ikigai.X

Skips: ikigai_wrapper (sibling — different module), IKIGAI_ (constant), Ikigai
(proper-noun references in docstrings/branding).

Does NOT touch:
- vault/ikigai (markdown, not Python)
- src/ikigai/ structure (except imports inside it)
- non-.py files
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]  # life/

# Patterns
RE_LONG_FORM = re.compile(r"\bsrc\.ikigai\.src\.ikigai\.")
RE_FROM_IMPORT = re.compile(r"(^|\n)([ \t]*from\s+)ikigai(\.)")
RE_IMPORT = re.compile(r"(^|\n)([ \t]*import\s+)ikigai(\.)")
RE_FROM_INLINE = re.compile(r"(\bfrom\s+)ikigai(\.)")  # for inline/function-body imports
RE_IMPORT_INLINE = re.compile(r"(\bimport\s+)ikigai(\.)")

total_files = 0
total_lines_changed = 0
total_replacements = 0
files_with_changes: list[str] = []

def rewrite(path: Path) -> int:
    """Return count of replacements in this file. 0 = no change."""
    text = path.read_text(encoding="utf-8")
    original = text
    file_count = 0

    # 1. Long-form first (most specific, avoid double-replacing sys_ikigai.ikigai.)
    text, n = RE_LONG_FORM.subn("sys_ikigai.", text)
    file_count += n

    # 2. Top-level `from sys_ikigai.X` (start of line, optionally indented)
    text, n = RE_FROM_IMPORT.subn(r"\1\2sys_ikigai\3", text)
    file_count += n

    # 3. Top-level `import sys_ikigai.X` (start of line, optionally indented)
    text, n = RE_IMPORT.subn(r"\1\2sys_ikigai\3", text)
    file_count += n

    # 4. Inline `from sys_ikigai.X` (inside function bodies, after other code)
    text, n = RE_FROM_INLINE.subn(r"\1sys_ikigai\2", text)
    file_count += n

    # 5. Inline `import sys_ikigai.X`
    text, n = RE_IMPORT_INLINE.subn(r"\1sys_ikigai\2", text)
    file_count += n

    if text != original:
        path.write_text(text, encoding="utf-8")
        files_with_changes.append(str(path.relative_to(REPO)))
    return file_count

# Walk all .py under REPO except .git and __pycache__
for py in REPO.rglob("*.py"):
    rel = py.relative_to(REPO)
    parts = rel.parts
    if any(p.startswith(".git") or p == "__pycache__" or p == ".venv" for p in parts):
        continue
    if parts[0] == "archive":
        continue  # legacy-pav; do not touch
    if str(rel) == "data/pytest-tmp/do_rename.py":
        continue
    n = rewrite(py)
    if n > 0:
        total_files += 1
        total_replacements += n

print(f"Files changed: {total_files}")
print(f"Total replacements: {total_replacements}")
print(f"\nFirst 30 files with changes:")
for f in files_with_changes[:30]:
    print(f"  {f}")
print(f"\nLast 5:")
for f in files_with_changes[-5:]:
    print(f"  {f}")

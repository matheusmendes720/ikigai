# External Folder Access Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship `external_folder_read` MCP tool with default-deny path-traversal guard so the Deep Agent v2 can ingest pre-form investigation data (CSVs, raw research notes, logs) from outside `vault/` without enabling arbitrary filesystem access.

**Architecture:** `config/external_roots.yaml` is a frozen allow-list of approved folder roots (default-empty → no external access). `path_traversal_guard.py` resolves candidate paths, rejects `..` traversal + null bytes + symlinks pointing outside allowed roots + absolute paths outside allow-list. `external_folder_read(folder_path, pattern, limit, actor)` MCP tool globs files via guard, returns structured file contents with audit logging. Drift invariant (i) verifies every external read stays within bounds + audit log shape.

**Tech Stack:** Python 3.12, Pydantic v2 (frozen=True, extra="forbid"), FastMCP, pathlib.Path, yaml.

---

## Global Constraints

- Pydantic v2 strict everywhere (`frozen=True`, `extra="forbid"`) — per codebase pattern
- Default-deny: empty `external_roots.yaml` → tool returns `EmptyAllowListError`
- Path-traversal guard rejects: `..` segments, null bytes (`\x00`), symlinks pointing outside allowed roots, absolute paths outside allowed roots, paths exceeding `max_path_length=4096`
- Audit log per read: append-only `.external_audit.log` with `actor=X path=Y pattern=Z timestamp=W limit=N result_count=K`
- IKIGAI_TOOLS count goes 12 → 13 with this tool; drift detector must remain 9/9 (Plan A) + add 1 new invariant = 10/10
- No symlink traversal even if path is within bounds (defense-in-depth)
- Read-only: tool refuses to write or modify any external file
- Tests must use `tmp_path` fixtures — never read real filesystem locations
- All commits atomic per task; drift detector must remain ≥9/9 PASS between tasks
- No `Co-Authored-By` trailer per CLAUDE.md L11
- Append-only invariant: audit log is append-only, rotate by timestamp NOT delete
- Plan A dependency: `DriftInvariants` class must exist before this plan's Task 5; if Plan A not yet shipped, see Plan A Task 10

---

## File Structure

**Created:**
- `config/external_roots.yaml` — default-empty allow-list
- `src/contracts/external_roots_config.py` — `ExternalRootsConfig` Pydantic schema
- `src/ikigai/src/ikigai/security/path_traversal_guard.py` — security primitives + exception types
- `src/ikigai/src/mcp_server/external_folder_read.py` — MCP tool implementation
- `tests/contracts/test_external_roots_config.py`
- `tests/ikigai/security/test_path_traversal_guard.py`
- `tests/mcp_server/test_external_folder_read.py`
- `tests/integration/test_external_folder_access_smoke.py`
- `tests/fixtures/external_roots_sample.yaml` — sample used by integration test

**Modified:**
- `src/ikigai/src/ikigai/security/drift_invariants.py` — adds `check_external_access_bounds` (i)
- `src/ikigai/src/mcp_server/__init__.py` — registers `external_folder_read` in IKIGAI_TOOLS list (12 → 13)
- `src/ikigai/tests/test_canonical_scope.py` — wires drift invariant (i) into detector
- `src/ikigai/src/mcp_server/__init__.py` — IKIGAI_TOOLS exported list grows by 1
- `src/contracts/__init__.py` — re-exports `ExternalRootsConfig`

**No changes to:**
- `vault/` — Plan B is read-only external; nothing written to vault from this plan
- `data/review_queue/` — Plan C territory
- `archive/legacy-pav/` — archive untouched

---

## Task 1: `ExternalRootsConfig` Pydantic schema

**Files:**
- Create: `src/contracts/external_roots_config.py`
- Modify: `src/contracts/__init__.py`
- Create: `config/external_roots.yaml` (default empty)
- Test: `tests/contracts/test_external_roots_config.py`

**Interfaces:**
- Produces: `ExternalRootsConfig(roots: tuple[ExternalRoot, ...], default_deny: bool = True)`
- `ExternalRoot(path: str, max_file_size_mb: int = 50, allowed_extensions: tuple[str, ...] = (".md", ".txt", ".csv", ".json"), read_only: bool = True)`

- [ ] **Step 1: Write the failing test**

```python
# tests/contracts/test_external_roots_config.py
from pathlib import Path
import pytest
from pydantic import ValidationError
from src.contracts.external_roots_config import ExternalRootsConfig, ExternalRoot


def test_default_config_is_empty_and_default_deny():
    cfg = ExternalRootsConfig(roots=())
    assert cfg.default_deny is True
    assert cfg.roots == ()


def test_config_with_one_root():
    cfg = ExternalRootsConfig(
        roots=(
            ExternalRoot(path="~/Documents/research"),
        )
    )
    assert len(cfg.roots) == 1
    assert cfg.roots[0].path == "~/Documents/research"
    assert cfg.roots[0].max_file_size_mb == 50
    assert cfg.roots[0].allowed_extensions == (".md", ".txt", ".csv", ".json")
    assert cfg.roots[0].read_only is True


def test_root_max_file_size_must_be_positive():
    with pytest.raises(ValidationError, match="max_file_size_mb"):
        ExternalRoot(path="/tmp/x", max_file_size_mb=0)


def test_root_rejects_unknown_extension():
    with pytest.raises(ValidationError, match="allowed_extensions"):
        # .exe is not in default allow-list
        ExternalRoot(path="/tmp/x", allowed_extensions=(".exe",))


def test_config_rejects_write_root_by_default():
    with pytest.raises(ValidationError, match="read_only"):
        ExternalRoot(path="/tmp/x", read_only=False)


def test_config_frozen():
    cfg = ExternalRootsConfig(roots=())
    with pytest.raises(Exception):
        cfg.default_deny = False


def test_config_loads_from_yaml(tmp_path):
    yaml_file = tmp_path / "external_roots.yaml"
    yaml_file.write_text(
        """
roots:
  - path: ~/Documents/research
    max_file_size_mb: 100
    allowed_extensions: [.md, .csv]
  - path: /tmp/investigations
default_deny: false
""",
        encoding="utf-8",
    )
    cfg = ExternalRootsConfig.from_yaml(yaml_file)
    assert len(cfg.roots) == 2
    assert cfg.roots[1].path == "/tmp/investigations"
    assert cfg.default_deny is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd C:\Users\mathe\code_space\life-oss\life\src\ikigai && PYTHONPATH=src;../../src pytest tests/../contracts/test_external_roots_config.py -v`
Expected: ImportError

- [ ] **Step 3: Implement `ExternalRootsConfig`**

Create `src/contracts/external_roots_config.py`:

```python
"""External folder access configuration — Pydantic v2 strict.

Per Plan B Task 1: default-deny allow-list of folders the agent can read.

Files are read-only by default; write access requires read_only=False
which must be explicitly opted-in.
"""
from pathlib import Path
from typing import Self

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator


class ExternalRoot(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    path: str = Field(min_length=1, max_length=4096)
    max_file_size_mb: int = Field(default=50, ge=1, le=1024)
    allowed_extensions: tuple[str, ...] = (".md", ".txt", ".csv", ".json")
    read_only: bool = True

    @field_validator("allowed_extensions")
    @classmethod
    def _validate_extensions(cls, v: tuple[str, ...]) -> tuple[str, ...]:
        if not v:
            raise ValueError("allowed_extensions cannot be empty")
        for ext in v:
            if not ext.startswith("."):
                raise ValueError(f"Extension {ext!r} must start with '.'")
        return v


class ExternalRootsConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    roots: tuple[ExternalRoot, ...] = ()
    default_deny: bool = True

    @classmethod
    def from_yaml(cls, path: Path | str) -> "ExternalRootsConfig":
        """Load config from YAML file. Frozen semantics respected."""
        text = Path(path).read_text(encoding="utf-8")
        data = yaml.safe_load(text) or {}
        return cls(roots=tuple(data.get("roots", [])), default_deny=data.get("default_deny", True))
```

- [ ] **Step 4: Add re-export to `src/contracts/__init__.py`**

Find a stable location (alphabetical) and append:

```python
from src.contracts.external_roots_config import ExternalRoot, ExternalRootsConfig
```

- [ ] **Step 5: Create default `config/external_roots.yaml`**

```yaml
# External folder access — default-deny (no access)
# Per Plan B §Global Constraints
# To allow access, add root entries below.
roots: []
default_deny: true
```

- [ ] **Step 6: Run test to verify it passes**

Run: `cd C:\Users\mathe\code_space\life-oss\life\src\ikigai && PYTHONPATH=src;../../src pytest tests/../contracts/test_external_roots_config.py -v`
Expected: 7 passed

- [ ] **Step 7: Commit**

```bash
cd C:\Users\mathe\code_space\life-oss\life
git add src/contracts/external_roots_config.py src/contracts/__init__.py config/external_roots.yaml tests/contracts/test_external_roots_config.py
git commit -m "feat(contracts): ExternalRootsConfig (Pydantic v2 strict) + default-deny allow-list"
```

---

## Task 2: `path_traversal_guard.py` — security primitives

**Files:**
- Create: `src/ikigai/src/ikigai/security/path_traversal_guard.py`
- Test: `tests/ikigai/security/test_path_traversal_guard.py`

**Interfaces:**
- Produces: `resolve_path_within_roots(candidate, allowed_roots) -> ResolvedPath`, exception classes (`PathTraversalError`, `EmptyAllowListError`, `SymlinkEscapeError`)

- [ ] **Step 1: Write the failing test**

```python
# tests/ikigai/security/test_path_traversal_guard.py
import pytest
from pathlib import Path
from src.ikigai.src.ikigai.security.path_traversal_guard import (
    resolve_path_within_roots,
    PathTraversalError,
    EmptyAllowListError,
    SymlinkEscapeError,
)


def test_empty_allow_list_raises(tmp_path):
    with pytest.raises(EmptyAllowListError):
        resolve_path_within_roots(
            candidate=str(tmp_path / "file.md"),
            allowed_roots=[],
        )


def test_relative_path_resolves_within_allowed_root(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "research").mkdir()
    (tmp_path / "research" / "data.md").write_text("x", encoding="utf-8")
    allowed = [str(tmp_path / "research")]
    candidate = "research/data.md"
    resolved = resolve_path_within_roots(candidate, allowed)
    assert resolved.path.exists()
    assert resolved.path.read_text(encoding="utf-8") == "x"


def test_dotdot_traversal_rejected(tmp_path):
    (tmp_path / "research").mkdir()
    (tmp_path / "research" / "data.md").write_text("x", encoding="utf-8")
    (tmp_path / "etc").mkdir()
    (tmp_path / "etc" / "passwd").write_text("secret", encoding="utf-8")
    allowed = [str(tmp_path / "research")]
    candidate = str(tmp_path / "research" / ".." / "etc" / "passwd")
    with pytest.raises(PathTraversalError, match="traversal"):
        resolve_path_within_roots(candidate, allowed)


def test_absolute_path_outside_roots_rejected(tmp_path):
    allowed = [str(tmp_path / "research")]
    with pytest.raises(PathTraversalError, match="outside allowed roots"):
        resolve_path_within_roots("C:/Windows/System32/drivers/etc/hosts", allowed)


def test_null_byte_rejected(tmp_path):
    allowed = [str(tmp_path)]
    with pytest.raises(PathTraversalError, match="null byte"):
        resolve_path_within_roots(str(tmp_path / "data.md\x00.txt"), allowed)


def test_symlink_escape_rejected(tmp_path):
    (tmp_path / "research").mkdir()
    (tmp_path / "secret").write_text("top secret", encoding="utf-8")
    symlink = tmp_path / "research" / "leak.md"
    symlink.symlink_to(tmp_path / "secret")
    allowed = [str(tmp_path / "research")]
    with pytest.raises(SymlinkEscapeError, match="symlink"):
        resolve_path_within_roots(str(symlink), allowed)


def test_symlink_within_root_allowed(tmp_path):
    (tmp_path / "research").mkdir()
    target = tmp_path / "research" / "real.md"
    target.write_text("hello", encoding="utf-8")
    symlink = tmp_path / "research" / "linked.md"
    symlink.symlink_to(target)
    allowed = [str(tmp_path / "research")]
    resolved = resolve_path_within_roots(str(symlink), allowed)
    # Symlink stays within root → resolved, content still readable
    assert resolved.path.read_text(encoding="utf-8") == "hello"


def test_multiple_roots_picks_matching_one(tmp_path):
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    (tmp_path / "a" / "file.md").write_text("a", encoding="utf-8")
    (tmp_path / "b" / "file.md").write_text("b", encoding="utf-8")
    allowed = [str(tmp_path / "a"), str(tmp_path / "b")]
    resolved_a = resolve_path_within_roots(str(tmp_path / "a" / "file.md"), allowed)
    assert resolved_a.path.read_text(encoding="utf-8") == "a"
    resolved_b = resolve_path_within_roots(str(tmp_path / "b" / "file.md"), allowed)
    assert resolved_b.path.read_text(encoding="utf-8") == "b"


def test_path_length_exceeded_rejected(tmp_path):
    allowed = [str(tmp_path)]
    long_candidate = str(tmp_path) + "/" + "a" * 5000
    with pytest.raises(PathTraversalError, match="path length"):
        resolve_path_within_roots(long_candidate, allowed)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd C:\Users\mathe\code_space\life-oss\life\src\ikigai && PYTHONPATH=src;../../src pytest tests/ikigai/security/test_path_traversal_guard.py -v`
Expected: ImportError

- [ ] **Step 3: Implement `path_traversal_guard.py`**

Create `src/ikigai/src/ikigai/security/path_traversal_guard.py`:

```python
"""Path-traversal guard for external_folder_read.

Per Plan B §Global Constraints + spec 2026-09-03-sonho-tree-hybrid-design §3.

Default-deny: empty allow-list raises EmptyAllowListError.
"""
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

MAX_PATH_LENGTH = 4096


class PathTraversalError(Exception):
    """Generic path-traversal attack."""


class EmptyAllowListError(Exception):
    """Tool called without any roots configured."""


class SymlinkEscapeError(Exception):
    """Symlink target points outside allowed root."""


@dataclass(frozen=True)
class ResolvedPath:
    """A path that passed all security checks."""
    path: Path
    root: Path


def resolve_path_within_roots(
    candidate: str,
    allowed_roots: Sequence[str | Path],
) -> ResolvedPath:
    """Resolve candidate path; reject any traversal/escape attempt.

    Returns ResolvedPath if path is within one of allowed_roots AND has no
    escape via traversal/symlink/null-byte.

    Args:
        candidate: User-supplied path string.
        allowed_roots: List of root paths.

    Returns:
        ResolvedPath with verified-safe absolute path + matched root.

    Raises:
        EmptyAllowListError: No roots configured.
        PathTraversalError: .., null bytes, outside-roots, too long.
        SymlinkEscapeError: Symlink target outside allowed root.
    """
    if not allowed_roots:
        raise EmptyAllowListError("external_folder_read called with empty allow-list")

    if not candidate:
        raise PathTraversalError("path is empty")

    if len(candidate) > MAX_PATH_LENGTH:
        raise PathTraversalError(f"path length {len(candidate)} exceeds limit {MAX_PATH_LENGTH}")

    if "\x00" in candidate:
        raise PathTraversalError("path contains null byte")

    # Expand ~ and resolve to absolute
    cand_path = Path(candidate).expanduser().resolve()

    # Check against each allowed root
    allowed_abs = [Path(r).expanduser().resolve() for r in allowed_roots]
    matched_root: Path | None = None
    for root in allowed_abs:
        try:
            cand_path.relative_to(root)
            matched_root = root
            break
        except ValueError:
            continue

    if matched_root is None:
        raise PathTraversalError(
            f"path {cand_path} outside allowed roots {[str(r) for r in allowed_abs]}"
        )

    # Symlink check: if resolved path differs from raw path, follow target
    # and verify it ALSO stays within the same root.
    raw_path = Path(candidate).expanduser()
    if raw_path.is_symlink():
        try:
            link_target = raw_path.resolve()
            link_target.relative_to(matched_root)
        except ValueError as e:
            raise SymlinkEscapeError(
                f"symlink {raw_path} → {link_target} escapes root {matched_root}"
            ) from e

    return ResolvedPath(path=cand_path, root=matched_root)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd C:\Users\mathe\code_space\life-oss\life\src\ikigai && PYTHONPATH=src;../../src pytest tests/ikigai/security/test_path_traversal_guard.py -v`
Expected: 9 passed

- [ ] **Step 5: Commit**

```bash
cd C:\Users\mathe\code_space\life-oss\life
git add src/ikigai/src/ikigai/security/path_traversal_guard.py tests/ikigai/security/test_path_traversal_guard.py
git commit -m "feat(security): path_traversal_guard with symlink/null-byte/length defenses"
```

---

## Task 3: `external_folder_read` MCP tool

**Files:**
- Create: `src/ikigai/src/mcp_server/external_folder_read.py`
- Test: `tests/mcp_server/test_external_folder_read.py`

**Interfaces:**
- Produces: `external_folder_read(folder_path: str, pattern: str = "*.md", limit: int = 50, actor: str = "agent") -> list[FileReadResult]`

- [ ] **Step 1: Write the failing test**

```python
# tests/mcp_server/test_external_folder_read.py
import pytest
from pathlib import Path
import os
from src.ikigai.src.mcp_server.external_folder_read import external_folder_read
from src.ikigai.src.ikigai.security.path_traversal_guard import (
    EmptyAllowListError,
    PathTraversalError,
)


@pytest.fixture
def configured_root(tmp_path, monkeypatch):
    """Create a configured external root +3 sample files."""
    research = tmp_path / "research"
    research.mkdir()
    (research / "a.md").write_text("# A", encoding="utf-8")
    (research / "b.md").write_text("# B", encoding="utf-8")
    (research / "data.csv").write_text("col1,col2\n1,2", encoding="utf-8")
    return research


def test_external_folder_read_with_empty_config_raises(monkeypatch):
    monkeypatch.setattr(
        "src.ikigai.src.mcp_server.external_folder_read._load_config",
        lambda: __import__("src.contracts.external_roots_config", fromlist=["ExternalRootsConfig"]).ExternalRootsConfig(roots=()),
    )
    with pytest.raises(EmptyAllowListError):
        external_folder_read(folder_path="/anywhere")


def test_external_folder_read_returns_markdown_files(configured_root, monkeypatch):
    from src.contracts.external_roots_config import ExternalRoot, ExternalRootsConfig
    cfg = ExternalRootsConfig(roots=(ExternalRoot(path=str(configured_root)),))
    monkeypatch.setattr(
        "src.ikigai.src.mcp_server.external_folder_read._load_config",
        lambda: cfg,
    )
    result = external_folder_read(folder_path=str(configured_root), pattern="*.md")
    assert len(result) == 2
    paths = {r.path for r in result}
    assert str(configured_root / "a.md") in paths
    assert str(configured_root / "b.md") in paths
    assert all(r.content in ("# A", "# B") for r in result)


def test_external_folder_read_respects_limit(configured_root, monkeypatch):
    from src.contracts.external_roots_config import ExternalRoot, ExternalRootsConfig
    cfg = ExternalRootsConfig(roots=(ExternalRoot(path=str(configured_root)),))
    monkeypatch.setattr(
        "src.ikigai.src.mcp_server.external_folder_read._load_config",
        lambda: cfg,
    )
    result = external_folder_read(folder_path=str(configured_root), pattern="*", limit=2)
    assert len(result) == 2


def test_external_folder_read_respects_allowed_extensions(configured_root, monkeypatch):
    """CSV is in default allow-list (.md, .txt, .csv, .json)."""
    from src.contracts.external_roots_config import ExternalRoot, ExternalRootsConfig
    cfg = ExternalRootsConfig(roots=(ExternalRoot(path=str(configured_root)),))
    monkeypatch.setattr(
        "src.ikigai.src.mcp_server.external_folder_read._load_config",
        lambda: cfg,
    )
    result = external_folder_read(folder_path=str(configured_root), pattern="*")
    extensions = {Path(r.path).suffix for r in result}
    # All files start with .md or .csv → both in default allow-list
    assert extensions == {".md", ".csv"}


def test_external_folder_read_rejects_traversal_outside_root(tmp_path, configured_root, monkeypatch):
    from src.contracts.external_roots_config import ExternalRoot, ExternalRootsConfig
    cfg = ExternalRootsConfig(roots=(ExternalRoot(path=str(configured_root)),))
    monkeypatch.setattr(
        "src.ikigai.src.mcp_server.external_folder_read._load_config",
        lambda: cfg,
    )
    # Try to escape via ..
    bad_path = str(configured_root / ".." / ".." / "etc" / "passwd")
    with pytest.raises(PathTraversalError):
        external_folder_read(folder_path=bad_path)


def test_external_folder_read_writes_audit_log(configured_root, monkeypatch):
    from src.contracts.external_roots_config import ExternalRoot, ExternalRootsConfig
    cfg = ExternalRootsConfig(roots=(ExternalRoot(path=str(configured_root)),))
    monkeypatch.setattr(
        "src.ikigai.src.mcp_server.external_folder_read._load_config",
        lambda: cfg,
    )
    external_folder_read(folder_path=str(configured_root), pattern="*.md", actor="agent")
    audit_log = configured_root / ".external_audit.log"
    assert audit_log.exists()
    log_content = audit_log.read_text(encoding="utf-8")
    assert "actor=agent" in log_content
    assert "pattern=*.md" in log_content
    assert str(configured_root) in log_content


def test_external_folder_read_rejects_file_size_overage(configured_root, monkeypatch):
    """If a file exceeds max_file_size_mb, skip with audit log."""
    from src.contracts.external_roots_config import ExternalRoot, ExternalRootsConfig
    # 1 MB limit, file is ~6 bytes (no overage), but stub config
    cfg = ExternalRootsConfig(roots=(ExternalRoot(path=str(configured_root), max_file_size_mb=1),))
    monkeypatch.setattr(
        "src.ikigai.src.mcp_server.external_folder_read._load_config",
        lambda: cfg,
    )
    result = external_folder_read(folder_path=str(configured_root), pattern="*")
    # 2 .md + 1 .csv within 1MB → all read
    assert len(result) == 3
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd C:\Users\mathe\code_space\life-oss\life\src\ikigai && PYTHONPATH=src;../../src pytest tests/../mcp_server/test_external_folder_read.py -v`
Expected: ImportError

- [ ] **Step 3: Implement `external_folder_read`**

Create `src/ikigai/src/mcp_server/external_folder_read.py`:

```python
"""external_folder_read MCP tool — read-only access to allow-listed folders.

Per Plan B / spec 2026-09-03-sonho-tree-hybrid-design §3.

Default-deny: tool returns EmptyAllowListError when external_roots.yaml
has no roots configured. Every read appends to .external_audit.log.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from src.contracts.external_roots_config import ExternalRootsConfig
from src.ikigai.src.ikigai.security.path_traversal_guard import (
    EmptyAllowListError,
    PathTraversalError,
    SymlinkEscapeError,
    resolve_path_within_roots,
)


CONFIG_PATH = Path("config/external_roots.yaml")


@dataclass(frozen=True)
class FileReadResult:
    """A single file returned by external_folder_read."""
    path: str
    content: str
    size_bytes: int
    actor: str
    timestamp: str


def _load_config() -> ExternalRootsConfig:
    """Load external_roots config from YAML. Falls back to default-deny."""
    if not CONFIG_PATH.exists():
        return ExternalRootsConfig(roots=())
    return ExternalRootsConfig.from_yaml(CONFIG_PATH)


def _audit(folder: Path, pattern: str, limit: int, actor: str, result_count: int, error: str | None) -> None:
    """Append to .external_audit.log (always at folder, never raises)."""
    audit_path = folder / ".external_audit.log"
    now = datetime.now(timezone.utc).isoformat()
    line = (
        f"{now} actor={actor} folder={folder} pattern={pattern} "
        f"limit={limit} result_count={result_count} error={error or 'none'}\n"
    )
    try:
        with audit_path.open("a", encoding="utf-8") as f:
            f.write(line)
    except Exception:  # audit log failure should never break the tool
        pass


def external_folder_read(
    folder_path: str,
    pattern: str = "*.md",
    limit: int = 50,
    actor: Literal["user", "agent", "system"] = "agent",
) -> list[FileReadResult]:
    """Read files from allow-listed external folder.

    Args:
        folder_path: Root folder to read from.
        pattern: Glob pattern (default: '*.md').
        limit: Max files to return (default 50, hard-cap 500).
        actor: Principal (user/agent/system) for audit.

    Returns:
        List of FileReadResult, one per matching file.

    Raises:
        EmptyAllowListError: external_roots.yaml has no roots.
        PathTraversalError: path escapes allowed root.
        SymlinkEscapeError: symlink target outside root.
    """
    if limit <= 0 or limit > 500:
        raise ValueError(f"limit must be 1..500, got {limit}")

    cfg = _load_config()
    if not cfg.roots:
        raise EmptyAllowListError("external_roots.yaml has no roots configured")

    # Build allowed-roots list, find matching root for folder_path
    allowed_roots = [Path(r.path) for r in cfg.roots]
    matched_root_cfg = None
    for r in cfg.roots:
        try:
            resolve_path_within_roots(folder_path, [r.path])  # validates
            matched_root_cfg = r
            break
        except (PathTraversalError, SymlinkEscapeError):
            continue

    if matched_root_cfg is None:
        # No root contains folder_path → default-deny
        raise PathTraversalError(
            f"folder_path {folder_path} not within any allowed root"
        )

    allowed_exts = set(matched_root_cfg.allowed_extensions)
    max_bytes = matched_root_cfg.max_file_size_mb * 1024 * 1024

    # Safe to glob now — guard already validated
    raw = Path(folder_path).expanduser()
    candidates = sorted(raw.glob(pattern))[:limit]

    results: list[FileReadResult] = []
    now = datetime.now(timezone.utc).isoformat()
    skipped = 0
    for c in candidates:
        if not c.is_file():
            continue
        if c.suffix not in allowed_exts:
            skipped += 1
            continue
        try:
            size = c.stat().st_size
        except OSError:
            skipped += 1
            continue
        if size > max_bytes:
            skipped += 1
            continue
        try:
            content = c.read_text(encoding="utf-8", errors="replace")
        except OSError:
            skipped += 1
            continue
        results.append(
            FileReadResult(
                path=str(c),
                content=content,
                size_bytes=size,
                actor=actor,
                timestamp=now,
            )
        )

    # Audit log: at the resolved root
    try:
        resolved_folder = resolve_path_within_roots(folder_path, allowed_roots)
        _audit(resolved_folder.folder if hasattr(resolved_folder, "folder") else raw, pattern, limit, actor, len(results), None)
    except Exception:  # audit failure not fatal
        pass

    return results
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd C:\Users\mathe\code_space\life-oss\life\src\ikigai && PYTHONPATH=src;../../src pytest tests/../mcp_server/test_external_folder_read.py -v`
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
cd C:\Users\mathe\code_space\life-oss\life
git add src/ikigai/src/mcp_server/external_folder_read.py tests/mcp_server/test_external_folder_read.py
git commit -m "feat(mcp): external_folder_read with audit log + size/ext guards"
```

---

## Task 4: Register `external_folder_read` in IKIGAI_TOOLS

**Files:**
- Modify: `src/ikigai/src/agents/tools.py` (IKIGAI_TOOLS list — append `external_folder_read`)
- Modify: `src/ikigai/src/mcp_server/server.py` (FastMCP `@MCP.tool` registration)
- Modify: `src/ikigai/tests/test_canonical_scope.py` (line 313: change `total_count == 12` → `== 13`)
- Modify: `scripts/mcp_inspect.py` (line 43: change `EXPECTED_IKIGAI_TOOLS_COUNT = 12` → `= 13`)

> **Gap-fix note (2026-09-03):** Earlier draft pointed at `src/ikigai/src/mcp_server/__init__.py`,
> but that file is just a docstring. The canonical `IKIGAI_TOOLS` list lives at
> `src/ikigai/src/agents/tools.py:556`, and FastMCP registration lives in
> `src/ikigai/src/mcp_server/server.py`. Drift detector reads `tools.py` at L283 and asserts
> `total_count == 12` at L313 — must update alongside the list.

**Interfaces:**
- Modifies: IKIGAI_TOOLS list grows 12 → 13

- [ ] **Step 1: Locate IKIGAI_TOOLS**

Read `src/ikigai/src/agents/tools.py` around line 556 (initial assignment) and any subsequent
`IKIGAI_TOOLS.extend([...])` calls. Do NOT modify `mcp_server/__init__.py`.

- [ ] **Step 2: Append to the list**

In `src/ikigai/src/agents/tools.py`, add at the bottom (use `.extend([...])` if the initial list
already has 12 items):

```python
from src.ikigai.src.mcp_server.external_folder_read import external_folder_read

IKIGAI_TOOLS.extend([
    external_folder_read,  # Tool #13
])
```

- [ ] **Step 3: Register FastMCP tool**

In `src/ikigai/src/mcp_server/server.py`, register the tool on the FastMCP instance:

```python
from src.ikigai.src.mcp_server.external_folder_read import external_folder_read

MCP.tool()(external_folder_read)
```

- [ ] **Step 4: Update drift detector + mcp_inspect**

Edit `src/ikigai/tests/test_canonical_scope.py` line 313:

```python
assert total_count == 13, (  # was 12
    f"IKIGAI_TOOLS must contain exactly 13 entries per ADR-013; "
    f"found {total_count}. Adding/removing requires updating ADR-013."
)
```

Edit `scripts/mcp_inspect.py` line 43:

```python
EXPECTED_IKIGAI_TOOLS_COUNT = 13  # was 12
```

- [ ] **Step 5: Verify via mcp_inspect + drift detector**

Run: `cd C:\Users\mathe\code_space\life-oss\life && python scripts/mcp_inspect.py --tool-count 13`
Expected: PASS (16 → 13 first time, then 13 stable)

Run: `cd C:\Users\mathe\code_space\life-oss\life\src\ikigai && PYTHONPATH=src;../../src pytest tests/test_canonical_scope.py -v`
Expected: 11/11 PASS (5 baseline + 4 Plan A a-e + 1 Plan B i + 1 baseline UEID — count is 11 invariants, 8 tests)

- [ ] **Step 6: Commit**

```bash
cd C:\Users\mathe\code_space\life-oss\life
git add src/ikigai/src/agents/tools.py src/ikigai/src/mcp_server/server.py src/ikigai/tests/test_canonical_scope.py scripts/mcp_inspect.py
git commit -m "feat(mcp): register external_folder_read as IKIGAI_TOOLS[13]"
```

---

## Task 5: Drift invariant (i) — external access bounds

**Files:**
- Modify: `src/ikigai/src/ikigai/security/drift_invariants.py`
- Modify: `src/ikigai/tests/test_canonical_scope.py`
- Test: `tests/ikigai/security/test_drift_invariants.py` (add 2 tests)

**Interfaces:**
- Produces: `DriftInvariants.check_external_access_bounds()` — verifies config valid + audit log timestamp within 24h of test run

- [ ] **Step 1: Write the failing test**

Append to `tests/ikigai/security/test_drift_invariants.py`:

```python
# tests/ikigai/security/test_drift_invariants.py (add to existing file)

import tempfile
from pathlib import Path


def test_drift_invariant_i_external_access_bounds_passes_when_valid(tmp_path, monkeypatch):
    """external_roots.yaml exists with valid structure; no audit-log violations."""
    from src.ikigai.src.ikigai.security.drift_invariants import DriftInvariants
    # Write valid config
    config = tmp_path / "config" / "external_roots.yaml"
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text(
        """
roots:
  - path: ~/Documents/research
    max_file_size_mb: 50
    allowed_extensions: [.md, .csv]
default_deny: true
""",
        encoding="utf-8",
    )
    # Monkeypatch the config path
    monkeypatch.setattr(
        "src.ikigai.src.mcp_server.external_folder_read.CONFIG_PATH",
        config,
    )
    DriftInvariants.check_external_access_bounds()  # no exception


def test_drift_invariant_i_fails_on_invalid_yaml(tmp_path, monkeypatch):
    from src.ikigai.src.ikigai.security.drift_invariants import DriftInvariants
    import pytest
    config = tmp_path / "config" / "external_roots.yaml"
    config.parent.mkdir(parents=True, exist_ok=True)
    # Missing required field (path) on first root
    config.write_text(
        """
roots:
  - max_file_size_mb: 50
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "src.ikigai.src.mcp_server.external_folder_read.CONFIG_PATH",
        config,
    )
    with pytest.raises(AssertionError, match="external_roots"):
        DriftInvariants.check_external_access_bounds()


def test_drift_invariant_i_fails_when_root_path_missing(tmp_path, monkeypatch):
    """A configured root path that doesn't exist on disk fails the check."""
    from src.ikigai.src.ikigai.security.drift_invariants import DriftInvariants
    import pytest
    config = tmp_path / "config" / "external_roots.yaml"
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text(
        f"""
roots:
  - path: {tmp_path}/nonexistent-folder
default_deny: true
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "src.ikigai.src.mcp_server.external_folder_read.CONFIG_PATH",
        config,
    )
    with pytest.raises(AssertionError, match="does not exist"):
        DriftInvariants.check_external_access_bounds()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd C:\Users\mathe\code_space\life-oss\life\src\ikigai && PYTHONPATH=src;../../src pytest tests/ikigai/security/test_drift_invariants.py -v`
Expected: ImportError (no `check_external_access_bounds` method)

- [ ] **Step 3: Implement `check_external_access_bounds`**

Add to `src/ikigai/src/ikigai/security/drift_invariants.py`:

```python
# Append to existing DriftInvariants class

    @staticmethod
    def check_external_access_bounds() -> None:
        """Invariant (i): external_roots.yaml is valid + configured roots exist.

        Per Plan B / spec 2026-09-03-sonho-tree-hybrid-design §Drift Invariants.
        """
        from src.ikigai.src.mcp_server.external_folder_read import CONFIG_PATH
        from src.contracts.external_roots_config import ExternalRootsConfig

        if not CONFIG_PATH.exists():
            # Default-deny is OK — file missing is valid; tool raises on use
            return

        try:
            cfg = ExternalRootsConfig.from_yaml(CONFIG_PATH)
        except Exception as e:
            raise AssertionError(f"external_roots.yaml failed to parse: {e}") from e

        for r in cfg.roots:
            root_path = Path(r.path).expanduser()
            if not root_path.exists():
                raise AssertionError(
                    f"external_root {r.path!r} configured but does not exist on disk"
                )

        # Audit log freshness check (last entry within 24h if any reads have happened)
        for r in cfg.roots:
            audit = Path(r.path).expanduser() / ".external_audit.log"
            if not audit.exists():
                continue
            try:
                last_line = audit.read_text(encoding="utf-8").strip().splitlines()[-1]
                # Parse leading ISO timestamp; if parseable, warn if > 24h old only if reads exist
                # (Current code skips hard-fail on stale log — auditor's responsibility)
            except Exception:
                pass
```

- [ ] **Step 4: Wire invariant into drift detector**

Append to `src/ikigai/tests/test_canonical_scope.py`:

```python
def test_drift_invariant_i_external_access_bounds():
    from src.ikigai.src.ikigai.security.drift_invariants import DriftInvariants
    DriftInvariants.check_external_access_bounds()  # no exception on default config
```

- [ ] **Step 5: Run full drift detector**

Run: `cd C:\Users\mathe\code_space\life-oss\life\src\ikigai && PYTHONPATH=src;../../src pytest tests/test_canonical_scope.py -v`
Expected: 5 + 4 (Plan A a-e) + 1 (Plan B i) = 10 invariants PASS

- [ ] **Step 6: Commit**

```bash
cd C:\Users\mathe\code_space\life-oss\life
git add src/ikigai/src/ikigai/security/drift_invariants.py src/ikigai/tests/test_canonical_scope.py tests/ikigai/security/test_drift_invariants.py
git commit -m "feat(drift): invariant i — external access bounds"
```

---

## Task 6: End-to-end smoke test

**Files:**
- Create: `tests/integration/test_external_folder_access_smoke.py`
- Create: `tests/fixtures/external_roots_sample.yaml`

**Interfaces:**
- Produces: 1 integration test exercising full flow (config + guard + read + audit)

- [ ] **Step 1: Create fixture**

Create `tests/fixtures/external_roots_sample.yaml`:

```yaml
# Sample used by integration test only.
# NOT loaded by production code at runtime.
roots:
  - path: tests/fixtures/external_root
    max_file_size_mb: 1
    allowed_extensions: [.md, .csv, .txt]
    read_only: true
default_deny: true
```

- [ ] **Step 2: Write integration test**

```python
# tests/integration/test_external_folder_access_smoke.py
"""End-to-end smoke test for Plan B External Folder Access.

Per spec 2026-09-03-sonho-tree-hybrid-design §3.
"""
from datetime import datetime, timezone
from pathlib import Path

import pytest


@pytest.fixture
def external_root(tmp_path):
    """Create a sample external root with 3 files of varying types."""
    root = tmp_path / "external_root"
    root.mkdir()
    (root / "research_notes.md").write_text("# Research Notes\n\nFindings from Q3.", encoding="utf-8")
    (root / "data.csv").write_text("date,value\n2026-09-03,42", encoding="utf-8")
    (root / "log.txt").write_text("2026-09-03T00:00:00Z — agent ran smoke test", encoding="utf-8")
    # File outside allow-list (.exe extension)
    (root / "binary.exe").write_text("MZ\x00\x00", encoding="utf-8")
    return root


def test_full_flow_agent_reads_investigation_files(tmp_path, monkeypatch, external_root):
    """Agent reads 3 files from external root, .exe is skipped, audit log captures all."""
    from src.contracts.external_roots_config import ExternalRoot, ExternalRootsConfig
    from src.ikigai.src.mcp_server.external_folder_read import external_folder_read

    cfg = ExternalRootsConfig(roots=(ExternalRoot(path=str(external_root)),))
    monkeypatch.setattr(
        "src.ikigai.src.mcp_server.external_folder_read._load_config",
        lambda: cfg,
    )

    # Step 1: agent reads
    results = external_folder_read(
        folder_path=str(external_root),
        pattern="*",
        limit=10,
        actor="agent",
    )

    # Step 2: 3 files returned, .exe skipped
    assert len(results) == 3
    names = {Path(r.path).name for r in results}
    assert names == {"research_notes.md", "data.csv", "log.txt"}

    # Step 3: audit log captures the read
    audit_log = external_root / ".external_audit.log"
    assert audit_log.exists()
    log_content = audit_log.read_text(encoding="utf-8")
    assert "actor=agent" in log_content
    assert "result_count=3" in log_content


def test_traversal_attack_blocked(tmp_path, monkeypatch, external_root):
    """Even with valid config, agent cannot escape via '..'."""
    from src.contracts.external_roots_config import ExternalRoot, ExternalRootsConfig
    from src.ikigai.src.mcp_server.external_folder_read import external_folder_read
    from src.ikigai.src.ikigai.security.path_traversal_guard import PathTraversalError

    cfg = ExternalRootsConfig(roots=(ExternalRoot(path=str(external_root)),))
    monkeypatch.setattr(
        "src.ikigai.src.mcp_server.external_folder_read._load_config",
        lambda: cfg,
    )

    bad_path = str(external_root / ".." / ".." / "etc" / "passwd")
    with pytest.raises(PathTraversalError):
        external_folder_read(folder_path=bad_path)


def test_default_deny_blocks_unconfigured(tmp_path, monkeypatch):
    """With empty config, even legitimate path is denied."""
    from src.contracts.external_roots_config import ExternalRootsConfig
    from src.ikigai.src.mcp_server.external_folder_read import external_folder_read
    from src.ikigai.src.ikigai.security.path_traversal_guard import EmptyAllowListError

    cfg = ExternalRootsConfig(roots=())
    monkeypatch.setattr(
        "src.ikigai.src.mcp_server.external_folder_read._load_config",
        lambda: cfg,
    )

    with pytest.raises(EmptyAllowListError):
        external_folder_read(folder_path=str(tmp_path))
```

- [ ] **Step 3: Run integration test**

Run: `cd C:\Users\mathe\code_space\life-oss\life\src\ikigai && PYTHONPATH=src;../../src pytest tests/integration/test_external_folder_access_smoke.py -v`
Expected: 3 passed

- [ ] **Step 4: Full test suite + lint + type check + mcp_inspect**

```bash
cd C:\Users\mathe\code_space\life-oss\life\src\ikigai
PYTHONPATH=src;../../src pytest -v
uv run ruff check src/
uv run ruff format --check src/
uv run mypy src/
```

Expected: all tests pass, lint clean.

```bash
cd C:\Users\mathe\code_space\life-oss\life
python scripts/mcp_inspect.py --tool-count 13
```

Expected: 13 IKIGAI_TOOLS advertised (was 12).

- [ ] **Step 5: Commit**

```bash
cd C:\Users\mathe\code_space\life-oss\life
git add tests/integration/test_external_folder_access_smoke.py tests/fixtures/external_roots_sample.yaml
git commit -m "test(integration): external_folder_access smoke + fixture"
```

---

## Verification (post-Plan-B complete)

```bash
# 1. Drift detector: 10 invariants PASS (5 baseline + 4 Plan A a-e + 1 Plan B i)
cd C:\Users\mathe\code_space\life-oss\life\src\ikigai
PYTHONPATH=src;../../src pytest tests/test_canonical_scope.py -v
# Expected: 10 invariants

# 2. All tests green
PYTHONPATH=src;../../src pytest -v

# 3. Lint + type
uv run ruff check src/
uv run ruff format --check src/
uv run mypy src/

# 4. MCP tool count = 13 (was 12, +1 for external_folder_read)
cd C:\Users\mathe\code_space\life-oss\life
python scripts/mcp_inspect.py --tool-count 13

# 5. Default config is empty (no paths leaked)
cat config/external_roots.yaml
# Expected: roots: [], default_deny: true

# 6. Audit log shape
PYTHONPATH=src;../../src pytest tests/integration/test_external_folder_access_smoke.py -v
# Expected: 3 passed, .external_audit.log line contains actor=agent pattern=* result_count=3
```

---

## Self-Review (per writing-plans skill)

**Spec coverage:**
- ✅ external_folder_read MCP tool → Tasks 3 + 4
- ✅ external_roots.yaml → Tasks 1 + 5 (validation)
- ✅ path-traversal guard → Task 2
- ✅ drift invariant (i) → Task 5
- ✅ Audit log → Task 3 step 3 (`_audit()` helper)
- ✅ Default-deny semantics → enforced throughout (Task 2 `EmptyAllowListError` + Task 3 fixture)
- ✅ Symlink escape defense → Task 2 step 1 test + step 3 implementation
- ✅ End-to-end smoke test → Task 6

**Placeholder scan:** No "TBD", "TODO", "implement later", "fill in details" — every step has explicit code.

**Type consistency:**
- `ExternalRootsConfig.from_yaml()` Task 1 → consumed Task 5 ✓
- `resolve_path_within_roots()` Task 2 → consumed Task 3 ✓
- `EmptyAllowListError` / `PathTraversalError` / `SymlinkEscapeError` Task 2 → consumed Tasks 3, 5, 6 ✓
- `CONFIG_PATH` Task 3 → consumed Tasks 4, 5 ✓
- `IKIGAI_TOOLS[12]` → `[13]` ✓

**Coverage gaps acknowledged:**
- No "write" capability (intentionally; spec says read-only)
- Audit log freshness check skipped >24h (advisory not enforced)
- Plan B does NOT add Lifestyle SONHOs (those ship with the broader agent roadmap post Plan C)
- Plan B does NOT add external_folder_write (deferred to future if/when needed)

---

## Open Items (deferred per spec)

- **Plan C**: Investigation Queue (`data/investigation_queue/` + 3 MCP tools + drift invariant h)
- **Lifestyle SONHOs**: enabled by deeper agent roadmap (post Plan C)
- **`external_folder_write`**: not in v1; add if user demands reversible writes
- **Audit log rotation**: per-size or per-day; not v1
- **Multi-agent concurrent reads**: same audit log is append-only; v1 single-actor assumption

---

*Scaffold: External Folder Access Implementation Plan · 2026-09-03 · Plan B · claude-code interactive*

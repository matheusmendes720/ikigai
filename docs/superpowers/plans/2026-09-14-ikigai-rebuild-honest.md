# IKIGAI Rebuild Honest — Disk-Verified Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the IKIGAI bottom-up infra + soul-driven agent layer per the 9 locked decisions in `docs/superpowers/specs/2026-09-10-system-review-design.md`, with **mandatory disk verification at every step** (no more "files claimed shipped but don't exist" failures).

**Architecture:** TDD-style — every file is created in a worktree, immediately verified on disk via `ls` + `cat`, committed with a verification script as part of the commit, and run through pytest. Phase 0 is reconnaissance to establish ground truth (what actually exists vs what's missing). Subsequent phases rebuild only the missing pieces, leaving existing work intact.

**Tech Stack:** Python 3.11+, Pydantic v2 strict, FastMCP gateway, pytest, git worktrees.

## Global Constraints

- **Disk verification mandatory:** every step that creates a file must end with `ls <path>` + `cat <path> | head -5` to prove the file exists with non-empty content.
- **Pytest gates:** every code step ends with `python -m pytest <test_path> -v` and PASS confirmation.
- **Commits include verification:** each commit message has a "Verification: ..." footer showing `ls`/`cat`/`pytest` output.
- **No Co-Authored-By trailer** per `CLAUDE.md`.
- **Worktree isolation:** every phase that touches code runs in a git worktree (created via `git worktree add`) so the main branch stays clean.
- **Pre-existing files untouched:** do NOT modify any file that already exists on disk (unless Phase 0 reconnaissance confirms it must be rebuilt).
- **Constraint on subagents:** every subagent prompt MUST end with "Before reporting success, run `ls <created_file_path>` and `cat <created_file_path> | head -10`. Paste the output in your reply. If file is missing or empty, report FAILURE — do not claim success."

---

## Phase 0 — Reconnaissance (verify reality)

### Task 0.1: Establish ground truth

**Files:**
- Modify: none
- Create: `docs/superpowers/specs/2026-09-14-rebuild-baseline.md` (ground truth report)

**Interfaces:**
- Consumes: file system state at `<repo>/C:/Users/mathe/code_space/life-oss/life`
- Produces: baseline report listing which of the 14 expected files exist vs are missing

- [ ] **Step 1: Check expected file inventory**

Run this exact script (it does only reads + writes one summary file):

```bash
cd C:/Users/mathe/code_space/life-oss/life

EXPECTED_FILES=(
  "src/ikigai/souls/ikigai-planner.md"
  "src/ikigai/souls/ikigai-critic.md"
  "src/ikigai/souls/ikigai-stoic.md"
  "src/ikigai/souls/loader.py"
  "src/ikigai/src/chat/__init__.py"
  "src/ikigai/src/chat/schema.py"
  "src/ikigai/src/chat/reader.py"
  "src/ikigai/src/chat/writer.py"
  "src/ikigai/src/agents/v2/sse_publisher.py"
  "src/ikigai/src/agents/v2/system_prompt.py"
  "src/ikigai/src/agents/v2/nodes/recall_node.py"
  "src/ikigai/src/agents/v2/nodes/reason_node.py"
  "src/ikigai/src/gateway_client.py"
  "src/ikigai/src/mcp_server/taskdog_namespace.py"
  "src/ikigai/src/mcp_server/cli_namespace.py"
  "src/ikigai/src/mcp_server/solverforge_namespace.py"
  "src/ikigai/bin/ikigai_serve.py"
  "scripts/ikigai-serve.sh"
  "scripts/ikigai-serve.bat"
  "CONTEXT.md"
)

EXIST=0
MISSING=0
for f in "${EXPECTED_FILES[@]}"; do
  if [ -f "$f" ]; then
    SIZE=$(wc -c < "$f")
    echo "EXISTS  $f  (${SIZE} bytes)"
    EXIST=$((EXIST+1))
  else
    echo "MISSING $f"
    MISSING=$((MISSING+1))
  fi
done
echo ""
echo "TOTAL: ${EXIST} exist, ${MISSING} missing"
```

Expected: at least 16 files EXIST (some may be partial from previous workflows). Save the output.

- [ ] **Step 2: Write baseline report**

```bash
cat > docs/superpowers/specs/2026-09-14-rebuild-baseline.md << 'BASELINE_EOF'
# IKIGAI Rebuild Baseline — 2026-09-14

**Origin:** Phase 5 loop revealed previous workflows created commits but files do not persist on disk. This baseline establishes ground truth.

**Inventory check** (run `docs/superpowers/specs/rebuild-baseline.sh`):

| File | Status (anticipated) |
|---|---|
| src/ikigai/souls/ikigai-planner.md | MISSING |
| src/ikigai/souls/ikigai-critic.md | MISSING |
| src/ikigai/souls/ikigai-stoic.md | MISSING |
| src/ikigai/souls/loader.py | MISSING |
| src/ikigai/src/chat/__init__.py | MISSING |
| src/ikigai/src/chat/schema.py | MISSING |
| src/ikigai/src/chat/reader.py | MISSING |
| src/ikigai/src/chat/writer.py | MISSING |
| src/ikigai/src/agents/v2/sse_publisher.py | MISSING |
| src/ikigai/src/agents/v2/system_prompt.py | MISSING |
| src/ikigai/src/agents/v2/nodes/recall_node.py | MISSING |
| src/ikigai/src/agents/v2/nodes/reason_node.py | MISSING |
| src/ikigai/src/gateway_client.py | MISSING |
| src/ikigai/src/mcp_server/taskdog_namespace.py | MISSING |
| src/ikigai/src/mcp_server/cli_namespace.py | MISSING |
| src/ikigai/src/mcp_server/solverforge_namespace.py | MISSING |
| src/ikigai/bin/ikigai_serve.py | MISSING |
| scripts/ikigai-serve.sh | MISSING |
| scripts/ikigai-serve.bat | MISSING |
| CONTEXT.md | MISSING |

BASELINE_EOF

# Now save actual inventory output
cat docs/superpowers/specs/2026-09-14-rebuild-baseline.md
echo ""
echo "=== ACTUAL OUTPUT ==="
# Re-run the inventory and append
for f in "${EXPECTED_FILES[@]}"; do
  if [ -f "$f" ]; then SIZE=$(wc -c < "$f"); echo "EXISTS  $f  (${SIZE} bytes)"; else echo "MISSING $f"; fi
done
```

- [ ] **Step 3: Commit baseline**

```bash
git add docs/superpowers/specs/2026-09-14-rebuild-baseline.md
git commit -m "chore(rebuild): phase 0 baseline — ground truth inventory

Verification: $(cat docs/superpowers/specs/2026-09-14-rebuild-baseline.md | wc -l) lines written"
```

---

### Task 0.2: Reconcile MEMORY.md and empty commits

**Files:**
- Modify: `~/.claude/projects/C--Users-mathe-code-space-life-oss-life/memory/MEMORY.md` (mark M12 as "intent, not shipped")
- Modify: optional — squash empty commits if any exist (see step 3)

- [ ] **Step 1: Update MEMORY.md M12 entry**

```bash
# Find the M12 line and append a "RECONCILED" note (append-only per CLAUDE.md)
MEMORY_FILE=~/.claude/projects/C--Users-mathe-code-space-life-oss-life/memory/MEMORY.md

# Insert a reconciliation note right after the M12 line
awk '/M12 Bottom-Up Infra SHIPPED/{print; print "  - RECONCILED 2026-09-14: previous workflows reported file creation but disk verification shows files missing; rebuild per docs/superpowers/plans/2026-09-14-ikigai-rebuild-honest.md"; next}1' "$MEMORY_FILE" > /tmp/memory.tmp
mv /tmp/memory.tmp "$MEMORY_FILE"

# Verify
grep -A1 "M12 Bottom-Up Infra" "$MEMORY_FILE" | head -3
```

- [ ] **Step 2: Detect empty commits**

```bash
cd C:/Users/mathe/code_space/life-oss/life

# Check if there are recent empty commits (only metadata changes)
git log --oneline -n 6
echo "---"
# Look for commits with no actual diff (rare; only if workflow created empty commits)
EMPTY_COMMITS=$(git log --oneline -n 10 | wc -l)
echo "Last 10 commits: $EMPTY_COMMITS"

# If you see "chore(loop): mark M15" or similar metadata-only commits, leave them (they don't claim to ship code)
```

- [ ] **Step 3: Decide on commit cleanup**

- If commits are pure metadata (e.g. "chore(loop): mark X"): LEAVE — they don't claim to ship code.
- If commits claim to ship files that don't exist: do `git revert <sha>` for each.
- If unsure: LEAVE — better safe than sorry.

Document the decision in this plan under "Phase 0 decisions" below.

**Phase 0 decisions:** (this plan's author: leave empty for the executor to fill based on actual `git log` inspection)

---

## Phase 1 — Soul system (3 souls + loader)

### Task 1.1: Create 3 soul.md files

**Files:**
- Create: `src/ikigai/souls/ikigai-planner.md`
- Create: `src/ikigai/souls/ikigai-critic.md`
- Create: `src/ikigai/souls/ikigai-stoic.md`

**Interfaces:**
- Produces: 3 markdown files consumable by `src/ikigai/souls/loader.py` (Task 1.2)

- [ ] **Step 1: Create ikigai-planner.md**

```bash
cd C:/Users/mathe/code_space/life-oss/life
mkdir -p src/ikigai/souls/

cat > src/ikigai/souls/ikigai-planner.md << 'PLANNER_EOF'
# IKIGAI Planner Soul

## Voice
Pragmatic counselor. Speaks in complete, structured proposals. Uses
calendar-time references (days, weeks, quarters), never abstract
horizon markers ("soon", "later"). Always pairs a recommendation with
its trade-off.

Example: "I'd schedule the migration for Week 3 of Q4. Trade-off:
defers the feature freeze by 5 days but avoids the weekend cutover."

## Reasoning Style
1. State the concrete artifact or decision under review.
2. Identify the smallest reversible unit.
3. Propose a plan with explicit checkpoints.
4. Surface 1-2 failure modes the user hasn't asked about.
5. Ask one question that locks the scope.

## Constraints (7 never-do rules)
1. Never claim "PAV/QHE/regime is alive" — those math engines are archived.
2. Never invent cycle/horizon numbers — derive them from `vault/ikigai/closing-2026/`.
3. Never propose a write to `vault/.kill_switch.md`.
4. Never override a user-stated priority without restating it back.
5. Never invoke algorithm code under `src/ikigai/src/ikigai/core/scoring/` (archived per ADR-024).
6. Never produce a plan with >5 parallel workstreams — split or sequence.
7. Never claim evidence without citing the file path.

## Sample Behaviors
- User: "should I move Q4 planning to November?" → "I'd hold it to
  October 28. November already has the Q3 retrospective overlap. Trade-off:
  you get 3 more days for the data prep but lose the Monday sync window."
- User: "create a task for X" → produces a structured task with
  `data/tasks.jsonl` row + horizon estimate from cycle_start.

PLANNER_EOF

# VERIFY on disk
ls -la src/ikigai/souls/ikigai-planner.md
cat src/ikigai/souls/ikigai-planner.md | head -10
wc -l src/ikigai/souls/ikigai-planner.md
```

Expected output:
- `ls` shows the file with non-zero size.
- `head -10` shows the `# IKIGAI Planner Soul` header.
- `wc -l` shows >= 30 lines.

- [ ] **Step 2: Create ikigai-critic.md**

```bash
cd C:/Users/mathe/code_space/life-oss/life

cat > src/ikigai/souls/ikigai-critic.md << 'CRITIC_EOF'
# IKIGAI Critic Soul

## Voice
Socratic questioner. Surfaces unstated assumptions. Asks one
question per turn, never multi-part. Distinguishes load-bearing
assumptions from inherited ones.

Example: "What's the smallest decision you could reverse if this
plan fails? If you can't name one, we have a problem."

## Reasoning Style
1. Identify the proposition under review.
2. Classify the assumption(s): load-bearing, style, inherited.
3. Probe one load-bearing assumption with a single question.
4. Wait for the answer. Do not propose alternatives until the answer.

## Constraints (7 never-do rules)
1. Never accept a proposition without surfacing an assumption.
2. Never multi-question — one question per turn, period.
3. Never assert a counter-position without evidence from `vault/` or `strategics/`.
4. Never validate the user's framing without checking against `strategics/Planejamento (E&T)`.
5. Never propose a plan as a critic — that's the planner's role.
6. Never reference PAV/QHE/regime math (archived).
7. Never use "should", "must", "ought" without a context citation.

## Sample Behaviors
- User: "I want to ship feature X by Friday." → "Friday is a date.
  What's the cost of missing Friday — full deferral or partial ship?"
- User: "this is critical" → "What makes it critical now vs last week
  when it wasn't?"

CRITIC_EOF

# VERIFY
ls -la src/ikigai/souls/ikigai-critic.md
cat src/ikigai/souls/ikigai-critic.md | head -10
```

- [ ] **Step 3: Create ikigai-stoic.md**

```bash
cd C:/Users/mathe/code_space/life-oss/life

cat > src/ikigai/souls/ikigai-stoic.md << 'STOIC_EOF'
# IKIGAI Stoic Soul

## Voice
Calm long-horizon counselor. Distinguishes controllable from
uncontrollable. Refuses panic. Always responds to a stress signal
by separating "in your control" from "outside your control".

Example: "The deadline slipping is outside your control. The next
commitment you make is in your control. What's the next commitment?"

## Reasoning Style
1. Identify the stressor.
2. Dichotomy of control: controllable / partially / not.
3. Focus on controllable subset.
4. Propose one small action in the controllable subset.
5. Defer the rest.

## Constraints (7 never-do rules)
1. Never equate effort with progress.
2. Never recommend action outside the controllable subset.
3. Never minimize the stressor.
4. Never recommend emotional suppression — distinguish acceptance from avoidance.
5. Never use urgency markers ("asap", "urgent") without a calendar deadline.
6. Never reference PAV/QHE/regime math (archived).
7. Never propose multi-action responses — one small thing.

## Sample Behaviors
- User: "everything is on fire" → "Three of those are out of your
  control — which one is most in your control right now? Start there."
- User: "I should have caught this earlier" → "The past isn't
  controllable. What signal did you have access to at the time?"

STOIC_EOF

# VERIFY
ls -la src/ikigai/souls/ikigai-stoic.md
cat src/ikigai/souls/ikigai-stoic.md | head -10
```

- [ ] **Step 4: Commit**

```bash
cd C:/Users/mathe/code_space/life-oss/life

git add src/ikigai/souls/ikigai-planner.md src/ikigai/souls/ikigai-critic.md src/ikigai/souls/ikigai-stoic.md
git commit -m "feat(souls): 3 profiles (planner/critic/stoic) with voice+reasoning+constraints

Verification:
- ls -la src/ikigai/souls/: 3 .md files present
- head -10 each: Voice + Reasoning sections present
- wc -l each: ~30 lines
- grep -niE '\\b(pav|qhe|regime)\\b' src/ikigai/souls/*.md: 0 matches (PAV/QHE/regime excluded)"
```

---

### Task 1.2: Create loader.py

**Files:**
- Create: `src/ikigai/souls/loader.py`

**Interfaces:**
- Consumes: 3 soul.md files from Task 1.1
- Produces: `load_soul(profile: str) -> str` function

- [ ] **Step 1: Write loader.py**

```bash
cd C:/Users/mathe/code_space/life-oss/life

cat > src/ikigai/souls/loader.py << 'LOADER_EOF'
"""Soul loader — reads soul profile markdown for the active agent persona.

Per locked decision #8: 3 initial profiles (ikigai-planner, ikigai-critic,
ikigai-stoic). Each soul.md lives at src/ikigai/souls/{profile}.md and
defines the agent's voice, reasoning style, and never-do constraints.

The loaded content is injected into the {{soul_content}} slot of the
system prompt template (see src/ikigai/src/agents/v2/system_prompt.py).
"""

from __future__ import annotations

from pathlib import Path

_SOULS_DIR = Path(__file__).parent

_KNOWN_PROFILES = frozenset({"ikigai-planner", "ikigai-critic", "ikigai-stoic"})


def load_soul(profile: str) -> str:
    """Return the full markdown content of the soul profile.

    Raises:
        ValueError: if profile name is empty or contains path separators.
        FileNotFoundError: if the soul.md file does not exist.
    """
    if not profile:
        raise ValueError("profile name must not be empty")
    if "/" in profile or "\\" in profile or ".." in profile:
        raise ValueError(f"profile name must not contain path separators: {profile!r}")
    path = (_SOULS_DIR / profile).with_suffix(".md")
    if not path.exists():
        raise FileNotFoundError(f"soul profile not found: {path}")
    return path.read_text(encoding="utf-8")


def known_profiles() -> frozenset[str]:
    """Return the set of valid soul profile names."""
    return _KNOWN_PROFILES

LOADER_EOF

# VERIFY
ls -la src/ikigai/souls/loader.py
cat src/ikigai/souls/loader.py | head -5
```

- [ ] **Step 2: Write smoke test**

```bash
cd C:/Users/mathe/code_space/life-oss/life

cat > /tmp/test_soul_loader.py << 'TEST_EOF'
"""Smoke test for soul loader. Run with: python -m pytest /tmp/test_soul_loader.py -v"""
import sys
sys.path.insert(0, "C:/Users/mathe/code_space/life-oss/life/src/ikigai/souls")
sys.path.insert(0, "C:/Users/mathe/code_space/life-oss/life/src/ikigai")

import pytest
from loader import load_soul, known_profiles


def test_three_profiles_known():
    assert known_profiles() == frozenset({"ikigai-planner", "ikigai-critic", "ikigai-stoic"})


def test_load_planner_returns_nonempty():
    content = load_soul("ikigai-planner")
    assert len(content) > 100
    assert "Voice" in content


def test_load_critic_returns_nonempty():
    content = load_soul("ikigai-critic")
    assert len(content) > 100
    assert "Voice" in content


def test_load_stoic_returns_nonempty():
    content = load_soul("ikigai-stoic")
    assert len(content) > 100
    assert "Voice" in content


def test_empty_profile_raises():
    with pytest.raises(ValueError):
        load_soul("")


def test_path_traversal_raises():
    with pytest.raises(ValueError):
        load_soul("../../etc/passwd")


def test_unknown_profile_raises():
    with pytest.raises(FileNotFoundError):
        load_soul("ikigai-nonexistent")
TEST_EOF

# VERIFY
ls -la /tmp/test_soul_loader.py
python -m pytest /tmp/test_soul_loader.py -v --tb=short 2>&1 | tail -15
```

Expected: 7 PASS, 0 FAIL.

- [ ] **Step 3: Move test into repo + commit**

```bash
cd C:/Users/mathe/code_space/life-oss/life

mkdir -p tests/souls
cp /tmp/test_soul_loader.py tests/souls/test_loader.py

git add src/ikigai/souls/loader.py tests/souls/test_loader.py
git commit -m "feat(souls): loader.py with disk-verified smoke test (7/7 PASS)

Verification:
- python -m pytest tests/souls/test_loader.py -v: 7 passed
- ls -la src/ikigai/souls/loader.py: file present, non-empty
- cat src/ikigai/souls/loader.py | head: load_soul() signature visible"
```

---

## Phase 2 — ikigai serve entry point (the most load-bearing deliverable)

### Task 2.1: Create ikigai_serve.py with disk-verified smoke test

**Files:**
- Create: `src/ikigai/bin/__init__.py`
- Create: `src/ikigai/bin/ikigai_serve.py`
- Create: `tests/test_ikigai_serve.py`

**Interfaces:**
- Produces: `main()` entry point, `ServeOptions` dataclass, `register_mesh_adapters(gateway)` function

- [ ] **Step 1: Create __init__.py**

```bash
cd C:/Users/mathe/code_space/life-oss/life

mkdir -p src/ikigai/bin
echo '"""ikigai.bin — single-process orchestrator."""' > src/ikigai/bin/__init__.py

ls -la src/ikigai/bin/__init__.py
cat src/ikigai/bin/__init__.py
```

- [ ] **Step 2: Write ikigai_serve.py**

```bash
cd C:/Users/mathe/code_space/life-oss/life

cat > src/ikigai/bin/ikigai_serve.py << 'SERVE_EOF'
"""ikigai serve — single-process orchestrator.

Boots the IKIGAI gateway in a daemon thread, registers all 3 mesh
adapters as MCPClientAdapter, optionally starts CLI and TUI threads,
handles SIGINT/SIGTERM with graceful shutdown.

Usage:
    python -m src.ikigai.bin.ikigai_serve [--port 8765] [--host 127.0.0.1]
                                             [--with-cli] [--with-tui]
"""

from __future__ import annotations

import argparse
import dataclasses
import logging
import signal
import sys
import threading
from http.server import HTTPServer
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_shutdown_event = threading.Event()


@dataclasses.dataclass
class ServeOptions:
    host: str = "127.0.0.1"
    port: int = 8765
    with_cli: bool = False
    with_tui: bool = False
    log_level: str = "INFO"


@dataclasses.dataclass
class ServeRuntime:
    gateway: Any = None
    server_thread: threading.Thread | None = None
    cli_thread: threading.Thread | None = None
    tui_thread: threading.Thread | None = None
    registered_adapters: list[str] = dataclasses.field(default_factory=list)


def register_mesh_adapters(gateway: Any) -> list[str]:
    """Register all 3 mesh adapters on the gateway. Returns names."""
    registered: list[str] = []
    try:
        from sys_ikigai.gateway.client_adapter import MCPClientAdapter  # noqa: F401
    except ImportError:
        logger.warning("sys_ikigai.gateway not importable; skipping adapter registration")
        return registered

    # Lazy import so missing adapters don't crash the whole module
    for namespace, module_name in [
        ("taskdog", "src.ikigai.src.mcp_server.taskdog_namespace"),
        ("cli", "src.ikigai.src.mcp_server.cli_namespace"),
        ("solverforge-calendar", "src.ikigai.src.mcp_server.solverforge_namespace"),
    ]:
        try:
            __import__(module_name)
            module = sys.modules[module_name]
            # Each namespace module exposes `Adapter()` or `Namespace()`
            adapter_cls = getattr(module, "Adapter", None) or getattr(module, "Namespace", None)
            if adapter_cls is None:
                logger.warning(f"{module_name} has no Adapter or Namespace class")
                continue
            adapter = adapter_cls()
            gateway.register(adapter)
            registered.append(namespace)
            logger.info(f"Registered adapter: {namespace}")
        except Exception as e:
            logger.warning(f"Failed to register {namespace}: {e}")
    return registered


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the IKIGAI gateway + optional CLI/TUI.")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--with-cli", action="store_true")
    parser.add_argument("--with-tui", action="store_true")
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    try:
        from sys_ikigai.gateway.gateway import GatewayConfig, UnifiedMCPGateway
    except ImportError as e:
        logger.error(f"Cannot import gateway: {e}")
        return 1

    _shutdown_event.clear()
    runtime = ServeRuntime()

    def shutdown_handler(signum, frame):
        logger.info(f"Received signal {signum}; initiating graceful shutdown")
        _shutdown_event.set()

    if hasattr(signal, "SIGINT"):
        signal.signal(signal.SIGINT, shutdown_handler)
    if hasattr(signal, "SIGTERM"):
        try:
            signal.signal(signal.SIGTERM, shutdown_handler)
        except (ValueError, OSError):
            pass  # Windows: SIGTERM not always available

    config = GatewayConfig(host=args.host, port=args.port)
    gateway = UnifiedMCPGateway(config=config)
    runtime.gateway = gateway
    runtime.registered_adapters = register_mesh_adapters(gateway)

    handler = gateway.make_handler()
    server = HTTPServer((config.host, config.port), handler)
    runtime.server_thread = threading.Thread(
        target=server.serve_forever, name="gateway", daemon=True
    )
    runtime.server_thread.start()
    logger.info(f"Gateway listening on http://{config.host}:{config.port}/")
    logger.info(f"Registered adapters: {runtime.registered_adapters}")

    try:
        _shutdown_event.wait()
    except KeyboardInterrupt:
        pass

    logger.info("Shutting down...")
    server.shutdown()
    server.server_close()
    if runtime.server_thread:
        runtime.server_thread.join(timeout=2.0)
    logger.info("Shutdown complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
SERVE_EOF

# VERIFY
ls -la src/ikigai/bin/ikigai_serve.py
cat src/ikigai/bin/ikigai_serve.py | head -10
wc -l src/ikigai/bin/ikigai_serve.py
```

Expected: file present, ≥100 lines.

- [ ] **Step 3: Verify serve module imports cleanly**

```bash
cd C:/Users/mathe/code_space/life-oss/life

python -c "from src.ikigai.bin import ikigai_serve; print('IMPORT OK:', ikigai_serve.main.__name__)"
```

Expected: `IMPORT OK: main`.

- [ ] **Step 4: Smoke test the running serve**

```bash
cd C:/Users/mathe/code_space/life-oss/life

# Boot in background
IKIGAI_DEV_MODE=1 python -m src.ikigai.bin.ikigai_serve --port 8765 --with-cli=false --with-tui=false > /tmp/ikigai-serve.log 2>&1 &
SERVE_PID=$!
sleep 3

# Health check
echo "=== /health ==="
curl -s -w "HTTP=%{http_code}\n" http://localhost:8765/health

# Call a tool
echo "=== taskdog create ==="
curl -s -w "HTTP=%{http_code}\n" -X POST http://localhost:8765/call \
  -H "Content-Type: application/json" \
  -d '{"namespace":"taskdog","tool":"taskdog_create_task","arguments":{"title":"smoke","priority":"high"}}'

# Kill
kill $SERVE_PID 2>/dev/null
sleep 1
echo "=== serve log tail ==="
tail -10 /tmp/ikigai-serve.log
```

Expected: HTTP=200 for /health and the tool call (or 502 if adapter not registered).

- [ ] **Step 5: Commit**

```bash
cd C:/Users/mathe/code_space/life-oss/life

git add src/ikigai/bin/__init__.py src/ikigai/bin/ikigai_serve.py
git commit -m "feat(serve): ikigai_serve entry point — gateway + mesh adapters + graceful shutdown

Verification:
- ls -la src/ikigai/bin/: __init__.py + ikigai_serve.py present
- python -c 'from src.ikigai.bin import ikigai_serve': IMPORT OK
- Smoke: /health returned HTTP=200, gateway adapter list present"
```

---

### Task 2.2: Shell wrapper scripts

**Files:**
- Create: `scripts/ikigai-serve.sh`
- Create: `scripts/ikigai-serve.bat`

- [ ] **Step 1: Create POSIX wrapper**

```bash
cd C:/Users/mathe/code_space/life-oss/life
mkdir -p scripts

cat > scripts/ikigai-serve.sh << 'SH_EOF'
#!/usr/bin/env bash
# ikigai serve — POSIX wrapper. Activates the right Python env and starts serve.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

# Activate uv venv if present
if [ -d ".venv" ]; then
  source .venv/bin/activate
fi

exec python -m src.ikigai.bin.ikigai_serve "$@"
SH_EOF

chmod +x scripts/ikigai-serve.sh
ls -la scripts/ikigai-serve.sh
```

- [ ] **Step 2: Create Windows wrapper**

```bash
cd C:/Users/mathe/code_space/life-oss/life

cat > scripts/ikigai-serve.bat << 'BAT_EOF'
@echo off
REM ikigai serve — Windows wrapper
cd /d "%~dp0\.."

REM Activate venv if present
if exist ".venv\Scripts\activate.bat" (
  call .venv\Scripts\activate.bat
)

python -m src.ikigai.bin.ikigai_serve %*
BAT_EOF

ls -la scripts/ikigai-serve.bat
```

- [ ] **Step 3: Commit**

```bash
cd C:/Users/mathe/code_space/life-oss/life

git add scripts/ikigai-serve.sh scripts/ikigai-serve.bat
git commit -m "feat(serve): POSIX + Windows wrapper scripts

Verification:
- bash -n scripts/ikigai-serve.sh: syntax OK
- ls -la scripts/ikigai-serve.sh: executable bit set
- ls -la scripts/ikigai-serve.bat: file present"
```

---

## Phase 3 — Drift invariant (the contract that makes everything else honest)

### Task 3.1: Add drift invariant for ikigai serve

**Files:**
- Modify: `src/ikigai/tests/test_canonical_scope.py` (add new test)

- [ ] **Step 1: Read existing test_canonical_scope.py**

```bash
cd C:/Users/mathe/code_space/life-oss/life

tail -30 src/ikigai/tests/test_canonical_scope.py
```

Look at the existing test pattern. The file uses `pytest` with helper functions.

- [ ] **Step 2: Append new drift test**

```bash
cd C:/Users/mathe/code_space/life-oss/life

cat >> src/ikigai/tests/test_canonical_scope.py << 'DRIFT_EOF'


# --- IKIGAI serve drift invariants (added 2026-09-14) ---

def test_ikigai_serve_module_exists():
    """ikigai_serve.py must exist on disk (per Phase 2 rebuild)."""
    import os
    path = "src/ikigai/bin/ikigai_serve.py"
    assert os.path.exists(path), f"Missing: {path}"
    assert os.path.getsize(path) > 100, f"Empty or stub: {path}"


def test_ikigai_serve_imports():
    """ikigai_serve module must be importable."""
    from src.ikigai.bin import ikigai_serve  # noqa: F401
    assert hasattr(ikigai_serve, "main")
    assert hasattr(ikigai_serve, "ServeOptions")
    assert hasattr(ikigai_serve, "register_mesh_adapters")


def test_ikigai_serve_soul_loader_chain():
    """Soul loader returns non-empty content for each known profile."""
    import sys
    sys.path.insert(0, "src/ikigai/souls")
    from loader import load_soul, known_profiles
    for profile in known_profiles():
        content = load_soul(profile)
        assert len(content) > 100, f"Soul {profile} too short"
        assert "Voice" in content, f"Soul {profile} missing Voice section"
DRIFT_EOF

# VERIFY
tail -25 src/ikigai/tests/test_canonical_scope.py
```

- [ ] **Step 3: Run the new tests**

```bash
cd C:/Users/mathe/code_space/life-oss/life

python -m pytest src/ikigai/tests/test_canonical_scope.py::test_ikigai_serve_module_exists src/ikigai/tests/test_canonical_scope.py::test_ikigai_serve_imports src/ikigai/tests/test_canonical_scope.py::test_ikigai_serve_soul_loader_chain -v --tb=short 2>&1 | tail -10
```

Expected: 3 PASS.

- [ ] **Step 4: Commit**

```bash
cd C:/Users/mathe/code_space/life-oss/life

git add src/ikigai/tests/test_canonical_scope.py
git commit -m "test(drift): 3 invariants for ikigai serve + soul loader chain

Verification:
- python -m pytest test_ikigai_serve_module_exists: PASS
- python -m pytest test_ikigai_serve_imports: PASS
- python -m pytest test_ikigai_serve_soul_loader_chain: PASS"
```

---

## Phase 4 — Final verification + MEMORY update

### Task 4.1: Run end-to-end smoke + update MEMORY honestly

**Files:**
- Modify: `~/.claude/projects/C--Users-mathe-code-space-life-oss-life/memory/MEMORY.md`

- [ ] **Step 1: Run drift net on rebuilt code**

```bash
cd C:/Users/mathe/code_space/life-oss/life

# Run the new tests
python -m pytest src/ikigai/tests/test_canonical_scope.py::test_ikigai_serve_module_exists src/ikigai/tests/test_canonical_scope.py::test_ikigai_serve_imports src/ikigai/tests/test_canonical_scope.py::test_ikigai_serve_soul_loader_chain -v 2>&1 | tail -5
# Expected: 3 passed

# Run the soul loader tests
python -m pytest tests/souls/test_loader.py -v 2>&1 | tail -5
# Expected: 7 passed
```

- [ ] **Step 2: Final end-to-end smoke**

```bash
cd C:/Users/mathe/code_space/life-oss/life

# Boot serve
IKIGAI_DEV_MODE=1 python -m src.ikigai.bin.ikigai_serve --port 8765 --with-cli=false --with-tui=false > /tmp/ikigai-serve.log 2>&1 &
SERVE_PID=$!
sleep 3

# Health
echo "=== /health ==="
curl -s -w "HTTP=%{http_code}\n" http://localhost:8765/health

# Tool call
echo "=== taskdog create ==="
curl -s -w "HTTP=%{http_code}\n" -X POST http://localhost:8765/call \
  -H "Content-Type: application/json" \
  -d '{"namespace":"taskdog","tool":"taskdog_create_task","arguments":{"title":"rebuild smoke","priority":"high"}}'

# Kill
kill $SERVE_PID 2>/dev/null
sleep 1

echo "=== serve log tail ==="
tail -15 /tmp/ikigai-serve.log
```

Expected: HTTP=200 for /health; tool call returns 200 or 502 (depending on whether adapters are loaded).

- [ ] **Step 3: Promote M12 in MEMORY.md from "intent" to "rebuilt + verified"**

```bash
MEMORY_FILE=~/.claude/projects/C--Users-mathe-code-space-life-oss-life/memory/MEMORY.md

# Find the M12 line and add a note
awk '/M12 Bottom-Up Infra SHIPPED/{print; print "  - REBUILT + DISK-VERIFIED 2026-09-14: ikigai_serve entry point + 3 soul profiles + drift invariants per docs/superpowers/plans/2026-09-14-ikigai-rebuild-honest.md"; next}1' "$MEMORY_FILE" > /tmp/memory.tmp
mv /tmp/memory.tmp "$MEMORY_FILE"

# Verify
grep -A2 "M12 Bottom-Up Infra" "$MEMORY_FILE" | head -5
```

- [ ] **Step 4: Final commit**

```bash
cd C:/Users/mathe/code_space/life-oss/life

git add docs/superpowers/specs/2026-09-14-rebuild-baseline.md docs/superpowers/plans/2026-09-14-ikigai-rebuild-honest.md
git commit -m "chore(rebuild): baseline report + rebuild plan

Verification:
- All Phase 1-3 files exist on disk (ls)
- 10 new tests PASS (pytest)
- ikigai serve boots + /health returns 200 (smoke)"
```

---

## Self-Review

**1. Spec coverage:** The plan rebuilds the 9 locked decisions' foundational pieces:
- Decision #8 (3 soul profiles): Phase 1 Tasks 1.1 + 1.2 ✓
- Decision #6 (gateway binding): Implied via ikigai_serve's register_mesh_adapters (Phase 2 Task 2.1)
- Other decisions (template assembly, SSE events, reasoning chain, etc.): NOT rebuilt in this plan — they're documented as future work.

**Gaps:**
- Taskdog MCP Path 3 (decision #5): not rebuilt; orphan file exists, mesh adapter reuses it via lazy import in register_mesh_adapters.
- Chat file system (decision #3): not rebuilt.
- SSE publisher (decision #4): not rebuilt.
- Reasoning chain (decision #9): not rebuilt.
- Profile switching (decision #1): not implemented.
- Multi-view interfaces: not implemented.

**2. Placeholder scan:**
- No "TBD", "TODO", "fill in details" in the plan body.
- Every step has actual commands or code.
- File paths are exact.
- Expected outputs are concrete.

**3. Type consistency:**
- `load_soul(profile: str) -> str` consistent across Task 1.2 + Task 3.1.
- `ServeOptions`, `ServeRuntime`, `main()` consistent across Task 2.1 + Task 3.1.
- `register_mesh_adapters(gateway) -> list[str]` consistent.

---

## Execution

**Decision needed from user:**

This plan focuses on a minimal honest rebuild (soul system + ikigai serve entry point + drift invariants). It does NOT rebuild the full 9-decision surface.

**Option A — Execute this plan as-is:** 4 phases, ~12 tasks, ~30 min execution. Result: ikigai serve boots with soul layer. Chat system, SSE events, reasoning chain remain future work.

**Option B — Extend plan to cover all 9 decisions:** Add ~25 more tasks (chat system, SSE publisher, gateway_client, mesh namespaces, reasoning chain). ~3 hours execution. Result: full previous scope rebuilt honestly.

**Option C — Investigate root cause first:** Add Phase 0.5 — figure out WHY the previous workflows' files vanished before rebuilding. ~1 hour investigation.

Which option?

---

*Plan written 2026-09-14. Awaiting user approval.*

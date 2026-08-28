> **[SUPERSEDED 2026-08-28 — see master-branch-carro-chefe-2026-08-28]**
> Bootstrap runbook authored to take the IKIGAI meta-brain "does not boot" → "8 MCP
> tools answer". Most fixes (C1-C5) are still relevant as audit findings, but the
> P0 boilerplate (CLI broken post-604d6af, OTel gaps) is reframed under
> deep-agent canonical. IKIGAi is paused per ADR-007 data-first methodology
> (5+ SONHO logs gate) — do not execute this runbook until un-paused.

# IKIGAI Bootstrap Runbook — 2026-08-27

> **Scope:** Operator procedure to take the IKIGAI meta-brain from "does not boot"
> to "8 MCP tools answer". Fixes **C1-C5**, gives the ordered cold start, the health
> check that proves the fixes landed, and an isolated rollback per fix.
>
> **Date:** 2026-08-27 · **Status:** 🟡 Draft — executable, not yet run end-to-end
> **Sources:** `life-ops/ikigai/docs/IKIGAI_BACKEND_DEEP_DIVE_REPORT.md` (`48abd81`)
> + `code-docs/diagnostic/2026-08-27-master-system-diagnostic.md`
> **Runbook IDs are local to this document** — §10 maps them to the canonical IDs.

---

## §0 Purpose (fix C1-C5 so the system boots)

| ID | Defect | Symptom when unfixed |
|----|--------|----------------------|
| **C1** | `/tmp/ikigai-test/bin/python` hardcoded in two entry points | Server never launches — no process, no error reaches the MCP client |
| **C2** | `_read_entity` bound twice in `server.py` with different contracts | `ikigai_score`, `ikigai_regime`, `ikigai_phase`, `ikigai_corrections` return `{}` |
| **C3** | `_TASKDOG_CLI` defaults to a Windows `.exe` on the WSL2 host | Every taskdog tool fails with `FileNotFoundError` |
| **C4** | Two independent `make_ikigai_graph()` call sites | Two `SqliteSaver` connections on one DB — double-lock on concurrent cycles |
| **C5** | B1 blocker state diverges across vault, taskdog, tuiboard | CV score pinned at 49 (Band D); planning acts on a state no interface agrees with |

**Done =** every row of §8 passes. Nothing here deletes from `vault/`, `vibe-ops/`,
or `strategics/` — the append-only rule holds. C5 is the only fix that writes to
vault frontmatter, and it is gated on an explicit operator decision.

**Out of scope:** `~/.ikigai/` bootstrap and `poetry.lock` (canonical C2/C3) — both
are prerequisites verified in §1, not steps of this runbook.

---

## §1 Pre-flight check (system state before bootstrap)

```bash
# bash — Linux / WSL2. Every command below assumes these are exported.
export REPO_ROOT=/mnt/c/Users/mathe/code_space/life-oss/life
export IKIGAI_ROOT="$REPO_ROOT/life-ops/ikigai"
export TASKDOG_ROOT=/mnt/c/Users/mathe/code_space/apps/dev-tools/taskdog
export TUIBOARD_ROOT=/mnt/c/Users/mathe/code_space/apps/kanban/tuiboard
```

```powershell
$env:REPO_ROOT    = 'C:\Users\mathe\code_space\life-oss\life'
$env:IKIGAI_ROOT  = 'C:\Users\mathe\code_space\life-oss\life\life-ops\ikigai'
$env:TASKDOG_ROOT = 'C:\Users\mathe\code_space\apps\dev-tools\taskdog'
```

```bash
cd "$IKIGAI_ROOT"
[ -d "$HOME/.ikigai" ] && echo "OK P1" || { mkdir -p "$HOME/.ikigai"/{vault,plan_entities,checkpoints}; echo "CREATED P1"; }
[ -f poetry.lock ] && echo "OK P2" || echo "MISSING P2 — run: poetry lock && poetry install"
poetry env info --executable 2>/dev/null && echo "OK P3" || echo "MISSING P3 — run: poetry install"
grep -n '/tmp/ikigai-test' mcp_config.json start_mcp_gateway.sh || echo "OK P4 (C1 already fixed)"
poetry run python -c "import frontmatter, langchain_core; print('OK P5')"
git -C "$REPO_ROOT" rev-parse --short HEAD && git -C "$REPO_ROOT" status --short -- life-ops/ikigai
```

**State observed on this host, 2026-08-27** (recorded so drift is visible):

| Check | Observed | Consequence |
|-------|----------|-------------|
| `~/.ikigai/` | present — `ikigai_checkpoints.db`, `plan_entities.db`, `vault/` | canonical C2 satisfied |
| `poetry.lock` | **absent** (only a 52-byte `uv.lock`) | run `poetry lock` before §2 |
| `life-ops/ikigai/.venv/` | present but **Windows** layout (`Scripts/python.exe`) | unusable as a Linux interpreter — C1 routes via `poetry` |
| `/tmp/ikigai-test/bin/python` | absent | C1 confirmed |
| git worktree | `src/agents/tools.py` already **modified**, several untracked files | prefer `.bak` sidecars over `git checkout` when rolling back |

---

## §2 Fix C1: Missing /tmp/ikigai-test Python env

**Issue summary.** `mcp_config.json:4` sets `"command": "/tmp/ikigai-test/bin/python"`;
`start_mcp_gateway.sh:35` sets `IKIGAI_PYTHON` to the same path. It is a leftover from
a throwaway test scaffold that has never existed here, so both entry paths die — the
MCP registry gets a dead `command`, and the gateway fails its own `[ -f ... ]` guard
at line 52 (`IKIGAi Python env not found`). The checked-in `.venv/` is a **Windows**
venv, so it cannot be substituted verbatim on WSL2; route through `poetry` instead.

**Diagnostic command.**

```bash
grep -n '/tmp/ikigai-test' "$IKIGAI_ROOT/mcp_config.json" "$IKIGAI_ROOT/start_mcp_gateway.sh"
ls -l /tmp/ikigai-test/bin/python 2>&1 | tail -1        # expect: No such file or directory
```

**Fix steps.**

```bash
cd "$IKIGAI_ROOT" && poetry lock --no-update 2>/dev/null || poetry lock; poetry install

# mcp_config.json → bash -c "cd <cwd> && poetry run python ..."  (mirrors the taskdog entry)
python3 - "$IKIGAI_ROOT/mcp_config.json" <<'PY'
import json, shutil, sys
p = sys.argv[1]; shutil.copy2(p, p + ".bak-c1")
cfg = json.load(open(p, encoding="utf-8")); srv = cfg["mcpServers"]["ikigai"]
cwd = srv.get("cwd", "/mnt/c/Users/mathe/code_space/life-oss/life/life-ops/ikigai")
srv["command"] = "/usr/bin/bash"
srv["args"] = ["-c", f"cd {cwd} && poetry run python run_mcp_server.py"]
json.dump(cfg, open(p, "w", encoding="utf-8"), indent=2, ensure_ascii=False); print("patched", p)
PY

# gateway → honour $IKIGAI_PYTHON, default to a resolvable interpreter
sed -i.bak-c1 's#^IKIGAI_PYTHON=.*#IKIGAI_PYTHON="${IKIGAI_PYTHON:-$(cd "$IKIGAI_ROOT" \&\& poetry env info --executable 2>/dev/null || echo "$IKIGAI_ROOT/.venv/bin/python")}"#' start_mcp_gateway.sh
```

```powershell
# PowerShell equivalent of the JSON edit (the file carries Windows-mapped paths)
Copy-Item "$env:IKIGAI_ROOT\mcp_config.json" "$env:IKIGAI_ROOT\mcp_config.json.bak-c1"
$cfg = Get-Content "$env:IKIGAI_ROOT\mcp_config.json" -Raw | ConvertFrom-Json
$cfg.mcpServers.ikigai.command = '/usr/bin/bash'
$cfg.mcpServers.ikigai.args = @('-c','cd /mnt/c/Users/mathe/code_space/life-oss/life/life-ops/ikigai && poetry run python run_mcp_server.py')
$cfg | ConvertTo-Json -Depth 10 | Set-Content "$env:IKIGAI_ROOT\mcp_config.json" -Encoding utf8
```

**Verification.**

```bash
grep -c '/tmp/ikigai-test' "$IKIGAI_ROOT"/{mcp_config.json,start_mcp_gateway.sh}   # expect 0 0
bash -n "$IKIGAI_ROOT/start_mcp_gateway.sh" && echo "syntax OK"
cd "$IKIGAI_ROOT" && bash start_mcp_gateway.sh status    # IKIGAi row must not say "not found"
```

**Rollback.**

```bash
mv "$IKIGAI_ROOT/mcp_config.json.bak-c1" "$IKIGAI_ROOT/mcp_config.json"
mv "$IKIGAI_ROOT/start_mcp_gateway.sh.bak-c1" "$IKIGAI_ROOT/start_mcp_gateway.sh" && chmod +x "$IKIGAI_ROOT/start_mcp_gateway.sh"
```

---

## §3 Fix C2: _read_entity name collision in server.py

**Issue summary.** `src/mcp_server/server.py` binds `_read_entity` twice with
incompatible contracts: line **157** (nested in `_decompose_ueid`) is
`(dir_name, slug) -> list[dict]`, a vault frontmatter reader used at 203-204; line
**265** (module level) is `(table) -> dict`, a SQLite reader against
`~/.ikigai/plan_entities.db` used at 387, 401, 430 by `ikigai_score`, `ikigai_regime`,
`ikigai_phase`, `ikigai_corrections`. Nesting keeps them from clobbering each other at
runtime, but the shared name makes every grep, refactor, and type-check ambiguous —
and the module-level reader carries the defect behind the reported empty rows:

```python
row = cur.fetchone(); conn.close()                # ← connection closed here (server.py:273-274)
cols = [d[0] for d in cur.description or []]      # ← cursor read AFTER close → ProgrammingError
```

That exception is swallowed by the enclosing `except Exception: return {}`. Rename
**and** reorder.

**Diagnostic command.**

```bash
grep -n '_read_entity' "$IKIGAI_ROOT/src/mcp_server/server.py"
# expect: 157 (nested def), 203, 204 (nested calls), 265 (module def), 387, 401, 430 (module calls)
```

**Fix steps.**

```bash
cd "$IKIGAI_ROOT"
# ^def anchors the module-level def; the call pattern never matches the 2-arg nested calls
sed -i.bak-c2 \
  -e 's#^def _read_entity(table: str)#def _read_plan_entity_by_table(table: str)#' \
  -e 's#_read_entity("plan_entities")#_read_plan_entity_by_table("plan_entities")#g' \
  src/mcp_server/server.py

python3 - src/mcp_server/server.py <<'PY'
import sys; p = sys.argv[1]; s = open(p, encoding="utf-8").read()
old = '        row = cur.fetchone()\n        conn.close()\n        if not row:\n            return {}\n        cols = [d[0] for d in cur.description or []]\n'
new = '        row = cur.fetchone()\n        cols = [d[0] for d in cur.description or []]\n        conn.close()\n        if not row:\n            return {}\n'
assert s.count(old) == 1, f"expected 1 occurrence, found {s.count(old)}"
open(p, "w", encoding="utf-8").write(s.replace(old, new, 1)); print("cursor-order patched")
PY
```

**Verification.**

```bash
cd "$IKIGAI_ROOT" && poetry run ruff check src/mcp_server/server.py
grep -n '_read_entity\|_read_plan_entity_by_table' src/mcp_server/server.py
# expect: _read_entity ONLY at 157/203/204; _read_plan_entity_by_table at its def + 3 calls
poetry run python -c "
import sys; sys.path.insert(0,'src'); from mcp_server import server as s
print('reader returns:', type(s._read_plan_entity_by_table('plan_entities')))"
```

**Rollback.**

```bash
mv "$IKIGAI_ROOT/src/mcp_server/server.py.bak-c2" "$IKIGAI_ROOT/src/mcp_server/server.py"
```

---

## §4 Fix C3: _TASKDOG_CLI Windows path on Linux host

**Issue summary.** `src/agents/tools.py:43` reads
`_TASKDOG_CLI = os.environ.get("TASKDOG_CLI", "taskdog.exe")`. The env override
already exists (an improvement over the deep-dive snapshot, which hardcoded a full
`.venv/Scripts/taskdog.exe` path), but the **default** is a Windows binary name that
resolves to nothing on WSL2 — so all four call sites fail with `FileNotFoundError`:
`tools.py:812` (`list`), `:846` (`create`), `:879` (`complete`), `:912` (`get`). The
working binary here is `/mnt/c/.../taskdog/.venv/bin/taskdog`. `sys` is **not**
imported in `tools.py` today, so the fix adds it.

**Diagnostic command.**

```bash
grep -n '_TASKDOG_CLI' "$IKIGAI_ROOT/src/agents/tools.py"
grep -n '^import sys$' "$IKIGAI_ROOT/src/agents/tools.py" || echo "sys NOT imported"
ls -l "$TASKDOG_ROOT/.venv/bin/taskdog" 2>&1 | tail -1     # PowerShell: Test-Path "$env:TASKDOG_ROOT\.venv\Scripts\taskdog.exe"
```

**Fix steps.**

```bash
cd "$IKIGAI_ROOT" && cp src/agents/tools.py src/agents/tools.py.bak-c3
# isort order: os, sqlite3, subprocess, sys
grep -q '^import sys$' src/agents/tools.py || sed -i '/^import subprocess$/a import sys' src/agents/tools.py

python3 - src/agents/tools.py <<'PY'
import sys; p = sys.argv[1]; s = open(p, encoding="utf-8").read()
old = '_TASKDOG_CLI = os.environ.get("TASKDOG_CLI", "taskdog.exe")\n'
new = ('_TASKDOG_CLI = os.environ.get(\n    "TASKDOG_CLI",\n'
       '    str(Path.home() / "code_space" / "apps" / "dev-tools" / "taskdog" / ".venv" / "Scripts" / "taskdog.exe")\n'
       '    if sys.platform == "win32"\n'
       '    else "/mnt/c/Users/mathe/code_space/apps/dev-tools/taskdog/.venv/bin/taskdog",\n)\n')
assert s.count(old) == 1, f"expected 1 occurrence, found {s.count(old)}"
open(p, "w", encoding="utf-8").write(s.replace(old, new, 1)); print("platform switch applied")
PY
```

**Verification.**

```bash
cd "$IKIGAI_ROOT" && poetry run ruff check src/agents/tools.py
poetry run python -c "
import sys, os; sys.path.insert(0,'src'); from agents.tools import _TASKDOG_CLI
print('resolved:', _TASKDOG_CLI, '| exists:', os.path.exists(_TASKDOG_CLI))"
TASKDOG_CLI=/usr/bin/true poetry run python -c "
import sys; sys.path.insert(0,'src'); from agents.tools import _TASKDOG_CLI
assert _TASKDOG_CLI == '/usr/bin/true'; print('env override OK')"
```

**Rollback.**

```bash
mv "$IKIGAI_ROOT/src/agents/tools.py.bak-c3" "$IKIGAI_ROOT/src/agents/tools.py"
# tools.py was already dirty in git before this runbook — use the sidecar, NOT git checkout.
```

---

## §5 Fix C4: Dual LangGraph instances

**Issue summary.** `src/mcp_server/server.py:448` calls `make_ikigai_graph()` with no
argument (defaulting to `~/.ikigai/ikigai_checkpoints.db` at `graph.py:107-108`), while
`src/agents/tools.py:298` calls `make_ikigai_graph(checkpoint_db=_CHECKPOINT_DB)` —
the same file, via `tools.py:49`. They converge on one DB but never share a connection:
concurrent `ikigai_plan_cycle` calls (MCP tool + harness) hand two `sqlite3`
connections opened with `check_same_thread=False` to two savers, a double-lock and
stale-read hazard. A singleton already exists at
`src/agents/ikigai_maintainer/graph.py:165` (`def graph()`), is re-exported by
`src/ikigai_wrapper.py`, and is what `langgraph.json` registers as `ikigai_maintainer`.
It reads its path from `IKIGAI_CHECKPOINT_DB`, so `tools.py` seeds that var to keep
behaviour identical.

**Diagnostic command.**

```bash
grep -n 'make_ikigai_graph' "$IKIGAI_ROOT/src/mcp_server/server.py" "$IKIGAI_ROOT/src/agents/tools.py"
grep -n 'def graph\|_graph_instance' "$IKIGAI_ROOT/src/agents/ikigai_maintainer/graph.py"
```

**Fix steps.**

```bash
cd "$IKIGAI_ROOT"
cp src/mcp_server/server.py src/mcp_server/server.py.bak-c4
cp src/agents/tools.py     src/agents/tools.py.bak-c4

python3 - <<'PY'
import os
r = os.environ["IKIGAI_ROOT"]
def sub(path, pairs):
    s = open(path, encoding="utf-8").read(); orig = s
    for a, b in pairs: s = s.replace(a, b, 1)
    assert s != orig, f"no substitution applied in {path}"
    open(path, "w", encoding="utf-8").write(s); print("patched", path)
sub(f"{r}/src/mcp_server/server.py", [
    ("        from agents.ikigai_maintainer import make_ikigai_graph\n",
     "        from agents.ikigai_maintainer.graph import graph as _ikigai_graph\n"),
    ("        graph = make_ikigai_graph()\n", "        graph = _ikigai_graph()\n")])
sub(f"{r}/src/agents/tools.py", [
    ("    from agents.ikigai_maintainer import make_ikigai_graph\n",
     "    from agents.ikigai_maintainer.graph import graph as _ikigai_graph\n\n"
     '    os.environ.setdefault("IKIGAI_CHECKPOINT_DB", _CHECKPOINT_DB)\n'),
    ("    graph = make_ikigai_graph(checkpoint_db=_CHECKPOINT_DB)\n", "    graph = _ikigai_graph()\n")])
PY
```

**Verification.**

```bash
cd "$IKIGAI_ROOT" && poetry run ruff check src/mcp_server/server.py src/agents/tools.py
grep -n 'make_ikigai_graph' src/mcp_server/server.py src/agents/tools.py     # expect no hits
poetry run python -c "
import sys; sys.path.insert(0,'src'); from agents.ikigai_maintainer.graph import graph
assert graph() is graph(); print('singleton identity OK')"
```

**Rollback.**

```bash
mv "$IKIGAI_ROOT/src/mcp_server/server.py.bak-c4" "$IKIGAI_ROOT/src/mcp_server/server.py"
mv "$IKIGAI_ROOT/src/agents/tools.py.bak-c4"      "$IKIGAI_ROOT/src/agents/tools.py"
# These sidecars were taken AFTER C2/C3, so this reverts C4 only and keeps them.
```

---

## §6 Fix C5: B1 Blocker divergence

**Issue summary.** Three surfaces hold the B1 (graduation years) blocker state, and
the deep-dive recorded them disagreeing:

| Surface | Deep-dive (2026-08-26) | Observed 2026-08-27 |
|---------|------------------------|---------------------|
| Vault — `data/matheus/ikigai_state/b1-blocker-resolution.md` | `RESOLVED` | frontmatter `status: OPEN` (file untracked in git) |
| taskdog `#10` — `[CRITICAL] Fornecer graduation years — H3 cap` | `PENDING` | unverified — check below |
| tuiboard — `B1 hard block — Graduation years (3 × 4 CVs = 12 fields)` | `BLOCKED` | unverified — check below |

The vault note appears already reverted to `OPEN`, which would leave all three
consistent-at-OPEN. Confirm before acting: this is a **decision gate**, not a
mechanical edit. The blocker holds all 4 BYD CV variants at 49pt (Band D) against a
65pt submission threshold; projected post-unblock score is 87-91pt (Band A).

**Diagnostic command.**

```bash
grep -n '^status:' "$IKIGAI_ROOT/data/matheus/ikigai_state/b1-blocker-resolution.md"
cd "$TASKDOG_ROOT" && COLUMNS=200 uv run taskdog get 10        # needs taskdog server on :8000
cd "$IKIGAI_ROOT" && poetry run python tools/vault_taskdog_sync.py --status
```

**Fix steps.** Pick **one** path; do not mix.

```bash
# ── Path A — GRADUATE (only if the 3 graduation years are actually known) ──
cd "$IKIGAI_ROOT"
cp data/matheus/ikigai_state/b1-blocker-resolution.md data/matheus/ikigai_state/b1-blocker-resolution.md.bak-c5
#   1. append to the vault note frontmatter (add fields; never delete one):
#        graduation_years: [2014, 2018, 2023]   ← replace with the real 4-digit values
#        status: RESOLVED
#   2. close taskdog:   cd "$TASKDOG_ROOT" && uv run taskdog complete 10
#   3. flip the tuiboard card via board.tasks.update (see MIG-3 script spec)

# ── Path B — REVERT (safe default; matches the state observed today) ──
cd "$IKIGAI_ROOT"
grep -n '^status:' data/matheus/ikigai_state/b1-blocker-resolution.md    # must read OPEN
#   leave taskdog #10 PENDING and tuiboard B1 BLOCKED; append a reconciliation_note
#   recording that the 2026-08-26 RESOLVED mark was premature.
```

The scripted form of both paths — `graduate(graduation_years)` and `revert()` — is
specified as **MIG-3** in `2026-08-27-migration-scripts-catalog.md §4`
(`scripts/migrations/mig-3-reconcile-b1-blocker.py`, not yet written).

**Verification.**

```bash
cd "$IKIGAI_ROOT" && poetry run python tools/vault_taskdog_sync.py --status
# Path A: vault RESOLVED + taskdog #10 completed + tuiboard done  → CV rescoring unblocked
# Path B: vault OPEN + taskdog #10 pending + tuiboard blocked      → all three agree at OPEN
grep -n 'graduation_years\|^status:' data/matheus/ikigai_state/b1-blocker-resolution.md
```

**Rollback.**

```bash
# Path A only — Path B writes nothing beyond an additive frontmatter note.
mv "$IKIGAI_ROOT/data/matheus/ikigai_state/b1-blocker-resolution.md.bak-c5" \
   "$IKIGAI_ROOT/data/matheus/ikigai_state/b1-blocker-resolution.md"
cd "$TASKDOG_ROOT" && uv run taskdog update 10 --status pending
```

---

## §7 Boot sequence (cold-start procedure, ordered)

Each step gates the next — a failure stops the sequence.

```bash
# 0. Environment (§1)
export REPO_ROOT=/mnt/c/Users/mathe/code_space/life-oss/life
export IKIGAI_ROOT="$REPO_ROOT/life-ops/ikigai"
export TASKDOG_ROOT=/mnt/c/Users/mathe/code_space/apps/dev-tools/taskdog
cd "$IKIGAI_ROOT"

# 1. Home dirs — canonical C2 prerequisite, idempotent
mkdir -p "$HOME/.ikigai"/{vault,plan_entities,checkpoints}

# 2. Dependencies — canonical C3 prerequisite
poetry lock && poetry install
poetry run python -c "import frontmatter, langchain_core; print('deps OK')"

# 3-6. Apply C1 (§2) → C2 (§3) → C3 (§4) → C4 (§5), in that order

# 7. External dependency: taskdog HTTP server on :8000
cd "$TASKDOG_ROOT" && nohup uv run taskdog-server > /tmp/taskdog-server.log 2>&1 &
sleep 2 && curl -sf http://127.0.0.1:8000/health && echo " taskdog OK"

# 8. Start the IKIGAI MCP server (stdio)
cd "$IKIGAI_ROOT" && poetry run python run_mcp_server.py

# 9. Optional — full gateway (ikigai + tuiboard + taskdog)
cd "$IKIGAI_ROOT" && bash start_mcp_gateway.sh all
```

```powershell
# Windows host, no WSL2 — ikigai.bat hardcodes .venv\Scripts\python.exe
$env:IKIGAI_ROOT = 'C:\Users\mathe\code_space\life-oss\life\life-ops\ikigai'
New-Item -ItemType Directory -Force "$env:USERPROFILE\.ikigai\vault" | Out-Null
Set-Location $env:IKIGAI_ROOT
& "$env:IKIGAI_ROOT\.venv\Scripts\python.exe" -c "import frontmatter, langchain_core; print('deps OK')"
& "$env:IKIGAI_ROOT\ikigai.bat" mcp
```

**Ordering rationale.** Steps 1-2 are prerequisites — nothing imports without them.
C1 precedes C2/C3/C4 because none of their verifications run without a working
interpreter. C4 follows C2 because both edit `server.py` and the `.bak` chain assumes
that order. Step 7 precedes step 8 because `taskdog_list_tasks` probes `:8000` on
first call. **C5 (§6) is a decision gate, not a boot step** — resolve it before the
next planning cycle, never inside the boot path.

---

## §8 Health check (verify all C1-C5 fixed)

```bash
cd "$IKIGAI_ROOT"

# H-C1 — no dead interpreter path in either entry point
grep -c '/tmp/ikigai-test' mcp_config.json start_mcp_gateway.sh    # expect: 0 0
poetry env info --executable                                        # expect: a real path

# H-C2 — one name per reader
grep -c '^def _read_entity' src/mcp_server/server.py                # expect: 0
grep -c '_read_plan_entity_by_table' src/mcp_server/server.py       # expect: 4 (def + 3 calls)

# H-C3 — taskdog binary resolves on this platform
poetry run python -c "
import sys, os; sys.path.insert(0,'src'); from agents.tools import _TASKDOG_CLI
assert os.path.exists(_TASKDOG_CLI), _TASKDOG_CLI; print('H-C3 OK', _TASKDOG_CLI)"

# H-C4 — single graph instance
poetry run python -c "
import sys; sys.path.insert(0,'src'); from agents.ikigai_maintainer.graph import graph
assert graph() is graph(); print('H-C4 OK')"

# H-C5 — three surfaces agree
poetry run python tools/vault_taskdog_sync.py --status

# H-ALL — acceptance gate from the master diagnostic
poetry run pytest -q && poetry run ruff check src/
printf '%s\n' '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' \
  | poetry run python run_mcp_server.py \
  | python3 -c "import sys,json; d=json.loads(sys.stdin.readline()); print('tools:', len(d['result']['tools']))"
```

| Check | Pass condition | Fails if |
|-------|----------------|----------|
| H-C1 | `0 0` + a real interpreter path | §2 not applied, or `poetry install` skipped |
| H-C2 | `0` and `4` | sed anchors did not match (line drift) — re-grep §3 |
| H-C3 | binary exists at the resolved path | taskdog venv absent — build it first |
| H-C4 | `graph() is graph()` | one call site still calls `make_ikigai_graph` |
| H-C5 | vault / taskdog / tuiboard read the same state | §6 decision not taken |
| H-ALL | `tools:` ≥ 8, pytest green, ruff clean | any of the above, or an unrelated regression |

> The JSON-RPC probe replaces the `grep -q "ikigai-maintainer"` check at
> `start_mcp_gateway.sh:247` (canonical **M3** — fragile grep-based test).

---

## §9 Rollback (revert each fix in isolation)

Each fix writes its own `.bak-cN` sidecar, so reverting one leaves the others intact —
**provided** the sidecars were taken in the §7 order. `server.py` and `tools.py` are
each touched by two fixes; the table records which sidecar wins.

| Fix | Artifacts touched | Isolated revert |
|-----|-------------------|-----------------|
| **C1** | `mcp_config.json`, `start_mcp_gateway.sh` | `mv mcp_config.json.bak-c1 mcp_config.json; mv start_mcp_gateway.sh.bak-c1 start_mcp_gateway.sh` |
| **C2** | `src/mcp_server/server.py` | `mv src/mcp_server/server.py.bak-c2 src/mcp_server/server.py` — re-apply §5 if C4 had landed |
| **C3** | `src/agents/tools.py` | `mv src/agents/tools.py.bak-c3 src/agents/tools.py` — re-apply §5 if C4 had landed |
| **C4** | both `server.py` and `tools.py` | `mv` each `*.bak-c4` back — keeps C2 + C3 |
| **C5** | vault note, taskdog `#10`, tuiboard card | Path A: restore `.bak-c5` + `taskdog update 10 --status pending`. Path B: nothing to revert |

```bash
# Full revert to the pre-runbook tree
cd "$REPO_ROOT" && git status --short -- life-ops/ikigai          # review before discarding
git checkout -- life-ops/ikigai/src/mcp_server/server.py life-ops/ikigai/mcp_config.json life-ops/ikigai/start_mcp_gateway.sh
# tools.py had UNCOMMITTED changes before this runbook — restore the sidecar, not git:
mv life-ops/ikigai/src/agents/tools.py.bak-c3 life-ops/ikigai/src/agents/tools.py
```

**Nothing here deletes.** Vault notes are restored in place (append-only rule), and
`~/.ikigai/` databases are never dropped — to reset a checkpoint DB, rename it aside:
`mv ikigai_checkpoints.db ikigai_checkpoints.db.$(date +%s)`.

---

## §10 Cross-references

**Runbook ID → canonical diagnostic ID.** Canonical **C2** (`~/.ikigai/` missing) and
**C3** (`poetry.lock`) are pre-flight prerequisites here — §1 P1 and P2.

| Runbook | Deep-dive | Master diagnostic | Backlog | Severity |
|---------|-----------|-------------------|---------|----------|
| **C1** | C1 | §1.1 C1 | ISSUE-001 | 🔴 Critical |
| **C2** | C4 | §1.1 C4 | ISSUE-006 | 🔴 Critical |
| **C3** | C5 | §1.1 C5 | ISSUE-007 | 🔴 Critical |
| **C4** | H5 | §1.2 H5 | ISSUE-010 | 🟠 High |
| **C5** | H4 | §1.2 H4 | ISSUE-009 | 🟠 High |

**Downstream issues unblocked**

| Blocked issue | Unblocked by | Source |
|---------------|--------------|--------|
| **I3** — `_read_entity` fallback reads wrong table | runbook C2 | master §1.4 |
| **S-M7** — `ikigai_score` fallback wrong table when checkpoint empty | runbook C2 | master §2.3 |
| **M1** — taskdog tag truncation (`COLUMNS=200`) | runbook C3 | master §1.3 |
| **M2** — taskdog `:8000` must be running | §7 step 7 | master §1.3 |
| **M3** — grep-based JSON-RPC test | §8 JSON-RPC probe | master §1.3 |
| **S-C3** — taskdog via MCP instead of CLI subprocess | runbook C3, then drop the subprocess path | master §2.1 |

**Source documents:** `life-ops/ikigai/docs/IKIGAI_BACKEND_DEEP_DIVE_REPORT.md` (19 issues) ·
`code-docs/diagnostic/2026-08-27-master-system-diagnostic.md` (77 issues) ·
`2026-08-27-issue-dependencies.md` · `2026-08-27-migration-scripts-catalog.md` (MIG-3 = C5) ·
`2026-08-27-github-issues-backlog.md` (ISSUE-001..010) · `2026-08-27-error-catalog.md` ·
`2026-08-27-pre-merge-checklist.md` · `life-ops/ikigai/MCP_GATEWAY.md`

**Code anchors** (verified 2026-08-27 — re-grep if lines drift)

| Symbol | File:line |
|--------|-----------|
| `IKIGAI_PYTHON` | `start_mcp_gateway.sh:35` (used at 52, 116, 120, 194, 212, 247) |
| `mcpServers.ikigai.command` | `mcp_config.json:4` |
| `_read_entity` — nested vault reader | `src/mcp_server/server.py:157` |
| `_read_entity` — module sqlite reader | `src/mcp_server/server.py:265` |
| `_TASKDOG_CLI` | `src/agents/tools.py:43` (used at 812, 846, 879, 912) |
| `make_ikigai_graph` call sites | `src/mcp_server/server.py:448`, `src/agents/tools.py:298` |
| `graph()` singleton | `src/agents/ikigai_maintainer/graph.py:165` |
| LangGraph registration | `langgraph.json` → `./src/ikigai_wrapper.py:graph` |
| B1 vault note | `life-ops/ikigai/data/matheus/ikigai_state/b1-blocker-resolution.md` |

---

*IKIGAI Bootstrap Runbook — v1.0 — 2026-08-27 — operator procedure; edits are applied
by the operator, not by this document.*

> **[SUPERSEDED 2026-08-28 — see master-branch-carro-chefe-2026-08-28]**
> Appendix to the pre-pivot ADR-008..011 decision package (impact tables,
> open questions, implementation gotchas). PAV is desativado; appendix
> scope is no longer active. Canonical direction is deep-agent over
> forks-prontas widgets ↔ vault \`.db.markdown\`.

# ADR-008..011 Decision Package — Appendix

> **Companion to:** `code-docs/adr/2026-08-28-adr-008-011-decision-package.md`
> **Scope:** deep-dive impact tables + open questions + implementation gotchas
> **Audience:** user + future migration-script authors (post-decision)

This appendix holds the per-ADR impact tables (files affected, tests affected,
user-visible workflow changes), the open-questions list, and the implementation
gotchas discovered during the 2026-08-28 deep-dive. The primary decision package
stays under 500 lines; this companion is reference material for after a
decision lands.

---

## §A.1 Per-ADR Impact Tables

### A.1.1 ADR-008 — Vector Count

| Layer | Files affected | 2A impact | 2B impact | 2C impact |
|-------|----------------|----------|----------|----------|
| **Specs** | `vibe-ops/planning/PRD-07-ikigai-vectors.md` | +1 vector row; doc rewrite | unchanged (already 4) | +1 vector row + v0 banner |
| **Code (entities)** | `life-ops/ikigai/src/ikigai/entities/profile.py` | unchanged (already 5) | drop `course` field | unchanged (already 5) |
| | `life-ops/ikigai/src/ikigai/entities/base.py` | unchanged (5-vector-capable) | unchanged | unchanged |
| **Code (enum)** | `life-ops/ikigai/src/ikigai/enums.py:66-70` | unchanged | remove `COURSE` | unchanged |
| | `life-ops/ikigai/src/ikigai/enums.py:153-161` (Phase weights) | unchanged | remove `course` from 5 phases | unchanged |
| **Code (scoring)** | `vibe-ops/pipeline/ikigai_scorer.py` | 4 → 5 normalization | unchanged | 4 → 5 normalization |
| **Vault data** | `life-ops/ikigai/data/matheus/**/*.md` | backfill 4 files with `course: 0.0` | strip `course` from 5 files (data loss) | backfill 4 files with `course: 0.0` + `course_reviewed: false` |
| **Templates** | `vibe-ops/planning/_templates_periodos_v2/01-sonho.md` | add `course:` field | no change | add `course:` field |
| **Tests** | `life-ops/ikigai/tests/`, `tests/` | harmonize 5-vector assertions | harmonize 4-vector assertions | harmonize 5-vector + `course_reviewed` checks |
| **Docs** | `life/CLAUDE.md`, `life/README.md`, `life/ARCHITECTURE_INDEX.md` | unchanged (already 5) | roll 5 → 4 | unchanged (already 5) |

**Vault file count for ADR-008** (verified 2026-08-28): 11 files with `ikigai_vectors:`.
Distribution by vector count:
- 5 vectors (full set): 2 files
- 4 vectors (no course): 3 files
- 2-3 vectors (subset): 6 files (mostly `[market, course]`, `[skill, market, course]`, etc.)

**`course:` is present in 5/11 files.** This is the load-bearing evidence for
Option 2C: Course is not zero-use, so 2B's data loss is non-trivial.

### A.1.2 ADR-009 — Pydantic Strict Mode

| Layer | Files affected | 3A impact | 3B impact | 3C impact |
|-------|----------------|----------|----------|----------|
| **Code (base)** | `life-ops/ikigai/src/ikigai/entities/base.py:36-41` | `frozen=True, extra="forbid", strict=True` | unchanged (lax) | unchanged for now |
| **Code (derived)** | 11 other entity files (profile.py, vector.py, regime.py, skill.py, opportunity.py, ueid.py, plan/*.py) | each gets strict config | `# INVARIANT-RELAXED:` comments | unchanged; CI check fails on new ones |
| **Mutable defaults** | wherever `list = []` or `dict = {}` appears | replace with `Field(default_factory=...)` | unchanged | unchanged for existing; CI enforces for new |
| **`custom` field** | `base.py:83`, `profile.py`, etc. | remove or freeze (data loss for ~6 vault files) | unchanged | unchanged; CI warns on new |
| **Tests** | ~50 tests | rewrite assertions using `model_copy` | unchanged | CI script `scripts/check-pydantic-strict.py` |
| **CI** | new file | `scripts/check-pydantic-strict.py` + GitHub Actions step | downgraded to warn | date-heuristic check (pre-2026-08-28 grandfathered) |
| **Docs** | `life/CLAUDE.md` §Global Conventions | unchanged (already strict) | relax wording + add "Pydantic Relaxation Standard" | append grandfather clause |

**Entity audit (verified 2026-08-28)** — entity creation dates unknown without
git archaeology; default grandfather list = all 12 IKIGAI entities + 17 vibe-ops
entities (29 total). New entities (post-2026-08-28) must be strict from birth.

**`scripts/check-pydantic-strict.py` sketch:**

```python
"""CI check: Pydantic strict mode invariant (ADR-009 Option 3C).

Enforces strict mode for entities created after 2026-08-28.
Grandfather list is read from scripts/strict_grandfather.yaml.
"""
import ast
import sys
from pathlib import Path
import yaml

GRANDFATHER_FILE = Path("scripts/strict_grandfather.yaml")
CUTOFF = "2026-08-28"

def is_strict(class_node: ast.ClassDef) -> bool:
    """Return True if the class has ConfigDict(frozen=True, extra='forbid', strict=True)."""
    for stmt in class_node.body:
        if isinstance(stmt, ast.Assign):
            for target in stmt.targets:
                if isinstance(target, ast.Name) and target.id == "model_config":
                    if isinstance(stmt.value, ast.Call):
                        args = {kw.arg: kw.value for kw in stmt.value.keywords}
                        if all(k in args for k in ("frozen", "extra", "strict")):
                            return True
    return False

def main():
    grandfather = yaml.safe_load(GRANDFATHER_FILE.read_text()) if GRANDFATHER_FILE.exists() else {}
    failures = []
    for entity_path in Path("src/ikigai/entities").rglob("*.py"):
        if entity_path.name in grandfather.get("files", []):
            continue
        tree = ast.parse(entity_path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name.endswith(("Entity", "Snapshot", "Point", "Audit")):
                if not is_strict(node):
                    failures.append(f"{entity_path}:{node.lineno} {node.name}")
    if failures:
        print("FAIL: entities missing strict mode:")
        for f in failures:
            print(f"  {f}")
        sys.exit(1)
    print("PASS: all post-2026-08-28 entities are strict")

if __name__ == "__main__":
    main()
```

### A.1.3 ADR-010 — Dual CLAUDE.md Scope

| Layer | Files affected | 4A impact | 4B impact | 4C impact |
|-------|----------------|----------|----------|----------|
| **Root CLAUDE.md** | `C:\Users\mathe\code_space\life-oss\CLAUDE.md` | DELETED | +`## Scope` header (~5 lines) | slimmed to ~20 lines (orientation only) |
| **life/CLAUDE.md** | `C:\Users\mathe\code_space\life-oss\life\CLAUDE.md` | +`## Monorepo Overview` (~50 lines merged) | +`## Scope` header (~5 lines) | unchanged |
| **fin_ops/CLAUDE.md** | `C:\Users\mathe\code_space\life-oss\fin_ops\CLAUDE.md` | unchanged | unchanged | NEW (~50 lines) |
| **strategics/CLAUDE.md** | `C:\Users\mathe\code_space\life-oss\strategics\CLAUDE.md` | unchanged | unchanged | NEW (~30 lines) |
| **Cross-links** | any `README.md` or `docs/` referencing root | update if Option B was canonical | add `See also` cross-refs | update if fin_ops/strategics gain CLAUDE.md |
| **Third CLAUDE.md** | `life-ops/operational/CLAUDE.md` | unchanged (PAV kernel) | unchanged; boundary headers clarify it | unchanged |

**Concrete `## Scope` header for Option 4B** (verified wording):

For `life-oss/CLAUDE.md`:
```markdown
## Scope

This CLAUDE.md describes **monorepo-level concerns only**:
- The 3 submodules (life/, fin_ops/, strategics/)
- Cross-submodule contracts and CI
- Universal rules that apply to every submodule (Pydantic v2 strict, fully local, etc.)

For life-submodule internals (PAV, IKIGAI, vibe-ops, conventions, pitfalls),
see life/CLAUDE.md. **That file is authoritative for life work.**

For user-level global instructions, see ~/.claude/CLAUDE.md (auto-loaded for all projects).
```

For `life/CLAUDE.md`:
```markdown
## Scope

This CLAUDE.md describes **life submodule internals**:
- PAV kernel (life-ops/operational/)
- IKIGAI meta-brain (life-ops/ikigai/)
- Cybernetic engine (vibe-ops/)
- Global conventions + pitfalls specific to life work
- Architecture decisions for the life submodule

For monorepo-level orientation (3 submodules, cross-submodule CI), see the root
CLAUDE.md. **That file is the entry point for newcomers.**
```

### A.1.4 ADR-011 — HTTP+SSE MCP Transport

| Layer | Files affected | 5A impact | 5B impact | 5C impact |
|-------|----------------|----------|----------|----------|
| **Server entrypoint** | `life-ops/ikigai/src/mcp_server/server.py:696` | branch on `IKIGAI_MCP_TRANSPORT` env var | delete stdio branch | unchanged |
| **Dependencies** | `pyproject.toml`, `requirements.txt` | +`starlette`, `uvicorn` | same | unchanged |
| **Launcher** | `start_mcp_gateway.sh`, `ikigai.bat` | pass `IKIGAI_MCP_TRANSPORT` env var | same | unchanged |
| **Tests** | `tests/`, `life-ops/ikigai/tests/` | parametrize over `[stdio, http]` | HTTP-only | unchanged |
| **Docs** | `life-ops/ikigai/README.md`, `ARCHITECTURE_INDEX.md` | add "Transport" section | same | document stdio limitation |
| **dcode MCP config** | `~/.claude/.mcp.json` | new entry for HTTP transport | same (mandatory) | unchanged |

**Concrete `server.py:696` rewrite for Option 5A** (sketch, not for immediate execution):

```python
import os
TRANSPORT = os.getenv("IKIGAI_MCP_TRANSPORT", "stdio")  # stdio | http
PORT = int(os.getenv("IKIGAI_MCP_PORT", "3737"))
AUTH_TOKEN = os.getenv("IKIGAI_MCP_AUTH_TOKEN")  # optional bearer

async def main():
    if TRANSPORT == "http":
        from mcp.server.sse import SseServerTransport
        from starlette.applications import Starlette
        from starlette.routing import Mount, Route
        from starlette.requests import Request
        import uvicorn

        # Auth middleware (no-op when AUTH_TOKEN unset)
        async def auth_middleware(request: Request, call_next):
            if AUTH_TOKEN:
                auth = request.headers.get("authorization", "")
                if not auth.startswith("Bearer ") or auth[7:] != AUTH_TOKEN:
                    return Response("Unauthorized", status_code=401)
            return await call_next(request)

        sse = SseServerTransport("/messages/")

        async def handle_sse(request):
            async with sse.connect_sse(
                request.scope, request.receive, request.send
            ) as streams:
                await SERVER.run(
                    streams[0], streams[1], SERVER.create_initialization_options()
                )

        app = Starlette(routes=[
            Route("/sse", endpoint=handle_sse),
            Mount("/messages/", app=sse.handle_post_message),
        ])
        app.add_middleware(auth_middleware)

        config = uvicorn.Config(app, host="127.0.0.1", port=PORT, log_level="info")
        server = uvicorn.Server(config)
        await server.serve()
    else:
        async with stdio_server() as (read_stream, write_stream):
            await SERVER.run(
                read_stream, write_stream, SERVER.create_initialization_options()
            )
```

**Verification command** for ADR-011 Option 5A:

```bash
# Stdio path (default)
ikigai.bat mcp
# → should behave exactly as today

# HTTP path
IKIGAI_MCP_TRANSPORT=http ikigai.bat mcp &
sleep 2
curl -X POST http://127.0.0.1:3737/sse -d '{"jsonrpc":"2.0","method":"tools/list","id":1}'
# → should return 10 tools

# HTTP path with auth
IKIGAI_MCP_TRANSPORT=http IKIGAI_MCP_AUTH_TOKEN=secret ikigai.bat mcp &
curl -X POST http://127.0.0.1:3737/sse -H "Authorization: Bearer secret" -d '{"jsonrpc":"2.0","method":"tools/list","id":1}'
# → should return 10 tools
curl -X POST http://127.0.0.1:3737/sse -d '{"jsonrpc":"2.0","method":"tools/list","id":1}'
# → should return 401 Unauthorized
```

---

## §A.2 Open Questions

These questions do not block the ADR decisions but should be tracked:

1. **Q1.** Is the third CLAUDE.md (`life-ops/operational/CLAUDE.md`) in scope for
   ADR-010? The source ADR says "out of scope but related." If user picks 4B,
   should the third file also get a `## Scope` header? Recommendation: yes
   (consistency), but it's a follow-up edit, not part of the main decision.

2. **Q2.** What is the canonical migration runner for the entity schema (S-M2)?
   Currently no migrations runner exists; `CREATE TABLE IF NOT EXISTS` is the only
   path. If ADR-009 Option 3C's CI check triggers a new entity, where does it
   persist? This is the S-M2 issue from the master diagnostic — orthogonal but
   coupled.

3. **Q3.** Should ADR-008 Option 2C's `course_reviewed` flag be a YAML frontmatter
   field, a separate `_course_review.json` sidecar, or a column in the
   `plan_entities` table? Each has trade-offs. The default (frontmatter) keeps
   it portable across the markdown vault SoT.

4. **Q4.** For ADR-011 Option 5A, should the HTTP+SSE port (3737) be made
   configurable per-process, or hard-coded to match solverforge? Solverforge uses
   the same port for HTTP+SSE stub (per master diagnostic SF-4). If both run on
   the same host, collision is possible. Default: env var `IKIGAI_MCP_PORT=3737`.

5. **Q5.** What is the canonical entity creation date heuristic for ADR-009
   Option 3C? Git log of first commit per entity file is brittle (files move).
   A config file (`scripts/strict_grandfather.yaml`) is more maintainable.

6. **Q6.** Does ADR-010 Option 4B interact with the `~/.claude/CLAUDE.md` (user's
   private global instructions)? Per the system reminder, that file is auto-loaded
   for all projects. Should it be referenced from the root CLAUDE.md? Default: yes
   (cross-link from root CLAUDE.md `## Scope` to `~/.claude/CLAUDE.md`).

7. **Q7.** For ADR-008 Option 2C, what is the re-evaluation cadence? 6 months
   is the proposal; but the user could also commit to a quarterly review. Quarterly
   catches drift earlier; 6 months respects ADR-007's "6 month re-evaluation" pattern.

8. **Q8.** ADR-011 Option 5A's HTTP path needs lifecycle management (graceful
   shutdown on SIGTERM). Is there a session-aware cleanup already in
   `tools.py:_MCP_SESSION_CACHE` (master diagnostic S-H2)? The cache invalidation
   issue is a separate fix; ADR-011 should not block on it, but the two fixes
   can land in the same sprint.

9. **Q9.** Does ADR-009 Option 3C require the `custom` field to be deprecated
   entirely, or can it remain as a forward-compat escape hatch under `extra="allow"`
   for grandfathered entities only? The decision affects how new entities are
   designed (no `custom` field from birth).

10. **Q10.** ADR-008 Option 2A/2C's promotion to 5 vectors changes the meta-vector
    scoring math in `ikigai_scorer`. Does this require re-tuning the Q_HE composite
    targets in `enums.py:RegimeType.qhe_target` (PUSH=0.85, MAINTAIN=0.65, etc.)?
    Per Algorithm Issues Registry N01, vector weight tuning is deferred until 5+
    SONHO logs. This question should be parked alongside N01.

---

## §A.3 Implementation Gotchas (discovered 2026-08-28)

These gotchas are not blocking but should be documented for the post-decision
migration scripts:

1. **`Phase.vector_weights` already includes `course`** (verified at
   `enums.py:153-161`). If user picks 2B (drop Course), this dict must be edited
   in 5 places (one per phase), not just the enum.

2. **`PlanEntity.custom: dict[str, Any]` is a Pydantic dict field**, not a typed
   dict. Under strict mode (`extra="forbid"`), it's allowed because it's an
   explicit field. But it's still mutable, which violates `frozen=True`.
   Fix: convert `custom` to a frozen Pydantic model (`CustomFields(BaseModel)` with
   `model_config = ConfigDict(extra="allow", frozen=True)`).

3. **`score_history` mutation pattern** in `regime.py` and similar uses
   `entity.score_history.append(point)`. Under `frozen=True`, this fails. Fix:
   use `entity = entity.model_copy(update={"score_history": entity.score_history + [point]})`.

4. **MCP server `tools.py:550` cache** (`_MCP_SESSION_CACHE`) is never invalidated
   on error (master diagnostic S-H2). When ADR-011's HTTP path lands, this cache
   becomes more visible (HTTP clients can reconnect and hit stale cache). The
   cache invalidation fix should land in the same sprint as ADR-011.

5. **Vault frontmatter parser** at `base.py:201-214` (`from_frontmatter_dict`)
   uses `custom = data.pop("custom", {})` and then `instance.custom = custom`
   (line 213). Under `frozen=True`, this assignment fails. Fix: pass `custom` as
   a constructor argument.

6. **Decision log file** (`code-docs/adr/DECISIONS-LOG.md`) does not exist yet.
   User picks ADR-008/009/010/011 → file is created per the decision questionnaire
   §6 template. The primary decision package §7 has the template; this appendix
   confirms the file path.

7. **`scripts/check-pydantic-strict.py`** (new file for ADR-009 Option 3C) should
   live in `scripts/`, but the path is relative to the repo root. The IKIGAI
   submodule is at `life-ops/ikigai/`. Decide: check lives in `life-ops/ikigai/scripts/`
   (only checks IKIGAI entities) or in repo-root `scripts/` (checks both IKIGAI
   and vibe-ops entities). Default: IKIGAI-local first; expand to repo-root when
   vibe-ops gets strict.

8. **HTTP port collision** (master diagnostic SF-4): solverforge HTTP+SSE uses
   3737; IKIGAI adopting the same port is fine for separate hosts but problematic
   on dev laptops running both. Mitigation: env-var override
   (`IKIGAI_MCP_PORT=3738` default in dev environments).

9. **`scripts/strict_grandfather.yaml`** (new file for ADR-009 Option 3C) needs
   to be populated before the CI check runs. Default content:
   ```yaml
   # ADR-009 Option 3C grandfather list
   # Entities created before 2026-08-28 are exempt from strict mode.
   # New entities (post-2026-08-28) must be strict.
   files:
     - src/ikigai/entities/base.py
     - src/ikigai/entities/profile.py
     - src/ikigai/entities/vector.py
     - src/ikigai/entities/regime.py
     - src/ikigai/entities/skill.py
     - src/ikigai/entities/opportunity.py
     - src/ikigai/entities/ueid.py
     - src/ikigai/entities/plan/goal.py
     - src/ikigai/entities/plan/objective.py
     - src/ikigai/entities/plan/project.py
     - src/ikigai/entities/plan/task.py
     - src/ikigai/entities/plan/deliverable.py
     - src/ikigai/entities/plan/dream.py
   ```

10. **`course_reviewed: false` flag for ADR-008 Option 2C** must be settable in
    vault frontmatter AND in the SQLite adapter. The `to_frontmatter_dict` /
    `from_frontmatter_dict` methods at `base.py:168-214` already handle arbitrary
    fields via `custom`, but for a canonical flag it should be a first-class
    field on `PlanEntity`. Add `course_reviewed: bool = False` field.

---

## §A.4 Concrete Test Counts (verified 2026-08-28)

| ADR | Tests affected by chosen option | Estimated test changes |
|-----|--------------------------------|------------------------|
| 008 2A | `ikigai_scorer` tests, `IKIGAiProfile` tests | ~5-8 tests |
| 008 2B | `IKIGAiProfile` tests, Phase tests, enums tests | ~5-8 tests |
| 008 2C | Same as 2A + `course_reviewed` flag test | ~6-9 tests |
| 009 3A | ~50 tests (mutable default + extra field + frozen mutation) | ~50 tests |
| 009 3B | 0 tests | 0 tests |
| 009 3C | New `test_strict_invariant.py` + grandfather inventory test | ~3 tests |
| 010 any | 0 tests | 0 tests (docs only) |
| 011 5A | 8 MCP tools × 2 transports + new HTTP lifecycle tests | ~16-20 tests |
| 011 5B | Same as 5A, stdio branch removed | ~16-20 tests |
| 011 5C | 0 tests | 0 tests |

**Test matrix growth for ADR-011 + ADR-008 + ADR-009** (combined):

```
   vector_count    ∈ {4, 5}                # ADR-008
 × pydantic_mode   ∈ {lax, strict}          # ADR-009
 × transport       ∈ {stdio, http_sse}     # ADR-011
 = 8 cells × 10 IKIGAI MCP tools = 80 test variants (worst case)
```

Realistic subset: 4 cells (5-vec/lax, 5-vec/strict, 4-vec/lax, 4-vec/strict) ×
2 transports = 8 cells × 10 tools = 80 test variants.

Mitigation: parametrize the tests once (`@pytest.mark.parametrize` over
`(transport, vector_count, pydantic_mode)`), and the 80 variants collapse to
~10 actual test functions × 8 parameter combinations = 80 runs but only 10
functions to maintain.

---

## §A.5 Sprint Sequencing (refined)

The recommended resolution sequence from §6 of the primary package, refined
with sprint-level granularity:

**Sprint N (week 1): Documentation + transport**

- Day 1: ADR-010 → 4B (add `## Scope` headers; ~10 minutes)
- Day 1-5: ADR-011 → 5A (HTTP+SSE wiring; 3-5 days; stdio default)
- Day 5: smoke test (`curl http://127.0.0.1:3737/sse` returns 10 tools)

**Sprint N+1 (week 2): Schema reconciliation**

- Day 1-2: ADR-008 audit (count `course:` occurrences in vault)
- Day 2: ADR-008 → 2C (promote PRD-07 to 5 vectors + vault backfill)
- Day 3-5: ADR-009 → 3C setup (add `scripts/check-pydantic-strict.py` + grandfather
  config; CI integration)
- Day 5: verify new entities (if any created during sprint) are strict

**Sprint N+2 (week 3+): Stage 1 namespace migration (PAV)**

- Day 1-5: pick PAV entities (e.g., `operational/entities/journal.py` +
  `habit.py`), convert to strict, fix tests, validate

**Sprint N+3+ (week 4+): Stage 2 namespace (IKIGAI) + Stage 3 (vibe-ops)**

- Same pattern; one namespace per sprint; tests stabilize before next namespace.

**Total wall-clock:** ~3-4 sprints for full ADR-009 completion. ADR-008/010/011
complete in sprint N or N+1.

---

## §A.6 Cross-references

### Source ADRs

- `code-docs/adr/ADR-008-ikigai-vector-count.md`
- `code-docs/adr/ADR-009-pydantic-strict-mode-invariance.md`
- `code-docs/adr/ADR-010-dual-claude-md-scope.md`
- `code-docs/adr/ADR-011-ikigai-mcp-http-sse-transport.md`

### Companion documents

- `code-docs/adr/2026-08-27-decision-questionnaire.md`
- `code-docs/adr/2026-08-27-master-adr-index.md`
- `code-docs/adr/2026-08-27-cross-cutting-triage.md`
- `code-docs/adr/2026-08-28-adr-008-011-decision-package.md` (primary)

### Diagnostics

- `code-docs/diagnostic/2026-08-27-master-system-diagnostic.md`
- `code-docs/diagnostic/2026-08-27-migration-scripts-catalog.md`
- `code-docs/diagnostic/2026-08-27-issue-dependencies.md`

### Glossary

- `code-docs/glossary.md` — IKIGAI, VectorType, Entity, MCP Server, Root CLAUDE.md

### Memory

- `algorithm-issues-registry.md` — N01 vector weight mechanism
- `ikigai-weight-mechanism-defer.md` — Option C chosen 2026-07-03
- `data-first-methodology.md` — ADR-007 implementation rules

---

*Decision Package Appendix — v1.0 — 2026-08-28 — deep-dive reference material for
post-decision migration script authors.*

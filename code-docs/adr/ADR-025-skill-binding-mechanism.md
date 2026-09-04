# ADR-025 — Skill Binding Mechanism (Hybrid)

> **Status:** DRAFT (proposed 2026-09-04 — pending user acceptance)
> **Deciders:** matheus (project owner)
> **Supersedes:** W3.4 task brief which incorrectly named this ADR-014 (ADR-014 is UEID canonical format, accepted 2026-09-04)
> **Load-bearing:** YES — W3.5 (wire daily entry point) and W5.4 (extend to monthly/quarterly) both depend on this contract
> **Wave:** dcode-harness roadmap Wave 3 (W3.4)

---

## Context

Wave 3 of the dcode-harness roadmap requires formalizing how the 4 IKIGAI v2 skills
(daily / weekly / monthly / quarterly) bind to LangGraph entry points. W3.5
(wire `daily` as entry point) is blocked pending this decision; W5.4 (extend to
monthly/quarterly) extends the same binding mechanism.

The 4 skills are defined as markdown files at
`src/ikigai/src/agents/v2/skills/{daily,weekly,monthly,quarterly}.md` and
document the skill contract (inputs, outputs, triggers, behavior). The v2 graph
factory `make_v2_graph(entry_point=...)` at `graph.py:215-243` accepts an
`entry_point` parameter to start execution at any named node in the `NODES` tuple
(`graph.py:83-94`).

The problem: the 4 per-skill commands in `interfaces/cli/v2.py` (lines 466-632)
compose the existing primitives (cycle/score/regime/suggest) manually. They do not
invoke `make_v2_graph(entry_point=...)` directly. W3.5 must wire `daily` to
`surface_intentions`, `weekly` to `score_vectors`, `monthly` to `decompose`,
`quarterly` to `observe` — but without a formal contract, the binding is implicit
and drift-prone.

Additionally, W2.3 shipped 4 unwired entry points (`surface_intentions`,
`score_vectors`, `decompose`, `observe`) that have no CLI surface. The skill binding
mechanism must make these accessible via the skill commands.

---

## Decision

**Hybrid binding: YAML manifest is canonical; programmatic `entry_point` is an override.**

Each skill `.md` file declares its **default** `entry_point` and `actor` in YAML
frontmatter. The loader (`invoke_skill()` in `interfaces/cli/v2.py`) reads the
manifest and calls `make_v2_graph(entry_point=manifest["entry_point"])`. Callers
may pass `entry_point=...` to override the manifest value; the override is logged
with a warning so drift is detectable. This preserves a testing escape hatch
(Alt A) while keeping the manifest as the authoritative binding.

### Manifest schema (add to each skill .md frontmatter)

```yaml
entry_point: surface_intentions   # one of: observe | score_vectors | heuristics |
                                  #          balance | decompose | plan | tag_and_persist |
                                  #          reflect | commit | surface_intentions
actor: user                       # user | agent
```

The `entry_point` value MUST be a member of `NODES` (`graph.py:83-94`). The
loader validates this at load time and raises `ValueError` with the valid set if
the manifest contains an unknown entry point.

### Loader rule (interfaces/cli/v2.py)

```python
def invoke_skill(skill_name: str, entry_point: str | None = None) -> Any:
    manifest = load_skill_manifest(skill_name)  # reads .md frontmatter
    if entry_point is None:
        entry_point = manifest["entry_point"]
    elif entry_point != manifest["entry_point"]:
        log.warning(
            f"Skill {skill_name!r} entry_point override: "
            f"manifest={manifest['entry_point']!r}, caller={entry_point!r}"
        )
    return make_v2_graph(entry_point=entry_point).invoke(initial_state)
```

### Skill to Entry Point Mapping

| Skill | entry_point | Actor | Rationale |
|-------|-------------|-------|-----------|
| `ikigai-daily` | `surface_intentions` | user | Surface-only — no full cycle; emit PAV suggestions |
| `ikigai-weekly` | `score_vectors` | user | Score vectors + heuristics + balance (regime check); no commit |
| `ikigai-monthly` | `decompose` | user | Plan-level work breakdown; no commit |
| `ikigai-quarterly` | `observe` | user | Full pipeline (strategic realignment) |

All 4 actors are **user** — skills fire via cron or slash command (per existing
frontmatter triggers), never invoked autonomously by the agent layer.

---

## Rationale

1. **Manifest is canonical (ADR-013 single-source-of-truth).** Skill contracts
   live in the skill `.md` files. Hardcoding bindings in `v2.py` would duplicate
   the source of truth across two files, creating a drift risk that the drift
   detector cannot catch (the v2.py hardcodes would not be visible to the
   manifest-based invariant).

2. **Programmatic override is necessary for testing.** FAKE_LLM stubs require
   temporary entry-point overrides without editing manifest files. The warning log
   ensures overrides are auditable.

3. **Validation at load prevents bad bindings from reaching the graph.** If a skill
   manifest contains an unknown `entry_point` value, the loader raises `ValueError`
   before any graph is compiled. This is fail-fast per R2.

4. **Actor consistency (ADR-012).** `vault_write` is the sole vault writer.
   Passing `actor=manifest["actor"]` to every `vault_write` call ensures writes
   are attributed to the correct actor. All 4 skills declare `actor: user`.

5. **Unwired entry points become accessible.** W2.3 shipped 4 nodes without CLI
   surface: `surface_intentions`, `score_vectors`, `decompose`, `observe`. The
   skill binding makes these reachable via `life v2 daily/weekly/monthly/quarterly`.

---

## Implementation Rules

**R1 — Manifest is canonical.** `src/ikigai/src/agents/v2/skills/*.md` frontmatter
`entry_point` field is the authoritative binding. Programmatic override is logged,
not enforced.

**R2 — Validation at load.** Loader rejects `entry_point` values not in `NODES`
(`graph.py:83-94`) with `ValueError` listing the valid set.

**R3 — vault_write actor consistency.** **Per ADR-012 + the attribution report §7**, `vault_write` is the canonical vault writer. The skill orchestrator MUST pass `actor=manifest["actor"]` to every `vault_write` call so audit logs distinguish user-invoked from agent-invoked writes.

**R4 — Drift detector invariant (k).** **Note:** R4 is a PLANNED invariant. The actual `test_no_hardcoded_entry_points_*` test in `src/ikigai/tests/test_canonical_scope.py` is added by W3.5 (R5) when the manifest frontmatter lands. Until then, this rule documents the enforcement intent — not current behavior.

New invariant in
`src/ikigai/tests/test_canonical_scope.py`:
- All 4 skill `.md` files have `entry_point` field
- All `entry_point` values are members of `NODES`
- All 4 skills declare `actor` field with value in `{"user", "agent"}`
- `interfaces/cli/v2.py` uses `invoke_skill()` for skill bindings; any
  `make_v2_graph(entry_point=...)` call outside `invoke_skill()` is flagged

**R5 — Add `entry_point` + `actor` to all 4 skill `.md` files.** `daily.md`,
`weekly.md`, `monthly.md`, `quarterly.md` each gain:
```yaml
entry_point: <node>
actor: user
```

**R6 — Refactor `v2.py` per-skill commands.** Replace the current
primitive-composition pattern in `_run_daily`, `_run_weekly`, `_run_monthly`,
`_run_quarterly` with `invoke_skill(name)` calls.

---

## Consequences

### Positive

- **Single source of truth** in skill `.md` frontmatter — no duplicate binding
  declarations to keep in sync.
- **Fail-fast** on bad `entry_point` values (R2) — catches misconfiguration before
  graph compilation.
- **Testing escape hatch** — programmatic override logs a warning but does not block.
- **Drift detector invariant (k)** prevents hardcoded entry points from creeping
  back into `v2.py` outside `invoke_skill()`.
- **W3.5 unblocked** — `daily` can be wired to `surface_intentions` via the
  manifest; no new code decision required.
- **W5.4 unblocked** — monthly/quarterly bindings follow the same mechanism.

### Negative

- **Loader required** — `v2.py` must gain an `invoke_skill()` function. This is
  minimal refactoring (R6), not a new architectural layer.

### Neutral

- The 4 skills are already cron-triggered (`daily.md:5`, `weekly.md:5`,
  `monthly.md:5`, `quarterly.md:5`). The binding mechanism does not change
  when skills fire — it changes which graph node executes.

---

## Alternatives Considered

### Alt A — Pure manifest (no override)

Manifest is the sole binding; no programmatic override exists.

- **Rejected:** Testing FAKE_LLM stubs requires temporary entry-point override
  without manifest edits. Without an override, tests must edit the manifest,
  which is fragile and pollutes the source-of-truth.

### Alt B — Pure programmatic (hardcode in v2.py)

Binding lives entirely in `v2.py` as `make_v2_graph(entry_point="surface_intentions")`
etc., with no manifest field.

- **Rejected:** Violates ADR-013 single-source-of-truth. The 4 skill files would
  become documentation only, not contracts. Any change to the binding would require
  editing both the skill file and `v2.py`, creating a 2-file drift risk.

### Alt C — Defer binding (use primitives only)

Status quo: per-skill commands compose existing primitives without invoking the
graph directly.

- **Rejected:** Skills never invoke the graph; W3.5/W5.4 are blocked. The 4
  unwired entry points (`surface_intentions`, `score_vectors`, `decompose`,
  `observe`) remain inaccessible via CLI. The binding must be formalized before
  wiring can proceed.

---

## References

- **dcode-harness roadmap:** `docs/superpowers/specs/2026-09-04-dcode-harness-TASKS.md` W3.4 (lines 184-196)
- **NODES tuple:** `src/ikigai/src/agents/v2/graph.py:83-94`
- **make_v2_graph factory:** `src/ikigai/src/agents/v2/graph.py:215-243`
- **Skill files:** `src/ikigai/src/agents/v2/skills/{daily,weekly,monthly,quarterly}.md`
- **v2.py per-skill commands:** `interfaces/cli/v2.py:466-632`
- **vault_write sole-writer rule:** ADR-012 §1 (vault_write is canonical writer)
- **Single-source-of-truth + drift detectors:** ADR-013 §8 (drift detector invariant is load-bearing)
- **UEID canonical format:** ADR-014 (unrelated numbering; same template)
- **W2.3 skill unwired entry points:** `interfaces/cli/v2.py:211-321` (per-skill orchestrators do not call `make_v2_graph`)
- **Test canonical scope:** `src/ikigai/tests/test_canonical_scope.py` (R4 invariant k location)

---

*ADR-025 — accepted 2026-09-04 — Wave 3 W3.4 — unblocks W3.5 + W5.4*

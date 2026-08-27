# SPEC: Vault Bidirectional Sync

> **Feature ID:** `vault-bidirectional-sync`
> **Status:** **DELIVERED** (T1-T13 complete; F-Wave pending)
> **Plan:** `.omo/plans/vault-bidirectional-sync.md`
> **Strategic framework:** [`docs/chat-Framework de Planejamento Estratégico.txt`](../../docs/chat-Framework%20de%20Planejamento%20Estrat%C3%A9gico.txt)
> **ADR-006 (Period Reports Schema):** [`vibe-ops/architecture/ADR-006-period-reports-schema.md`](../../vibe-ops/architecture/ADR-006-period-reports-schema.md)
> **Codebase commit:** 586a26d (T13 latest)
> **Test count:** 192 passing across sync suite

---

## 1. Context

The Algorithmic Life OS had two parallel data systems that never talked:

- **Obsidian vault** (`notas_estudo`, 234+ notes) — human-curated, manual fields
  like `xp_points`, `mastery_level`, `subject`, `tech_stack`, `milestone`,
  `deliverable`, `commercial_goal`, `vault_path`.
- **vibe-ops engine** — computed outputs from `PolicyEngine`, `IkigaiScorer`,
  `HypothesisEvaluator` (RICE scores, regime, policy decisions).

The vault held the user's manual reality; the engine held algorithmic
truth. Neither could see the other. Dashboards in the vault queried
`policy_state`, `rice_score`, `falsifiability_score` fields that never
got populated because the engine output never crossed the bridge.

This spec delivers a **BidirectionalSync** middleware that moves data
both directions, idempotently, with explicit conflict resolution.

### 1.1 Problem
- 234+ vault notes have `xp_points`, `mastery_level`, `subject` fields
  that the engine cannot read.
- `PolicyEngine` outputs `PolicyDecision` rows that never reach the
  vault — dashboards sit empty.
- `FalsifiableHypothesis` exists only in prose; no Pydantic entity,
  no evaluator that decides `validated` / `falsified` / `pivoted`.
- `compute_rice_score` lives in scattered places; no shared
  `compute_priority_rank` for project ordering.
- Frontmatter parser silently returns `None` on parse errors — sync
  would hide failures instead of incrementing an error counter.

### 1.2 Solution
BidirectionalSync middleware + RICE module + FalsifiableHypothesis
entity + HypothesisEvaluator + `pav sync` CLI bridge.

### 1.3 Relevant Files (pinned to commit `586a26d`)

| Path | Lines | Role |
|------|------:|------|
| `vibe-ops/src/middleware/bidirectional_sync.py` | 489 | Core sync engine |
| `vibe-ops/src/pipeline/rice_exporter.py` | 100 | RICE scoring + dense ranking |
| `vibe-ops/src/pipeline/hypothesis_evaluator.py` | 230 | Axis 1-3 evaluator |
| `vibe-ops/src/models/hypothesis_entities.py` | 75 | `FalsifiableHypothesis`, `HypothesisEvaluation` |
| `vibe-ops/src/models/dream_entities.py` | 50 | `Dream` long-horizon anchor |
| `vibe-ops/src/models/project_entities.py` | +18 | 9 vault fields on `Project` |
| `vibe-ops/src/models/study_entities.py` | +14 | 9 vault fields on `StudyProject` |
| `vibe-ops/src/pipeline/frontmatter_parser.py` | +5 | 3 new MODEL_MAP entries |
| `vibe-ops/src/scripts/vault_sync.py` | 180 | Standalone bridge CLI |
| `vibe-ops/migrations/005_vault_sync.sql` | 50 | DB migration (idempotent) |
| `life-ops/.../migrations/003_vault_sync.sql` | 12 | Operational mirror migration |
| `life-ops/.../commands/sync_cmd.py` | 165 | `pav sync vault|code|all|status|conflicts` |
| `vibe-ops/tests/fixtures/vault/` | 7 files | 6 valid + 1 broken YAML |
| `vibe-ops/tests/conftest.py` | 70 | Shared fixtures (`temp_vault`, `temp_db`, `sync_engine`) |

---

## 2. Decisions (Locked D1-D5)

### D1: Full stack delivery (templates + Bases + swarm-equivalent)
Vault sync ships as a complete stack: entities + middleware + evaluator
+ CLI + tests. No half-built layer requiring future work.

### D2: Bidirectional, not one-way
`vibe-ops/src/middleware/sync_engine.py` was one-way
(vault → SQLite). This spec adds `sync_code_to_vault` for the reverse.
Both directions use the same idempotency key (sha256 of canonical JSON).

### D3: Conflict policy
- **Vault wins** for manual fields (xp_, mastery_, subject,
  learning_phase, tech_stack, milestone, deliverable, commercial_goal).
- **Code wins** for computed fields (regime, hardwork_budget_hours,
  pause_minutes, sleep_target_hours, qhe_target, policy_decision_at,
  policy_severity, policy_recommendations, policy_alerts, rice_score,
  priority_rank, falsifiability_score, hypothesis_verdict).
- **Ambiguous field** (anything else) → appended to `.sync-conflicts.md`
  (append-only invariant). `sync_code_to_vault` skips the field rather
  than overwriting.

### D4: Test infra both subsystems
Tests live in both `vibe-ops/tests/` (component + E2E) and
`life-ops/operational/tests/integration/` (CLI bridge).

### D5: Sequential agent execution
Plan designed for 4 parallel agents, but executed sequentially in a
single session to keep commit history atomic.

---

## 3. Architecture

```
                ┌──────────────────────────────────┐
                │   Obsidian vault (.md files)    │
                │  2_projeto/, 5_atomicas/,       │
                │  3_indice/, 4_leitura/          │
                └──────────┬───────────────────────┘
                           │ frontmatter
                           ↓
                ┌──────────────────────────────────┐
                │ BidirectionalSync                │
                │  ├─ sync_vault_to_code()         │
                │  ├─ sync_code_to_vault()         │
                │  ├─ resolve_conflicts()          │
                │  └─ status()                     │
                └──────┬─────────────┬─────────────┘
                       │             │
        planning_entities    vault_sync_state
        (id, entity_type,    (vault_path PK,
         payload_json,        last_hash)
         upstream_id)
                       │             │
                       ↓             ↓
                ┌──────────────────────────────────┐
                │ vibe-ops SQLite (WAL mode)      │
                │  + policy_decisions              │
                │  + falsifiable_hypotheses        │
                │  + hypothesis_evaluations        │
                └──────────────────────────────────┘
                           │
                ┌──────────┴───────────┐
                ↓                      ↓
        HypothesisEvaluator    RICE scoring
        (Axis 1-3 logic)        (compute_priority_rank)
```

### 3.1 Idempotency
Each frontmatter payload is hashed with sha256(json.dumps(payload,
sort_keys=True, default=str))[:12]. The 12-char prefix lives in
`vault_sync_state.last_hash`. Unchanged content → skip. Changed
content → re-upsert with new upstream_id.

### 3.2 Atomic writes (code → vault)
Each vault file is rewritten via `{path}.tmp` then `os.replace()`.
A crash mid-write leaves the original file untouched.

### 3.3 Advisory locks
`BidirectionalSync.advisory_lock(name)` context manager uses
SQLite `BEGIN IMMEDIATE` with retry-on-busy (5s timeout). Serializes
cross-process writers on the same `vibe_ops.db`.

---

## 4. Algorithm Details

### 4.1 RICE scoring

```
RICE(reach, impact, confidence, effort_h) =
    (reach × impact × confidence) / max(effort_h, 0.1)

Components clamped to non-negative.
Effort clamped at 0.1 to avoid div-by-zero.
```

### 4.2 Priority rank (dense)

```
Sort tasks by RICE descending; assign dense rank 1..N.
Ties share rank; next integer skips forward (1, 1, 2 ...).
Deterministic alphabetical tiebreak for stability.
```

### 4.3 Falsification score (B5.3)

```
score = (leading_met / total_leading) × 0.5
      + (1 - lagging_met / total_lagging) × 0.5

Empty indicator lists treated as 100% satisfied (no constraint to fail).
Result clamped to [0.0, 1.0].
```

Spec value verified: `compute_falsification_score(2, 1, 3, 4) ≈ 0.708`.

### 4.4 Hypothesis verdict rules (priority order)
1. `refactor_trigger` detected in journal → `pivoted`
2. All leading met + lagging all below threshold → `validated`
3. All leading met + lagging above threshold → `falsified`
4. Partial leading → `no_change`

### 4.5 PolicyDecision → 12 frontmatter keys

`sync_code_to_vault` reads the latest row from `policy_decisions` and
emits to vault frontmatter:

| Key | Source |
|-----|--------|
| `regime` | policy_decisions.policy |
| `hardwork_budget_hours` | hardwork_budget_hours |
| `pause_minutes` | pause_duration_minutes |
| `sleep_target_hours` | sleep_target_hours |
| `qhe_target` | qhe |
| `policy_decision_at` | computed_at |
| `policy_severity` | derived (CRITICAL/HIGH/MEDIUM/LOW) |
| `policy_recommendations` | recomendacoes (JSON) |
| `policy_alerts` | alertas (JSON) |
| `rice_score` | computed from payload if components present |

---

## 5. CLI Surface

```
pav sync vault --vault <path> --db <path> --json
pav sync code  --vault <path> --db <path> --json
pav sync all   --vault <path> --db <path> --json
pav sync status [--vault <path>] --db <path> --json
pav sync conflicts --vault <path> --json
```

All subcommands support `--json`. The CLI bridges to
`vibe-ops/src/scripts/vault_sync.py` via subprocess (operational stays
standalone — does NOT import vibe-ops directly).

---

## 6. Test Coverage

| Test file | Count | Purpose |
|-----------|------:|---------|
| `test_project_entities.py` | 35 | Vault enrichment fields on `Project` |
| `test_study_entities.py` | 39 | Vault enrichment fields on `StudyProject` |
| `test_bidirectional_sync.py` | 9 | sync_vault_to_code happy path + error tolerance |
| `test_sync_code_to_vault.py` | 6 | Code → vault + PolicyDecision + RICE |
| `test_rice_exporter.py` | 13 | RICE formula + dense ranking edge cases |
| `test_hypothesis_entities.py` | 25 | FalsifiableHypothesis + HypothesisEvaluation |
| `test_hypothesis_evaluator.py` | 22 | Score formula + verdict rules + persistence |
| `test_fixture_smoke.py` | 6 | Fixture vault + conftest integration |
| `test_frontmatter_parser.py` | 10 | Dream + FalsifiableHypothesis MODEL_MAP |
| `test_migrations.py` | 13 | Schema + WAL mode + advisory locks + SQL files |
| `test_full_sync_cycle.py` | 9 | End-to-end bidirectional cycle |
| `test_sync_cmd.py` (operational) | 12 | CLI bridge routing + exit codes |
| `test_conflict_resolution.py` | 5 | D3 conflict policy + 100-iteration property test |
| **Total** | **192** | |

---

## 7. Known Limitations

- **Refactor trigger detection** is keyword-substring on
  `<vault>/0_daily/journal.md`. v1 has no semantic matching; v1.1 will
  integrate with the IKIGAi signal extractor.
- **Leading/lagging indicator counts** in `HypothesisEvaluator` are
  conservative v1 returns 0/total until external evidence tables are
  wired in.
- **No watcher/daemon** — sync is explicit via `pav sync all`. v1.1 will
  add `life sync watch` for file-change-driven syncs.
- **No Taskwarrior integration** — this layer is Obsidian ↔ SQLite only.
  TW hooks remain in the existing `sync_engine.py`.

---

## 8. Migration Path

Existing `vibe_ops.db` users get the new tables idempotently via:

```sql
-- migrations/005_vault_sync.sql
CREATE TABLE IF NOT EXISTS vault_sync_state (...);
CREATE TABLE IF NOT EXISTS falsifiable_hypotheses (...);
CREATE TABLE IF NOT EXISTS hypothesis_evaluations (...);
```

The operational mirror migration (`003_vault_sync.sql`) handles the
operational DB if any code path queries vault_sync_state there.

---

## 9. Future Work

| Version | Item | Rationale |
|---------|------|-----------|
| v1.1 | `life sync watch --vault <path>` | File-watcher mode (deferred from D2) |
| v1.1 | Evidence tables for leading/lagging counts | Replace v1's conservative 0/total |
| v1.1 | Semantic refactor trigger matching | Beyond keyword substring |
| v2 | Real-time sync via Obsidian URI handler | User requests no daemon (locked) |
| v2 | Vector-search integration with RAG indexer | dream/falsifiable_hypothesis → embeddings |
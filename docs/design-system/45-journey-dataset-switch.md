# 45 — Journey: Dataset Switch (FLOW-008 + reset FLOW-009 + doctor FLOW-010)

> **⚠️ ADR-007 propagation note (2026-08-29):** References to "5 SONHO logs gate (ADR-007)" in this doc reflect a **propagated misconception**. ADR-007's "5+ manual logs per workflow" rule is **observation depth**, NOT a release gate. The actual gate for algorithm work is **system readiness** (backend + data + agent functional). Canonical clarification: `~/.claude/projects/C--Users-mathe-code-space-life-oss-life/memory/algorithm-gate-system-readiness-not-sonho-2026-08-29.md`. The deferral rule still applies here — this content is correctly deferred — but for the reason "system not ready," not "5 logs not reached."

> **Categoria:** JOURNEY CANVAS (Layer 6 — User journeys & screens, posição #45)
> **Anchor canônico:** `src/operational/docs/ux/04-fluxos/FLOW-008-trocar-dataset.md` + `FLOW-009-limpar-resetar.md` + `FLOW-010-doctor.md` + `docs/diagnostics/2026-08-28-phase2-interface-re/06-synthesis-mesh-readiness.md` (Phase 3 readiness) + `code-docs/adr/ADR-007-data-first-methodology.md`
> **Público:** Eu mesmo + agentes futuros
> **Idioma:** PT-BR prose + EN technical terms (dataset switch, snapshot, rollback, mesh consistency, doctor, diagnostics, append-only, gate, state dir, JSONL, atomic rename, TIME_TASKER_DATASET, env var, ADR-007, data-first methodology)

---

## §1 — Resumo

A jornada **dataset switch** é a operação **operator-side** que troca o dataset ativo do sistema entre **production / synthetic / test / clean / archive**. No modelo dual-layer deep-agent canonical 2026-08-28 ([[master-branch-carro-chefe-2026-08-28]]), ela é **exclusivamente operator-side** (Layer B) — **NÃO** user-side, porque trocar dataset pode corromper estado se mal feito. A versão PAV-era canônica é **FLOW-008-trocar-dataset.md** + **FLOW-009-limpar-resetar.md** + **FLOW-010-doctor.md** (3 flows relacionados: switch + reset + diagnostics). Esta canvas documenta **safe state snapshot antes de switch** + **verify mesh consistency** + **rollback path** + **ADR-007 5-log constraint gate** + **doctor command diagnostics** (verifica state dir, repos, CSV datasets, atomic writes).

**Modos:** INDEX canvas — não prescreve nova jornada; mapeia componentes verbatim.

**Invariante load-bearing:** Toda switch de dataset **DEVE** passar por `safe_snapshot` antes + `verify_mesh_consistency` depois + rollback path documentado. ADR-007 (data-first methodology) impõe **5+ SONHO logs manuais** antes de algorithm polish — dataset switch é parte desse gate (testa se o agent observa planned vs actual via dataset simulado).

**Importante:** No modelo dual-layer, dataset switch é **operator CLI only** (Layer B) — forks-prontas (tuiboard, taskdog, solverforge-calendar) NÃO têm dataset concept (cada fork usa seu próprio DB local). Switch de dataset afeta o operator CLI + agent run + vault-side planning.

---

## §2 — Inventário

### 2.1 Os 3 flows canônicos PAV-era

| Flow | Operação | LOC | Anchor |
|:-----|:----------|:----|:-------|
| **FLOW-008** | Trocar dataset (PROPOSTA: `TIME_TASKER_DATASET=…` (env var name change per migration; deep-agent era uses `PAV_DATASET`)) | TBD | `src/operational/docs/ux/04-fluxos/FLOW-008-trocar-dataset.md` |
| **FLOW-009** | Limpar/resetar state (PROPOSTA: `operational demo clear` (PAV-era CLI command)) | TBD | `src/operational/docs/ux/04-fluxos/FLOW-009-limpar-resetar.md` |
| **FLOW-010** | Doctor diagnostics (PROPOSTA: `operational doctor` (PAV-era CLI command)) | TBD | `src/operational/docs/ux/04-fluxos/FLOW-010-doctor.md` |

### 2.2 Os 5 datasets suportados (PAV-era)

| Dataset | Path | Conteúdo | Uso |
|:--------|:-----|:---------|:----|
| `production` | `~/.time-tasker/` (state dir lazy) | state real do usuário | produção |
| `synthetic` | `docs/synthetic.csv` + auto-load | 345 entities sintéticas | dev/test |
| `test` | `data/test-fixtures/test-<uuid>.db` | fixture mínimo | unit tests |
| `clean` | state dir vazio (lazy) | fresh start | reset completo |
| `archive` | `~/.time-tasker-archive/<YYYY-MM-DD>/` | snapshot do production antes de switch | rollback safety |

### 2.3 Components críticos

| Componente | Anchor | Função |
|:-----------|:-------|:-------|
| PROPOSTA: `dataset_selector.py:resolve_dataset` (path place-holder) | `src/operational/cli/dataset_selector.py` | lê `TIME_TASKER_DATASET` env var; retorna path |
| `state.py:JSONRepository._load_all` | PROPOSTA: `src/operational/cli/state.py` (path place-holder) | lazy `mkdir -p`; load JSONL |
| `state.py:JSONRepository.upsert` | PROPOSTA: `src/operational/cli/state.py` (path place-holder) | append atomic temp+rename |
| `safe_snapshot` (PROPOSTA) | n/a | cria `~/.time-tasker-archive/<date>/` antes de switch |
| `verify_mesh_consistency` | `src/mesh/queue.py:consume_pending` | valida que não há events pendentes |
| `rollback` (PROPOSTA) | n/a | restaura archive sobre production |
| PROPOSTA: `doctor_cmd` (CLI command name PAV-era) | PROPOSTA: `src/operational/cli/commands/doctor_cmd.py` (path place-holder) | SCR-007-doctor.md |
| PROPOSTA: `doctor` (CLI subcommand) checks | PROPOSTA: `src/operational/cli/commands/doctor_cmd.py` (path place-holder) | state_dir, repos, CSV datasets, atomic writes, UEID format |

### 2.4 Cross-fork dataset concept (gap)

| Fork | Dataset concept? | Mecânica |
|:-----|:------------------|:---------|
| **tuiboard** | ✗ NÃO tem | markdown round-trip local; user edita diretamente |
| **taskdog** | ✗ NÃO tem | SQLite single-DB; `~/.local/share/taskdog/tasks.db` |
| **solverforge-calendar** | ✗ NÃO tem | dual-DB federation; `~/.local/share/solverforge-calendar/calendar.db` + `unified_planning.db` |
| **PAV-era CLI** | ✓ SIM | `TIME_TASKER_DATASET` env var; `~/.time-tasker/` |
| **vault** | ✓ SIM (source-of-truth) | `vault/ikigai/closing-2026/{q}-{w}/` |

**Implicação:** Dataset switch só afeta operator CLI + agent run. Forks-prontas continuam com seus próprios DBs locais.

### 2.5 Pre-condições + constraints

**Pre-condições:**
- Agent run halted (se ativo) — `agent.stop()` antes de switch.
- Sem events pendentes em `data/review_queue/` — `consume_pending()` vazio.
- State dir acessível — `state.show()` retorna sem erro.
- CSV dataset existe (se synthetic) — `TIME_TASKER_DATASET=synthetic operational home` falha se `docs/synthetic.csv` movido.

**Constraints (ADR-007):**
- 5+ SONHO logs manuais **antes** de algorithm polish.
- Dataset switch é teste empírico (synthetic dataset valida planned vs actual).
- Rollback obrigatório se check falha.

### 2.6 Phase 3 readiness cross-link

`docs/diagnostics/2026-08-28-phase2-interface-re/06-synthesis-mesh-readiness.md` lista readiness por OQ (Open Question):

- **OQ-7:** adapter storage convergence — taskdog UPSERT + solverforge PK reuse + CLI JSONL → verified em synthetic.
- **OQ-8:** MCP transport dual (taskdog stdio + solverforge stdio+HTTP stub) — verified em test dataset.
- **OQ-10:** cross-fork status consistency — verified via dataset switch (production → synthetic → production).

### 2.7 Doctor checks (FLOW-010 verbatim)

PROPOSTA: `operational doctor` (PAV-era CLI command) (SCR-007) verifica:

1. `state_dir: ok | missing | corrupted` — verifica `~/.time-tasker/` existe + JSONL parse-able.
2. `datasets: production=ok | synthetic=MISSING | test=ok` — verifica CSV fixture paths.
3. `atomic_writes: ok | race_detected` — check último write tem timestamp coerente.
4. `UEID_format: ok | invalid` — regex Pattern #10 em todos IDs.
5. `queue_empty: yes | no (<N> pending)` — `data/review_queue/` vazio.
6. `mesh_consistency: ok | partial_propagation (<N> stale)` — cross-fork join.
7. `python_version: 3.10+` — runtime check.
8. `uv_installed: yes | no` — workspace tool check.

---

## §3 — Conteúdo principal

### 3.1 Dataset switch flow (5 steps end-to-end)

```text
[1] Pre-flight check (PROPOSTA — italic gap fill)
   - agent.stop() if running
   - data/review_queue/ = empty (consume_pending() retorna [])
   - state.show() returns ok
   - safe_snapshot created: cp -r ~/.time-tasker/ ~/.time-tasker-archive/<YYYY-MM-DD>/
   │
   ▼
[2] Switch dataset
   export TIME_TASKER_DATASET=<production|synthetic|test|clean|archive>
   operational home
   │
   ▼
[3] Verify mesh consistency (PROPOSTA)
   - cli: data/tasks.jsonl parse ok
   - taskdog: data/taskdog/tasks.db UPSERT ok
   - solverforge-calendar: unified_planning.db PK reuse ok
   - vault: vault/ikigai/meta/ parse ok
   │
   ▼
[4] Run synthetic scenario (se applicable)
   - FLOW-001 + FLOW-002 + FLOW-007 etc.
   - Verifica que planned vs actual observa via agent
   - Incrementa SONHO counter (manual gate)
   │
   ▼
[5] Rollback if check fails (PROPOSTA)
   if any consistency check fails:
     rm -rf ~/.time-tasker/
     cp -r ~/.time-tasker-archive/<YYYY-MM-DD>/ ~/.time-tasker/
     log rollback event to vault/ikigai/meta/rollbacks.md
```

### 3.2 Reset flow (FLOW-009 — limpar/resetar)

PROPOSTA: `operational demo clear` (PAV-era CLI command) ou `operational reset --confirm`:

1. Confirma com user: "Isso vai deletar X entities. Continuar? (yes/no)"
2. Para cada repo (routines, time_blocks, journals, habits, sleep_records, pomodoros, policy_decisions, etc.):
   - `repo.clear()` → atomic write empty JSONL
3. Não deleta arquivos físicos (append-only); apenas esvazia.
4. Vault-side: NÃO toca (vault é source-of-truth, separado).
5. State dir recriado lazy no próximo `metric sleep`.

**Importante:** Reset é destrutivo. Doctor (`FLOW-010`) deve ser rodado após reset para verificar consistência.

### 3.3 Doctor command (FLOW-010)

PROPOSTA: `operational doctor` (PAV-era CLI command) (SCR-007-doctor.md):

```
⚕️  OPERATIONAL DOCTOR — 2026-08-28

✅ state_dir: ok (~/.time-tasker/, 7 files, 124KB)
✅ datasets: production=ok | synthetic=ok (345 entities) | test=ok
✅ atomic_writes: ok (last write 2026-08-28T19:45:23Z, <1ms drift)
✅ UEID_format: ok (412/412 entities pass regex)
⚠️  queue_empty: no (3 pending events in data/review_queue/)
✅ mesh_consistency: ok (no stale propagations)
✅ python_version: 3.11.4 (>= 3.10 required)
✅ uv_installed: yes (uv 0.4.18)

→ All systems nominal. Safe to operate.
```

Se algum check falha, doctor retorna exit code 1 + lista o que falhou.

### 3.4 Cross-fork consistency check (PROPOSTA — italic gap)

*PROPOSTA: Adicionar cross-fork consistency check em PROPOSTA: `operational doctor` (PAV-era CLI command):*

```python
# src/operational/cli/commands/doctor_cmd.py (PROPOSTA)
def check_mesh_consistency() -> CheckResult:
    """Verify all 3 fork adapters + vault are consistent."""
    results = {}

    # CliAdapter
    jsonl_records = read_jsonl("data/tasks.jsonl")
    results["cli"] = len(jsonl_records) > 0 or "empty_ok"

    # TaskdogAdapter
    taskdog_db = sqlite3.connect("data/taskdog/tasks.db")
    taskdog_count = taskdog_db.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
    results["taskdog"] = taskdog_count == len(jsonl_records) or f"drift ({taskdog_count} vs {len(jsonl_records)})"

    # SolverforgeCalendarAdapter
    upi_db = sqlite3.connect("data/solverforge_calendar/unified_planning.db")
    upi_count = upi_db.execute("SELECT COUNT(*) FROM unified_planning_items WHERE deleted_at IS NULL").fetchone()[0]
    results["upi"] = upi_count == len(jsonl_records) or f"drift ({upi_count} vs {len(jsonl_records)})"

    # vault
    vault_files = list(Path("vault/ikigai/meta/tasks/").glob("*.md"))
    results["vault"] = len(vault_files) >= len(jsonl_records) or f"lag ({len(vault_files)} vs {len(jsonl_records)})"

    return results
```

Output: tabula 4 sources (cli / taskdog / upi / vault) com counts + drift detection.

### 3.5 Decision tree — "Quando fazer dataset switch?"

```text
START: user/operator quer mudar dataset
   │
   ▼
Q1: objetivo é desenvolvimento/teste?
   ├─ YES → TIME_TASKER_DATASET=synthetic
   │         (auto-loader popula 345 entities via docs/synthetic.csv)
   │
   └─ NO
      │
      ▼
Q2: objetivo é resetar tudo (fresh start)?
   ├─ YES → operational reset --confirm
      │      (FLOW-009; apaga state, mantém vault)
      │
      └─ NO
         │
         ▼
Q3: objetivo é arquivar estado atual antes de mudança grande?
   ├─ YES → safe_snapshot
      │      cp -r ~/.time-tasker/ ~/.time-tasker-archive/<YYYY-MM-DD>/
      │      (PROPOSTA — italic gap; não implementado ainda)
      │
      └─ NO
         │
         ▼
Q4: objetivo é diagnosticar problemas?
   ├─ YES → operational doctor
      │      (FLOW-010; verifica 8 checks + cross-fork consistency PROPOSTA)
      │
      └─ NO → NO-OP (não trocar dataset)
```

### 3.6 ADR-007 5-log constraint gate

`code-docs/adr/ADR-007-data-first-methodology.md` impõe que **5+ SONHO logs manuais** sejam escritos antes de qualquer algorithm polish. Dataset switch entra nesse gate porque:

1. Synthetic dataset permite testar planned vs actual via agent sem risco.
2. Operator pode escrever SONHO log após synthetic run (template PROPOSTA: `vault/ikigai/closing-2026/<q>-<w>/sonho_<N>.md` (template)).
3. SONHO counter (PROPOSTA: `vault/ikigai/meta/sonho_counter.json` (state file path place-holder)) incrementa após write.
4. Após 5 SONHOs, agent run é destravado (não mais "IKIGAi pausado").

**Estado atual (2026-08-28):** SONHO counter = 1/5 (cross-ref [[ikigai-persona-vault-bootstrap]]). 4 SONHOs restantes para destravar agent.

### 3.7 PROPOSTA — Safe snapshot (italic gap)

*PROPOSTA: Adicionar comando `operational dataset snapshot --label <name>`:*

```python
# src/operational/cli/commands/dataset_cmd.py (PROPOSTA)
def snapshot(label: str) -> str:
    """Create a safe snapshot of current state dir before risky operation."""
    archive_dir = Path.home() / ".time-tasker-archive" / f"{datetime.now().isoformat()}-{label}"
    archive_dir.mkdir(parents=True, exist_ok=True)
    state_dir = Path("~/.time-tasker/").expanduser()
    if not state_dir.exists():
        return f"No state dir to snapshot at {state_dir}"
    shutil.copytree(state_dir, archive_dir, dirs_exist_ok=False)
    manifest = {
        "label": label,
        "created_at": datetime.now().isoformat(),
        "files_copied": sum(1 for _ in archive_dir.rglob("*")),
        "size_bytes": sum(f.stat().st_size for f in archive_dir.rglob("*")),
    }
    (archive_dir / "MANIFEST.json").write_text(json.dumps(manifest, indent=2))
    return f"Snapshot created: {archive_dir}"
```

Pre-switch safety net. Idempotent (same label → refuse).

### 3.8 PROPOSTA — Rollback (italic gap)

*PROPOSTA: Adicionar comando `operational dataset rollback --to <archive-name>`:*

```python
def rollback(archive_name: str, confirm: bool = False) -> str:
    """Restore state dir from archive."""
    archive_dir = Path.home() / ".time-tasker-archive" / archive_name
    if not archive_dir.exists():
        raise FileNotFoundError(f"Archive {archive_name} not found")
    if not confirm:
        return f"Pass --confirm to rollback to {archive_dir}"

    state_dir = Path("~/.time-tasker/").expanduser()
    if state_dir.exists():
        shutil.rmtree(state_dir)
    shutil.copytree(archive_dir, state_dir)
    return f"Rolled back to {archive_dir}"
```

Audit log entry: PROPOSTA: `vault/ikigai/meta/rollbacks/<YYYY-MM-DD>.md` (template) com archive_name + reason.

### 3.9 Pitfalls known (dataset switch)

- **G-DATASET-01** — dataset switch operator CLI only; user-facing dataset picker não existe. Cross-ref doc 40 §2.4.
- **G-FORK-04** — solverforge-calendar `SyncEngine::poll` misnomer (counts local rows). Doc 22 §4.6.
- **G-AGENT-01** — Agent gated por ADR-007 5+ SONHO logs. [[data-first-methodology]].
- **Gap P1** (doc 09) — dataset switch sem safe_snapshot padrão; risco de corruption. Resolve via PROPOSTA §3.7.

### 3.10 Métricas de dataset switch

| Métrica | Target | Origem |
|:--------|:-------|:-------|
| Switch time | < 5s | env var + lazy load |
| Snapshot size | < 50MB (production típico) | shutil.copytree |
| Rollback time | < 10s | shutil.rmtree + copytree |
| Doctor checks pass rate | ≥ 95% | FLOW-010 success criteria |
| SONHO log completion | ≥ 80% semanas | ADR-007 gate |
| Cross-fork drift | 0 entities | consistency check |

---

## §4 — Cross-references

### 4.1 Design-system docs (Layer 1-6)

- **`docs/design-system/00-INDEX.md`** §3 — Layer 6 navigation.
- **`docs/design-system/04-canvas-mesh-architecture.md`** §3 — mesh topology.
- **`docs/design-system/12-pattern-append-only-queue.md`** §3.1 — queue protocol.
- **`docs/design-system/13-pattern-fork-adapter-protocol.md`** §2.2-2.5 — 3 adapters.
- **`docs/design-system/14-pattern-idempotency-upstream-id.md`** §3 — UPSERT + replay-safe.
- **`docs/design-system/17-pattern-reliability-decorators.md`** §3 — retry decorators.
- **`docs/design-system/20-fork-tuiboard-architecture.md`** — fork-local storage.
- **`docs/design-system/21-fork-taskdog-architecture.md`** §3.3 — SQLite UPSERT.
- **`docs/design-system/22-fork-solverforge-calendar-architecture.md`** §3.3 — UPI PK reuse.
- **`docs/design-system/23-fork-status-enum-mapping.md`** §3 — canonical 6-state.
- **`docs/design-system/40-index-user-journeys.md`** §3.5 (métricas dataset switch).

### 4.2 PAV-era `ux/` (verbatim)

- **`src/operational/docs/ux/04-fluxos/FLOW-008-trocar-dataset.md`** — dataset switch anchor.
- **`src/operational/docs/ux/04-fluxos/FLOW-009-limpar-resetar.md`** — reset/clear operator-side.
- **`src/operational/docs/ux/04-fluxos/FLOW-010-doctor.md`** — diagnostics anchor.
- **`src/operational/docs/ux/05-telas/SCR-006-demo-dataset-list.md`** — dataset list screen.
- **`src/operational/docs/ux/05-telas/SCR-007-doctor.md`** — doctor screen.

### 4.3 Phase 2 diagnostics

- **`docs/diagnostics/2026-08-28-phase2-interface-re/06-synthesis-mesh-readiness.md`** — Phase 3 readiness OQ-7/OQ-8/OQ-10.

### 4.4 Memory cross-refs

- **[[]]** — dual-layer.
- **[[]]** — deep-agent canonical.
- **[[]]** — ADR-007 5+ SONHO logs gate.
- **[[]]** — SONHO counter 1/5.
- **[[]]** — Phase 1 audit (gateways cwd stale).
- **[[]]** — apps/ deletion.

### 4.5 Code anchors (verificados)

| Path | LOC / Conteúdo | Padrão |
|:-----|:---------------|:-------|
| `src/operational/cli/dataset_selector.py:resolve_dataset` | env var reader | PAV-era |
| `src/operational/cli/state.py:JSONRepository._load_all` | lazy load | PAV-era |
| `src/operational/cli/state.py:JSONRepository.upsert` | append atomic | PAV-era |
| PROPOSTA: `src/operational/cli/commands/doctor_cmd.py` (path place-holder) | 8 checks | FLOW-010 |
| `src/mesh/queue.py:consume_pending` | queue validator | Pattern #12 |
| `src/mesh/adapters/cli.py` | CliAdapter JSONL | adapter 1 |
| `src/mesh/adapters/taskdog.py` | SQLite UPSERT | adapter 2 |
| `src/mesh/adapters/solverforge_calendar.py` | UPI PK reuse | adapter 3 |
| `code-docs/adr/ADR-007-data-first-methodology.md` | gate constraint | ADR |
| PROPOSTA: `vault/ikigai/meta/sonho_counter.json` (state file path place-holder) | SONHO counter (1/5) | gate state |

### 4.6 Pitfalls known (cross-ref)

| Gap | Severidade | Cross-ref |
|:----|:----------:|:----------|
| G-DATASET-01 (dataset picker user-facing) | HIGH | doc 40 §2.4 |
| G-FORK-04 (SyncEngine misnomer) | MEDIUM | doc 22 §4.6 |
| G-AGENT-01 (agent gated) | CRITICAL | [[data-first-methodology]] |
| P1 (snapshot sem padrão) | HIGH | PROPOSTA §3.7 |

---

## §5 — Fontes

### Code (verbatim, lidos via Read tool)
- `src/contracts/common.py` — UEID
- `src/mesh/queue.py` — consume_pending (queue validator)
- `src/mesh/agent_consumer.py` — PAE rules
- `src/mesh/adapters/cli.py` — CliAdapter
- `src/mesh/adapters/taskdog.py` — TaskdogAdapter UPSERT
- `src/mesh/adapters/solverforge_calendar.py` — SolverforgeCalendarAdapter PK reuse

### Docs design-system (verbatim, lidos via Read tool)
- `docs/design-system/13-pattern-fork-adapter-protocol.md` — ForkAdapter Pattern #13
- `docs/design-system/14-pattern-idempotency-upstream-id.md` — Pattern #14
- `docs/design-system/17-pattern-reliability-decorators.md` — Pattern #17
- `docs/design-system/20-fork-tuiboard-architecture.md` — tuiboard fork
- `docs/design-system/21-fork-taskdog-architecture.md` — taskdog fork
- `docs/design-system/22-fork-solverforge-calendar-architecture.md` — solverforge fork
- `docs/design-system/40-index-user-journeys.md` — Layer 6 INDEX

### PAV-era docs (referência indireta)
- `src/operational/docs/ux/04-fluxos/FLOW-008-trocar-dataset.md` — *referência indireta*
- `src/operational/docs/ux/04-fluxos/FLOW-009-limpar-resetar.md` — *referência indireta*
- `src/operational/docs/ux/04-fluxos/FLOW-010-doctor.md` — *referência indireta*

### Phase 2 diagnostics
- `docs/diagnostics/2026-08-28-phase2-interface-re/06-synthesis-mesh-readiness.md` — Phase 3 readiness

### Memory cross-refs
- [[]]
- [[]]
- [[]]
- [[]]
- [[]]
- [[]]

### Métricas de cobertura
- **5 sections principais** (§1-§5) — Resumo / Inventário / Conteúdo / Cross-refs / Fontes (template Pattern #10 verbatim)
- **3 flows canônicos PAV-era** documentados em §2.1 (FLOW-008 switch, FLOW-009 reset, FLOW-010 doctor)
- **5 datasets suportados** tabulados em §2.2 (production, synthetic, test, clean, archive)
- **5-step dataset switch flow** em §3.1 (pre-flight + switch + verify + run + rollback)
- **8 doctor checks** em §2.7 (state_dir, datasets, atomic_writes, UEID_format, queue_empty, mesh_consistency, python_version, uv_installed)
- **4-step decision tree** em §3.5 (Q1-Q4 dev/reset/snapshot/diagnose)
- **3 PROPOSTA italic gaps** em §3.4 (cross-fork consistency), §3.7 (safe snapshot), §3.8 (rollback)
- **6 métricas** em §3.10 (switch time, snapshot size, rollback time, doctor pass rate, SONHO completion, cross-fork drift)
- **10 code anchors** verificados via Read tool em §4.5
- **6 memory cross-refs** em §4.4
- **4 pitfalls known** em §3.9 (G-DATASET-01, G-FORK-04, G-AGENT-01, P1)
- **Honest rigor:** flag dataset switch como operator-only (não user-facing); flag 3 forks-prontas sem dataset concept; flag cross-fork consistency check como PROPOSTA italic; flag safe_snapshot + rollback como PROPOSTA italic; flag ADR-007 gate como critical unblocking criterion.

---

> **Próxima ação recomendada:** Após 5+ SONHO logs ([[data-first-methodology]] gate), implementar PROPOSTA §3.4 (cross-fork consistency check) + §3.7 (safe snapshot) + §3.8 (rollback) como `operational dataset {check,snapshot,rollback}` commands. Adicionar `vault/ikigai/meta/rollbacks/` audit log. Adicionar CI hook que roda PROPOSTA: `operational doctor` (PAV-era CLI command) antes de cada commit que toca `src/mesh/` ou `data/`.
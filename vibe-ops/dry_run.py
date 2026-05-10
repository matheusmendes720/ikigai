"""
Dry Run — Cybernetic MVL
Testa o pipeline completo sem depender do binário `task` instalado.
Usa um MockTaskWarrior quando o binário não está disponível.
"""
import sys, os, sqlite3, json, shutil, uuid
from pathlib import Path
from datetime import date

# ── path setup ────────────────────────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

# ── mock TW (sem binário 'task') ───────────────────────────────
class _MockTask(dict):
    def __init__(self, **kw):
        super().__init__(uuid=str(uuid.uuid4()), status="pending", **kw)
    def save(self):
        pass
    def done(self):
        self["status"] = "completed"

class _MockTaskSet:
    def __init__(self):
        self._tasks: list[_MockTask] = []

    def add(self, **kw) -> _MockTask:
        t = _MockTask(**kw)
        self._tasks.append(t)
        return t

    def pending(self):
        return [t for t in self._tasks if t["status"] == "pending"]

    def filter(self, **kw):
        results = []
        for t in self._tasks:
            if all(t.get(k) == v for k, v in kw.items()):
                results.append(t)
        return results

    def get(self, **kw):
        res = self.filter(**kw)
        if not res:
            raise KeyError(f"Task not found: {kw}")
        return res[0]

class MockTaskWarrior:
    def __init__(self):
        self.tasks = _MockTaskSet()


# ── imports do projeto ─────────────────────────────────────────
from cybernetics.daily_loop import CyberneticDailyLoop
from middleware.sync_engine import SyncEngine


def run():
    print("─" * 60)
    print("   Dry Run — Cybernetic MVL  (mock TW)")
    print("─" * 60)

    base_dir  = Path(__file__).parent
    db_path   = base_dir / "test_vibe.db"
    tw_path   = base_dir / "test_tw_data"
    vault_path = base_dir / "test_vault"

    # ── limpeza ────────────────────────────────────────────────
    for p in [db_path, tw_path, vault_path]:
        if p.exists():
            p.unlink() if p.is_file() else shutil.rmtree(p)
    vault_path.mkdir()
    tw_path.mkdir()

    # ── 1. Schema ─────────────────────────────────────────────
    print("\n[1] Inicializando schema SQLite...")
    schema_path = base_dir / "src" / "storage" / "schema.sql"
    with sqlite3.connect(db_path) as conn:
        conn.executescript(schema_path.read_text(encoding="utf-8"))
    print("    ✓ Schema aplicado")

    # ── 2. Seed data ──────────────────────────────────────────
    print("\n[2] Inserindo dados de teste...")
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO habits (id, name, category, weight_in_qhe, status) "
            "VALUES ('h1', 'Leitura Técnica', 'Estudo', 1.0, 'active')"
        )
        conn.execute(
            "INSERT INTO habit_states (habit_id, date, streak_current, executed) "
            "VALUES ('h1', date('now','-1 day'), 0, 1)"
        )
        conn.execute(
            "INSERT INTO habit_states (habit_id, date, streak_current, executed) "
            "VALUES ('h1', date('now'), 1, 0)"
        )
        conn.execute(
            "INSERT INTO study_sessions (date, duration_minutes, topic_id) "
            "VALUES (date('now'), 45, NULL)"
        )
        dummy_plan = {
            "id": "sp1",
            "entity_type": "study_plan",
            "title": "FastAPI Avançado",
            "tw_project_key": "S1.O2.study_backend_01",
            "daily_target_minutes": 30,
        }
        conn.execute(
            "INSERT INTO planning_entities (id, entity_type, payload_json, upstream_id) "
            "VALUES (?, ?, ?, ?)",
            ("sp1", "study_plan", json.dumps(dummy_plan), "seed_hash_001"),
        )
        conn.execute(
            "INSERT INTO roadmap_sync (study_plan_fk, status) VALUES (?, ?)",
            ("sp1", "pending"),
        )
        conn.commit()
    print("    ✓ Dados inseridos")

    # ── 3. SyncEngine: SQLite → TW (mock) ────────────────────
    print("\n[3] SyncEngine: SQLite → TaskWarrior (mock)...")
    mock_tw = MockTaskWarrior()
    sync = SyncEngine(vault_path, db_path, tw_path, tw_client=mock_tw)
    stats_out = sync.sync_sqlite_to_taskwarrior("MAINTAIN")
    print(f"    Sync stats: {stats_out}")
    pending = mock_tw.tasks.pending()
    print(f"    Tarefas pendentes: {len(pending)}")
    for t in pending:
        print(f"      → {t['description']} | projeto={t.get('project')} | upstream={t.get('upstream_id')}")

    # ── 4. Simular conclusão de tarefa ────────────────────────
    print("\n[4] Marcando tarefas como concluídas...")
    for t in pending:
        t.done()
        print(f"    ✓ '{t['description']}' concluída")

    # ── 5. SyncEngine: TW → SQLite ───────────────────────────
    print("\n[5] SyncEngine: TaskWarrior → SQLite (reverse sync)...")
    stats_in = sync.sync_taskwarrior_to_sqlite()
    print(f"    Sync stats: {stats_in}")

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT status FROM roadmap_sync WHERE study_plan_fk = 'sp1'"
        ).fetchone()
        print(f"    roadmap_sync.status: {row['status']}")

    # ── 6. CyberneticDailyLoop ───────────────────────────────
    print("\n[6] Executando CyberneticDailyLoop...")
    loop = CyberneticDailyLoop(db_path, tw_path, vault_path, tw_client=mock_tw)
    decision = loop.execute_daily_cycle(date.today())
    print(f"    Policy decidida : {decision.policy.value}")
    print(f"    QHE             : {decision.qhe}")
    print(f"    Budget horas    : {decision.hardwork_budget_hours}h")
    print(f"    Recomendações   : {decision.recomendacoes}")

    # ── 7. Verificar persistência ─────────────────────────────
    print("\n[7] Verificando policy_decisions no DB...")
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT date, policy, qhe, hardwork_budget_hours FROM policy_decisions"
        ).fetchall()
        for r in rows:
            print(f"    {r['date']} | {r['policy']} | qhe={r['qhe']} | {r['hardwork_budget_hours']}h")

    print("\n" + "─" * 60)
    print("   ✅  Dry Run Completo — todos os módulos funcionaram")
    print("─" * 60)


if __name__ == "__main__":
    run()

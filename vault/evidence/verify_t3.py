import sys; sys.path.insert(0, 'src')
import tempfile, os
from pathlib import Path
from middleware.period_sync import PeriodReportSync

with tempfile.TemporaryDirectory() as tmp:
    vault = Path(tmp) / 'vault'
    templates = vault / '_templates_periodos'
    templates.mkdir(parents=True)

    (templates / 'sonho-1.md').write_text("""---
type: period_report
entity_type: period_report
period: sonho
id: sonho-1
date_start: 2026-01-01
date_end: 2026-12-31
verdict: ACTIVE
verdict_score: 0.70
template_version: '1.0'
ikigai_cluster: plan
ikigai_vector: passion
status: active
tags: [period/sonho]
---
""", encoding='utf-8')

    (templates / 'Q1-2026.md').write_text("""---
type: period_report
entity_type: period_report
period: quarterly
id: Q1-2026
date_start: 2026-01-01
date_end: 2026-03-31
verdict: PASS
verdict_score: 0.75
sonho_id: sonho-1
parent_period: sonho-1
ikigai_vector: passion
status: active
tags: [period/quarterly]
---
""", encoding='utf-8')

    (templates / 'orphan.md').write_text("""---
type: period_report
entity_type: period_report
period: weekly
id: orphan-week
date_start: 2026-01-01
date_end: 2026-01-07
verdict: PASS
verdict_score: 0.80
sonho_id: sonho-1
parent_period: NONEXISTENT
ikigai_vector: skill
status: active
tags: [period/weekly]
---
""", encoding='utf-8')

    (templates / 'broken.md').write_text("""---
type: period_report
period: daily
date_start: not-a-date
date_end: 2026-06-26
verdict: PASS
verdict_score: 0.85
---
""", encoding='utf-8')

    db = Path(tmp) / 'test.db'
    sync = PeriodReportSync(vault, db)

    stats1 = sync.sync_vault_to_db()
    print(f"PASS1: ingested={stats1.ingested}, skipped={stats1.skipped}, errors={stats1.errors}, orphans={stats1.orphans}")
    # Alphabetical sort: Q1-2026, broken, orphan, sonho-1
    # Q1-2026 → parent_period=sonho-1 NOT YET in DB → orphan
    # broken → parser returns None → skipped (silent)
    # orphan-week → parent_period=NONEXISTENT → orphan
    # sonho-1 → no parent_period → ingested
    assert stats1.ingested == 1, f"Expected 1 ingested (sonho-1), got {stats1.ingested}"
    assert stats1.orphans == 2, f"Expected 2 orphans, got {stats1.orphans}"
    assert stats1.skipped == 0, f"Expected 0 skipped, got {stats1.skipped}"

    stats2 = sync.sync_vault_to_db()
    print(f"PASS2: ingested={stats2.ingested}, skipped={stats2.skipped}, errors={stats2.errors}, orphans={stats2.orphans}")
    # Pass 2: Q1-2026 parent now resolves → ingested; orphan-week still orphan; broken/sonho skipped
    assert stats2.ingested == 1, f"Expected 1 ingested (Q1-2026), got {stats2.ingested}"
    assert stats2.skipped == 1, f"Expected 1 skipped (sonho-1), got {stats2.skipped}"
    assert stats2.orphans == 1, f"Expected 1 orphan, got {stats2.orphans}"

    tree = sync.get_period_hierarchy('sonho-1')
    print(f"HIERARCHY: count={tree['count']}, roots={len(tree['tree'])}")
    assert tree['count'] == 2
    assert len(tree['tree']) == 1
    assert len(tree['tree'][0]['children']) == 1

    noop = sync.sync_db_to_vault()
    print(f"NOOP: ingested={noop.ingested}, skipped={noop.skipped}, errors={noop.errors}")
    assert noop.ingested == 0 and noop.skipped == 0

    import sqlite3
    with sqlite3.connect(db) as conn:
        count = conn.execute('SELECT COUNT(*) FROM period_reports').fetchone()[0]
        print(f"DB_ROWS: {count}")
        assert count == 2

    print("ALL T3 TESTS PASSED")
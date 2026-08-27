"""QA verification script for PeriodReportSync (T3).

Run from vibe-ops/:
    uv run --with pydantic --with python-frontmatter python ../.omo/evidence/period-3-verify.py
"""
import sys
sys.path.insert(0, 'src')

import json
import sqlite3
import tempfile
from pathlib import Path

from middleware.period_sync import PeriodReportSync


def write_md(path: Path, content: str) -> None:
    path.write_text(content, encoding='utf-8')


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        vault = Path(tmp) / 'vault'
        templates = vault / '_templates_periodos'
        templates.mkdir(parents=True)

        # Sonho (root)
        write_md(templates / 'sonho-1.md',
                 "---\n"
                 "type: period_report\n"
                 "entity_type: period_report\n"
                 "period: sonho\n"
                 "id: sonho-1\n"
                 "date_start: 2026-01-01\n"
                 "date_end: 2026-12-31\n"
                 "verdict: ACTIVE\n"
                 "verdict_score: 0.70\n"
                 "template_version: '1.0'\n"
                 "ikigai_cluster: plan\n"
                 "ikigai_vector: passion\n"
                 "status: active\n"
                 "tags: [period/sonho]\n"
                 "---\n"
                 "\n"
                 "# Sonho body\n")

        # Trimestral (parent = sonho-1)
        write_md(templates / 'Q1-2026.md',
                 "---\n"
                 "type: period_report\n"
                 "entity_type: period_report\n"
                 "period: quarterly\n"
                 "id: Q1-2026\n"
                 "date_start: 2026-01-01\n"
                 "date_end: 2026-03-31\n"
                 "verdict: PASS\n"
                 "verdict_score: 0.75\n"
                 "sonho_id: sonho-1\n"
                 "parent_period: sonho-1\n"
                 "ikigai_vector: passion\n"
                 "status: active\n"
                 "tags: [period/quarterly]\n"
                 "---\n"
                 "\n"
                 "# Trimestral body\n")

        # Broken YAML (date_start is invalid)
        write_md(templates / 'broken.md',
                 "---\n"
                 "type: period_report\n"
                 "period: daily\n"
                 "date_start: not-a-date\n"
                 "date_end: 2026-06-26\n"
                 "verdict: PASS\n"
                 "verdict_score: 0.85\n"
                 "---\n")

        db = Path(tmp) / 'test.db'
        sync = PeriodReportSync(vault, db)

        # Pass 1
        stats1 = sync.sync_vault_to_db()
        print(f'PASS1: ingested={stats1.ingested}, skipped={stats1.skipped}, '
              f'errors={stats1.errors}, orphans={stats1.orphans}')

        # Pass 2 (idempotency)
        stats2 = sync.sync_vault_to_db()
        print(f'PASS2: ingested={stats2.ingested}, skipped={stats2.skipped}, '
              f'errors={stats2.errors}, orphans={stats2.orphans}')

        # Hierarchy
        tree = sync.get_period_hierarchy('sonho-1')
        print(f'HIERARCHY: count={tree["count"]}, roots={len(tree["tree"])}')
        if tree['tree']:
            root = tree['tree'][0]
            print(f'  root.id={root["id"]}, children={len(root["children"])}')

        # DB row count
        with sqlite3.connect(db) as conn:
            count = conn.execute('SELECT COUNT(*) FROM period_reports').fetchone()[0]
            print(f'DB_ROWS: {count}')

        # sync_db_to_vault no-op stub
        stats3 = sync.sync_db_to_vault()
        print(f'SYNC_DBV: ingested={stats3.ingested}, skipped={stats3.skipped}, '
              f'errors={stats3.errors}, orphans={stats3.orphans}, '
              f'updated={stats3.updated}, conflicts={stats3.conflicts}')


if __name__ == '__main__':
    main()

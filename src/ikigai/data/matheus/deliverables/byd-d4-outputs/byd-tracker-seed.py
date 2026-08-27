"""BYD + Salvador outreach tracker seed script — pre-fill 6 planned outreach events.

Usage:
    python byd-tracker-seed.py

Pre-fills:
- 1 BYD anchor (Yueying Zhang, Business Specialist Camacari) — T0 lean
- 5 Salvador/remote Tier 1 fallback (FullStack, BairesDev, Jobbol, INDI, Alignerr)

Idempotent: skips INSERTs if outreach_id already exists.
"""

from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

DB_FILE = Path(__file__).parent / "byd-tracker.db"

# Pre-planned outreach events (Wd 1 batch)
PLANNED_OUTREACH = [
    {
        "company": "BYD",
        "vaga": "Business Specialist Camacari",
        "channel": "linkedin_message",
        "manager_name": "Yueying Zhang",
        "manager_ueid": "ikigai:manager:yueying-zhang-byd:00000000:00000000",
        "persona_used": "T0_lean",
        "template_id": "t0-lean-linkedin-byh",
        "message_body": "Olá Yueying, vi a vaga de Business Specialist em Camaçari (postada ontem). Sou Matheus, Salvador-BA, trabalho com análise quantitativa (análise de vulnerabilidades cambiais e supply chain). Estou começando um estudo focado em BYD Brasil esse mês. Posso contribuir para essa posição? Abraço.",
        "notes": "ANCHOR #1 — posted 2026-07-08 (1 dia), 200+ applicants esperados, function Supply Chain",
    },
    {
        "company": "FullStack Labs",
        "vaga": "Data Engineer Remote",
        "channel": "linkedin_message",
        "manager_name": "TBD_recruiter",
        "manager_ueid": None,
        "persona_used": "T1_polite",
        "template_id": "t1-fullstack-data-engineer",
        "message_body": "Olá! Vi a vaga de Data Engineer Remote. Sou Matheus, Salvador-BA, trabalho com Python/Polars + data pipelines (DuckDB, Plotly). Posso contribuir para o time de Salvador. Posso compartilhar 1-pager de análise quant que fiz esse mês? Abraço.",
        "notes": "TIER 1 FALLBACK #1 — posted 2026-07-09 (6h ago), Salvador remote, Python/data puro",
    },
    {
        "company": "BairesDev",
        "vaga": "Analista de Dados Remoto",
        "channel": "email",
        "manager_name": "TBD_TA_LATAM",
        "manager_ueid": None,
        "persona_used": "T3_email",
        "template_id": "t3-bairesdev-analista",
        "message_body": "Sou Matheus Mendes, Salvador-BA, atuo com Python/Polars aplicado a análise de dados quantitativos (PTAX, supply chain, risco regulatório). Vi a vaga Analista de Dados Remoto postada 3 d atrás — localização Salvador + stack Python = match perfeito. Posso compartilhar 1-pager de análise que fiz esse mês (BRL/USD stress test BYD Brasil) em 15 min de conversa.",
        "notes": "TIER 1 FALLBACK #2 — posted 2026-07-06 (3d), remote-first established company",
    },
    {
        "company": "Jobbol",
        "vaga": "Engenheiro de Dados Pleno Salvador",
        "channel": "linkedin_message",
        "manager_name": "platform_no_specific_manager",
        "manager_ueid": None,
        "persona_used": "T1_polite",
        "template_id": "t1-jobbol-engenheiro-dados",
        "message_body": "Sou Matheus, Salvador-BA, Python + Polars + DuckDB + data pipelines. Vi a vaga Engenheiro Dados Pleno. Localização + stack alinham perfeitamente. Posso demonstrar com 1-pager de análise quantitativa (cambio BYD) que preparei este mês. Prazo de início imediato.",
        "notes": "TIER 1 FALLBACK #3 — posted 2026-06-25 (2 sem), job portal aggregator, no individual manager",
    },
    {
        "company": "INDI Staffing",
        "vaga": "Talent Data Analyst Remote",
        "channel": "linkedin_message",
        "manager_name": "TBD_INDI_recruiter",
        "manager_ueid": None,
        "persona_used": "T1_polite",
        "template_id": "t1-indi-talent-analyst",
        "message_body": "Olá! Vi a vaga Talent Data Analyst Remote na INDI. Sou Matheus, Salvador-BA, Python + análise de dados. Remoto + análise quantitativa = match. Posso compartilhar 1-pager de análise BYD cambial que fiz este mês. 15 min? Abraço.",
        "notes": "TIER 1 FALLBACK #4 — posted 2026-07-08 (1d), staffing agency, remote flexibility",
    },
    {
        "company": "Alignerr",
        "vaga": "Engenheiro Software AI Training",
        "channel": "linkedin_message",
        "manager_name": "TBD_Alignerr_recruiter",
        "manager_ueid": None,
        "persona_used": "T1_polite",
        "template_id": "t1-alignerr-ai-training",
        "message_body": "Olá! Vi a vaga Engenheiro Software AI Training na Alignerr. Sou Matheus, Salvador-BA, Python + ML básico + análise quantitativa. AI training = avaliar outputs modelo + data quality = match com minha stack. Posso compartilhar 1-pager de análise cambial BYD este mês? Abraço.",
        "notes": "TIER 1 FALLBACK #5 — posted 2026-07-09 (17h ago), URGENT fresh, AI training annotation",
    },
]

# Process entries: per-vaga lifecycle (status: discovered → planned outreach)
PLANNED_PROCESS = [
    {
        "company": "BYD",
        "vaga": "Business Specialist Camacari",
        "stage": "discovered",
        "stage_entered_at": "2026-07-09T00:00:00Z",
        "next_action": "Send T0 LinkedIn connection + T0 email to Yueying Zhang",
        "next_action_at": "2026-07-09T12:00:00Z",
        "contact_email": "yueying.zhang@byd.com (Hunter.io verify)",
        "contact_linkedin": "https://linkedin.com/in/yueying-zhang-byh-brasil",
        "salary_brl": None,
        "notes": "ANCHOR #1; YGN if no response in 5 wd → escalate Salvador tier 1 to primary",
    },
    {
        "company": "FullStack Labs",
        "vaga": "Data Engineer Remote",
        "stage": "discovered",
        "stage_entered_at": "2026-07-09T00:00:00Z",
        "next_action": "Send LinkedIn connection + Easy Apply cover note",
        "next_action_at": "2026-07-09T18:00:00Z",
        "contact_email": "recruiter@fullstacklabs.com (verify Hunter.io)",
        "contact_linkedin": None,
        "salary_brl": None,
        "notes": "TIER 1 FALLBACK #1",
    },
    {
        "company": "BairesDev",
        "vaga": "Analista de Dados Remoto",
        "stage": "discovered",
        "stage_entered_at": "2026-07-09T00:00:00Z",
        "next_action": "Send email to careers@bairesdev.com + apply via portal",
        "next_action_at": "2026-07-09T18:00:00Z",
        "contact_email": "careers@bairesdev.com",
        "contact_linkedin": None,
        "salary_brl": None,
        "notes": "TIER 1 FALLBACK #2",
    },
    {
        "company": "Jobbol",
        "vaga": "Engenheiro de Dados Pleno Salvador",
        "stage": "discovered",
        "stage_entered_at": "2026-07-09T00:00:00Z",
        "next_action": "Apply via Jobbol platform (no individual outreach)",
        "next_action_at": "2026-07-09T20:00:00Z",
        "contact_email": "n/a (job portal)",
        "contact_linkedin": None,
        "salary_brl": None,
        "notes": "TIER 1 FALLBACK #3",
    },
    {
        "company": "INDI Staffing",
        "vaga": "Talent Data Analyst Remote",
        "stage": "discovered",
        "stage_entered_at": "2026-07-09T00:00:00Z",
        "next_action": "Send LinkedIn Easy Apply + INDI recruiter outreach",
        "next_action_at": "2026-07-10T12:00:00Z",
        "contact_email": "TBD (verify Hunter.io)",
        "contact_linkedin": None,
        "salary_brl": None,
        "notes": "TIER 1 FALLBACK #4",
    },
    {
        "company": "Alignerr",
        "vaga": "Engenheiro Software AI Training",
        "stage": "discovered",
        "stage_entered_at": "2026-07-09T00:00:00Z",
        "next_action": "Send LinkedIn Easy Apply + Alignerr recruiter outreach",
        "next_action_at": "2026-07-10T12:00:00Z",
        "contact_email": "careers@alignerr.com",
        "contact_linkedin": None,
        "salary_brl": None,
        "notes": "TIER 1 FALLBACK #5",
    },
]


def seed_outreach(db_path: Path = DB_FILE) -> None:
    """Insert planned outreach events (idempotent by outreach_id)."""
    conn = sqlite3.connect(db_path)
    try:
        now = datetime.now(timezone.utc).isoformat()
        inserted = 0
        skipped = 0
        for o in PLANNED_OUTREACH:
            outreach_id = f"ikigai:outreach:{uuid.uuid4().hex[:8]}:00000000"
            sent_at = "2026-07-09T00:00:00Z"  # planned, not yet sent
            cur = conn.execute(
                """INSERT OR IGNORE INTO outreach (
                    outreach_id, sent_at, company, vaga, channel, manager_name,
                    manager_ueid, persona_used, template_id, message_body,
                    notes, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    outreach_id, sent_at, o["company"], o["vaga"], o["channel"],
                    o["manager_name"], o["manager_ueid"], o["persona_used"],
                    o["template_id"], o["message_body"], o["notes"], now, now
                ),
            )
            if cur.rowcount > 0:
                inserted += 1
            else:
                skipped += 1
        conn.commit()
        print(f"outreach: {inserted} inserted, {skipped} skipped (already exist)")

        inserted = 0
        skipped = 0
        for p in PLANNED_PROCESS:
            process_id = f"ikigai:process:{uuid.uuid4().hex[:8]}:00000000"
            cur = conn.execute(
                """INSERT OR IGNORE INTO process (
                    process_id, company, vaga, stage, stage_entered_at,
                    next_action, next_action_at, contact_email, contact_linkedin,
                    salary_brl, notes, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    process_id, p["company"], p["vaga"], p["stage"],
                    p["stage_entered_at"], p["next_action"], p["next_action_at"],
                    p["contact_email"], p["contact_linkedin"], p["salary_brl"],
                    p["notes"], now, now
                ),
            )
            if cur.rowcount > 0:
                inserted += 1
            else:
                skipped += 1
        conn.commit()
        print(f"process: {inserted} inserted, {skipped} skipped (already exist)")

        # Verify
        cur = conn.execute("SELECT company, vaga, channel, persona_used FROM outreach ORDER BY company")
        print("\n=== outreach rows ===")
        for row in cur.fetchall():
            print(f"  {row[0]:<20} {row[1]:<45} {row[2]:<22} {row[3]}")
        cur = conn.execute("SELECT company, vaga, stage FROM process ORDER BY company")
        print("\n=== process rows ===")
        for row in cur.fetchall():
            print(f"  {row[0]:<20} {row[1]:<45} {row[2]}")
    finally:
        conn.close()


if __name__ == "__main__":
    seed_outreach()
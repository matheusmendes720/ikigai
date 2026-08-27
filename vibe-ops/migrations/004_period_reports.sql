-- Migration: 004_period_reports (2026-06-26)
-- Source: ADR-006 (Period Reports Schema Contract) + period-reports-sync plan T1
-- Ingests _templates_periodos/*.md as entity_type: period_report

CREATE TABLE IF NOT EXISTS period_reports (
    -- Identity
    id TEXT PRIMARY KEY,
    entity_type TEXT NOT NULL DEFAULT 'period_report',

    -- Period contract (ADR-006 §3)
    period TEXT NOT NULL
        CHECK (period IN ('daily','weekly','onda','quarterly','sonho')),
    date_start DATE NOT NULL,
    date_end DATE NOT NULL,

    -- Verdict contract (per-period enum)
    verdict TEXT NOT NULL,
    verdict_score REAL NOT NULL
        CHECK (verdict_score >= 0.0 AND verdict_score <= 1.0),

    -- Optional metadata (ADR-006 §3.2)
    template_version TEXT DEFAULT '1.0',
    ikigai_cluster TEXT DEFAULT 'plan',
    sonho_id TEXT,
    ikigai_vector TEXT
        CHECK (ikigai_vector IS NULL OR ikigai_vector IN ('passion','skill','market','revenue')),
    xp_gained INTEGER,
    mastery_delta TEXT,
    policy_recommendation TEXT
        CHECK (policy_recommendation IS NULL OR policy_recommendation IN ('push','maintain','reduce','recover')),
    parent_period TEXT,
    status TEXT NOT NULL DEFAULT 'active'
        CHECK (status IN ('draft','active','closed')),
    tags TEXT,

    -- Sync metadata
    vault_path TEXT NOT NULL,
    vault_hash TEXT NOT NULL,
    last_synced_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CHECK (date_end >= date_start),
    CHECK (
        (period = 'sonho' AND parent_period IS NULL)
        OR (period != 'sonho' AND parent_period IS NOT NULL)
        OR (period != 'sonho' AND parent_period IS NULL)
    ),
    CHECK (
        (verdict IN ('PASS','CONTINUE_WAVE','VALIDATED') AND verdict_score >= 0.5)
        OR (verdict IN ('PARTIAL','CORRECT_TRAJECTORY','PIVOTED') AND verdict_score >= 0.25)
        OR (verdict IN ('FAIL','KILL_WAVE','FALSIFIED','ABANDONED') AND verdict_score < 0.5)
        OR verdict IN ('ACTIVE', 'RECOVER')
    )
);

CREATE INDEX IF NOT EXISTS idx_period_reports_period
    ON period_reports(period, date_start DESC);

CREATE INDEX IF NOT EXISTS idx_period_reports_sonho
    ON period_reports(sonho_id)
    WHERE sonho_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_period_reports_parent
    ON period_reports(parent_period)
    WHERE parent_period IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_period_reports_verdict
    ON period_reports(period, verdict)
    WHERE verdict IN ('FAIL','KILL_WAVE','FALSIFIED','ABANDONED');

CREATE INDEX IF NOT EXISTS idx_period_reports_policy
    ON period_reports(policy_recommendation)
    WHERE policy_recommendation IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_period_reports_vault_hash
    ON period_reports(vault_hash);

CREATE INDEX IF NOT EXISTS idx_period_reports_updated
    ON period_reports(updated_at DESC);

CREATE TRIGGER IF NOT EXISTS trg_period_reports_updated
AFTER UPDATE ON period_reports
BEGIN
    UPDATE period_reports SET updated_at = CURRENT_TIMESTAMP WHERE id = OLD.id;
END;

CREATE VIEW IF NOT EXISTS v_period_hierarchy AS
WITH RECURSIVE hierarchy AS (
    SELECT id, period, date_start, date_end, parent_period, sonho_id,
           verdict, verdict_score, 0 AS depth, id AS root_id
    FROM period_reports WHERE parent_period IS NULL
    UNION ALL
    SELECT c.id, c.period, c.date_start, c.date_end, c.parent_period, c.sonho_id,
           c.verdict, c.verdict_score, h.depth + 1, h.root_id
    FROM period_reports c
    JOIN hierarchy h ON c.parent_period = h.id
)
SELECT * FROM hierarchy;

CREATE VIEW IF NOT EXISTS v_onda_aggregated AS
SELECT
    pr.id AS onda_id,
    pr.date_start AS onda_start,
    pr.date_end AS onda_end,
    pr.verdict AS onda_verdict,
    pr.verdict_score AS onda_score,
    pr.sonho_id,
    COUNT(c.id) AS children_count,
    ROUND(AVG(c.verdict_score), 3) AS avg_child_score,
    GROUP_CONCAT(c.verdict, ',') AS child_verdicts
FROM period_reports pr
LEFT JOIN period_reports c ON c.parent_period = pr.id AND c.period = 'weekly'
WHERE pr.period = 'onda'
GROUP BY pr.id;

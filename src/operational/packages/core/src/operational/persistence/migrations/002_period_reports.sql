-- Migration: 002_period_reports (2026-06-26)
-- Source: ADR-006 + period-reports-sync plan T9
-- Adds period_report entity type to operational's single-table JSON blob approach.
-- Uses CREATE INDEX IF NOT EXISTS for idempotency.

-- Index on entity_type + period + date_start for dashboard queries
CREATE INDEX IF NOT EXISTS idx_entities_period_report
    ON entities(entity_type, json_extract(data, '$.period'), json_extract(data, '$.date_start'))
    WHERE entity_type = 'period_report';

-- Index on sonho_id for hierarchical queries
CREATE INDEX IF NOT EXISTS idx_entities_period_report_sonho
    ON entities(json_extract(data, '$.sonho_id'))
    WHERE entity_type = 'period_report' AND json_extract(data, '$.sonho_id') IS NOT NULL;

-- Index on period + verdict for FAIL alerts (filtered)
CREATE INDEX IF NOT EXISTS idx_entities_period_report_verdict
    ON entities(json_extract(data, '$.period'), json_extract(data, '$.verdict'))
    WHERE entity_type = 'period_report'
    AND json_extract(data, '$.verdict') IN ('FAIL','KILL_WAVE','FALSIFIED','ABANDONED');

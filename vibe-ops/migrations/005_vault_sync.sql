-- Migration: 2026_06_22_vault_sync
-- Source: .omo/plans/vault-bidirectional-sync.md (T10)
-- Adds vault_sync_state cache + hypothesis_evaluations table.
-- Idempotent: every CREATE uses IF NOT EXISTS.

CREATE TABLE IF NOT EXISTS vault_sync_state (
    vault_path TEXT PRIMARY KEY,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    last_hash TEXT NOT NULL,
    last_synced_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_vault_sync_state_entity
    ON vault_sync_state(entity_type, entity_id);

CREATE TABLE IF NOT EXISTS falsifiable_hypotheses (
    id TEXT PRIMARY KEY,
    dream_id TEXT NOT NULL,
    hypothesis_text TEXT NOT NULL,
    evidence_threshold TEXT NOT NULL,
    measurement_window_days INTEGER NOT NULL DEFAULT 90,
    leading_indicators TEXT NOT NULL DEFAULT '[]',
    lagging_indicators TEXT NOT NULL DEFAULT '[]',
    refactor_triggers TEXT NOT NULL DEFAULT '[]',
    kill_switch_date TEXT,
    status TEXT NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'validated', 'falsified', 'pivoted', 'abandoned')),
    last_evaluated_at TEXT,
    created_at TEXT NOT NULL,
    vault_path TEXT,
    last_synced_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_falsifiable_hypotheses_dream
    ON falsifiable_hypotheses(dream_id);

CREATE INDEX IF NOT EXISTS idx_falsifiable_hypotheses_status
    ON falsifiable_hypotheses(status);

CREATE TABLE IF NOT EXISTS hypothesis_evaluations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hypothesis_id TEXT NOT NULL,
    evaluated_at TEXT NOT NULL,
    verdict TEXT NOT NULL
        CHECK (verdict IN ('validated', 'falsified', 'pivoted', 'no_change')),
    score REAL NOT NULL
        CHECK (score >= 0.0 AND score <= 1.0),
    notes TEXT DEFAULT '',
    leading_met INTEGER DEFAULT 0,
    lagging_met INTEGER DEFAULT 0,
    leading_total INTEGER DEFAULT 0,
    lagging_total INTEGER DEFAULT 0,
    FOREIGN KEY (hypothesis_id) REFERENCES falsifiable_hypotheses(id)
);

CREATE INDEX IF NOT EXISTS idx_hypothesis_evaluations_hyp
    ON hypothesis_evaluations(hypothesis_id, evaluated_at DESC);
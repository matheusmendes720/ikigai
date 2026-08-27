-- 001_initial.sql
-- Initial schema for the operational persistence layer.
--
-- Uses a single ``entities`` table with a JSON ``data`` column.
-- This is the optimal trade-off for a single-user local system:
--   * No per-entity DDL to maintain
--   * Full-text search potential on JSON content
--   * Single file for the whole database
--
-- Migration: 001 (2026-06-07)
-- Applied by: persistence/runner.py

CREATE TABLE IF NOT EXISTS entities (
    id          TEXT PRIMARY KEY,                          -- UEID
    entity_type TEXT NOT NULL,                             -- e.g. "routine", "habit"
    data        TEXT NOT NULL,                             -- JSON blob of entity fields
    created_at  TEXT NOT NULL,                             -- ISO-8601 UTC
    updated_at  TEXT NOT NULL                              -- ISO-8601 UTC
);

CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(entity_type);
CREATE INDEX IF NOT EXISTS idx_entities_created ON entities(created_at);

-- ---------------------------------------------------------------------------
-- Migration metadata table
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS _migrations (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL UNIQUE,                   -- e.g. "001_initial"
    applied_at  TEXT    NOT NULL,                          -- ISO-8601 UTC
    checksum    TEXT,                                      -- optional SHA-256
    success     INTEGER NOT NULL DEFAULT 1                 -- 1 = OK, 0 = failed
);

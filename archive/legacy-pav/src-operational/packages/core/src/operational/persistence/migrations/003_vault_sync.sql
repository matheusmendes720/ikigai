-- Mirror migration: 2026_06_22_vault_sync
-- Source: .omo/plans/vault-bidirectional-sync.md (T10)
-- Idempotent. Mirrors vibe-ops migration 005_vault_sync.

CREATE TABLE IF NOT EXISTS vault_sync_state (
    vault_path TEXT PRIMARY KEY,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    last_hash TEXT NOT NULL,
    last_synced_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_vault_sync_state_entity
    ON vault_sync_state(entity_type, entity_id);
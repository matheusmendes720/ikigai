-- Tabela: roadmap_sync (espelho enriquecido do sync bidirecional)
CREATE TABLE IF NOT EXISTS roadmap_sync (
    task_uuid TEXT PRIMARY KEY,
    description TEXT NOT NULL,
    project_key TEXT NOT NULL,
    status TEXT CHECK(status IN ('pending','waiting','completed','deleted')),
    
    -- JSONB para pré-requisitos (SQLite 3.38+ suporta json_each)
    knowledge_prerequisites JSON DEFAULT '[]',
    cognitive_debt JSON,
    
    -- Métricas
    time_tracked_minutes INTEGER DEFAULT 0,
    pomodoros_completed INTEGER DEFAULT 0,
    energy_avg REAL CHECK(energy_avg BETWEEN 0 AND 10),
    
    -- Controle
    contract_version TEXT DEFAULT '1.0.0',
    upstream_id TEXT NOT NULL,
    synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Índices para queries de débito cognitivo e bloqueios
CREATE INDEX IF NOT EXISTS idx_roadmap_sync_by_debt_level 
    ON roadmap_sync(json_extract(cognitive_debt, '$.level'))
    WHERE json_extract(cognitive_debt, '$.level') IN ('high','critical');

CREATE INDEX IF NOT EXISTS idx_roadmap_sync_by_project 
    ON roadmap_sync(project_key, status);

-- Trigger para manter updated_at
CREATE TRIGGER IF NOT EXISTS trg_roadmap_sync_updated 
AFTER UPDATE ON roadmap_sync
BEGIN
    UPDATE roadmap_sync SET updated_at = CURRENT_TIMESTAMP WHERE task_uuid = OLD.task_uuid;
END;

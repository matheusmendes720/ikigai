-- migrations/001_create_dev_cluster_tables.sql
-- Executar com Alembic ou sqlite3 direto

-- =====================================================
-- TABELA: roadmaps (fora do Obsidian - SQLite)
-- =====================================================
CREATE TABLE IF NOT EXISTS roadmaps (
    roadmap_id TEXT PRIMARY KEY CHECK(roadmap_id ~ '^rm_[a-z0-9_]+$'),
    title TEXT NOT NULL CHECK(length(title) >= 5),
    
    -- FK para StudyProject (ponte entre clusters)
    study_project_fk TEXT NOT NULL,
    
    -- Hierarquia estratégica (denormalizada para query rápida)
    parent_dream TEXT CHECK(parent_dream ~ '^S\d+$'),
    parent_objective TEXT NOT NULL CHECK(parent_objective ~ '^O\d+$'),
    parent_meta TEXT CHECK(parent_meta ~ '^M\d+$'),
    
    -- Métricas de progresso
    total_story_points INTEGER DEFAULT 0 CHECK(total_story_points >= 0),
    completed_story_points INTEGER DEFAULT 0 CHECK(completed_story_points >= 0),
    velocity_avg REAL CHECK(velocity_avg >= 0),  -- pontos/sprint
    
    -- Controle temporal
    status TEXT DEFAULT 'active' CHECK(status IN ('active', 'paused', 'completed', 'archived')),
    started DATE,
    expected_end DATE,
    completed DATE,
    
    -- Metadados do sistema
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    version INTEGER DEFAULT 1,
    
    -- Constraints de integridade
    CHECK(completed_story_points <= total_story_points),
    CHECK(expected_end IS NULL OR started IS NULL OR expected_end >= started)
);

-- Índices para queries frequentes
CREATE INDEX idx_roadmaps_by_objective ON roadmaps(parent_objective, status);
CREATE INDEX idx_roadmaps_by_study_project ON roadmaps(study_project_fk);
CREATE INDEX idx_roadmaps_active ON roadmaps(status) WHERE status = 'active';

-- =====================================================
-- TABELA: features (desagregação do roadmap)
-- =====================================================
CREATE TABLE IF NOT EXISTS features (
    feat_id TEXT PRIMARY KEY CHECK(feat_id ~ '^feat_[a-z0-9_]+$'),
    roadmap_fk TEXT NOT NULL REFERENCES roadmaps(roadmap_id) ON DELETE CASCADE,
    
    title TEXT NOT NULL,
    description TEXT,
    
    -- Estimativas
    story_points INTEGER CHECK(story_points >= 0),
    effort_hours_estimated REAL CHECK(effort_hours_estimated >= 0),
    
    -- Status e fluxo
    status TEXT DEFAULT 'backlog' CHECK(status IN ('backlog', 'ready', 'in_progress', 'review', 'done')),
    priority TEXT DEFAULT 'medium' CHECK(priority IN ('critical', 'high', 'medium', 'low')),
    
    -- Conexão com conhecimento
    study_topics_required JSONB DEFAULT '[]',  -- Array de study_topic_fk
    prerequisite_tasks JSONB DEFAULT '[]',     -- Array de task_uuids do TW
    
    -- Métricas
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Unique: uma feature por roadmap com este ID
    UNIQUE(roadmap_fk, feat_id)
);

CREATE INDEX idx_features_by_roadmap ON features(roadmap_fk, status);
CREATE INDEX idx_features_blocked ON features(status) 
    WHERE status IN ('backlog', 'ready') AND jsonb_array_length(study_topics_required) > 0;

-- =====================================================
-- TABELA: backlog_tasks (espelho enriquecido do Taskwarrior)
-- =====================================================
CREATE TABLE IF NOT EXISTS backlog_tasks (
    -- Chave primária: UUID do Taskwarrior (fonte da verdade)
    task_uuid TEXT PRIMARY KEY,
    
    -- Metadados do TW (espelhados)
    description TEXT NOT NULL,
    project_key TEXT NOT NULL,  -- Ex: "S1.O2.M3.Backlog"
    status TEXT CHECK(status IN ('pending', 'waiting', 'completed', 'deleted')),
    priority TEXT CHECK(priority IN ('H', 'M', 'L', NULL)),
    due_date DATE,
    entered TIMESTAMP,
    modified TIMESTAMP,
    end_date TIMESTAMP,  -- Quando foi concluída
    
    -- Conexão com features/roadmaps
    feature_fk TEXT REFERENCES features(feat_id) ON DELETE SET NULL,
    roadmap_fk TEXT REFERENCES roadmaps(roadmap_id) ON DELETE SET NULL,
    
    -- Conexão com estudo (chaves estrangeiras cruzadas)
    knowledge_prerequisites JSONB DEFAULT '[]',  -- Array de objetos: {study_topic_fk, depth_required, depth_current, status}
    
    -- Métricas de execução (preenchidas pelo pipeline de sync)
    time_tracked_minutes INTEGER DEFAULT 0 CHECK(time_tracked_minutes >= 0),
    pomodoros_completed INTEGER DEFAULT 0,
    context_switches INTEGER DEFAULT 0,
    energy_avg REAL CHECK(energy_avg BETWEEN 0 AND 10),
    
    -- Débito cognitivo (calculado)
    cognitive_debt_level TEXT CHECK(cognitive_debt_level IN ('none', 'low', 'medium', 'high', 'critical')),
    cognitive_debt_interest REAL DEFAULT 0 CHECK(cognitive_debt_interest BETWEEN 0 AND 1),
    
    -- Controle do pipeline
    last_synced_at TIMESTAMP,
    sync_hash TEXT,  -- SHA-256 do payload do TW para detectar mudanças
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Índices críticos para o ciclo de feedback
CREATE INDEX idx_tasks_by_feature ON backlog_tasks(feature_fk, status);
CREATE INDEX idx_tasks_by_knowledge_gap ON backlog_tasks 
    WHERE jsonb_exists_any(knowledge_prerequisites, ARRAY['{"status":"deficit"}'::jsonb]);
CREATE INDEX idx_tasks_cognitive_debt ON backlog_tasks(cognitive_debt_level) 
    WHERE cognitive_debt_level IN ('high', 'critical');
CREATE INDEX idx_tasks_project_key ON backlog_tasks(project_key);

-- =====================================================
-- TABELA: changelogs (resultados de commits + testes + aprendizado)
-- =====================================================
CREATE TABLE IF NOT EXISTS changelogs (
    changelog_id TEXT PRIMARY KEY CHECK(changelog_id ~ '^cl_[0-9]{8}_[0-9]{4}$'),  -- Ex: cl_20260710_0001
    
    -- FK para task (fonte do evento)
    task_uuid_fk TEXT NOT NULL REFERENCES backlog_tasks(task_uuid) ON DELETE CASCADE,
    
    -- Metadados do commit
    commit_hash TEXT,
    commit_message TEXT,
    commit_author TEXT,
    commit_timestamp TIMESTAMP,
    files_changed INTEGER DEFAULT 0,
    lines_added INTEGER DEFAULT 0,
    lines_deleted INTEGER DEFAULT 0,
    
    -- Métricas de qualidade de código
    complexity_score REAL,  -- ciclomática média
    code_smells_count INTEGER DEFAULT 0,
    security_vulnerabilities INTEGER DEFAULT 0,
    technical_debt_minutes INTEGER DEFAULT 0,
    
    -- Resultados de testes
    tests_total INTEGER DEFAULT 0,
    tests_passed INTEGER DEFAULT 0,
    tests_failed INTEGER DEFAULT 0,
    coverage_pct REAL CHECK(coverage_pct BETWEEN 0 AND 100),
    test_execution_time_seconds REAL,
    
    -- Impacto no aprendizado (array de tópicos que evoluíram)
    learning_outcomes JSONB DEFAULT '[]',  -- [{study_topic_fk, depth_before, depth_after, evidence}]
    
    -- Feedback do LLM (code review automatizado)
    llm_review_score REAL CHECK(llm_review_score BETWEEN 0 AND 10),
    llm_suggestions JSONB DEFAULT '[]',
    llm_best_practices JSONB DEFAULT '[]',
    
    -- Telemetria de produtividade
    pomodoros_used INTEGER DEFAULT 0,
    focus_score REAL CHECK(focus_score BETWEEN 0 AND 1),
    energy_consumed REAL CHECK(energy_consumed BETWEEN 0 AND 1),
    efficiency_ratio REAL,  -- output/energy
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Índices para analytics e feedback loop
CREATE INDEX idx_changelogs_by_task ON changelogs(task_uuid_fk);
CREATE INDEX idx_changelogs_by_date ON changelogs(commit_timestamp DESC);
CREATE INDEX idx_changelogs_learning ON changelogs 
    WHERE jsonb_array_length(learning_outcomes) > 0;
CREATE INDEX idx_changelogs_quality ON changelogs(coverage_pct, llm_review_score) 
    WHERE tests_total > 0;

-- =====================================================
-- VIEW: dashboard_unificado (consulta cruzada clusters)
-- =====================================================
CREATE VIEW IF NOT EXISTS v_dashboard_study_dev AS
SELECT 
    sp.study_project_fk,
    sp.title AS project_title,
    r.roadmap_id,
    r.title AS roadmap_title,
    
    -- Progresso do roadmap
    ROUND(100.0 * r.completed_story_points / NULLIF(r.total_story_points, 1), 1) AS roadmap_progress_pct,
    
    -- Tasks bloqueadas por conhecimento
    COUNT(DISTINCT CASE 
        WHEN bt.status = 'pending' 
             AND EXISTS (
                 SELECT 1 FROM jsonb_array_elements(bt.knowledge_prerequisites) AS kp
                 WHERE kp->>'status' = 'deficit'
             )
        THEN bt.task_uuid 
    END) AS tasks_blocked_by_knowledge,
    
    -- Débito cognitivo crítico
    COUNT(DISTINCT CASE 
        WHEN bt.cognitive_debt_level IN ('high', 'critical') 
        THEN bt.task_uuid 
    END) AS tasks_with_critical_debt,
    
    -- Aprendizado recente (últimos 7 dias)
    COUNT(DISTINCT CASE 
        WHEN cl.created_at >= date('now', '-7 days')
             AND jsonb_array_length(cl.learning_outcomes) > 0
        THEN cl.task_uuid_fk 
    END) AS learning_events_7d,
    
    -- Qualidade média de código
    ROUND(AVG(cl.coverage_pct), 1) AS avg_coverage,
    ROUND(AVG(cl.llm_review_score), 1) AS avg_llm_score
    
FROM roadmaps r
JOIN study_projects sp ON sp.id = r.study_project_fk  -- Assumindo tabela study_projects existente
LEFT JOIN features f ON f.roadmap_fk = r.roadmap_id
LEFT JOIN backlog_tasks bt ON bt.feature_fk = f.feat_id OR bt.roadmap_fk = r.roadmap_id
LEFT JOIN changelogs cl ON cl.task_uuid_fk = bt.task_uuid
WHERE r.status = 'active'
GROUP BY sp.study_project_fk, sp.title, r.roadmap_id, r.title, 
         r.completed_story_points, r.total_story_points;

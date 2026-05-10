-- Schema for Vibe-Ops Data Mesh

-- TEMPORAL CLUSTER
CREATE TABLE IF NOT EXISTS temporal_waves (
    id TEXT PRIMARY KEY,
    title TEXT,
    entity_type TEXT DEFAULT 'wave',
    status TEXT,
    start_date DATE,
    expected_end DATE,
    wave_number INTEGER,
    parent_cycle TEXT,
    parent_objective TEXT,
    c_comp REAL,
    ic REAL,
    tags TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS temporal_cycles (
    id TEXT PRIMARY KEY,
    title TEXT,
    entity_type TEXT DEFAULT 'cycle',
    status TEXT,
    start_date DATE,
    expected_end DATE,
    cycle_number INTEGER,
    parent_phase TEXT,
    parent_objective TEXT,
    aligned_half_quarter TEXT,
    tags TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS temporal_phases (
    id TEXT PRIMARY KEY,
    title TEXT,
    entity_type TEXT DEFAULT 'phase',
    status TEXT,
    start_date DATE,
    expected_end DATE,
    phase_number INTEGER,
    parent_dream TEXT,
    aligned_quarter_start TEXT,
    aligned_quarter_end TEXT,
    tags TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- STUDY CLUSTER
CREATE TABLE IF NOT EXISTS study_plans (
    id TEXT PRIMARY KEY,
    title TEXT,
    entity_type TEXT DEFAULT 'study_plan',
    status TEXT,
    parent_dream TEXT,
    parent_objective TEXT,
    anchor_wave TEXT,
    anchor_cycle TEXT,
    study_cadence TEXT,
    work_ratio REAL,
    daily_target_minutes INTEGER,
    target_clr REAL,
    tags TEXT,
    created_at DATE
);

CREATE TABLE IF NOT EXISTS study_topics (
    id TEXT PRIMARY KEY,
    name TEXT,
    entity_type TEXT DEFAULT 'study_topic',
    category TEXT,
    difficulty TEXT,
    depth_level REAL DEFAULT 0.0,
    cognitive_debt REAL DEFAULT 0.0,
    transferability TEXT,
    priority TEXT,
    status TEXT,
    parent_skill TEXT,
    estimated_hours REAL,
    completed_hours REAL,
    created_at DATE
);

CREATE TABLE IF NOT EXISTS study_notes (
    id TEXT PRIMARY KEY,
    obsidian_path TEXT,
    proj_id TEXT,
    task_id TEXT,
    topic_id TEXT,
    abstraction_level TEXT,
    tags TEXT,
    last_refined TIMESTAMP
);

-- DEVELOPMENT CLUSTER
CREATE TABLE IF NOT EXISTS dev_projects (
    id TEXT PRIMARY KEY,
    goal_id TEXT,
    obj_weekly TEXT,
    title TEXT,
    project_type TEXT,
    status TEXT,
    parent_meta TEXT,
    parent_objective TEXT,
    parent_dream TEXT,
    wave_id TEXT,
    storypoints_total INTEGER DEFAULT 0,
    revenue_impact TEXT,
    due_date DATE,
    note_idx TEXT,
    tags TEXT,
    created_at DATE
);

CREATE TABLE IF NOT EXISTS dev_roadmaps (
    id TEXT PRIMARY KEY,
    goal_id TEXT,
    title TEXT,
    storypoints INTEGER,
    status TEXT,
    features TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS dev_backlogs (
    id TEXT PRIMARY KEY,
    roadmap_item_id TEXT,
    description TEXT,
    commits TEXT,
    code_reviews TEXT,
    transferability TEXT,
    status TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS dev_changelogs (
    id TEXT PRIMARY KEY,
    backlog_task_id TEXT,
    test_results TEXT,
    telemetry_summary TEXT,
    stack_trace TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- HABIT CLUSTER
CREATE TABLE IF NOT EXISTS habits (
    id TEXT PRIMARY KEY,
    name TEXT,
    category TEXT,
    resistance REAL,
    lambda_learning REAL,
    weight_in_qhe REAL,
    status TEXT,
    created_at DATE
);

CREATE TABLE IF NOT EXISTS habit_states (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    habit_id TEXT,
    date DATE,
    streak_current INTEGER,
    streak_broken BOOLEAN,
    habit_level REAL,
    energy_required REAL,
    executed BOOLEAN,
    FOREIGN KEY(habit_id) REFERENCES habits(id)
);

CREATE TABLE IF NOT EXISTS mesh_metadata_catalog (
    node_id TEXT PRIMARY KEY,
    domain TEXT,
    source_path TEXT,
    contract_id TEXT,
    contract_version TEXT,
    physical_table TEXT,
    vector_collection TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS mesh_state_machine (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    node_id TEXT,
    current_state TEXT,
    last_event TEXT,
    event_payload TEXT,
    transitioned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(node_id) REFERENCES mesh_metadata_catalog(node_id)
);

-- ADDITIONS FOR MVL COMPLETION

CREATE TABLE IF NOT EXISTS policy_decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE,
    policy TEXT,
    qhe REAL,
    c_comp REAL,
    infrações_24h INTEGER,
    tipo_dia TEXT,
    hardwork_budget_hours REAL,
    pause_duration_minutes INTEGER,
    sleep_target_hours REAL,
    recomendacoes TEXT,
    alertas TEXT,
    days_in_current_policy INTEGER,
    policy_prev TEXT,
    computed_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS study_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE,
    duration_minutes INTEGER,
    topic_id TEXT
);

CREATE TABLE IF NOT EXISTS planning_entities (
    id TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    payload_json TEXT,
    upstream_id TEXT,
    synced_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id, entity_type)
);

CREATE TABLE IF NOT EXISTS roadmap_sync (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    study_plan_fk TEXT,
    status TEXT,
    tw_uuid TEXT,
    last_synced TIMESTAMP
);

CREATE VIEW IF NOT EXISTS v_epistemic_priority AS
SELECT 
    id as study_topic_fk,
    name as title,
    (cognitive_debt + depth_level) as epistemic_score,
    ROW_NUMBER() OVER(ORDER BY (cognitive_debt + depth_level) DESC) as priority_rank
FROM study_topics
WHERE status != 'completed';

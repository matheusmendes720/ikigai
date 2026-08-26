-- BYD + Salvador outreach tracker — D4 schema (sqlite3 stdlib)
-- Author: Matheus Mendes | 2026-07-09

PRAGMA foreign_keys = ON;

-- ============================================================
-- Outreach events: every cold message sent
-- ============================================================
CREATE TABLE IF NOT EXISTS outreach (
    outreach_id     TEXT PRIMARY KEY,        -- ueid: ikigai:outreach:<uuid8>:<hash8>
    sent_at         TEXT NOT NULL,           -- ISO 8601 datetime
    company         TEXT NOT NULL,           -- 'BYD', 'FullStack', 'BairesDev', etc.
    vaga            TEXT NOT NULL,           -- job title slug
    channel         TEXT NOT NULL CHECK (channel IN ('linkedin_connect','linkedin_message','email','easy_apply')),
    manager_name    TEXT,                    -- 'Yueying Zhang' or NULL for easy_apply
    manager_ueid    TEXT,                    -- optional cross-link to hiring-managers.md
    persona_used    TEXT NOT NULL CHECK (persona_used IN ('T0_lean','T1_polite','T2_followup','T3_email')),
    template_id     TEXT,                    -- template slug
    message_body    TEXT NOT NULL,           -- full text sent
    response_at     TEXT,                    -- nullable
    response_type   TEXT,                    -- 'accept', 'reply', 'reject', 'no_response'
    sentiment       TEXT,                    -- 'positive', 'neutral', 'negative'
    notes           TEXT,
    created_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_outreach_company ON outreach(company);
CREATE INDEX IF NOT EXISTS idx_outreach_channel ON outreach(channel);
CREATE INDEX IF NOT EXISTS idx_outreach_sent_at ON outreach(sent_at);

-- ============================================================
-- Process events: full hiring pipeline tracking per vaga
-- ============================================================
CREATE TABLE IF NOT EXISTS process (
    process_id      TEXT PRIMARY KEY,        -- ueid
    company         TEXT NOT NULL,
    vaga            TEXT NOT NULL,
    stage           TEXT NOT NULL CHECK (stage IN (
                        'discovered','applied','screening','interview_phone',
                        'interview_tech','interview_onsite','offer','rejected','ghosted'
                    )),
    stage_entered_at TEXT NOT NULL,
    next_action     TEXT,
    next_action_at  TEXT,
    contact_email   TEXT,
    contact_linkedin TEXT,
    salary_brl      INTEGER,                 -- nullable until offer stage
    notes           TEXT,
    created_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (company, vaga)
);

CREATE INDEX IF NOT EXISTS idx_process_stage ON process(stage);
CREATE INDEX IF NOT EXISTS idx_process_company ON process(company);

-- ============================================================
-- Response events: replies received (linked to outreach)
-- ============================================================
CREATE TABLE IF NOT EXISTS response (
    response_id     TEXT PRIMARY KEY,
    outreach_id     TEXT NOT NULL,
    received_at     TEXT NOT NULL,
    response_type   TEXT NOT NULL CHECK (response_type IN (
                        'accept','reply','reject','ask_more_info','auto_reply'
                    )),
    sentiment       TEXT CHECK (sentiment IN ('positive','neutral','negative')),
    body            TEXT,
    next_step       TEXT,                    -- 'phone_screen_2026-07-15', 'send_portfolio', 'wait'
    created_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (outreach_id) REFERENCES outreach(outreach_id)
);

CREATE INDEX IF NOT EXISTS idx_response_outreach ON response(outreach_id);

-- ============================================================
-- Decision log: macro-level decisions (mirror to options-exploration-log.md)
-- ============================================================
CREATE TABLE IF NOT EXISTS decision_log (
    decision_id     TEXT PRIMARY KEY,        -- 'DEC-2026-07-09-12'
    decided_at      TEXT NOT NULL,
    question        TEXT NOT NULL,
    options_json    TEXT NOT NULL,           -- JSON array
    chosen_option   TEXT NOT NULL,
    rationale       TEXT NOT NULL,
    revisit_trigger TEXT,
    created_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- Weekly dashboard (auto-generated view)
-- ============================================================
CREATE VIEW IF NOT EXISTS v_weekly_summary AS
SELECT
    strftime('%Y-W%W', sent_at) AS week,
    company,
    channel,
    COUNT(*) AS outreach_count,
    SUM(CASE WHEN response_at IS NOT NULL THEN 1 ELSE 0 END) AS response_count,
    ROUND(100.0 * SUM(CASE WHEN response_at IS NOT NULL THEN 1 ELSE 0 END) / COUNT(*), 1) AS response_rate_pct
FROM outreach
GROUP BY week, company, channel
ORDER BY week DESC, company;

-- ============================================================
-- Final wave report: at end of W4, generate TL;DR
-- ============================================================
CREATE VIEW IF NOT EXISTS v_wave_final AS
SELECT
    company,
    COUNT(*) AS total_outreach,
    SUM(CASE WHEN response_at IS NOT NULL THEN 1 ELSE 0 END) AS total_responses,
    SUM(CASE WHEN response_type = 'accept' THEN 1 ELSE 0 END) AS accepts,
    SUM(CASE WHEN response_type = 'reply' THEN 1 ELSE 0 END) AS replies,
    SUM(CASE WHEN response_type = 'reject' THEN 1 ELSE 0 END) AS rejects,
    SUM(CASE WHEN response_type = 'no_response' OR response_at IS NULL THEN 1 ELSE 0 END) AS no_response,
    ROUND(100.0 * SUM(CASE WHEN response_at IS NOT NULL THEN 1 ELSE 0 END) / COUNT(*), 1) AS response_rate_pct
FROM outreach
GROUP BY company
ORDER BY total_outreach DESC;
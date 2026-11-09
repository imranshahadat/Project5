-- Reference DDL. scripts/init_db.py creates the schema from the SQLAlchemy
-- models; keep this file in sync. Alternative bootstrap:
--   psql "$DATABASE_URL" -f db/reference_schema.sql
CREATE TABLE IF NOT EXISTS documents (
    id VARCHAR(36) PRIMARY KEY,
    title VARCHAR(512) NOT NULL,
    content TEXT NOT NULL,
    source VARCHAR(512),
    status VARCHAR(20) NOT NULL DEFAULT 'pending' CONSTRAINT ck_documents_status CHECK (
        status IN ('pending', 'processing', 'ready', 'failed')
    ),
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_documents_status_created ON documents (status, created_at);

CREATE TABLE IF NOT EXISTS chat_history (
    id VARCHAR(36) PRIMARY KEY,
    thread_id VARCHAR(64) NOT NULL,
    role VARCHAR(16) NOT NULL CONSTRAINT ck_chat_history_role CHECK (
        role IN ('system', 'user', 'assistant', 'tool')
    ),
    content TEXT NOT NULL,
    doc_ids JSONB,
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_chat_history_thread_created ON chat_history (thread_id, created_at);

CREATE TABLE IF NOT EXISTS approvals (
    id VARCHAR(36) PRIMARY KEY,
    thread_id VARCHAR(64) NOT NULL,
    request_type VARCHAR(64) NOT NULL,
    payload JSONB NOT NULL,
    status VARCHAR(16) NOT NULL DEFAULT 'pending' CONSTRAINT ck_approvals_status CHECK (
        status IN ('pending', 'approved', 'rejected', 'expired')
    ),
    requested_by VARCHAR(128),
    decided_by VARCHAR(128),
    decision_note TEXT,
    requested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    decided_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS ix_approvals_thread_id ON approvals (thread_id);
CREATE INDEX IF NOT EXISTS ix_approvals_status_requested ON approvals (status, requested_at);

CREATE TABLE IF NOT EXISTS feedback (
    id VARCHAR(36) PRIMARY KEY,
    thread_id VARCHAR(64) NOT NULL,
    message_id VARCHAR(36) REFERENCES chat_history (id) ON DELETE SET NULL,
    rating SMALLINT CONSTRAINT ck_feedback_rating CHECK (
        rating IS NULL OR rating BETWEEN 1 AND 5
    ),
    is_helpful BOOLEAN,
    category VARCHAR(64),
    comment TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_feedback_thread_id ON feedback (thread_id);

CREATE TABLE IF NOT EXISTS audit_events (
    id VARCHAR(36) PRIMARY KEY,
    actor VARCHAR(128) NOT NULL DEFAULT 'system',
    actor_type VARCHAR(16) NOT NULL DEFAULT 'system' CONSTRAINT ck_audit_actor_type CHECK (
        actor_type IN ('user', 'agent', 'system')
    ),
    action VARCHAR(128) NOT NULL,
    entity_type VARCHAR(64),
    entity_id VARCHAR(36),
    detail JSONB,
    ip_address VARCHAR(45),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_audit_action_created ON audit_events (action, created_at);
CREATE INDEX IF NOT EXISTS ix_audit_entity ON audit_events (entity_type, entity_id);

CREATE TABLE IF NOT EXISTS guardrail_logs (
    id VARCHAR(36) PRIMARY KEY,
    thread_id VARCHAR(64),
    stage VARCHAR(16) NOT NULL CONSTRAINT ck_guardrail_stage CHECK (
        stage IN ('input', 'output')
    ),
    guardrail VARCHAR(64) NOT NULL,
    outcome VARCHAR(16) NOT NULL CONSTRAINT ck_guardrail_outcome CHECK (
        outcome IN ('blocked', 'flagged', 'redacted', 'allowed')
    ),
    reason TEXT,
    snippet TEXT,
    scores JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_guardrail_thread_id ON guardrail_logs (thread_id);
CREATE INDEX IF NOT EXISTS ix_guardrail_outcome_created ON guardrail_logs (outcome, created_at);
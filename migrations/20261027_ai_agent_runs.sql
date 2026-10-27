CREATE TABLE IF NOT EXISTS brady.ai_agent_runs (
    id BIGSERIAL PRIMARY KEY,
    trace_id UUID NOT NULL UNIQUE,
    actor_role VARCHAR(40) NOT NULL,
    actor_id VARCHAR(80) NOT NULL,
    status VARCHAR(30) NOT NULL,
    agents_consulted JSONB NOT NULL DEFAULT '[]'::jsonb,
    sources JSONB NOT NULL DEFAULT '[]'::jsonb,
    error_code VARCHAR(80),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_ai_agent_runs_actor_created
ON brady.ai_agent_runs(actor_role, actor_id, created_at DESC);

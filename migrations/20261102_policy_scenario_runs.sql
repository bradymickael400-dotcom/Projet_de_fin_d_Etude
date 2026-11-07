CREATE TABLE IF NOT EXISTS brady.policy_scenario_runs (
    id BIGSERIAL PRIMARY KEY,
    trace_id UUID NOT NULL UNIQUE,
    scenario_id VARCHAR(100) NOT NULL,
    actor_role VARCHAR(40) NOT NULL,
    actor_id VARCHAR(80) NOT NULL,
    synthetic BOOLEAN NOT NULL DEFAULT TRUE CHECK (synthetic = TRUE),
    result JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_policy_scenario_runs_actor_created
ON brady.policy_scenario_runs(actor_role, actor_id, created_at DESC);

CREATE TABLE IF NOT EXISTS brady.argos_planned_routes (
    black_box_id BIGINT PRIMARY KEY,
    route_name TEXT NOT NULL,
    mode VARCHAR(20) NOT NULL CHECK (mode IN ('road','sea','multimodal')),
    waypoints JSONB NOT NULL,
    corridor_width_m INTEGER NOT NULL DEFAULT 1000 CHECK (corridor_width_m BETWEEN 50 AND 50000),
    alert_threshold INTEGER NOT NULL DEFAULT 60 CHECK (alert_threshold BETWEEN 1 AND 100),
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    updated_by_role TEXT NOT NULL,
    updated_by_id TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (jsonb_typeof(waypoints)='array' AND jsonb_array_length(waypoints)>=2)
);
CREATE INDEX IF NOT EXISTS idx_argos_planned_routes_enabled
    ON brady.argos_planned_routes(enabled) WHERE enabled=TRUE;

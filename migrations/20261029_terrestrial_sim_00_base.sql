CREATE TABLE IF NOT EXISTS brady.argos_transport_sim_sessions (
    session_uid UUID PRIMARY KEY,
    mode VARCHAR(20) NOT NULL DEFAULT 'SIMULATION' CHECK (mode='SIMULATION'),
    status VARCHAR(20) NOT NULL DEFAULT 'RUNNING'
        CHECK (status IN ('RUNNING','PAUSED','STOPPING','STOPPED','COMPLETED','FAILED')),
    requested_by_role VARCHAR(40) NOT NULL,
    requested_by_id VARCHAR(100),
    interval_seconds INTEGER NOT NULL DEFAULT 60 CHECK (interval_seconds BETWEEN 10 AND 600),
    duration_seconds INTEGER NOT NULL DEFAULT 3600 CHECK (duration_seconds BETWEEN 60 AND 3600),
    time_scale INTEGER NOT NULL DEFAULT 5 CHECK (time_scale BETWEEN 1 AND 20),
    active_elapsed_seconds DOUBLE PRECISION NOT NULL DEFAULT 0 CHECK (active_elapsed_seconds >= 0),
    last_active_at TIMESTAMPTZ,
    worker_heartbeat_at TIMESTAMPTZ,
    last_tick_at TIMESTAMPTZ,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    stopped_at TIMESTAMPTZ,
    last_error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_argos_transport_sim_active
    ON brady.argos_transport_sim_sessions(status, created_at DESC);

CREATE TABLE IF NOT EXISTS brady.argos_transport_sim_scenarios (
    session_uid UUID NOT NULL REFERENCES brady.argos_transport_sim_sessions(session_uid) ON DELETE CASCADE,
    scenario_code VARCHAR(40) NOT NULL CHECK (scenario_code IN ('douala_ndjamena','kribi_bertoua')),
    black_box_id BIGINT NOT NULL,
    container_id VARCHAR(80),
    box_serial VARCHAR(80),
    route_name TEXT NOT NULL,
    origin TEXT NOT NULL,
    destination TEXT NOT NULL,
    route_geometry JSONB NOT NULL,
    origin_geocode JSONB NOT NULL DEFAULT '{}'::jsonb,
    destination_geocode JSONB NOT NULL DEFAULT '{}'::jsonb,
    route_distance_m DOUBLE PRECISION NOT NULL CHECK (route_distance_m > 0),
    route_duration_s DOUBLE PRECISION NOT NULL CHECK (route_duration_s > 0),
    route_source TEXT NOT NULL,
    route_retrieved_at TIMESTAMPTZ NOT NULL,
    route_version TEXT,
    route_steps JSONB NOT NULL DEFAULT '[]'::jsonb,
    route_limitations JSONB NOT NULL DEFAULT '[]'::jsonb,
    scenario_config JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (session_uid, scenario_code),
    UNIQUE (session_uid, black_box_id),
    CHECK (jsonb_typeof(route_geometry)='object'),
    CHECK (jsonb_typeof(origin_geocode)='object' AND jsonb_typeof(destination_geocode)='object'),
    CHECK (jsonb_typeof(route_steps)='array')
);
CREATE INDEX IF NOT EXISTS idx_argos_transport_sim_scenario_box
    ON brady.argos_transport_sim_scenarios(black_box_id, created_at DESC);

CREATE TABLE IF NOT EXISTS brady.argos_transport_sim_samples (
    id BIGSERIAL PRIMARY KEY,
    session_uid UUID NOT NULL,
    scenario_code VARCHAR(40) NOT NULL,
    sequence BIGINT NOT NULL CHECK (sequence >= 0),
    measured_at TIMESTAMPTZ NOT NULL,
    simulated_at TIMESTAMPTZ NOT NULL,
    simulated_elapsed_seconds DOUBLE PRECISION NOT NULL CHECK (simulated_elapsed_seconds >= 0),
    latitude DOUBLE PRECISION NOT NULL CHECK (latitude BETWEEN -90 AND 90),
    longitude DOUBLE PRECISION NOT NULL CHECK (longitude BETWEEN -180 AND 180),
    speed_kmh DOUBLE PRECISION NOT NULL CHECK (speed_kmh >= 0),
    heading DOUBLE PRECISION NOT NULL CHECK (heading BETWEEN 0 AND 360),
    remaining_distance_m DOUBLE PRECISION NOT NULL CHECK (remaining_distance_m >= 0),
    stopped_seconds DOUBLE PRECISION NOT NULL DEFAULT 0 CHECK (stopped_seconds >= 0),
    vehicle_state VARCHAR(30) NOT NULL,
    eta_reference_at TIMESTAMPTZ NOT NULL,
    eta_current_at TIMESTAMPTZ NOT NULL,
    eta_delay_seconds DOUBLE PRECISION NOT NULL DEFAULT 0,
    sensor_values JSONB NOT NULL DEFAULT '{}'::jsonb,
    active_events JSONB NOT NULL DEFAULT '[]'::jsonb,
    rule_assessments JSONB NOT NULL DEFAULT '{}'::jsonb,
    provenance JSONB NOT NULL DEFAULT '{"dataOrigin":"SYNTHETIC"}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (session_uid, scenario_code, sequence),
    FOREIGN KEY (session_uid, scenario_code)
        REFERENCES brady.argos_transport_sim_scenarios(session_uid, scenario_code) ON DELETE CASCADE,
    CHECK (jsonb_typeof(sensor_values)='object'),
    CHECK (jsonb_typeof(active_events)='array'),
    CHECK (jsonb_typeof(provenance)='object' AND provenance->>'dataOrigin'='SYNTHETIC')
);
CREATE INDEX IF NOT EXISTS idx_argos_transport_sim_samples_latest
    ON brady.argos_transport_sim_samples(session_uid, scenario_code, sequence DESC);

CREATE TABLE IF NOT EXISTS brady.argos_transport_sim_episodes (
    episode_uid UUID PRIMARY KEY,
    session_uid UUID NOT NULL,
    scenario_code VARCHAR(40) NOT NULL,
    event_type VARCHAR(80) NOT NULL,
    severity VARCHAR(20) NOT NULL CHECK (severity IN ('info','warning','critical')),
    status VARCHAR(20) NOT NULL CHECK (status IN ('new','ongoing','aggravated','resolved')),
    first_sequence BIGINT NOT NULL,
    last_sequence BIGINT NOT NULL,
    first_simulated_at TIMESTAMPTZ NOT NULL,
    last_simulated_at TIMESTAMPTZ NOT NULL,
    closed_at TIMESTAMPTZ,
    evidence JSONB NOT NULL DEFAULT '[]'::jsonb,
    recommendation TEXT,
    provenance JSONB NOT NULL DEFAULT '{"dataOrigin":"SYNTHETIC"}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    FOREIGN KEY (session_uid, scenario_code)
        REFERENCES brady.argos_transport_sim_scenarios(session_uid, scenario_code) ON DELETE CASCADE,
    CHECK (jsonb_typeof(evidence)='array'),
    CHECK (jsonb_typeof(provenance)='object' AND provenance->>'dataOrigin'='SYNTHETIC')
);
CREATE INDEX IF NOT EXISTS idx_argos_transport_sim_episodes
    ON brady.argos_transport_sim_episodes(session_uid, scenario_code, first_simulated_at);

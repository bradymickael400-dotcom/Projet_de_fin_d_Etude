ALTER TABLE brady.argos_transport_sim_samples
    ADD COLUMN IF NOT EXISTS telemetry_payload JSONB NOT NULL DEFAULT '{}'::jsonb;

ALTER TABLE brady.argos_transport_sim_samples
    ADD CONSTRAINT chk_argos_transport_sim_telemetry_origin
    CHECK (telemetry_payload = '{}'::jsonb OR
           telemetry_payload->'quality'->>'dataOrigin'='SYNTHETIC');

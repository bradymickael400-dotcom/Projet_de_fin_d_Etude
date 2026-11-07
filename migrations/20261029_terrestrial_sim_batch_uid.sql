ALTER TABLE brady.argos_transport_sim_samples
    ADD COLUMN IF NOT EXISTS batch_uid UUID;

UPDATE brady.argos_transport_sim_samples
SET batch_uid = md5(session_uid::text || ':' || scenario_code || ':' || sequence::text)::uuid
WHERE batch_uid IS NULL;

ALTER TABLE brady.argos_transport_sim_samples
    ALTER COLUMN batch_uid SET NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_argos_transport_sim_batch_uid
    ON brady.argos_transport_sim_samples(batch_uid);

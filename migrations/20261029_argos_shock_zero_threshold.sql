-- Zero is not a valid shock alarm threshold: it raises an alert for any
-- positive sensor reading. Five G is the ARGOS operational fallback, not an
-- ISO/CSC damage limit. Individual positive per-box settings remain intact.
ALTER TABLE seuils_alerte
    ALTER COLUMN choc_max SET DEFAULT 5.0;

UPDATE seuils_alerte
SET choc_max = 5.0
WHERE choc_max IS NULL OR choc_max <= 0;

COMMENT ON COLUMN seuils_alerte.choc_max IS
    'ARGOS operational shock threshold in G; fallback 5 G is not a CSC/ISO structural damage limit.';

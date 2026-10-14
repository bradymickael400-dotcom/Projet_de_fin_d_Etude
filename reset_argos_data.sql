-- =============================================================================
-- ARGOS - RESET COMPLET DES DONNEES + SEED COHERENT
-- ATTENTION: ce script vide toutes les tables du schema brady.
-- Usage:
--   psql "$DATABASE_URL" -f reset_argos_data.sql
-- =============================================================================

BEGIN;

CREATE SCHEMA IF NOT EXISTS brady;
SET search_path = brady, public;

-- Numero metier des boites noires: prefixe fixe 2 lettres + sequence + suffixe lettres.
CREATE SEQUENCE IF NOT EXISTS brady.boite_serial_seq START WITH 1 INCREMENT BY 1;

CREATE OR REPLACE FUNCTION brady.argos_next_boite_serial(prefix text DEFAULT 'BB')
RETURNS text
LANGUAGE plpgsql
AS $$
DECLARE
    n bigint;
    clean_prefix text;
    suffix text;
BEGIN
    clean_prefix := upper(left(regexp_replace(coalesce(prefix, 'BB'), '[^A-Za-z]', '', 'g') || 'BB', 2));
    n := nextval('brady.boite_serial_seq');
    suffix := chr(65 + (((n - 1) / 26) % 26)::int) || chr(65 + ((n - 1) % 26)::int);
    RETURN clean_prefix || '-' || lpad(n::text, 6, '0') || '-' || suffix;
END;
$$;

ALTER TABLE brady.boite_noir
    ADD COLUMN IF NOT EXISTS numero_serie varchar(20);

ALTER TABLE brady.boite_noir
    ALTER COLUMN numero_serie SET DEFAULT brady.argos_next_boite_serial('BB');

CREATE UNIQUE INDEX IF NOT EXISTS uq_boite_noir_numero_serie
    ON brady.boite_noir(numero_serie);

-- ═══════════════════════════════════════════════════════════════════
--  INITIALISATION SCHÉMA: Colonnes pour archivage et gestion
-- ═══════════════════════════════════════════════════════════════════

-- Conteneurs: colonnes de gestion
ALTER TABLE brady.conteneurs 
    ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'ok';

-- Boîtes noires: colonnes d'état et archivage
ALTER TABLE brady.boite_noir 
    ADD COLUMN IF NOT EXISTS archived BOOLEAN DEFAULT FALSE;

ALTER TABLE brady.boite_noir 
    ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'active';

ALTER TABLE brady.boite_noir 
    ADD COLUMN IF NOT EXISTS battery_level NUMERIC DEFAULT 100;

ALTER TABLE brady.boite_noir 
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();

-- Vidage complet du schema applicatif.
DO $$
DECLARE
    stmt text;
BEGIN
    SELECT 'TRUNCATE TABLE ' ||
           string_agg(format('%I.%I', schemaname, tablename), ', ') ||
           ' RESTART IDENTITY CASCADE'
    INTO stmt
    FROM pg_tables
    WHERE schemaname = 'brady';

    IF stmt IS NOT NULL THEN
        EXECUTE stmt;
    END IF;
END $$;

ALTER SEQUENCE brady.boite_serial_seq RESTART WITH 1;

-- Comptes.
-- Mot de passe superadmin: admin123
INSERT INTO brady.superadmin (id, login, password)
VALUES
    (1, 'superadmin', 'scrypt:32768:8:1$2Rx3Mv5Dpc5WH80w$2e32a5a8fd0dd1632f727d646baef2aadc66da0b71c7c4a5ad4a8d8374aac5371417f6334d4fa2e12a644fb3c0b6310bd4e7a9068796bf260f262be99a7cc53b')
ON CONFLICT (id) DO NOTHING;
SELECT setval('brady.superadmin_id_seq', 1, true);

-- Mot de passe des comptes demo: admin123
INSERT INTO brady.proprietaire_conteneur
    (id, niu, nom_agence, login, password, addresse_mail, lieu_residence, lat, lon, nbr_boite)
VALUES
    (1, 'NIU-ARGOS-001', 'CamShip Logistics', 'owner_camship',
     'scrypt:32768:8:1$2Rx3Mv5Dpc5WH80w$2e32a5a8fd0dd1632f727d646baef2aadc66da0b71c7c4a5ad4a8d8374aac5371417f6334d4fa2e12a644fb3c0b6310bd4e7a9068796bf260f262be99a7cc53b',
     'ops@camship.example', 'Douala', 4.0511, 9.7085, 2),
    (2, 'NIU-ARGOS-002', 'Kribi Fresh Cargo', 'owner_kribi',
     'scrypt:32768:8:1$2Rx3Mv5Dpc5WH80w$2e32a5a8fd0dd1632f727d646baef2aadc66da0b71c7c4a5ad4a8d8374aac5371417f6334d4fa2e12a644fb3c0b6310bd4e7a9068796bf260f262be99a7cc53b',
     'contact@kribifresh.example', 'Kribi', 2.9394, 9.9072, 2);
SELECT setval('brady.proprietaire_conteneur_id_seq', 2, true);

INSERT INTO brady.agence_utilisatrice
    (niu, nom_agence, login, password, addresse_mail)
VALUES
    ('AG-TRANS-001', 'Transit Douala', 'agency_dla',
     'scrypt:32768:8:1$2Rx3Mv5Dpc5WH80w$2e32a5a8fd0dd1632f727d646baef2aadc66da0b71c7c4a5ad4a8d8374aac5371417f6334d4fa2e12a644fb3c0b6310bd4e7a9068796bf260f262be99a7cc53b',
     'agency@douala.example');

INSERT INTO brady.client
    (id_cni, login, password, nom, prenom, address_mail, created_by)
VALUES
    ('CNI-CLI-001', 'client_alpha',
     'scrypt:32768:8:1$2Rx3Mv5Dpc5WH80w$2e32a5a8fd0dd1632f727d646baef2aadc66da0b71c7c4a5ad4a8d8374aac5371417f6334d4fa2e12a644fb3c0b6310bd4e7a9068796bf260f262be99a7cc53b',
     'Meka', 'Aline', 'aline.meka@example.com', 'seed'),
    ('CNI-CLI-002', 'client_beta',
     'scrypt:32768:8:1$2Rx3Mv5Dpc5WH80w$2e32a5a8fd0dd1632f727d646baef2aadc66da0b71c7c4a5ad4a8d8374aac5371417f6334d4fa2e12a644fb3c0b6310bd4e7a9068796bf260f262be99a7cc53b',
     'Ngono', 'Paul', 'paul.ngono@example.com', 'seed');

INSERT INTO brady.transporteur
    (id_cni, login, password, nom, prenom, contact, id_boite, id_boites, blocked)
VALUES
    ('CNI-DRV-001', 'driver_one',
     'scrypt:32768:8:1$2Rx3Mv5Dpc5WH80w$2e32a5a8fd0dd1632f727d646baef2aadc66da0b71c7c4a5ad4a8d8374aac5371417f6334d4fa2e12a644fb3c0b6310bd4e7a9068796bf260f262be99a7cc53b',
     'Talla', 'Eric', '+237690000001', '1', '[1,2]', false),
    ('CNI-DRV-002', 'driver_two',
     'scrypt:32768:8:1$2Rx3Mv5Dpc5WH80w$2e32a5a8fd0dd1632f727d646baef2aadc66da0b71c7c4a5ad4a8d8374aac5371417f6334d4fa2e12a644fb3c0b6310bd4e7a9068796bf260f262be99a7cc53b',
     'Biloa', 'Sarah', '+237690000002', '3', '[3,4]', false);

-- Conteneurs ISO 6346 valides (2 uniquement).
INSERT INTO brady.conteneurs
    (id_conteneurs, taile_perimetre, type_conteneurs, status)
VALUES
    ('MSCU1234566', '20 pieds / 14.6 m', 'DRY', 'ok'),
    ('CMAU7654321', '40 pieds / 24.2 m', 'HighCube', 'ok');

INSERT INTO brady.boite_noir
    (id_boite, numero_serie, id_conteneurs, id_proprietaire, type_boite, versions, 
     log_action, status, archived, battery_level, updated_at)
VALUES
    (1, 'BB-000001-AA', 'MSCU1234566', 1, 'monthly', 'v2.1', 'Seed initial', 'active', FALSE, 100, NOW()),
    (2, 'BB-000002-AB', 'CMAU7654321', 1, 'monthly', 'v2.1', 'Seed initial', 'active', FALSE, 100, NOW());

SELECT setval('brady.boite_noir_id_boite_seq', 2, true);
SELECT setval('brady.boite_serial_seq', 2, true);

INSERT INTO brady.abonner
    (id_cni, id_boite, type_abonnement, status, created_at)
VALUES
    ('CNI-CLI-001', 1, 'Mensuel', 'Actif', NOW() - INTERVAL '35 days'),
    ('CNI-CLI-002', 2, 'Mensuel', 'Actif', NOW() - INTERVAL '12 days');

INSERT INTO brady.colis
    (id_cni_client, id_cni_transporteur, num_plom, desc_colis, destination, status)
VALUES
    ('CNI-CLI-001', 'CNI-DRV-001', 'PL-001', 'Pieces industrielles', 'Yaounde', 'En Transit'),
    ('CNI-CLI-002', 'CNI-DRV-002', 'PL-002', 'Produits frais', 'Kribi', 'En Transit');

INSERT INTO brady.seuils_alerte
    (id_boite, temp_max, temp_min, humi_max, choc_max, pression_min, vitesse_max, angle_max)
VALUES
    (1, 32, -10, 75, 5, 995, 90, 30),
    (2, 32, -10, 75, 5, 995, 90, 30);

-- Telemetrie recente: valeurs normales + alertes.
INSERT INTO brady.evenement_save
    (horodatage, id_boite, temperature, humidite, pressions, chocs, vitesse, lat, lon, log_action, notif)
VALUES
    (NOW() - INTERVAL '6 days', 1, 27.4, 61.0, 1008.4, 0.4, 42.0, 4.0511, 9.7085, 'Scan regulier', NULL),
    (NOW() - INTERVAL '5 days', 1, 34.8, 67.2, 1001.2, 1.1, 48.0, 4.0700, 9.7200, 'Alerte generee', '["Temperature trop haute (34.8 C > 32.0)"]'),
    (NOW() - INTERVAL '4 days', 2, 26.2, 58.1, 1005.8, 0.9, 62.0, 4.1500, 9.8100, 'Scan regulier', NULL),
    (NOW() - INTERVAL '3 days', 2, 28.5, 64.4, 993.1, 6.3, 55.0, 4.2600, 9.9200, 'Alerte generee', '["Choc critique detecte (6.3G)", "Pression basse (993.1hPa < 995.0)"]');

-- Notifications volontairement presentes pour tester les statistiques combinees.
INSERT INTO brady.notifications
    (type, message, cible_role, id_boite, initiator_id, status, horodatage)
VALUES
    ('THRESHOLD_ALERT', 'Temperature trop haute sur BB-000001-AA', 'all', 1, NULL, 'unread', NOW() - INTERVAL '5 days'),
    ('SECURITY_ALERT', 'Choc critique detecte sur BB-000002-AB', 'all', 2, NULL, 'unread', NOW() - INTERVAL '3 days');

-- Donnees maritimes minimales pour l'autorite portuaire.
INSERT INTO brady.port (locode, port_name, country_code, lat, lon, timezone, has_argos)
VALUES
    ('CMDLE', 'Port Autonome de Douala', 'CM', 4.051100, 9.708500, 'Africa/Douala', true),
    ('CMKBI', 'Port de Kribi', 'CM', 2.939400, 9.907200, 'Africa/Douala', true)
ON CONFLICT (locode) DO NOTHING;

INSERT INTO brady.port_authority_user
    (id, login, password, full_name, port_locode, authority_type, permissions)
VALUES
    (1, 'port_douala',
     'scrypt:32768:8:1$2Rx3Mv5Dpc5WH80w$2e32a5a8fd0dd1632f727d646baef2aadc66da0b71c7c4a5ad4a8d8374aac5371417f6334d4fa2e12a644fb3c0b6310bd4e7a9068796bf260f262be99a7cc53b',
     'Autorite Portuaire Douala', 'CMDLE', 'customs', ARRAY['read', 'clearance']),
    (2, 'port_kribi',
     'scrypt:32768:8:1$2Rx3Mv5Dpc5WH80w$2e32a5a8fd0dd1632f727d646baef2aadc66da0b71c7c4a5ad4a8d8374aac5371417f6334d4fa2e12a644fb3c0b6310bd4e7a9068796bf260f262be99a7cc53b',
     'Autorite Portuaire Kribi', 'CMKBI', 'customs', ARRAY['read', 'clearance'])
ON CONFLICT (id) DO NOTHING;
SELECT setval('brady.port_authority_user_id_seq', 2, true);

-- Le bloc genesis est cree par l'application avec un hash canonique au premier appel.

COMMIT;

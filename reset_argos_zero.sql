-- ARGOS - remise a zero des donnees metier pour le prototype physique.
--
-- Le schema et l'historique des migrations sont conserves. Toutes les anciennes
-- mesures, alertes, notifications, associations, utilisateurs et donnees metier
-- sont effaces. Seuls les deux comptes demandes et l'identite minimale de
-- l'ESP32-S3 de demonstration sont recrees.

BEGIN;
SET search_path = brady, public;

DO $$
DECLARE
    statement text;
BEGIN
    SELECT 'TRUNCATE TABLE ' ||
           string_agg(format('%I.%I', schemaname, tablename), ', ') ||
           ' RESTART IDENTITY CASCADE'
      INTO statement
      FROM pg_tables
     WHERE schemaname = 'brady'
       AND tablename <> 'schema_migrations';

    IF statement IS NOT NULL THEN
        EXECUTE statement;
    END IF;
END $$;

ALTER SEQUENCE IF EXISTS brady.boite_serial_seq RESTART WITH 2;

-- Compte administrateur du prototype : superadmin / admin123
INSERT INTO brady.superadmin (id, login, password)
VALUES (
    1,
    'superadmin',
    'scrypt:32768:8:1$o5dM2xFnEBg5lqLD$7ee5417aa066f8a5a97f92184aafd16e9ef5eb7d30f8c8a677c18865addf8b0ac17ccb0550d9d1c86bbc3ed1e80dee34320f238f7307ad4ec628c7773ce2c21e'
);
SELECT setval('brady.superadmin_id_seq', 1, true);

-- Compte demande pour le Port Autonome de Douala : pad / padpasse
INSERT INTO brady.port
    (locode, port_name, country_code, lat, lon, timezone, has_argos)
VALUES
    ('CMDLE', 'Port Autonome de Douala', 'CM', 4.0511, 9.7085,
     'Africa/Douala', true);

INSERT INTO brady.port_authority_user
    (id, login, password, full_name, port_locode, authority_type, permissions)
VALUES (
    1,
    'pad',
    'scrypt:32768:8:1$wQBXoBCJ1eLtTbFN$dd7564afcf5c682c11e395d795234351974e49e616e0df6a09f44af893b83339df7005892d9e65f96c2321ec3832a2321ddfed3f1a841eef53f35eeb07e418e9',
    'Port Autonome de Douala',
    'CMDLE',
    'port_authority',
    ARRAY['read', 'clearance']
);
SELECT setval('brady.port_authority_user_id_seq', 1, true);

-- Invalide toutes les sessions signees avant la remise a zero. La version
-- utilise l'epoque courante (entier 32 bits jusqu'en 2038) au lieu de repartir
-- a 1, ce qui empecherait sinon un ancien jeton de redevenir valide.
UPDATE brady.identity_registry
   SET token_version = EXTRACT(EPOCH FROM clock_timestamp())::integer,
       must_change_password = false,
       updated_at = NOW()
 WHERE (actor_role = 'superadmin' AND actor_id = '1')
    OR (actor_role = 'port_authority' AND actor_id = '1');

-- Identite minimale conservee pour que le mode Wi-Fi direct fonctionne des le
-- premier demarrage, sans fabriquer de fausses mesures historiques.
INSERT INTO brady.boite_noir
    (id_boite, numero_serie, id_conteneurs, id_proprietaire, type_boite,
     versions, log_action, status, archived, battery_level)
VALUES
    (1, 'BB-000001-AA', NULL, NULL, 'continuous', 'v2.1-esp32-s3',
     'Prototype ESP32-S3 remis a zero', 'unassigned', false, 100);
SELECT setval('brady.boite_noir_id_boite_seq', 1, true);

INSERT INTO brady.iot_devices
    (id, device_uid, hardware_serial, firmware_version, protocol_version,
     status, metadata)
VALUES
    (1, 'ESP32-54CBE462F8B8', 'ESP32-54CBE462F8B8',
     'ARGOS-ESP32-S3', '1.0', 'PENDING_ENROLLMENT',
     '{"source":"prototype-reset","directWifi":true}'::jsonb);
SELECT setval('brady.iot_devices_id_seq', 1, true);

INSERT INTO brady.black_box_devices
    (id, black_box_id, device_id, assigned_by, status)
VALUES
    (1, 1, 1, 'reset_argos_zero', 'ACTIVE');
SELECT setval('brady.black_box_devices_id_seq', 1, true);

INSERT INTO brady.seuils_alerte
    (id_boite, temp_max, temp_min, humi_max, humi_min, choc_max,
     pression_min, pression_max, vitesse_max, angle_max)
VALUES
    (1, 32, -10, 75, 20, 5, 995, 1035, 90, 30);

COMMIT;

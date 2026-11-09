CREATE TABLE IF NOT EXISTS brady.argos_port_locations (
    port_id VARCHAR(20) PRIMARY KEY,
    port_name TEXT NOT NULL,
    country VARCHAR(100) NOT NULL,
    country_code CHAR(2) NOT NULL,
    latitude DOUBLE PRECISION NOT NULL CHECK (latitude BETWEEN -90 AND 90),
    longitude DOUBLE PRECISION NOT NULL CHECK (longitude BETWEEN -180 AND 180),
    location_type VARCHAR(40) NOT NULL DEFAULT 'commercial_port',
    operational_status VARCHAR(40) NOT NULL DEFAULT 'TO_VERIFY',
    coordinate_precision VARCHAR(80) NOT NULL DEFAULT 'REFERENCE_POINT_NOT_BOUNDARY',
    boundary_geojson JSONB,
    coordinate_source TEXT NOT NULL,
    verification_status VARCHAR(60) NOT NULL DEFAULT 'USER_PROVIDED_UNVERIFIED',
    last_verified_at DATE,
    proximity_radius_m INTEGER NOT NULL DEFAULT 3000 CHECK (proximity_radius_m BETWEEN 250 AND 20000),
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS brady.argos_port_statistics (
    statistic_id BIGSERIAL PRIMARY KEY,
    port_id VARCHAR(20) NOT NULL REFERENCES brady.argos_port_locations(port_id),
    period_year INTEGER NOT NULL,
    indicator TEXT NOT NULL,
    value NUMERIC(20,2) NOT NULL,
    unit VARCHAR(30) NOT NULL,
    source_url TEXT NOT NULL,
    source_page TEXT,
    verification_status VARCHAR(60) NOT NULL DEFAULT 'USER_PROVIDED_SOURCE_NOT_RECHECKED',
    notes TEXT NOT NULL DEFAULT '',
    UNIQUE(port_id, period_year, indicator, unit)
);

CREATE INDEX IF NOT EXISTS ix_argos_port_locations_enabled
ON brady.argos_port_locations(enabled, country_code);
CREATE INDEX IF NOT EXISTS ix_argos_port_statistics_port_year
ON brady.argos_port_statistics(port_id, period_year);

-- Le polygone de démonstration de Douala n'est pas une limite officielle;
-- les alertes portuaires utilisent désormais le point de référence provisoire.
UPDATE brady.argos_geofence_zones
SET enabled=FALSE
WHERE zone_id='CM_DOUALA_PORT'
  AND zone_name ILIKE '%démonstration%';

INSERT INTO brady.regulatory_sources
    (source_key,title,source_type,authority,jurisdiction,transport_modes,legal_status,
     applicability_conditions,summary,verified_at)
VALUES
('ARGOS_PORT_LOCATIONS','Référentiel initial des points portuaires ARGOS','OPERATIONAL_DATA','ARGOS / référentiel fourni par utilisateur','Afrique centrale',ARRAY['sea','multimodal'],'INTERNAL_UNVERIFIED',
 'Coordonnées ponctuelles WGS84 fournies comme repères; confirmer auprès des autorités. Un rayon informatique ne constitue pas une limite officielle.',
 'Référentiel de repères portuaires et terminaux spécialisés; positions non certifiées et périmètres officiels absents.',NULL),
('ARGOS_PORT_STATISTICS','Premiers indicateurs portuaires issus du référentiel ARGOS','STATISTICAL_DATA','Sources portuaires citées par utilisateur','Afrique centrale',ARRAY['sea','multimodal'],'SOURCE_NOT_RECHECKED',
 'Valeurs de périodes et unités différentes; consulter le rapport lié, son périmètre et sa page avant comparaison.',
 'Ne pas interpréter un trafic comme des conteneurs uniques ou un nombre d’incidents; les flux origine-destination manquants restent indisponibles, pas égaux à zéro.',NULL)
ON CONFLICT (source_key) DO UPDATE SET
    title=EXCLUDED.title, summary=EXCLUDED.summary, updated_at=NOW();

INSERT INTO brady.argos_port_locations
    (port_id,port_name,country,country_code,latitude,longitude,location_type,
     coordinate_source,verification_status,proximity_radius_m)
VALUES
('CM-DLA','Port de Douala','Cameroun','CM',4.0370,9.6730,'commercial_port','Référentiel utilisateur; wilhelmsen.com; Douala Port Information','USER_PROVIDED_UNVERIFIED',3000),
('CM-KBI','Port en eau profonde de Kribi','Cameroun','CM',2.7267,9.8600,'commercial_port','Référentiel utilisateur; Kribi Port Information','USER_PROVIDED_UNVERIFIED',3000),
('CM-LIM','Port de Limbe','Cameroun','CM',4.0030,9.1250,'commercial_port','Référentiel utilisateur; TotalEnergies Marine Fuels','USER_PROVIDED_UNVERIFIED',3000),
('CG-PNR','Port autonome de Pointe-Noire','République du Congo','CG',-4.7833,11.8167,'commercial_port','Référentiel utilisateur; orientallogistics.com','USER_PROVIDED_UNVERIFIED',3000),
('CG-DJE','Terminal pétrolier de Djeno','République du Congo','CG',-4.9333,11.9000,'specialized_terminal','Référentiel utilisateur; orientallogistics.com','USER_PROVIDED_UNVERIFIED',1500),
('GA-OWE','Port d’Owendo','Gabon','GA',0.2917,9.5053,'commercial_port','Référentiel utilisateur; référence indiquée Wikipedia','USER_PROVIDED_UNVERIFIED',3000),
('GA-LBV','Zone portuaire de Libreville','Gabon','GA',0.4000,9.4330,'commercial_port','Référentiel utilisateur; orientallogistics.com','USER_PROVIDED_UNVERIFIED',3000),
('GA-PGE','Port de Port-Gentil','Gabon','GA',-0.7167,8.7917,'commercial_port','Référentiel utilisateur; msi.nga.mil','USER_PROVIDED_UNVERIFIED',3000),
('GA-CLO','Terminal de Cap Lopez','Gabon','GA',-0.6320,8.7200,'specialized_terminal','Référentiel utilisateur; PDFCOFFEE.COM','USER_PROVIDED_UNVERIFIED',1500),
('GA-GAM','Terminal pétrolier de Gamba','Gabon','GA',-2.8600,9.9700,'specialized_terminal','Référentiel utilisateur; PDFCOFFEE.COM','USER_PROVIDED_UNVERIFIED',1500),
('GQ-MAL','Port de Malabo','Guinée équatoriale','GQ',3.7500,8.7833,'commercial_port','Référentiel utilisateur; La navigation','USER_PROVIDED_UNVERIFIED',3000),
('GQ-BAT','Port de Bata','Guinée équatoriale','GQ',1.8667,9.7667,'commercial_port','Référentiel utilisateur; orientallogistics.com','USER_PROVIDED_UNVERIFIED',3000),
('GQ-LUB','Port de Luba','Guinée équatoriale','GQ',3.4667,8.5500,'commercial_port','Référentiel utilisateur; orientallogistics.com','USER_PROVIDED_UNVERIFIED',3000),
('GQ-COG','Port de Cogo','Guinée équatoriale','GQ',1.0833,9.7000,'commercial_port','Référentiel utilisateur; orientallogistics.com','USER_PROVIDED_UNVERIFIED',3000),
('GQ-PEU','Terminal de Punta Europa','Guinée équatoriale','GQ',3.7833,8.7167,'specialized_terminal','Référentiel utilisateur; La navigation','USER_PROVIDED_UNVERIFIED',1500),
('GQ-CEI','Terminal de Ceiba','Guinée équatoriale','GQ',1.4000,9.2167,'specialized_terminal','Référentiel utilisateur; library.stipjakarta.ac.id','USER_PROVIDED_UNVERIFIED',1500),
('ST-SAO','Port de São Tomé','São Tomé-et-Príncipe','ST',0.3500,6.7500,'commercial_port','Référentiel utilisateur; library.stipjakarta.ac.id','USER_PROVIDED_UNVERIFIED',3000),
('ST-PRI','Port de Santo António, île de Príncipe','São Tomé-et-Príncipe','ST',1.6500,7.4500,'commercial_port','Référentiel utilisateur; library.stipjakarta.ac.id','USER_PROVIDED_UNVERIFIED',3000),
('CD-MAT','Port de Matadi','République démocratique du Congo','CD',-5.8200,13.4520,'river_port','Référentiel utilisateur; wilhelmsen.com','USER_PROVIDED_UNVERIFIED',3000),
('CD-BOM','Port de Boma','République démocratique du Congo','CD',-5.8500,13.0500,'river_port','Référentiel utilisateur; référence indiquée Wikipedia','USER_PROVIDED_UNVERIFIED',3000),
('CD-BNW','Port de Banana','République démocratique du Congo','CD',-5.9830,12.3830,'commercial_port','Référentiel utilisateur; référence indiquée Wikipedia','USER_PROVIDED_UNVERIFIED',3000),
('CD-MUA','Zone portuaire de Muanda','République démocratique du Congo','CD',-5.9597,12.3436,'commercial_port','Référentiel utilisateur; TotalEnergies Marine Fuels','USER_PROVIDED_UNVERIFIED',3000),
('AO-LUA','Port de Luanda','Angola','AO',-8.7967,13.2500,'commercial_port','Référentiel utilisateur; PDFCOFFEE.COM','USER_PROVIDED_UNVERIFIED',3000),
('AO-CAB','Port de Cabinda','Angola','AO',-5.5500,12.2000,'commercial_port','Référentiel utilisateur; référence nautique indiquée','USER_PROVIDED_UNVERIFIED',3000),
('AO-SOY','Port de Soyo','Angola','AO',-6.1167,12.3667,'commercial_port','Référentiel utilisateur; référence nautique indiquée','USER_PROVIDED_UNVERIFIED',3000),
('AO-LOB','Port de Lobito','Angola','AO',-12.3467,13.5483,'commercial_port','Référentiel utilisateur; PDFCOFFEE.COM','USER_PROVIDED_UNVERIFIED',3000),
('AO-NAM','Port de Namibe','Angola','AO',-15.1950,12.1500,'commercial_port','Référentiel utilisateur; PDFCOFFEE.COM','USER_PROVIDED_UNVERIFIED',3000),
('AO-PAM','Port d’Amboim','Angola','AO',-10.7283,13.7517,'commercial_port','Référentiel utilisateur; PDFCOFFEE.COM','USER_PROVIDED_UNVERIFIED',3000)
ON CONFLICT (port_id) DO UPDATE SET
    port_name=EXCLUDED.port_name,country=EXCLUDED.country,country_code=EXCLUDED.country_code,
    latitude=EXCLUDED.latitude,longitude=EXCLUDED.longitude,location_type=EXCLUDED.location_type,
    coordinate_source=EXCLUDED.coordinate_source,verification_status=EXCLUDED.verification_status,
    proximity_radius_m=EXCLUDED.proximity_radius_m,enabled=TRUE,updated_at=NOW();

INSERT INTO brady.argos_port_statistics
    (port_id,period_year,indicator,value,unit,source_url,verification_status,notes)
VALUES
('CG-PNR',2023,'Trafic total de marchandises, avitaillements inclus',11241284,'tonnes','https://papn-cg.org/wp-content/uploads/2025/09/RAPPORT-ACTIVITE-2023-DU-PAPN.pdf','USER_PROVIDED_SOURCE_NOT_RECHECKED','Périmètre tel que présenté dans le référentiel fourni; ne pas comparer à des EVP.'),
('CG-PNR',2022,'Trafic total de marchandises',13363667,'tonnes','https://papn-cg.org/wp-content/uploads/2025/09/RAPPORT-ACTIVITE-2023-DU-PAPN.pdf','USER_PROVIDED_SOURCE_NOT_RECHECKED','Valeur rapportée dans le référentiel fourni; vérifier définition et page du rapport.'),
('CG-PNR',2023,'Conteneurs en transbordement',801353,'EVP','https://papn-cg.org/wp-content/uploads/2025/09/RAPPORT-ACTIVITE-2023-DU-PAPN.pdf','USER_PROVIDED_SOURCE_NOT_RECHECKED','Mouvements EVP; pas nécessairement des conteneurs uniques.'),
('CG-PNR',2023,'Mouvements de conteneurs embarquement et débarquement',1008284,'EVP','https://papn-cg.org/wp-content/uploads/2025/09/RAPPORT-ACTIVITE-2023-DU-PAPN.pdf','USER_PROVIDED_SOURCE_NOT_RECHECKED','Ne représente pas un compte garanti de conteneurs uniques.'),
('CG-PNR',2023,'Part du transbordement dans le trafic conteneurisé',79,'percent','https://papn-cg.org/wp-content/uploads/2025/09/RAPPORT-ACTIVITE-2023-DU-PAPN.pdf','USER_PROVIDED_SOURCE_NOT_RECHECKED','Définition à confirmer dans le rapport original.'),
('CM-KBI',2023,'Transit importation toutes marchandises',52525,'tonnes','https://pak.cm/fr/apropos/statistiques-commerciales/','USER_PROVIDED_SOURCE_NOT_RECHECKED','Ne représente pas le trafic total du port.'),
('CM-KBI',2023,'Transit exportation',215501,'tonnes','https://pak.cm/fr/apropos/statistiques-commerciales/','USER_PROVIDED_SOURCE_NOT_RECHECKED','Ne représente pas le trafic total du port.'),
('CM-KBI',2023,'Transit total EVP à l’importation',4312,'EVP','https://pak.cm/fr/apropos/statistiques-commerciales/','USER_PROVIDED_SOURCE_NOT_RECHECKED','Donnée de transit rapportée; vérifier le tableau et son périmètre.'),
('CM-KBI',2023,'Transit total EVP à l’exportation',15145,'EVP','https://pak.cm/fr/apropos/statistiques-commerciales/','USER_PROVIDED_SOURCE_NOT_RECHECKED','Donnée de transit rapportée; vérifier le tableau et son périmètre.')
ON CONFLICT (port_id,period_year,indicator,unit) DO UPDATE SET
    value=EXCLUDED.value,source_url=EXCLUDED.source_url,
    verification_status=EXCLUDED.verification_status,notes=EXCLUDED.notes;

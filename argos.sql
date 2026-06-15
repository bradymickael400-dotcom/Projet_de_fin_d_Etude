-- ==========================================
-- 1. EXTENSIONS ET SÉQUENCES
-- ==========================================
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Séquence pour générer le suffixe à 6 chiffres de la Boîte Noire
CREATE SEQUENCE IF NOT EXISTS seq_boite_noir START 1;

-- Fonction générique pour mettre à jour automatiquement la date de modification (Logs)
CREATE OR REPLACE FUNCTION update_timestamp_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;


-- ==========================================
-- 2. CRÉATION DES TABLES (Avec champs de logs)
-- ==========================================
drop table if exists SuperAdmin, Conteneurs, Boite_noir, Proprietaire_Conteneur, Client, Agence_Utilisatrice, Abonner, Transporteur, Colis, Evenement_save cascade;
-- Table: SuperAdmin
CREATE TABLE if NOT EXISTS SuperAdmin (
    id SERIAL PRIMARY KEY, -- Auto-incrémenté, sans interaction
    id_cni VARCHAR(50) UNIQUE,
    login VARCHAR(50) UNIQUE NOT NULL,
    password TEXT NOT NULL, -- Chiffré
    dd_pass DATE,
    -- Champs de suivi et logs
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    log_action VARCHAR(255) DEFAULT 'Création'
);

-- Table: Conteneurs
CREATE TABLE if NOT EXISTS Conteneurs (
    id_conteneurs VARCHAR(50) PRIMARY KEY, -- Rempli par l'utilisateur
    resistance VARCHAR(50),
    taile_perimetre VARCHAR(50),
    type_conteneurs VARCHAR(50),
    -- Champs de suivi et logs
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    log_action VARCHAR(255) DEFAULT 'Création'
);

-- Table: Boite_noir
CREATE TABLE if NOT EXISTS Boite_noir (
    -- ID généré auto : 'BN-' suivi de 6 chiffres (ex: BN-000001)
    id_boite VARCHAR(15) PRIMARY KEY DEFAULT 'BN-' || LPAD(nextval('seq_boite_noir')::TEXT, 6, '0'),
    id_conteneurs VARCHAR(50) REFERENCES Conteneurs(id_conteneurs) ON DELETE SET NULL,
    type_boite VARCHAR(50),
    versions VARCHAR(50),
    -- Champs de suivi et logs
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    log_action VARCHAR(255) DEFAULT 'Création'
);

-- Table: Proprietaire_Conteneur
CREATE TABLE if NOT EXISTS Proprietaire_Conteneur (
    id SERIAL PRIMARY KEY, -- Identifiant de compte auto-incrémenté
    NIU VARCHAR(50) UNIQUE NOT NULL,
    id_boite VARCHAR(15) REFERENCES Boite_noir(id_boite) ON DELETE SET NULL,
    Nom_agence VARCHAR(100),
    login VARCHAR(50) UNIQUE NOT NULL,
    password TEXT NOT NULL, -- Chiffré
    addresse_mail VARCHAR(100) UNIQUE NOT NULL,
    lieu_residence VARCHAR(100),
    lon NUMERIC(9, 6),
    lat NUMERIC(9, 6),
    Nbr_boite INT DEFAULT 0,
    -- Champs de suivi et logs
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    log_action VARCHAR(255) DEFAULT 'Création'
);

-- Table: Client
CREATE TABLE if NOT EXISTS Client (
    id_cni VARCHAR(50) PRIMARY KEY,
    login VARCHAR(50) UNIQUE NOT NULL,
    password TEXT NOT NULL, -- Chiffré
    nom VARCHAR(100),
    prenom VARCHAR(100),
    date_reception_expedition DATE,
    address_mail VARCHAR(100) UNIQUE NOT NULL,
    contact VARCHAR(20),
    -- Champs de suivi et logs
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    log_action VARCHAR(255) DEFAULT 'Création'
);

-- Table: Agence_Utilisatrice (Hérite ou est liée au Client)
CREATE TABLE if NOT EXISTS Agence_Utilisatrice (
    NIU VARCHAR(50) PRIMARY KEY,
    id_cni VARCHAR(50) REFERENCES Client(id_cni) ON DELETE CASCADE,
    Nom_agence VARCHAR(100),
    login VARCHAR(50) UNIQUE NOT NULL,
    password TEXT NOT NULL, -- Chiffré
    addresse_mail VARCHAR(100) UNIQUE NOT NULL,
    lieu_residence VARCHAR(150),
    lat NUMERIC(9, 6),
    lon NUMERIC(9, 6),
    status VARCHAR(50),
    -- Champs de suivi et logs
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    log_action VARCHAR(255) DEFAULT 'Création'
);

-- Table: Abonner
CREATE TABLE if NOT EXISTS Abonner (
    numero_A SERIAL PRIMARY KEY,
    id_boite VARCHAR(15) REFERENCES Boite_noir(id_boite) ON DELETE CASCADE,
    id_cni VARCHAR(50) REFERENCES Client(id_cni) ON DELETE CASCADE,
    type_a VARCHAR(50),
    debut_a DATE,
    fin_a DATE,
    status VARCHAR(50),
    frais NUMERIC(10, 2),
    -- Champs de suivi et logs
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    log_action VARCHAR(255) DEFAULT 'Création'
);

-- Table: Transporteur
CREATE TABLE if NOT EXISTS Transporteur (
    id_cni VARCHAR(50) PRIMARY KEY,
    nom_chauffeurs VARCHAR(150),
    login VARCHAR(50) UNIQUE NOT NULL,
    password TEXT NOT NULL, -- Chiffré
    -- Champs de suivi et logs
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    log_action VARCHAR(255) DEFAULT 'Création'
);

-- Table: Colis
CREATE TABLE if NOT EXISTS Colis (
    id_colis VARCHAR(50) PRIMARY KEY,
    id_cni_client VARCHAR(50) REFERENCES Client(id_cni) ON DELETE SET NULL,
    id_cni_transporteur VARCHAR(50) REFERENCES Transporteur(id_cni) ON DELETE SET NULL,
    nom_colis VARCHAR(100),
    poids_colis NUMERIC(8, 2), -- Correction de "poind_colis"
    valeur_colis NUMERIC(12, 2),
    temperature_moyenne NUMERIC(5, 2),
    lieux_expedition VARCHAR(150),
    lieux_receptions VARCHAR(150),
    date_heure_exp TIMESTAMPTZ,
    date_heure_reception TIMESTAMPTZ,
    moyen_transport VARCHAR(50),
    -- Champs de suivi et logs
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    log_action VARCHAR(255) DEFAULT 'Création'
);

-- Table: Evenement_save (Pour TimescaleDB)
CREATE TABLE if NOT EXISTS Evenement_save (
    id_eventinit SERIAL,
    horodatage TIMESTAMPTZ NOT NULL DEFAULT NOW(), -- Clé temporelle pour TimescaleDB
    id_boite VARCHAR(15) REFERENCES Boite_noir(id_boite) ON DELETE CASCADE,
    media_1_url TEXT, -- Images ajoutées selon ta demande précédente
    media_2_url TEXT,
    temperature NUMERIC(5, 2),
    humidite NUMERIC(5, 2),
    pressions NUMERIC(7, 2),
    lat NUMERIC(9, 6),
    lon NUMERIC(9, 6),
    -- Champs de suivi et logs
    created_at TIMESTAMPTZ DEFAULT NOW(),
    log_action VARCHAR(255) DEFAULT 'Enregistrement Capteur',
    PRIMARY KEY (id_eventinit, horodatage) -- Requis par TimescaleDB
);

-- ==========================================
-- 3. CONFIGURATION TIMESCALEDB & TRIGGERS
-- ==========================================

-- Conversion de Evenement_save en Hypertable TimescaleDB
SELECT create_hypertable('Evenement_save', 'horodatage');

-- Application des Triggers pour la mise à jour automatique de "updated_at"
CREATE TRIGGER trg_superadmin_upd BEFORE UPDATE ON SuperAdmin FOR EACH ROW EXECUTE FUNCTION update_timestamp_column();
CREATE TRIGGER trg_conteneurs_upd BEFORE UPDATE ON Conteneurs FOR EACH ROW EXECUTE FUNCTION update_timestamp_column();
CREATE TRIGGER trg_boitenoir_upd BEFORE UPDATE ON Boite_noir FOR EACH ROW EXECUTE FUNCTION update_timestamp_column();
CREATE TRIGGER trg_proprio_upd BEFORE UPDATE ON Proprietaire_Conteneur FOR EACH ROW EXECUTE FUNCTION update_timestamp_column();
CREATE TRIGGER trg_client_upd BEFORE UPDATE ON Client FOR EACH ROW EXECUTE FUNCTION update_timestamp_column();
CREATE TRIGGER trg_agence_upd BEFORE UPDATE ON Agence_Utilisatrice FOR EACH ROW EXECUTE FUNCTION update_timestamp_column();
CREATE TRIGGER trg_abonner_upd BEFORE UPDATE ON Abonner FOR EACH ROW EXECUTE FUNCTION update_timestamp_column();
CREATE TRIGGER trg_transport_upd BEFORE UPDATE ON Transporteur FOR EACH ROW EXECUTE FUNCTION update_timestamp_column();
CREATE TRIGGER trg_colis_upd BEFORE UPDATE ON Colis FOR EACH ROW EXECUTE FUNCTION update_timestamp_column();


-- ==========================================
-- 4. INSERTIONS DE DONNÉES (TESTS)
-- ==========================================

-- Insert SuperAdmin Spécifique (Mot de passe chiffré)
INSERT INTO SuperAdmin (id_cni, login, password, dd_pass) 
VALUES ('CNI-SA-001', 'Argos_br', crypt('argos_supper123', gen_salt('bf')), '2026-12-31');

-- Insert Conteneurs (L'ID est manuel)
INSERT INTO Conteneurs (id_conteneurs, resistance, taile_perimetre, type_conteneurs) VALUES 
('CONT-A1', 'Haute', '20x10x10', 'Frigorifique'),
('CONT-B2', 'Moyenne', '10x10x10', 'Standard'),
('CONT-C3', 'Haute', '40x20x20', 'Renforcé'),
('CONT-D4', 'Basse', '5x5x5', 'Léger'),
('CONT-E5', 'Extrême', '20x10x10', 'Blindé');

-- Insert Boite_noir (L'ID se génère tout seul : BN-000001, etc.)
INSERT INTO Boite_noir (id_conteneurs, type_boite, versions) VALUES 
('CONT-A1', 'GPS+Temp', 'v1.0'),
('CONT-B2', 'GPS Seulement', 'v1.2'),
('CONT-C3', 'Full Sensors', 'v2.1'),
('CONT-D4', 'Basic', 'v1.0'),
('CONT-E5', 'Full Sensors', 'v2.1');

-- Insert Proprietaire_Conteneur
INSERT INTO Proprietaire_Conteneur (NIU, id_boite, Nom_agence, login, password, addresse_mail, lon, lat) VALUES 
('NIU-1001', 'BN-000001', 'LogisTech', 'logis_admin', crypt('pass123', gen_salt('bf')), 'contact@logistech.cm', 9.709, 4.051),
('NIU-1002', 'BN-000002', 'TransExpress', 'trans_admin', crypt('pass123', gen_salt('bf')), 'hello@transexpress.cm', 9.710, 4.055),
('NIU-1003', 'BN-000003', 'FretCam', 'fret_admin', crypt('pass123', gen_salt('bf')), 'info@fretcam.cm', 11.511, 3.848),
('NIU-1004', 'BN-000004', 'MondialRelay', 'mondial_user', crypt('pass123', gen_salt('bf')), 'support@mondial.cm', 11.520, 3.850),
('NIU-1005', 'BN-000005', 'SpeedCargo', 'speed_admin', crypt('pass123', gen_salt('bf')), 'direction@speedcargo.cm', 9.750, 4.060);

-- Insert Client
INSERT INTO Client (id_cni, login, password, nom, prenom, address_mail, contact) VALUES 
('CNI-111', 'jean_dupont', crypt('pwd1', gen_salt('bf')), 'Dupont', 'Jean', 'jean.d@mail.com', '690000001'),
('CNI-222', 'marie_curie', crypt('pwd2', gen_salt('bf')), 'Curie', 'Marie', 'marie.c@mail.com', '690000002'),
('CNI-333', 'paul_biya', crypt('pwd3', gen_salt('bf')), 'Biya', 'Paul', 'paul.b@mail.com', '690000003'),
('CNI-444', 'anne_z', crypt('pwd4', gen_salt('bf')), 'Zambo', 'Anne', 'anne.z@mail.com', '690000004'),
('CNI-555', 'luc_m', crypt('pwd5', gen_salt('bf')), 'Mbah', 'Luc', 'luc.m@mail.com', '690000005');

-- Insert Transporteur
INSERT INTO Transporteur (id_cni, nom_chauffeurs, login, password) VALUES 
('TR-001', 'Chauffeur Alain', 'alain_trans', crypt('trans1', gen_salt('bf'))),
('TR-002', 'Chauffeur Boris', 'boris_trans', crypt('trans2', gen_salt('bf'))),
('TR-003', 'Chauffeur Claude', 'claude_trans', crypt('trans3', gen_salt('bf'))),
('TR-004', 'Chauffeur David', 'david_trans', crypt('trans4', gen_salt('bf'))),
('TR-005', 'Chauffeur Eric', 'eric_trans', crypt('trans5', gen_salt('bf')));

-- Insert Colis
INSERT INTO Colis (id_colis, id_cni_client, id_cni_transporteur, nom_colis, poids_colis, valeur_colis, temperature_moyenne) VALUES 
('COL-001', 'CNI-111', 'TR-001', 'Médicaments', 5.5, 150000, 4.0),
('COL-002', 'CNI-222', 'TR-002', 'Poissons surgelés', 50.0, 75000, -18.0),
('COL-003', 'CNI-333', 'TR-003', 'Électronique', 12.0, 500000, 25.0),
('COL-004', 'CNI-444', 'TR-004', 'Fruits frais', 100.0, 30000, 10.0),
('COL-005', 'CNI-555', 'TR-005', 'Documents', 1.0, 5000, 25.0);

-- Insert Evenement_save (Générera l'horodatage automatiquement)
INSERT INTO Evenement_save (id_boite, media_1_url, temperature, humidite, pressions, lat, lon) VALUES 
('BN-000001', 'url_img_1.jpg', 4.2, 80.5, 1013.2, 4.0511, 9.7091),
('BN-000001', 'url_img_2.jpg', 4.5, 81.0, 1013.0, 4.0515, 9.7095),
('BN-000002', 'url_img_3.jpg', -17.5, 40.0, 1015.0, 3.8481, 11.5111),
('BN-000003', 'url_img_4.jpg', 24.5, 60.0, 1012.5, 3.8500, 11.5200),
('BN-000004', 'url_img_5.jpg', 10.2, 75.0, 1010.0, 4.0600, 9.7500);

-- Insert Agence_Utilisatrice
INSERT INTO Agence_Utilisatrice (NIU, id_cni, Nom_agence, login, password, addresse_mail, status) VALUES 
('AG-NIU-1', 'CNI-111', 'Agence Nord', 'ag_nord', crypt('pwd', gen_salt('bf')), 'nord@agence.cm', 'Actif'),
('AG-NIU-2', 'CNI-222', 'Agence Sud', 'ag_sud', crypt('pwd', gen_salt('bf')), 'sud@agence.cm', 'Actif'),
('AG-NIU-3', 'CNI-333', 'Agence Est', 'ag_est', crypt('pwd', gen_salt('bf')), 'est@agence.cm', 'Inactif'),
('AG-NIU-4', 'CNI-444', 'Agence Ouest', 'ag_ouest', crypt('pwd', gen_salt('bf')), 'ouest@agence.cm', 'Actif'),
('AG-NIU-5', 'CNI-555', 'Agence Centre', 'ag_centre', crypt('pwd', gen_salt('bf')), 'centre@agence.cm', 'Actif');

-- Insert Abonner
INSERT INTO Abonner (id_boite, id_cni, type_a, debut_a, status, frais) VALUES 
('BN-000001', 'CNI-111', 'Premium', '2026-06-01', 'Actif', 15000),
('BN-000002', 'CNI-222', 'Standard', '2026-06-05', 'Actif', 5000),
('BN-000003', 'CNI-333', 'Premium', '2026-01-10', 'Expiré', 15000),
('BN-000004', 'CNI-444', 'Basic', '2026-06-10', 'Actif', 2000),
('BN-000005', 'CNI-555', 'Premium', '2026-06-12', 'Actif', 15000);
-- ==============================================================================
--  ARGOS DATABASE SCHEMA (Formatage Complet & Initialisation)
-- ==============================================================================

-- 1. CRÉATION DU SCHÉMA USER-LOCAL SI NÉCESSAIRE
DO $$ BEGIN
    EXECUTE 'CREATE SCHEMA IF NOT EXISTS ' || quote_ident(CURRENT_USER);
END $$;

SET search_path = brady, public;

-- 2. EXTENSIONS REQUISES
-- Aucun module SQL externe requis : les mots de passe sont hachés dans le code Flask.

-- ==============================================================================
--  TABLES DES ACTEURS (MULTI-TENANT)
-- ==============================================================================

-- Superadmin (Accès global)
CREATE TABLE superadmin (
    id SERIAL PRIMARY KEY,
    login VARCHAR(100) UNIQUE NOT NULL,
    password TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Propriétaires de Conteneurs (Entreprises / Compagnies)
CREATE TABLE proprietaire_conteneur (
    id SERIAL PRIMARY KEY,
    niu VARCHAR(50) UNIQUE,
    nom_agence VARCHAR(255) NOT NULL,
    login VARCHAR(100) UNIQUE NOT NULL,
    password TEXT NOT NULL,
    addresse_mail VARCHAR(255),
    lieu_residence VARCHAR(255),
    lat FLOAT DEFAULT 0.0,
    lon FLOAT DEFAULT 0.0,
    nbr_boite INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Agence Utilisatrice (Table de support / Legacy)
CREATE TABLE agence_utilisatrice (
    niu VARCHAR(50) PRIMARY KEY,
    nom_agence VARCHAR(255) NOT NULL,
    login VARCHAR(100) UNIQUE NOT NULL,
    password TEXT NOT NULL,
    addresse_mail VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Clients (Expéditeurs / Destinataires de Colis)
CREATE TABLE client (
    id_cni VARCHAR(50) PRIMARY KEY,
    login VARCHAR(100) UNIQUE NOT NULL,
    password TEXT NOT NULL,
    nom VARCHAR(150),
    prenom VARCHAR(150),
    address_mail VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Transporteurs (Chauffeurs)
CREATE TABLE transporteur (
    id_cni VARCHAR(50) PRIMARY KEY,
    login VARCHAR(100) UNIQUE NOT NULL,
    password TEXT NOT NULL,
    nom VARCHAR(150),
    prenom VARCHAR(150),
    contact VARCHAR(50),
    id_boite TEXT,
    blocked BOOLEAN DEFAULT FALSE,
    id_boites TEXT DEFAULT '[]',
    cni_file TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ==============================================================================
--  TABLES MATÉRIELLES (CONTENEURS & IOT)
-- ==============================================================================

-- Conteneurs physiques
CREATE TABLE conteneurs (
    id_conteneurs VARCHAR(100) PRIMARY KEY,
    taile_perimetre VARCHAR(100),
    type_conteneurs VARCHAR(100),
    status VARCHAR(20) DEFAULT 'ok', -- IMPORTANT: VARCHAR et non BOOLEAN
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Boîtes Noires (IoT) - Le lien crucial avec le propriétaire
CREATE TABLE boite_noir (
    id_boite SERIAL PRIMARY KEY,
    id_conteneurs VARCHAR(100) REFERENCES conteneurs(id_conteneurs) ON DELETE SET NULL,
    id_proprietaire INTEGER REFERENCES proprietaire_conteneur(id) ON DELETE CASCADE,
    type_boite VARCHAR(50) DEFAULT 'monthly',
    versions VARCHAR(50) DEFAULT 'v1.0',
    log_action VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ==============================================================================
--  TABLES LOGISTIQUES (ABONNEMENTS & COLIS)
-- ==============================================================================

-- Abonnements (Liaison Client <-> Boîte Noire)
CREATE TABLE abonner (
    numero_a SERIAL PRIMARY KEY,
    id_cni VARCHAR(50) REFERENCES client(id_cni) ON DELETE CASCADE,
    id_boite INTEGER REFERENCES boite_noir(id_boite) ON DELETE CASCADE,
    type_abonnement VARCHAR(100),
    status VARCHAR(50) DEFAULT 'Actif',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Colis en transit
CREATE TABLE colis (
    id_colis SERIAL PRIMARY KEY,
    id_cni_client VARCHAR(50) REFERENCES client(id_cni) ON DELETE CASCADE,
    id_cni_transporteur VARCHAR(50) REFERENCES transporteur(id_cni) ON DELETE SET NULL,
    num_plom VARCHAR(100),
    desc_colis TEXT,
    destination VARCHAR(255) NOT NULL,
    status VARCHAR(50) DEFAULT 'En Transit',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ==============================================================================
--  TABLES TÉLÉMÉTRIE, ALERTES & SÉCURITÉ
-- ==============================================================================

-- Événements envoyés par l'ESP32/Arduino
CREATE TABLE evenement_save (
    id_eventinit SERIAL PRIMARY KEY,
    horodatage TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    id_boite INTEGER REFERENCES boite_noir(id_boite) ON DELETE CASCADE,
    temperature FLOAT,
    humidite FLOAT,
    pressions FLOAT,
    chocs FLOAT,
    vitesse FLOAT,
    lat FLOAT,
    lon FLOAT,
    log_action VARCHAR(255),
    notif TEXT, -- Format JSON (ex: '["Température trop haute", "Choc violent"]')
    media_1_url VARCHAR(255),
    media_2_url VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Seuils d'alerte configurables par boîte
CREATE TABLE seuils_alerte (
    id_boite INTEGER PRIMARY KEY REFERENCES boite_noir(id_boite) ON DELETE CASCADE,
    temp_max FLOAT DEFAULT 32.0,
    temp_min FLOAT DEFAULT -10.0,
    humi_max FLOAT DEFAULT 75.0,
    choc_max FLOAT DEFAULT 5.0,
    pression_min FLOAT DEFAULT 995.0,
    vitesse_max FLOAT DEFAULT 90.0,
    angle_max FLOAT DEFAULT 30.0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Système de Notifications & Demandes de Vidage
CREATE TABLE notifications (
    id SERIAL PRIMARY KEY,
    type VARCHAR(50) NOT NULL, -- ex: 'VIDAGE_REQUEST', 'SECURITY_ALERT'
    message TEXT NOT NULL,
    cible_role VARCHAR(50) NOT NULL, -- ex: 'all', 'owner', ou un user_id
    id_boite INTEGER REFERENCES boite_noir(id_boite) ON DELETE CASCADE,
    initiator_id VARCHAR(100),
    status VARCHAR(20) DEFAULT 'unread',
    horodatage TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ==============================================================================
--  TABLES DE COMMUNICATIONS & ARCHIVES
-- ==============================================================================

-- Blockchain ARGOS (Scellage immuable)
CREATE TABLE blockchain_argos (
    block_index SERIAL PRIMARY KEY,
    previous_hash TEXT NOT NULL,
    block_hash TEXT NOT NULL UNIQUE,
    horodatage TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    event_type VARCHAR(100) NOT NULL,
    id_boite INTEGER, -- Peut être NULL pour des événements globaux
    payload TEXT NOT NULL -- Données scellées en JSON
);

-- Publications (Blog / Annonces internes)
CREATE TABLE publications (
    id SERIAL PRIMARY KEY,
    titre VARCHAR(255) NOT NULL,
    niveau VARCHAR(50),
    contenu TEXT NOT NULL,
    cible VARCHAR(100),
    date_pub TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ==============================================================================
--  INDEX D'OPTIMISATION (Pour des requêtes rapides)
-- ==============================================================================
CREATE INDEX idx_boite_proprietaire ON boite_noir(id_proprietaire);
CREATE INDEX idx_evenement_boite ON evenement_save(id_boite);
CREATE INDEX idx_evenement_horodatage ON evenement_save(horodatage DESC);
CREATE INDEX idx_colis_client ON colis(id_cni_client);
CREATE INDEX idx_abonner_client ON abonner(id_cni);

-- ==============================================================================
--  INSERTION PAR DÉFAUT (Pour se connecter immédiatement)
-- ==============================================================================

-- Création du compte superadmin par défaut
-- Identifiant : superadmin | Mot de passe : admin123
INSERT INTO superadmin (login, password) 
VALUES ('superadmin', 'scrypt:32768:8:1$2Rx3Mv5Dpc5WH80w$2e32a5a8fd0dd1632f727d646baef2aadc66da0b71c7c4a5ad4a8d8374aac5371417f6334d4fa2e12a644fb3c0b6310bd4e7a9068796bf260f262be99a7cc53b');
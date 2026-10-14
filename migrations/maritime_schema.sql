-- ARGOS v4.0 - Extension Maritime
-- Référentiel : ISO 6346 (BIC), IMO, UN/LOCODE.

CREATE TABLE IF NOT EXISTS bic_owner_prefix (
    prefix        CHAR(4) PRIMARY KEY,
    company_name  VARCHAR(200) NOT NULL,
    country_code  CHAR(2),
    bic_verified  BOOLEAN DEFAULT FALSE,
    updated_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS container_specs_bic (
    container_number    CHAR(11) PRIMARY KEY,
    owner_prefix        CHAR(4) REFERENCES bic_owner_prefix(prefix),
    type_code           VARCHAR(6),
    max_gross_mass_kg   NUMERIC(10,2),
    tare_mass_kg        NUMERIC(10,2),
    net_mass_kg         NUMERIC(10,2) GENERATED ALWAYS AS (max_gross_mass_kg - tare_mass_kg) STORED,
    internal_length_mm  INTEGER,
    internal_width_mm   INTEGER,
    internal_height_mm  INTEGER,
    external_length_mm  INTEGER,
    external_width_mm   INTEGER,
    external_height_mm  INTEGER,
    door_width_mm       INTEGER,
    door_height_mm      INTEGER,
    capacity_m3         NUMERIC(8,3),
    manufacture_year    INTEGER,
    bic_fetch_ts        TIMESTAMPTZ DEFAULT NOW(),
    bic_raw_response    JSONB
);

CREATE TABLE IF NOT EXISTS vessel (
    imo_number     CHAR(9) PRIMARY KEY,
    vessel_name    VARCHAR(200) NOT NULL,
    vessel_type    VARCHAR(100),
    flag_code      CHAR(2),
    call_sign      VARCHAR(10),
    mmsi           CHAR(9),
    gross_tonnage  INTEGER,
    operator_name  VARCHAR(200),
    ais_source     VARCHAR(50) DEFAULT 'manual',
    updated_at     TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS port (
    locode        VARCHAR(7) PRIMARY KEY,
    port_name     VARCHAR(200) NOT NULL,
    country_code  CHAR(2) NOT NULL,
    lat           NUMERIC(9,6),
    lon           NUMERIC(9,6),
    timezone      VARCHAR(50),
    has_argos     BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS maritime_voyage (
    id                  SERIAL PRIMARY KEY,
    voyage_number       VARCHAR(50) NOT NULL,
    imo_number          CHAR(9) REFERENCES vessel(imo_number),
    bl_number           VARCHAR(100),
    booking_reference   VARCHAR(100),
    pol_locode          VARCHAR(7) REFERENCES port(locode),
    pod_locode          VARCHAR(7) REFERENCES port(locode),
    etd                 TIMESTAMPTZ,
    atd                 TIMESTAMPTZ,
    eta                 TIMESTAMPTZ,
    ata                 TIMESTAMPTZ,
    shipping_line       VARCHAR(100),
    tracking_api_id     VARCHAR(200),
    tracking_provider   VARCHAR(50),
    voyage_status       VARCHAR(50) DEFAULT 'planned',
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS container_voyage_assignment (
    id                  SERIAL PRIMARY KEY,
    container_number    CHAR(11) REFERENCES container_specs_bic(container_number),
    id_boite            VARCHAR(15),
    voyage_id           INTEGER REFERENCES maritime_voyage(id),
    seal_number         VARCHAR(50),
    stuffing_date       TIMESTAMPTZ,
    stripping_date      TIMESTAMPTZ,
    cargo_description   TEXT,
    hs_code             VARCHAR(10),
    customs_status      VARCHAR(50) DEFAULT 'pending',
    customs_cleared_by  VARCHAR(100),
    customs_cleared_at  TIMESTAMPTZ,
    assigned_at         TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (container_number, voyage_id)
);

CREATE TABLE IF NOT EXISTS ais_position (
    id            BIGSERIAL PRIMARY KEY,
    imo_number    CHAR(9) REFERENCES vessel(imo_number),
    ts            TIMESTAMPTZ NOT NULL,
    lat           NUMERIC(9,6) NOT NULL,
    lon           NUMERIC(9,6) NOT NULL,
    speed_knots   NUMERIC(5,2),
    heading_deg   SMALLINT,
    nav_status    VARCHAR(50),
    source        VARCHAR(50) DEFAULT 'ais'
);

CREATE INDEX IF NOT EXISTS idx_ais_imo_ts ON ais_position (imo_number, ts DESC);

CREATE TABLE IF NOT EXISTS litige_alerte (
    id                   SERIAL PRIMARY KEY,
    id_boite             VARCHAR(15) NOT NULL,
    container_number     CHAR(11),
    voyage_id            INTEGER REFERENCES maritime_voyage(id),
    iot_event_id         INTEGER,
    event_ts             TIMESTAMPTZ NOT NULL,
    alert_type           VARCHAR(100),
    alert_values         JSONB,
    iot_lat              NUMERIC(9,6),
    iot_lon              NUMERIC(9,6),
    ais_lat              NUMERIC(9,6),
    ais_lon              NUMERIC(9,6),
    position_source      VARCHAR(20),
    vessel_name          VARCHAR(200),
    nearest_port_locode  VARCHAR(7),
    distance_to_port_nm  NUMERIC(8,2),
    litige_status        VARCHAR(50) DEFAULT 'open',
    created_at           TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS port_authority_user (
    id              SERIAL PRIMARY KEY,
    login           VARCHAR(100) UNIQUE NOT NULL,
    password        TEXT NOT NULL,
    full_name       VARCHAR(200),
    port_locode     VARCHAR(7) REFERENCES port(locode),
    authority_type  VARCHAR(50),
    permissions     TEXT[],
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

INSERT INTO port (locode, port_name, country_code, lat, lon, timezone, has_argos)
VALUES
    ('CMDLE', 'Port Autonome de Douala', 'CM', 4.0511, 9.7085, 'Africa/Douala', TRUE),
    ('CMKBI', 'Port de Kribi', 'CM', 2.9394, 9.9072, 'Africa/Douala', FALSE),
    ('NGAPP', 'Apapa Port Lagos', 'NG', 6.4500, 3.3667, 'Africa/Lagos', FALSE),
    ('GHACC', 'Tema Port', 'GH', 5.6037, -0.0174, 'Africa/Accra', FALSE),
    ('FRFOS', 'Port de Marseille-Fos', 'FR', 43.3369, 4.8564, 'Europe/Paris', FALSE),
    ('BEANR', 'Port d''Anvers', 'BE', 51.2213, 4.4051, 'Europe/Brussels', FALSE),
    ('CNSHA', 'Shanghai Port', 'CN', 31.2304, 121.4737, 'Asia/Shanghai', FALSE),
    ('SGSIN', 'Port of Singapore', 'SG', 1.2897, 103.8501, 'Asia/Singapore', FALSE)
ON CONFLICT DO NOTHING;

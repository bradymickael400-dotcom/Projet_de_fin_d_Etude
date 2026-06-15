--
-- PostgreSQL database dump
--

\restrict KEDkCzc7P1yw5H26QjpYvxgUaJ65NbhqDO9Hc2Fu62eKNbq5hhAybhQ5HUjf8Tn

-- Dumped from database version 16.14 (Ubuntu 16.14-0ubuntu0.24.04.1)
-- Dumped by pg_dump version 16.14 (Ubuntu 16.14-0ubuntu0.24.04.1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: timescaledb; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS timescaledb WITH SCHEMA public;


--
-- Name: EXTENSION timescaledb; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION timescaledb IS 'Enables scalable inserts and complex queries for time-series data (Community Edition)';


--
-- Name: pgcrypto; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA public;


--
-- Name: EXTENSION pgcrypto; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION pgcrypto IS 'cryptographic functions';


--
-- Name: update_timestamp_column(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.update_timestamp_column() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;


ALTER FUNCTION public.update_timestamp_column() OWNER TO postgres;

--
-- Name: update_updated_at_column(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.update_updated_at_column() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$;


ALTER FUNCTION public.update_updated_at_column() OWNER TO postgres;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: evenement_save; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.evenement_save (
    id_eventinit integer NOT NULL,
    horodatage timestamp with time zone DEFAULT now() NOT NULL,
    id_boite character varying(15),
    media_1_url text,
    media_2_url text,
    temperature numeric(5,2),
    humidite numeric(5,2),
    pressions numeric(6,2),
    lat numeric(9,6),
    lon numeric(9,6),
    created_at timestamp with time zone DEFAULT now(),
    log_action character varying(255) DEFAULT 'Enregistrement Capteur'::character varying,
    vitesse numeric(5,2),
    notif text,
    chocs numeric(5,2)
);


ALTER TABLE public.evenement_save OWNER TO postgres;

--
-- Name: _hyper_6_3_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_6_3_chunk (
    CONSTRAINT constraint_3 CHECK (((horodatage >= '2026-06-11 01:00:00+01'::timestamp with time zone) AND (horodatage < '2026-06-18 01:00:00+01'::timestamp with time zone)))
)
INHERITS (public.evenement_save);


ALTER TABLE _timescaledb_internal._hyper_6_3_chunk OWNER TO postgres;

--
-- Name: abonner; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.abonner (
    numero_a integer NOT NULL,
    id_boite character varying(15),
    id_cni character varying(50),
    type_a character varying(50),
    debut_a date,
    fin_a date,
    status character varying(50),
    frais numeric(10,2),
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    log_action character varying(255) DEFAULT 'Création'::character varying,
    img_inventaire text
);


ALTER TABLE public.abonner OWNER TO postgres;

--
-- Name: abonner_numero_a_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.abonner_numero_a_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.abonner_numero_a_seq OWNER TO postgres;

--
-- Name: abonner_numero_a_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.abonner_numero_a_seq OWNED BY public.abonner.numero_a;


--
-- Name: agence_utilisatrice; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.agence_utilisatrice (
    niu character varying(50) NOT NULL,
    id_cni character varying(50),
    nom_agence character varying(100),
    login character varying(50) NOT NULL,
    password text NOT NULL,
    addresse_mail character varying(100) NOT NULL,
    lieu_residence character varying(150),
    lat numeric(9,6),
    lon numeric(9,6),
    status character varying(50),
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    log_action character varying(255) DEFAULT 'Création'::character varying
);


ALTER TABLE public.agence_utilisatrice OWNER TO postgres;

--
-- Name: seq_boite_noir; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.seq_boite_noir
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.seq_boite_noir OWNER TO postgres;

--
-- Name: boite_noir; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.boite_noir (
    id_boite character varying(15) DEFAULT ('BN-'::text || lpad((nextval('public.seq_boite_noir'::regclass))::text, 6, '0'::text)) NOT NULL,
    id_conteneurs character varying(50),
    type_boite character varying(50),
    versions character varying(50),
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    log_action character varying(255) DEFAULT 'Création'::character varying
);


ALTER TABLE public.boite_noir OWNER TO postgres;

--
-- Name: boite_noir_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.boite_noir_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.boite_noir_seq OWNER TO postgres;

--
-- Name: client; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.client (
    id_cni character varying(50) NOT NULL,
    login character varying(50) NOT NULL,
    password text NOT NULL,
    nom character varying(100),
    prenom character varying(100),
    date_reception_expedition date,
    address_mail character varying(100) NOT NULL,
    contact character varying(20),
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    log_action character varying(255) DEFAULT 'Création'::character varying
);


ALTER TABLE public.client OWNER TO postgres;

--
-- Name: colis; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.colis (
    id_colis character varying(50) NOT NULL,
    id_cni_client character varying(50),
    id_cni_transporteur character varying(50),
    nom_colis character varying(100),
    poids_colis numeric(8,2),
    valeur_colis numeric(12,2),
    temperature_moyenne numeric(5,2),
    lieux_expedition character varying(150),
    lieux_receptions character varying(150),
    date_heure_exp timestamp with time zone,
    date_heure_reception timestamp with time zone,
    moyen_transport character varying(50),
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    log_action character varying(255) DEFAULT 'Création'::character varying,
    type_colis character varying(15)
);


ALTER TABLE public.colis OWNER TO postgres;

--
-- Name: conteneurs; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.conteneurs (
    id_conteneurs character varying(50) NOT NULL,
    resistance character varying(50),
    taile_perimetre character varying(50),
    type_conteneurs character varying(50),
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    log_action character varying(255) DEFAULT 'Création'::character varying,
    status boolean DEFAULT false
);


ALTER TABLE public.conteneurs OWNER TO postgres;

--
-- Name: evenement_save_id_eventinit_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.evenement_save_id_eventinit_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.evenement_save_id_eventinit_seq OWNER TO postgres;

--
-- Name: evenement_save_id_eventinit_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.evenement_save_id_eventinit_seq OWNED BY public.evenement_save.id_eventinit;


--
-- Name: proprietaire_conteneur; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.proprietaire_conteneur (
    id integer NOT NULL,
    niu character varying(50) NOT NULL,
    id_boite character varying(15),
    nom_agence character varying(100),
    login character varying(50) NOT NULL,
    password text NOT NULL,
    addresse_mail character varying(100) NOT NULL,
    lieu_residence character varying(100),
    lon numeric(9,6),
    lat numeric(9,6),
    nbr_boite integer DEFAULT 0,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    log_action character varying(255) DEFAULT 'Création'::character varying
);


ALTER TABLE public.proprietaire_conteneur OWNER TO postgres;

--
-- Name: proprietaire_conteneur_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.proprietaire_conteneur_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.proprietaire_conteneur_id_seq OWNER TO postgres;

--
-- Name: proprietaire_conteneur_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.proprietaire_conteneur_id_seq OWNED BY public.proprietaire_conteneur.id;


--
-- Name: seq_colis; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.seq_colis
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.seq_colis OWNER TO postgres;

--
-- Name: seq_conteneurs; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.seq_conteneurs
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.seq_conteneurs OWNER TO postgres;

--
-- Name: seq_super_admin; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.seq_super_admin
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.seq_super_admin OWNER TO postgres;

--
-- Name: seq_transporteur; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.seq_transporteur
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.seq_transporteur OWNER TO postgres;

--
-- Name: seuils_alerte; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.seuils_alerte (
    id integer NOT NULL,
    id_boite character varying(15),
    temp_max numeric(5,2) DEFAULT 32,
    humi_max numeric(5,2) DEFAULT 75,
    choc_max numeric(5,2) DEFAULT 5,
    pression_min numeric(7,2) DEFAULT 995,
    vitesse_max numeric(5,2) DEFAULT 90,
    angle_max numeric(5,2) DEFAULT 30,
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.seuils_alerte OWNER TO postgres;

--
-- Name: seuils_alerte_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.seuils_alerte_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.seuils_alerte_id_seq OWNER TO postgres;

--
-- Name: seuils_alerte_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.seuils_alerte_id_seq OWNED BY public.seuils_alerte.id;


--
-- Name: superadmin; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.superadmin (
    id integer NOT NULL,
    id_cni character varying(50),
    login character varying(50) NOT NULL,
    password text NOT NULL,
    dd_pass date,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    log_action character varying(255) DEFAULT 'Création'::character varying
);


ALTER TABLE public.superadmin OWNER TO postgres;

--
-- Name: superadmin_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.superadmin_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.superadmin_id_seq OWNER TO postgres;

--
-- Name: superadmin_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.superadmin_id_seq OWNED BY public.superadmin.id;


--
-- Name: transporteur; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.transporteur (
    id_cni character varying(50) NOT NULL,
    nom_chauffeurs character varying(150),
    login character varying(50) NOT NULL,
    password text NOT NULL,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    log_action character varying(255) DEFAULT 'Création'::character varying
);


ALTER TABLE public.transporteur OWNER TO postgres;

--
-- Name: _hyper_6_3_chunk id_eventinit; Type: DEFAULT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_6_3_chunk ALTER COLUMN id_eventinit SET DEFAULT nextval('public.evenement_save_id_eventinit_seq'::regclass);


--
-- Name: _hyper_6_3_chunk horodatage; Type: DEFAULT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_6_3_chunk ALTER COLUMN horodatage SET DEFAULT now();


--
-- Name: _hyper_6_3_chunk created_at; Type: DEFAULT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_6_3_chunk ALTER COLUMN created_at SET DEFAULT now();


--
-- Name: _hyper_6_3_chunk log_action; Type: DEFAULT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_6_3_chunk ALTER COLUMN log_action SET DEFAULT 'Enregistrement Capteur'::character varying;


--
-- Name: abonner numero_a; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.abonner ALTER COLUMN numero_a SET DEFAULT nextval('public.abonner_numero_a_seq'::regclass);


--
-- Name: evenement_save id_eventinit; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.evenement_save ALTER COLUMN id_eventinit SET DEFAULT nextval('public.evenement_save_id_eventinit_seq'::regclass);


--
-- Name: proprietaire_conteneur id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.proprietaire_conteneur ALTER COLUMN id SET DEFAULT nextval('public.proprietaire_conteneur_id_seq'::regclass);


--
-- Name: seuils_alerte id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.seuils_alerte ALTER COLUMN id SET DEFAULT nextval('public.seuils_alerte_id_seq'::regclass);


--
-- Name: superadmin id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.superadmin ALTER COLUMN id SET DEFAULT nextval('public.superadmin_id_seq'::regclass);


--
-- Data for Name: hypertable; Type: TABLE DATA; Schema: _timescaledb_catalog; Owner: postgres
--

COPY _timescaledb_catalog.hypertable (id, schema_name, table_name, associated_schema_name, associated_table_prefix, num_dimensions, chunk_sizing_func_schema, chunk_sizing_func_name, chunk_target_size, compression_state, compressed_hypertable_id, status) FROM stdin;
6	public	evenement_save	_timescaledb_internal	_hyper_6	1	_timescaledb_functions	calculate_chunk_interval	0	0	\N	0
\.


--
-- Data for Name: bgw_job; Type: TABLE DATA; Schema: _timescaledb_catalog; Owner: postgres
--

COPY _timescaledb_catalog.bgw_job (id, application_name, schedule_interval, max_runtime, max_retries, retry_period, proc_schema, proc_name, owner, scheduled, fixed_schedule, initial_start, hypertable_id, config, check_schema, check_name, timezone) FROM stdin;
\.


--
-- Data for Name: chunk; Type: TABLE DATA; Schema: _timescaledb_catalog; Owner: postgres
--

COPY _timescaledb_catalog.chunk (id, hypertable_id, schema_name, table_name, compressed_chunk_id, status, osm_chunk, creation_time) FROM stdin;
3	6	_timescaledb_internal	_hyper_6_3_chunk	\N	0	f	2026-06-13 00:37:39.893167+01
\.


--
-- Data for Name: chunk_column_stats; Type: TABLE DATA; Schema: _timescaledb_catalog; Owner: postgres
--

COPY _timescaledb_catalog.chunk_column_stats (id, hypertable_id, chunk_id, column_name, range_start, range_end, valid) FROM stdin;
\.


--
-- Data for Name: dimension; Type: TABLE DATA; Schema: _timescaledb_catalog; Owner: postgres
--

COPY _timescaledb_catalog.dimension (id, hypertable_id, column_name, column_type, aligned, num_slices, partitioning_func_schema, partitioning_func, interval_length, compress_interval_length, integer_now_func_schema, integer_now_func) FROM stdin;
6	6	horodatage	timestamp with time zone	t	\N	\N	\N	604800000000	\N	\N	\N
\.


--
-- Data for Name: dimension_slice; Type: TABLE DATA; Schema: _timescaledb_catalog; Owner: postgres
--

COPY _timescaledb_catalog.dimension_slice (id, dimension_id, range_start, range_end) FROM stdin;
3	6	1781136000000000	1781740800000000
\.


--
-- Data for Name: chunk_constraint; Type: TABLE DATA; Schema: _timescaledb_catalog; Owner: postgres
--

COPY _timescaledb_catalog.chunk_constraint (chunk_id, dimension_slice_id, constraint_name, hypertable_constraint_name) FROM stdin;
3	3	constraint_3	\N
3	\N	3_5_evenement_save_id_boite_fkey	evenement_save_id_boite_fkey
3	\N	3_6_evenement_save_pkey	evenement_save_pkey
\.


--
-- Data for Name: compression_chunk_size; Type: TABLE DATA; Schema: _timescaledb_catalog; Owner: postgres
--

COPY _timescaledb_catalog.compression_chunk_size (chunk_id, compressed_chunk_id, uncompressed_heap_size, uncompressed_toast_size, uncompressed_index_size, compressed_heap_size, compressed_toast_size, compressed_index_size, numrows_pre_compression, numrows_post_compression, numrows_frozen_immediately) FROM stdin;
\.


--
-- Data for Name: compression_settings; Type: TABLE DATA; Schema: _timescaledb_catalog; Owner: postgres
--

COPY _timescaledb_catalog.compression_settings (relid, compress_relid, segmentby, orderby, orderby_desc, orderby_nullsfirst, index) FROM stdin;
\.


--
-- Data for Name: continuous_agg; Type: TABLE DATA; Schema: _timescaledb_catalog; Owner: postgres
--

COPY _timescaledb_catalog.continuous_agg (mat_hypertable_id, raw_hypertable_id, parent_mat_hypertable_id, user_view_schema, user_view_name, partial_view_schema, partial_view_name, direct_view_schema, direct_view_name, materialized_only) FROM stdin;
\.


--
-- Data for Name: continuous_aggs_bucket_function; Type: TABLE DATA; Schema: _timescaledb_catalog; Owner: postgres
--

COPY _timescaledb_catalog.continuous_aggs_bucket_function (mat_hypertable_id, bucket_func, bucket_width, bucket_origin, bucket_offset, bucket_timezone, bucket_fixed_width) FROM stdin;
\.


--
-- Data for Name: continuous_aggs_hypertable_invalidation_log; Type: TABLE DATA; Schema: _timescaledb_catalog; Owner: postgres
--

COPY _timescaledb_catalog.continuous_aggs_hypertable_invalidation_log (hypertable_id, lowest_modified_value, greatest_modified_value) FROM stdin;
\.


--
-- Data for Name: continuous_aggs_invalidation_threshold; Type: TABLE DATA; Schema: _timescaledb_catalog; Owner: postgres
--

COPY _timescaledb_catalog.continuous_aggs_invalidation_threshold (hypertable_id, watermark) FROM stdin;
\.


--
-- Data for Name: continuous_aggs_jobs_refresh_ranges; Type: TABLE DATA; Schema: _timescaledb_catalog; Owner: postgres
--

COPY _timescaledb_catalog.continuous_aggs_jobs_refresh_ranges (materialization_id, start_range, end_range, pid, job_id, created_at) FROM stdin;
\.


--
-- Data for Name: continuous_aggs_materialization_invalidation_log; Type: TABLE DATA; Schema: _timescaledb_catalog; Owner: postgres
--

COPY _timescaledb_catalog.continuous_aggs_materialization_invalidation_log (materialization_id, lowest_modified_value, greatest_modified_value) FROM stdin;
\.


--
-- Data for Name: continuous_aggs_materialization_ranges; Type: TABLE DATA; Schema: _timescaledb_catalog; Owner: postgres
--

COPY _timescaledb_catalog.continuous_aggs_materialization_ranges (materialization_id, lowest_modified_value, greatest_modified_value) FROM stdin;
\.


--
-- Data for Name: continuous_aggs_watermark; Type: TABLE DATA; Schema: _timescaledb_catalog; Owner: postgres
--

COPY _timescaledb_catalog.continuous_aggs_watermark (mat_hypertable_id, watermark) FROM stdin;
\.


--
-- Data for Name: metadata; Type: TABLE DATA; Schema: _timescaledb_catalog; Owner: postgres
--

COPY _timescaledb_catalog.metadata (key, value, include_in_telemetry) FROM stdin;
install_timestamp	2026-06-11 03:17:16.731364+01	t
timescaledb_version	2.27.2	f
exported_uuid	9efdab19-d37e-40ca-96e2-d0809fb2f8f4	t
\.


--
-- Data for Name: tablespace; Type: TABLE DATA; Schema: _timescaledb_catalog; Owner: postgres
--

COPY _timescaledb_catalog.tablespace (id, hypertable_id, tablespace_name) FROM stdin;
\.


--
-- Data for Name: _hyper_6_3_chunk; Type: TABLE DATA; Schema: _timescaledb_internal; Owner: postgres
--

COPY _timescaledb_internal._hyper_6_3_chunk (id_eventinit, horodatage, id_boite, media_1_url, media_2_url, temperature, humidite, pressions, lat, lon, created_at, log_action, vitesse, notif, chocs) FROM stdin;
6	2026-06-13 00:37:39.892699+01	BN-000001	url_img_1.jpg	\N	4.20	80.50	1013.20	4.051100	9.709100	2026-06-13 00:37:39.892699+01	Enregistrement Capteur	\N	\N	\N
7	2026-06-13 00:37:39.892699+01	BN-000001	url_img_2.jpg	\N	4.50	81.00	1013.00	4.051500	9.709500	2026-06-13 00:37:39.892699+01	Enregistrement Capteur	\N	\N	\N
8	2026-06-13 00:37:39.892699+01	BN-000002	url_img_3.jpg	\N	-17.50	40.00	1015.00	3.848100	11.511100	2026-06-13 00:37:39.892699+01	Enregistrement Capteur	\N	\N	\N
9	2026-06-13 00:37:39.892699+01	BN-000003	url_img_4.jpg	\N	24.50	60.00	1012.50	3.850000	11.520000	2026-06-13 00:37:39.892699+01	Enregistrement Capteur	\N	\N	\N
10	2026-06-13 00:37:39.892699+01	BN-000004	url_img_5.jpg	\N	10.20	75.00	1010.00	4.060000	9.750000	2026-06-13 00:37:39.892699+01	Enregistrement Capteur	\N	\N	\N
11	2026-06-13 00:37:59.76726+01	BN-000001	url_img_1.jpg	\N	4.20	80.50	1013.20	4.051100	9.709100	2026-06-13 00:37:59.76726+01	Enregistrement Capteur	\N	\N	\N
12	2026-06-13 00:37:59.76726+01	BN-000001	url_img_2.jpg	\N	4.50	81.00	1013.00	4.051500	9.709500	2026-06-13 00:37:59.76726+01	Enregistrement Capteur	\N	\N	\N
13	2026-06-13 00:37:59.76726+01	BN-000002	url_img_3.jpg	\N	-17.50	40.00	1015.00	3.848100	11.511100	2026-06-13 00:37:59.76726+01	Enregistrement Capteur	\N	\N	\N
14	2026-06-13 00:37:59.76726+01	BN-000003	url_img_4.jpg	\N	24.50	60.00	1012.50	3.850000	11.520000	2026-06-13 00:37:59.76726+01	Enregistrement Capteur	\N	\N	\N
15	2026-06-13 00:37:59.76726+01	BN-000004	url_img_5.jpg	\N	10.20	75.00	1010.00	4.060000	9.750000	2026-06-13 00:37:59.76726+01	Enregistrement Capteur	\N	\N	\N
16	2026-06-15 01:29:58.0287+01	BN-000001	\N	\N	31.80	52.70	1013.20	4.986410	11.166770	2026-06-15 01:29:58.0287+01	Alerte générée	50.70	["Choc violent: 5.9G (Max: 5.0)"]	5.90
17	2026-06-15 01:30:00.038993+01	BN-000001	\N	\N	38.40	63.40	996.10	4.185140	10.546420	2026-06-15 01:30:00.038993+01	Alerte générée	78.60	["Temp\\u00e9rature critique: 38.4\\u00b0C (Max: 32.0)", "Choc violent: 5.8G (Max: 5.0)"]	5.80
18	2026-06-15 01:30:02.050328+01	BN-000001	\N	\N	33.20	75.20	1010.70	4.179950	10.314760	2026-06-15 01:30:02.050328+01	Alerte générée	69.70	["Temp\\u00e9rature critique: 33.2\\u00b0C (Max: 32.0)", "Humidit\\u00e9 critique: 75.2% (Max: 75.0)"]	3.30
19	2026-06-15 01:30:04.063077+01	BN-000001	\N	\N	39.10	64.80	996.80	5.273070	9.912150	2026-06-15 01:30:04.063077+01	Alerte générée	11.50	["Temp\\u00e9rature critique: 39.1\\u00b0C (Max: 32.0)"]	2.80
20	2026-06-15 01:30:06.071647+01	BN-000001	\N	\N	37.30	68.80	1003.80	5.015510	9.920070	2026-06-15 01:30:06.071647+01	Alerte générée	51.50	["Temp\\u00e9rature critique: 37.3\\u00b0C (Max: 32.0)"]	4.70
21	2026-06-15 01:30:08.081861+01	BN-000001	\N	\N	28.50	79.80	1002.20	4.771000	10.742750	2026-06-15 01:30:08.081861+01	Alerte générée	109.00	["Humidit\\u00e9 critique: 79.8% (Max: 75.0)", "Survitesse: 109.0km/h (Max: 90.0)"]	2.90
22	2026-06-15 01:30:10.092919+01	BN-000001	\N	\N	26.60	63.00	1000.00	4.426420	9.805310	2026-06-15 01:30:10.092919+01	Alerte générée	94.20	["Choc violent: 5.5G (Max: 5.0)", "Survitesse: 94.2km/h (Max: 90.0)"]	5.50
23	2026-06-15 01:30:12.103129+01	BN-000001	\N	\N	41.30	60.60	1002.00	4.970610	11.242850	2026-06-15 01:30:12.103129+01	Alerte générée	26.30	["Temp\\u00e9rature critique: 41.3\\u00b0C (Max: 32.0)", "Choc violent: 7.2G (Max: 5.0)"]	7.20
24	2026-06-15 01:30:14.113365+01	BN-000001	\N	\N	38.90	75.40	1004.80	4.798560	10.034640	2026-06-15 01:30:14.113365+01	Alerte générée	2.90	["Temp\\u00e9rature critique: 38.9\\u00b0C (Max: 32.0)", "Humidit\\u00e9 critique: 75.4% (Max: 75.0)", "Choc violent: 7.4G (Max: 5.0)"]	7.40
25	2026-06-15 01:30:16.123337+01	BN-000001	\N	\N	40.60	58.10	1010.70	5.117300	10.443590	2026-06-15 01:30:16.123337+01	Alerte générée	90.40	["Temp\\u00e9rature critique: 40.6\\u00b0C (Max: 32.0)", "Survitesse: 90.4km/h (Max: 90.0)"]	1.10
26	2026-06-15 01:30:18.130218+01	BN-000001	\N	\N	34.50	80.00	987.70	5.257850	10.213120	2026-06-15 01:30:18.130218+01	Alerte générée	84.20	["Temp\\u00e9rature critique: 34.5\\u00b0C (Max: 32.0)", "Humidit\\u00e9 critique: 80.0% (Max: 75.0)", "Pression basse: 987.7hPa (Min: 995.0)"]	0.30
27	2026-06-15 01:30:20.141752+01	BN-000001	\N	\N	33.60	73.60	1012.00	3.912060	10.049040	2026-06-15 01:30:20.141752+01	Alerte générée	15.90	["Temp\\u00e9rature critique: 33.6\\u00b0C (Max: 32.0)", "Choc violent: 7.9G (Max: 5.0)"]	7.90
28	2026-06-15 01:30:22.150639+01	BN-000001	\N	\N	37.30	82.40	991.90	4.406730	10.831080	2026-06-15 01:30:22.150639+01	Alerte générée	17.00	["Temp\\u00e9rature critique: 37.3\\u00b0C (Max: 32.0)", "Humidit\\u00e9 critique: 82.4% (Max: 75.0)", "Choc violent: 6.3G (Max: 5.0)", "Pression basse: 991.9hPa (Min: 995.0)"]	6.30
29	2026-06-15 01:30:24.160292+01	BN-000001	\N	\N	25.80	51.40	986.40	4.868820	9.990660	2026-06-15 01:30:24.160292+01	Alerte générée	57.70	["Choc violent: 6.4G (Max: 5.0)", "Pression basse: 986.4hPa (Min: 995.0)"]	6.40
30	2026-06-15 01:30:26.169793+01	BN-000001	\N	\N	28.70	83.70	1004.90	3.958810	11.054950	2026-06-15 01:30:26.169793+01	Alerte générée	38.10	["Humidit\\u00e9 critique: 83.7% (Max: 75.0)"]	3.40
31	2026-06-15 01:30:28.177181+01	BN-000001	\N	\N	25.20	59.30	983.60	4.680530	10.170380	2026-06-15 01:30:28.177181+01	Alerte générée	6.20	["Choc violent: 6.0G (Max: 5.0)", "Pression basse: 983.6hPa (Min: 995.0)"]	6.00
32	2026-06-15 01:30:30.187758+01	BN-000001	\N	\N	28.40	62.20	993.40	4.236370	11.047700	2026-06-15 01:30:30.187758+01	Alerte générée	90.20	["Pression basse: 993.4hPa (Min: 995.0)", "Survitesse: 90.2km/h (Max: 90.0)"]	4.50
33	2026-06-15 01:30:32.198988+01	BN-000001	\N	\N	32.30	50.90	985.20	4.319550	10.997450	2026-06-15 01:30:32.198988+01	Alerte générée	95.50	["Temp\\u00e9rature critique: 32.3\\u00b0C (Max: 32.0)", "Choc violent: 7.1G (Max: 5.0)", "Pression basse: 985.2hPa (Min: 995.0)", "Survitesse: 95.5km/h (Max: 90.0)"]	7.10
34	2026-06-15 01:30:34.210444+01	BN-000001	\N	\N	31.20	68.90	1010.90	3.970690	10.913290	2026-06-15 01:30:34.210444+01	Scan régulier	12.50	\N	4.40
35	2026-06-15 01:30:36.219037+01	BN-000001	\N	\N	28.50	63.80	995.50	5.148400	10.233590	2026-06-15 01:30:36.219037+01	Scan régulier	86.50	\N	2.00
36	2026-06-15 01:30:38.228212+01	BN-000001	\N	\N	30.10	77.30	1008.10	4.985160	11.418790	2026-06-15 01:30:38.228212+01	Alerte générée	69.60	["Humidit\\u00e9 critique: 77.3% (Max: 75.0)"]	4.00
37	2026-06-15 01:30:40.240919+01	BN-000001	\N	\N	35.60	77.20	999.40	3.803590	10.289910	2026-06-15 01:30:40.240919+01	Alerte générée	25.90	["Temp\\u00e9rature critique: 35.6\\u00b0C (Max: 32.0)", "Humidit\\u00e9 critique: 77.2% (Max: 75.0)"]	1.70
38	2026-06-15 01:30:42.252345+01	BN-000001	\N	\N	41.70	69.10	990.80	5.027840	10.515950	2026-06-15 01:30:42.252345+01	Alerte générée	39.00	["Temp\\u00e9rature critique: 41.7\\u00b0C (Max: 32.0)", "Pression basse: 990.8hPa (Min: 995.0)"]	2.40
39	2026-06-15 01:30:44.264502+01	BN-000001	\N	\N	28.90	53.80	981.20	4.911380	10.972150	2026-06-15 01:30:44.264502+01	Alerte générée	74.40	["Choc violent: 7.4G (Max: 5.0)", "Pression basse: 981.2hPa (Min: 995.0)"]	7.40
40	2026-06-15 01:30:46.275099+01	BN-000001	\N	\N	30.10	84.90	984.50	4.001840	10.504430	2026-06-15 01:30:46.275099+01	Alerte générée	98.90	["Humidit\\u00e9 critique: 84.9% (Max: 75.0)", "Choc violent: 5.7G (Max: 5.0)", "Pression basse: 984.5hPa (Min: 995.0)", "Survitesse: 98.9km/h (Max: 90.0)"]	5.70
\.


--
-- Data for Name: abonner; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.abonner (numero_a, id_boite, id_cni, type_a, debut_a, fin_a, status, frais, created_at, updated_at, log_action, img_inventaire) FROM stdin;
6	BN-000001	CNI-111	Premium	2026-06-01	\N	Actif	15000.00	2026-06-13 00:37:39.912223+01	2026-06-13 00:37:39.912223+01	Création	\N
7	BN-000002	CNI-222	Standard	2026-06-05	\N	Actif	5000.00	2026-06-13 00:37:39.912223+01	2026-06-13 00:37:39.912223+01	Création	\N
8	BN-000003	CNI-333	Premium	2026-01-10	\N	Expiré	15000.00	2026-06-13 00:37:39.912223+01	2026-06-13 00:37:39.912223+01	Création	\N
9	BN-000004	CNI-444	Basic	2026-06-10	\N	Actif	2000.00	2026-06-13 00:37:39.912223+01	2026-06-13 00:37:39.912223+01	Création	\N
10	BN-000005	CNI-555	Premium	2026-06-12	\N	Actif	15000.00	2026-06-13 00:37:39.912223+01	2026-06-13 00:37:39.912223+01	Création	\N
11	BN-000001	CNI-111	Premium	2026-06-01	\N	Actif	15000.00	2026-06-13 00:37:59.779317+01	2026-06-13 00:37:59.779317+01	Création	\N
12	BN-000002	CNI-222	Standard	2026-06-05	\N	Actif	5000.00	2026-06-13 00:37:59.779317+01	2026-06-13 00:37:59.779317+01	Création	\N
13	BN-000003	CNI-333	Premium	2026-01-10	\N	Expiré	15000.00	2026-06-13 00:37:59.779317+01	2026-06-13 00:37:59.779317+01	Création	\N
14	BN-000004	CNI-444	Basic	2026-06-10	\N	Actif	2000.00	2026-06-13 00:37:59.779317+01	2026-06-13 00:37:59.779317+01	Création	\N
15	BN-000005	CNI-555	Premium	2026-06-12	\N	Actif	15000.00	2026-06-13 00:37:59.779317+01	2026-06-13 00:37:59.779317+01	Création	\N
\.


--
-- Data for Name: agence_utilisatrice; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.agence_utilisatrice (niu, id_cni, nom_agence, login, password, addresse_mail, lieu_residence, lat, lon, status, created_at, updated_at, log_action) FROM stdin;
AG-NIU-1	CNI-111	Agence Nord	ag_nord	$2a$06$a1vg59V9vFFkFy3VcwaBHupv1E6mTLSuJipyvX9.2TSZPgFYTFpcW	nord@agence.cm	\N	\N	\N	Actif	2026-06-13 00:35:49.709132+01	2026-06-13 00:35:49.709132+01	Création
AG-NIU-2	CNI-222	Agence Sud	ag_sud	$2a$06$Wm4j3ASpP.XmayohexPO3eSg.uPe6kzMDGdCPz1nRCLLK/kz.BsnG	sud@agence.cm	\N	\N	\N	Actif	2026-06-13 00:35:49.709132+01	2026-06-13 00:35:49.709132+01	Création
AG-NIU-3	CNI-333	Agence Est	ag_est	$2a$06$1Vtqwoxcr3JeJ7qISNcajuw5sq418uFbTy4DAq6y4Fx9B1S.H5bB2	est@agence.cm	\N	\N	\N	Inactif	2026-06-13 00:35:49.709132+01	2026-06-13 00:35:49.709132+01	Création
AG-NIU-4	CNI-444	Agence Ouest	ag_ouest	$2a$06$n5XPadyZxZ5Nk1b6ZaoufOadVw/nVmRHTzlO8hPCymr4yHDFaYD0S	ouest@agence.cm	\N	\N	\N	Actif	2026-06-13 00:35:49.709132+01	2026-06-13 00:35:49.709132+01	Création
AG-NIU-5	CNI-555	Agence Centre	ag_centre	$2a$06$Adw1fNBz1widAw07.hZDxeTBju0Dm6xxxcMMe2IiNBR1zMF9rvsu2	centre@agence.cm	\N	\N	\N	Actif	2026-06-13 00:35:49.709132+01	2026-06-13 00:35:49.709132+01	Création
\.


--
-- Data for Name: boite_noir; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.boite_noir (id_boite, id_conteneurs, type_boite, versions, created_at, updated_at, log_action) FROM stdin;
BN-000001	CONT-A1	GPS+Temp	v1.0	2026-06-13 00:37:39.861695+01	2026-06-13 00:37:39.861695+01	Création
BN-000002	CONT-B2	GPS Seulement	v1.2	2026-06-13 00:37:39.861695+01	2026-06-13 00:37:39.861695+01	Création
BN-000003	CONT-C3	Full Sensors	v2.1	2026-06-13 00:37:39.861695+01	2026-06-13 00:37:39.861695+01	Création
BN-000004	CONT-D4	Basic	v1.0	2026-06-13 00:37:39.861695+01	2026-06-13 00:37:39.861695+01	Création
BN-000005	CONT-E5	Full Sensors	v2.1	2026-06-13 00:37:39.861695+01	2026-06-13 00:37:39.861695+01	Création
BN-000006	CONT-A1	GPS+Temp	v1.0	2026-06-13 00:37:59.738688+01	2026-06-13 00:37:59.738688+01	Création
BN-000007	CONT-B2	GPS Seulement	v1.2	2026-06-13 00:37:59.738688+01	2026-06-13 00:37:59.738688+01	Création
BN-000008	CONT-C3	Full Sensors	v2.1	2026-06-13 00:37:59.738688+01	2026-06-13 00:37:59.738688+01	Création
BN-000009	CONT-D4	Basic	v1.0	2026-06-13 00:37:59.738688+01	2026-06-13 00:37:59.738688+01	Création
BN-000010	CONT-E5	Full Sensors	v2.1	2026-06-13 00:37:59.738688+01	2026-06-13 00:37:59.738688+01	Création
BN-000011	bn123456789	monthly	\N	2026-06-13 01:32:28.93473+01	2026-06-13 01:32:28.93473+01	Création
BN-000012	bbm232005	monthly	\N	2026-06-13 01:47:43.592859+01	2026-06-13 01:47:43.592859+01	Création
BN-000013	BN-009	monthly	\N	2026-06-13 02:24:45.042896+01	2026-06-13 02:24:45.042896+01	Création
BN-000014	idcnt2024	monthly	\N	2026-06-13 02:33:24.209236+01	2026-06-13 02:33:24.209236+01	Création
\.


--
-- Data for Name: client; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.client (id_cni, login, password, nom, prenom, date_reception_expedition, address_mail, contact, created_at, updated_at, log_action) FROM stdin;
CNI-111	jean_dupont	$2a$06$V9yC.9PFaEGt.U6DnD9s.u690M3ZmFyN4vxafXIAV2hTIg.ppX.7u	Dupont	Jean	\N	jean.d@mail.com	690000001	2026-06-13 00:35:49.654758+01	2026-06-13 00:35:49.654758+01	Création
CNI-222	marie_curie	$2a$06$OM7IqEanqJB5r4rhuafTXuAwLde35aOT.7RY.mq8OIlvaZERx1tia	Curie	Marie	\N	marie.c@mail.com	690000002	2026-06-13 00:35:49.654758+01	2026-06-13 00:35:49.654758+01	Création
CNI-333	paul_biya	$2a$06$1WEHQhnV7N8D0O1gzW5Wn.VttNDoLccU/6tWkUmqKRpWLAPjGnwQC	Biya	Paul	\N	paul.b@mail.com	690000003	2026-06-13 00:35:49.654758+01	2026-06-13 00:35:49.654758+01	Création
CNI-444	anne_z	$2a$06$KifAYWpNc07UtLfB4.LZQOvwMFGRMo2mVZcP9eeVakol7tCmnqVl6	Zambo	Anne	\N	anne.z@mail.com	690000004	2026-06-13 00:35:49.654758+01	2026-06-13 00:35:49.654758+01	Création
CNI-555	luc_m	$2a$06$lWDrig5iarV5q1ZhMHD.NeCyMzcPvmx9Mv0G05p3QZEokmrSQLiyG	Mbah	Luc	\N	luc.m@mail.com	690000005	2026-06-13 00:35:49.654758+01	2026-06-13 00:35:49.654758+01	Création
TC123	testclient	$2a$06$TgAbPtBRR0XEI18koBcorutAxA2btwoajH0MHfL6iux93iAy9oyKi	TestClient	T	\N	test@client.com	+237600000001	2026-06-13 04:42:36.941965+01	2026-06-13 04:42:36.941965+01	Création
	bbn	$2a$06$BPzIphvuKbTQQaLsal.pkeTK9borgUeY5Jldf3MFflhkESEyiaKK2	brady	bb	\N	brady@gmail.com	658377787	2026-06-13 04:45:35.14647+01	2026-06-13 04:45:35.14647+01	Création
\.


--
-- Data for Name: colis; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.colis (id_colis, id_cni_client, id_cni_transporteur, nom_colis, poids_colis, valeur_colis, temperature_moyenne, lieux_expedition, lieux_receptions, date_heure_exp, date_heure_reception, moyen_transport, created_at, updated_at, log_action, type_colis) FROM stdin;
COL-001	CNI-111	TR-001	Médicaments	5.50	150000.00	4.00	\N	\N	\N	\N	\N	2026-06-13 00:35:49.69101+01	2026-06-13 00:35:49.69101+01	Création	\N
COL-002	CNI-222	TR-002	Poissons surgelés	50.00	75000.00	-18.00	\N	\N	\N	\N	\N	2026-06-13 00:35:49.69101+01	2026-06-13 00:35:49.69101+01	Création	\N
COL-003	CNI-333	TR-003	Électronique	12.00	500000.00	25.00	\N	\N	\N	\N	\N	2026-06-13 00:35:49.69101+01	2026-06-13 00:35:49.69101+01	Création	\N
COL-004	CNI-444	TR-004	Fruits frais	100.00	30000.00	10.00	\N	\N	\N	\N	\N	2026-06-13 00:35:49.69101+01	2026-06-13 00:35:49.69101+01	Création	\N
COL-005	CNI-555	TR-005	Documents	1.00	5000.00	25.00	\N	\N	\N	\N	\N	2026-06-13 00:35:49.69101+01	2026-06-13 00:35:49.69101+01	Création	\N
\.


--
-- Data for Name: conteneurs; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.conteneurs (id_conteneurs, resistance, taile_perimetre, type_conteneurs, created_at, updated_at, log_action, status) FROM stdin;
CONT-A1	Haute	20x10x10	Frigorifique	2026-06-13 00:35:49.632648+01	2026-06-13 00:35:49.632648+01	Création	f
CONT-B2	Moyenne	10x10x10	Standard	2026-06-13 00:35:49.632648+01	2026-06-13 00:35:49.632648+01	Création	f
CONT-C3	Haute	40x20x20	Renforcé	2026-06-13 00:35:49.632648+01	2026-06-13 00:35:49.632648+01	Création	f
CONT-D4	Basse	5x5x5	Léger	2026-06-13 00:35:49.632648+01	2026-06-13 00:35:49.632648+01	Création	f
CONT-E5	Extrême	20x10x10	Blindé	2026-06-13 00:35:49.632648+01	2026-06-13 00:35:49.632648+01	Création	f
bn123456789	\N	\N	\N	2026-06-13 01:32:28.93473+01	2026-06-13 01:32:28.93473+01	Création	f
bbm232005	\N	\N	\N	2026-06-13 01:47:43.592859+01	2026-06-13 01:47:43.592859+01	Création	f
BN-009	\N	12	DRY	2026-06-13 02:24:45.042896+01	2026-06-13 02:24:45.042896+01	Création	f
idcnt2024	\N	966.34 m	DRY	2026-06-13 02:33:24.209236+01	2026-06-13 02:33:24.209236+01	Création	f
\.


--
-- Data for Name: evenement_save; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.evenement_save (id_eventinit, horodatage, id_boite, media_1_url, media_2_url, temperature, humidite, pressions, lat, lon, created_at, log_action, vitesse, notif, chocs) FROM stdin;
\.


--
-- Data for Name: proprietaire_conteneur; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.proprietaire_conteneur (id, niu, id_boite, nom_agence, login, password, addresse_mail, lieu_residence, lon, lat, nbr_boite, created_at, updated_at, log_action) FROM stdin;
6	NIU-1001	BN-000001	LogisTech	logis_admin	$2a$06$Vv.9yBAOEyivbYHYCu1n0O6v.AQCXnZlqQxOcVMtfBmw7NUlUAM96	contact@logistech.cm	\N	9.709000	4.051000	0	2026-06-13 00:37:39.863444+01	2026-06-13 00:37:39.863444+01	Création
7	NIU-1002	BN-000002	TransExpress	trans_admin	$2a$06$y6ai45JEeEL3oLA8vfeKde5nxNWXOC5mYQs/l2haNrBx8fr/xdEK.	hello@transexpress.cm	\N	9.710000	4.055000	0	2026-06-13 00:37:39.863444+01	2026-06-13 00:37:39.863444+01	Création
8	NIU-1003	BN-000003	FretCam	fret_admin	$2a$06$AYDzEkzuXAfyqFuRqz/Sv.7ygj8e3MLus/TSsSoMkYDayEIJfMKgC	info@fretcam.cm	\N	11.511000	3.848000	0	2026-06-13 00:37:39.863444+01	2026-06-13 00:37:39.863444+01	Création
9	NIU-1004	BN-000004	MondialRelay	mondial_user	$2a$06$uANg9bu5Mrd/Zu1Hw195ROf7vyKwSebuZ.Sgn1tUOxWL5k6UGcO4.	support@mondial.cm	\N	11.520000	3.850000	0	2026-06-13 00:37:39.863444+01	2026-06-13 00:37:39.863444+01	Création
10	NIU-1005	BN-000005	SpeedCargo	speed_admin	$2a$06$WaUf6L0pRqUbKuapvJaDiegNNOCf7yNnTlbBZnjza/8cycEKqxh.2	direction@speedcargo.cm	\N	9.750000	4.060000	0	2026-06-13 00:37:39.863444+01	2026-06-13 00:37:39.863444+01	Création
17	pcmr123456789	\N	lgl	lgl	$2a$06$IxFXEq/6ZtFb9ZSkiuNsW.kKlls7nzvAr2/3MZzDc7ClTT/f0BSzS	bradyecoledesposte@gmail.com	\N	0.000000	0.000000	1	2026-06-13 01:32:28.93473+01	2026-06-13 01:32:28.93473+01	Création
18	jfjfjfjfjfjfjfjf	\N	brady	bbl	$2a$06$lffaBwAVkhL0.XmiKzqjquh3HjVNQfrCaGFSiDXBNgBkjfbD/Nepy	bradyecoe@gmail.com	\N	0.000000	0.000000	1	2026-06-13 01:47:43.592859+01	2026-06-13 01:47:43.592859+01	Création
19	T12345	\N	Test Agence	testuser	$2a$06$lzA8KSBDrbTMB5TVP0ffw..8MjuWgbv9l82XgSbaj5Wf0G9QBEaai	test@agence.com	Douala, Cameroun	9.767900	4.051100	1	2026-06-13 02:24:45.042896+01	2026-06-13 02:24:45.042896+01	Création
22	mnmnmnmnmn	\N	brady_logistique	bmj	$2a$06$Vju4q1vbLN.My1W1Q7c90uFm6i4Kf4QN9uvsb5MK2JyPuu6gy1JGy	brd@gmail.com	yaounde cameroun	11.417799	3.944994	1	2026-06-13 02:33:24.209236+01	2026-06-13 02:33:24.209236+01	Création
\.


--
-- Data for Name: seuils_alerte; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.seuils_alerte (id, id_boite, temp_max, humi_max, choc_max, pression_min, vitesse_max, angle_max, updated_at) FROM stdin;
2	BN-000014	32.00	75.00	5.00	995.00	90.00	30.00	2026-06-15 00:50:44.449096+01
\.


--
-- Data for Name: superadmin; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.superadmin (id, id_cni, login, password, dd_pass, created_at, updated_at, log_action) FROM stdin;
1	CNI-SA-001	Argos_br	$2a$06$1D6SBiiv4xMzl/WSDGldJOzqJtqY725PMOpUQBbAZdew4sm.ZO2ey	2026-12-31	2026-06-13 00:35:49.627419+01	2026-06-13 00:35:49.627419+01	Création
\.


--
-- Data for Name: transporteur; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.transporteur (id_cni, nom_chauffeurs, login, password, created_at, updated_at, log_action) FROM stdin;
TR-001	Chauffeur Alain	alain_trans	$2a$06$eiJLZ9mcTF9.TaKm6uMkfOfTSHkzshJZ742sNCbal4gyAnGm1TkHW	2026-06-13 00:35:49.673576+01	2026-06-13 00:35:49.673576+01	Création
TR-002	Chauffeur Boris	boris_trans	$2a$06$S3g/uAIg5VNHbjb3j3.I.OtWka4bZgWLKA9JfjqZZHfG/Y.EcXbdm	2026-06-13 00:35:49.673576+01	2026-06-13 00:35:49.673576+01	Création
TR-003	Chauffeur Claude	claude_trans	$2a$06$CZSom.mllKXytSvK8P7yEO9bxiCz8Vrdi.n7I2bjTnTjwCOhWHRme	2026-06-13 00:35:49.673576+01	2026-06-13 00:35:49.673576+01	Création
TR-004	Chauffeur David	david_trans	$2a$06$qke1t1GQ4ZVnKBXSeOZ9s.40oGmpG2VO8/fPAnP1tbde0t5Z.yNLy	2026-06-13 00:35:49.673576+01	2026-06-13 00:35:49.673576+01	Création
TR-005	Chauffeur Eric	eric_trans	$2a$06$voeNMBholjO7zV7v9W756.feJr4mEappzP9PXqrRw5azWOckKbSda	2026-06-13 00:35:49.673576+01	2026-06-13 00:35:49.673576+01	Création
\.


--
-- Name: bgw_job_id_seq; Type: SEQUENCE SET; Schema: _timescaledb_catalog; Owner: postgres
--

SELECT pg_catalog.setval('_timescaledb_catalog.bgw_job_id_seq', 1000, false);


--
-- Name: chunk_column_stats_id_seq; Type: SEQUENCE SET; Schema: _timescaledb_catalog; Owner: postgres
--

SELECT pg_catalog.setval('_timescaledb_catalog.chunk_column_stats_id_seq', 1, false);


--
-- Name: chunk_constraint_name; Type: SEQUENCE SET; Schema: _timescaledb_catalog; Owner: postgres
--

SELECT pg_catalog.setval('_timescaledb_catalog.chunk_constraint_name', 6, true);


--
-- Name: chunk_id_seq; Type: SEQUENCE SET; Schema: _timescaledb_catalog; Owner: postgres
--

SELECT pg_catalog.setval('_timescaledb_catalog.chunk_id_seq', 3, true);


--
-- Name: dimension_id_seq; Type: SEQUENCE SET; Schema: _timescaledb_catalog; Owner: postgres
--

SELECT pg_catalog.setval('_timescaledb_catalog.dimension_id_seq', 6, true);


--
-- Name: dimension_slice_id_seq; Type: SEQUENCE SET; Schema: _timescaledb_catalog; Owner: postgres
--

SELECT pg_catalog.setval('_timescaledb_catalog.dimension_slice_id_seq', 3, true);


--
-- Name: hypertable_id_seq; Type: SEQUENCE SET; Schema: _timescaledb_catalog; Owner: postgres
--

SELECT pg_catalog.setval('_timescaledb_catalog.hypertable_id_seq', 6, true);


--
-- Name: abonner_numero_a_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.abonner_numero_a_seq', 20, true);


--
-- Name: boite_noir_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.boite_noir_seq', 1, false);


--
-- Name: evenement_save_id_eventinit_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.evenement_save_id_eventinit_seq', 40, true);


--
-- Name: proprietaire_conteneur_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.proprietaire_conteneur_id_seq', 22, true);


--
-- Name: seq_boite_noir; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.seq_boite_noir', 14, true);


--
-- Name: seq_colis; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.seq_colis', 2, true);


--
-- Name: seq_conteneurs; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.seq_conteneurs', 2, true);


--
-- Name: seq_super_admin; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.seq_super_admin', 2, true);


--
-- Name: seq_transporteur; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.seq_transporteur', 3, true);


--
-- Name: seuils_alerte_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.seuils_alerte_id_seq', 3, true);


--
-- Name: superadmin_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.superadmin_id_seq', 3, true);


--
-- Name: _hyper_6_3_chunk 3_6_evenement_save_pkey; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_6_3_chunk
    ADD CONSTRAINT "3_6_evenement_save_pkey" PRIMARY KEY (id_eventinit, horodatage);


--
-- Name: abonner abonner_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.abonner
    ADD CONSTRAINT abonner_pkey PRIMARY KEY (numero_a);


--
-- Name: agence_utilisatrice agence_utilisatrice_addresse_mail_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.agence_utilisatrice
    ADD CONSTRAINT agence_utilisatrice_addresse_mail_key UNIQUE (addresse_mail);


--
-- Name: agence_utilisatrice agence_utilisatrice_login_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.agence_utilisatrice
    ADD CONSTRAINT agence_utilisatrice_login_key UNIQUE (login);


--
-- Name: agence_utilisatrice agence_utilisatrice_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.agence_utilisatrice
    ADD CONSTRAINT agence_utilisatrice_pkey PRIMARY KEY (niu);


--
-- Name: boite_noir boite_noir_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.boite_noir
    ADD CONSTRAINT boite_noir_pkey PRIMARY KEY (id_boite);


--
-- Name: client client_address_mail_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.client
    ADD CONSTRAINT client_address_mail_key UNIQUE (address_mail);


--
-- Name: client client_login_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.client
    ADD CONSTRAINT client_login_key UNIQUE (login);


--
-- Name: client client_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.client
    ADD CONSTRAINT client_pkey PRIMARY KEY (id_cni);


--
-- Name: colis colis_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.colis
    ADD CONSTRAINT colis_pkey PRIMARY KEY (id_colis);


--
-- Name: conteneurs conteneurs_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.conteneurs
    ADD CONSTRAINT conteneurs_pkey PRIMARY KEY (id_conteneurs);


--
-- Name: evenement_save evenement_save_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.evenement_save
    ADD CONSTRAINT evenement_save_pkey PRIMARY KEY (id_eventinit, horodatage);


--
-- Name: proprietaire_conteneur proprietaire_conteneur_addresse_mail_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.proprietaire_conteneur
    ADD CONSTRAINT proprietaire_conteneur_addresse_mail_key UNIQUE (addresse_mail);


--
-- Name: proprietaire_conteneur proprietaire_conteneur_login_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.proprietaire_conteneur
    ADD CONSTRAINT proprietaire_conteneur_login_key UNIQUE (login);


--
-- Name: proprietaire_conteneur proprietaire_conteneur_niu_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.proprietaire_conteneur
    ADD CONSTRAINT proprietaire_conteneur_niu_key UNIQUE (niu);


--
-- Name: proprietaire_conteneur proprietaire_conteneur_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.proprietaire_conteneur
    ADD CONSTRAINT proprietaire_conteneur_pkey PRIMARY KEY (id);


--
-- Name: seuils_alerte seuils_alerte_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.seuils_alerte
    ADD CONSTRAINT seuils_alerte_pkey PRIMARY KEY (id);


--
-- Name: superadmin superadmin_id_cni_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.superadmin
    ADD CONSTRAINT superadmin_id_cni_key UNIQUE (id_cni);


--
-- Name: superadmin superadmin_login_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.superadmin
    ADD CONSTRAINT superadmin_login_key UNIQUE (login);


--
-- Name: superadmin superadmin_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.superadmin
    ADD CONSTRAINT superadmin_pkey PRIMARY KEY (id);


--
-- Name: transporteur transporteur_login_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.transporteur
    ADD CONSTRAINT transporteur_login_key UNIQUE (login);


--
-- Name: transporteur transporteur_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.transporteur
    ADD CONSTRAINT transporteur_pkey PRIMARY KEY (id_cni);


--
-- Name: seuils_alerte unique_id_boite; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.seuils_alerte
    ADD CONSTRAINT unique_id_boite UNIQUE (id_boite);


--
-- Name: _hyper_6_3_chunk_evenement_save_horodatage_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_6_3_chunk_evenement_save_horodatage_idx ON _timescaledb_internal._hyper_6_3_chunk USING btree (horodatage DESC);


--
-- Name: evenement_save_horodatage_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX evenement_save_horodatage_idx ON public.evenement_save USING btree (horodatage DESC);


--
-- Name: abonner trg_abonner_upd; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trg_abonner_upd BEFORE UPDATE ON public.abonner FOR EACH ROW EXECUTE FUNCTION public.update_timestamp_column();


--
-- Name: agence_utilisatrice trg_agence_upd; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trg_agence_upd BEFORE UPDATE ON public.agence_utilisatrice FOR EACH ROW EXECUTE FUNCTION public.update_timestamp_column();


--
-- Name: boite_noir trg_boitenoir_upd; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trg_boitenoir_upd BEFORE UPDATE ON public.boite_noir FOR EACH ROW EXECUTE FUNCTION public.update_timestamp_column();


--
-- Name: client trg_client_upd; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trg_client_upd BEFORE UPDATE ON public.client FOR EACH ROW EXECUTE FUNCTION public.update_timestamp_column();


--
-- Name: colis trg_colis_upd; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trg_colis_upd BEFORE UPDATE ON public.colis FOR EACH ROW EXECUTE FUNCTION public.update_timestamp_column();


--
-- Name: conteneurs trg_conteneurs_upd; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trg_conteneurs_upd BEFORE UPDATE ON public.conteneurs FOR EACH ROW EXECUTE FUNCTION public.update_timestamp_column();


--
-- Name: proprietaire_conteneur trg_proprio_upd; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trg_proprio_upd BEFORE UPDATE ON public.proprietaire_conteneur FOR EACH ROW EXECUTE FUNCTION public.update_timestamp_column();


--
-- Name: superadmin trg_superadmin_upd; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trg_superadmin_upd BEFORE UPDATE ON public.superadmin FOR EACH ROW EXECUTE FUNCTION public.update_timestamp_column();


--
-- Name: transporteur trg_transport_upd; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trg_transport_upd BEFORE UPDATE ON public.transporteur FOR EACH ROW EXECUTE FUNCTION public.update_timestamp_column();


--
-- Name: _hyper_6_3_chunk 3_5_evenement_save_id_boite_fkey; Type: FK CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_6_3_chunk
    ADD CONSTRAINT "3_5_evenement_save_id_boite_fkey" FOREIGN KEY (id_boite) REFERENCES public.boite_noir(id_boite) ON DELETE CASCADE;


--
-- Name: abonner abonner_id_boite_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.abonner
    ADD CONSTRAINT abonner_id_boite_fkey FOREIGN KEY (id_boite) REFERENCES public.boite_noir(id_boite) ON DELETE CASCADE;


--
-- Name: abonner abonner_id_cni_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.abonner
    ADD CONSTRAINT abonner_id_cni_fkey FOREIGN KEY (id_cni) REFERENCES public.client(id_cni) ON DELETE CASCADE;


--
-- Name: agence_utilisatrice agence_utilisatrice_id_cni_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.agence_utilisatrice
    ADD CONSTRAINT agence_utilisatrice_id_cni_fkey FOREIGN KEY (id_cni) REFERENCES public.client(id_cni) ON DELETE CASCADE;


--
-- Name: boite_noir boite_noir_id_conteneurs_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.boite_noir
    ADD CONSTRAINT boite_noir_id_conteneurs_fkey FOREIGN KEY (id_conteneurs) REFERENCES public.conteneurs(id_conteneurs) ON DELETE SET NULL;


--
-- Name: colis colis_id_cni_client_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.colis
    ADD CONSTRAINT colis_id_cni_client_fkey FOREIGN KEY (id_cni_client) REFERENCES public.client(id_cni) ON DELETE SET NULL;


--
-- Name: colis colis_id_cni_transporteur_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.colis
    ADD CONSTRAINT colis_id_cni_transporteur_fkey FOREIGN KEY (id_cni_transporteur) REFERENCES public.transporteur(id_cni) ON DELETE SET NULL;


--
-- Name: evenement_save evenement_save_id_boite_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.evenement_save
    ADD CONSTRAINT evenement_save_id_boite_fkey FOREIGN KEY (id_boite) REFERENCES public.boite_noir(id_boite) ON DELETE CASCADE;


--
-- Name: proprietaire_conteneur proprietaire_conteneur_id_boite_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.proprietaire_conteneur
    ADD CONSTRAINT proprietaire_conteneur_id_boite_fkey FOREIGN KEY (id_boite) REFERENCES public.boite_noir(id_boite) ON DELETE SET NULL;


--
-- Name: seuils_alerte seuils_alerte_id_boite_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.seuils_alerte
    ADD CONSTRAINT seuils_alerte_id_boite_fkey FOREIGN KEY (id_boite) REFERENCES public.boite_noir(id_boite);


--
-- Name: TABLE evenement_save; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.evenement_save TO brady;


--
-- Name: TABLE _hyper_6_3_chunk; Type: ACL; Schema: _timescaledb_internal; Owner: postgres
--

GRANT ALL ON TABLE _timescaledb_internal._hyper_6_3_chunk TO brady;


--
-- Name: TABLE abonner; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.abonner TO brady;


--
-- Name: SEQUENCE abonner_numero_a_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public.abonner_numero_a_seq TO brady;


--
-- Name: TABLE agence_utilisatrice; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.agence_utilisatrice TO brady;


--
-- Name: SEQUENCE seq_boite_noir; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public.seq_boite_noir TO brady;


--
-- Name: TABLE boite_noir; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.boite_noir TO brady;


--
-- Name: SEQUENCE boite_noir_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public.boite_noir_seq TO brady;


--
-- Name: TABLE client; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.client TO brady;


--
-- Name: TABLE colis; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.colis TO brady;


--
-- Name: TABLE conteneurs; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.conteneurs TO brady;


--
-- Name: SEQUENCE evenement_save_id_eventinit_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public.evenement_save_id_eventinit_seq TO brady;


--
-- Name: TABLE proprietaire_conteneur; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.proprietaire_conteneur TO brady;


--
-- Name: SEQUENCE proprietaire_conteneur_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public.proprietaire_conteneur_id_seq TO brady;


--
-- Name: SEQUENCE seq_colis; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public.seq_colis TO brady;


--
-- Name: SEQUENCE seq_conteneurs; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public.seq_conteneurs TO brady;


--
-- Name: SEQUENCE seq_super_admin; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public.seq_super_admin TO brady;


--
-- Name: SEQUENCE seq_transporteur; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public.seq_transporteur TO brady;


--
-- Name: TABLE seuils_alerte; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.seuils_alerte TO brady;


--
-- Name: SEQUENCE seuils_alerte_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public.seuils_alerte_id_seq TO brady;


--
-- Name: TABLE superadmin; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.superadmin TO brady;


--
-- Name: SEQUENCE superadmin_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public.superadmin_id_seq TO brady;


--
-- Name: TABLE transporteur; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.transporteur TO brady;


--
-- Name: DEFAULT PRIVILEGES FOR SEQUENCES; Type: DEFAULT ACL; Schema: public; Owner: postgres
--

ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT ALL ON SEQUENCES TO brady;


--
-- Name: DEFAULT PRIVILEGES FOR TABLES; Type: DEFAULT ACL; Schema: public; Owner: postgres
--

ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT ALL ON TABLES TO brady;


--
-- PostgreSQL database dump complete
--

\unrestrict KEDkCzc7P1yw5H26QjpYvxgUaJ65NbhqDO9Hc2Fu62eKNbq5hhAybhQ5HUjf8Tn


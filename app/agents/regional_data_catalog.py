"""Evidence and acquisition guidance for ARGOS Central Africa data workflows.

This catalog is derived from the project team's supplied inventory. It is a
discovery aid, not a verified feed or a source of operational ground truth.
"""

from __future__ import annotations

import re

from app.agents.registry import AgentRegistry, AgentResult, AgentSpec


DOCUMENT_ROLES = frozenset({
    "superadmin", "owner", "company", "client", "driver", "port_authority",
})

SOURCE_CATALOG = [
    {
        "country": "Cameroon",
        "source": "Port Authority of Kribi (PAK)",
        "source_type": "port_statistics",
        "reported_availability": "Some exportable aggregate series, including years 2018–2023.",
        "training_readiness": "context_only_until_raw_event_logs_are_obtained",
        "url": "https://pak.cm/en/apropos/trade-statistics/",
        "caveat": "Aggregate vessel calls, TEU, tonnage, or transit totals are not individual journeys or observed arrival labels.",
    },
    {
        "country": "Cameroon",
        "source": "National Shippers' Council of Cameroon (CNCC/CNSC), Q1 2025 bulletin",
        "source_type": "aggregate_freight_statistics",
        "reported_availability": "Aggregate port-linked freight statistics.",
        "training_readiness": "context_only_until_authorized_event_level_extract_is_obtained",
        "url": "https://www.cncc.cm/uploads/media/publication/0001/04/625c0efd20e57234ee53d4776dd351a2808b93da.pdf",
        "caveat": "The reported tonnage is an aggregate, not millions of labelled samples.",
    },
    {
        "country": "Republic of the Congo",
        "source": "Port Autonome de Pointe-Noire (PAPN)",
        "source_type": "published_vessel_schedule_and_port_calls",
        "reported_availability": "Public schedule and alongside-vessel table with dates, times, berth, origin, and destination.",
        "training_readiness": "candidate_after_row_level_validation",
        "url": "https://papn-cg.org/programmation-des-navires-navires-a-quai/",
        "caveat": "The supplied inventory reports mixed planned and observed events and inconsistent dates; validate every row against movement logs before using arrival labels.",
    },
    {
        "country": "Democratic Republic of the Congo",
        "source": "OGEFREM Matadi vessel schedules",
        "source_type": "planned_arrival_schedules",
        "reported_availability": "Published planned vessel arrival dates for some periods.",
        "training_readiness": "forecast_context_only",
        "url": "https://www.ogefrem.cd/services/horaires.html",
        "caveat": "Planned dates are not observed arrival times; obtain port-call and berth timestamps for ETA validation.",
    },
    {
        "country": "Central Africa regional",
        "source": "CRESMAC public incident register",
        "source_type": "reported_maritime_incidents",
        "reported_availability": "Dated incident reports with locations and descriptions.",
        "training_readiness": "candidate_cases_only_status_and_cause_must_be_preserved",
        "url": "https://www.cresmac.org/incidents",
        "caveat": "A reported or suspicious event is not automatically a confirmed incident or confirmed cause. Keep reported, investigation ongoing, confirmed, cause confirmed, and inconclusive distinct.",
    },
    {
        "country": "Cameroon and Central African corridors",
        "source": "World Bank / OECD corridor publications",
        "source_type": "aggregate_corridor_indicators",
        "reported_availability": "Published corridor-level travel-time and infrastructure context for selected corridors and periods.",
        "training_readiness": "context_only_not_individual_trip_training_rows",
        "url": "https://www.worldbank.org/en/news/press-release/2026/06/12/world-bank-approves-us-1-12-billion-program-to-modernize-the-douala-bangui-economic-corridor",
        "caveat": "Corridor averages, announced ranges, checkpoints, and historic indicators do not replace timestamped individual trip observations.",
    },
]


ETA_REQUIRED_FIELDS = [
    "trip_id (pseudonymized)", "asset_id (pseudonymized)", "timestamp_utc",
    "latitude", "longitude", "origin", "destination", "transport_mode",
    "eta_original", "eta_updates", "arrival_event_type", "arrival_observed",
    "departure_observed", "delay_reason (if evidenced)", "source_reference",
]

INCIDENT_REQUIRED_FIELDS = [
    "incident_id", "event_time", "event_location", "asset_type",
    "incident_type", "severity_scheme", "confirmation_status", "cause",
    "evidence_reference", "source_timestamp",
]

TRANSFER_REQUIRED_FIELDS = [
    "shipment_id", "container_id (pseudonymized)", "handover_location",
    "handover_time", "next_actor_takeover_time", "seal_and_container_state",
    "handover_evidence", "time_discrepancy", "responsible_data_validator",
]

MODEL_PATHS = {
    "ETA": {
        "baseline": "median observed duration by corridor and transport category",
        "later_candidate": "regression such as LightGBM or CatBoost after sufficient authorized trip-level labels exist",
        "evaluation": ["MAE in minutes or hours", "prediction bias", "error by corridor", "share within defined tolerance"],
    },
    "anomaly": {
        "current_argos_experiment": "binary logistic regression trained on 301 synthetic replay samples across five scenarios; not loaded by operational alerts",
        "candidate": "Isolation Forest on documented route and sensor features",
        "evaluation": ["confirmed incident recall", "false alert rate", "performance by route and operating context"],
        "rule": "An anomaly score is not an incident finding or a probability unless separately calibrated and validated.",
    },
    "incident_classification": {
        "candidate": "interpretable classifier trained on evidence-backed event labels and normal journeys",
        "evaluation": ["recall for severe incidents", "precision", "false alert rate", "performance by confirmation status"],
        "rule": "Never collapse reported, investigated, confirmed, cause-confirmed, and inconclusive cases into one label.",
    },
}

CURRENT_ANOMALY_MODEL = {
    "model_id": "argos_demo_anomaly_logistic_v2",
    "artifact": "models/argos_demo_anomaly_logistic_v2.json",
    "training_datasets": [
        "datasets/argos_demo_two_routes.json",
        "datasets/argos_central_africa_60min.json",
    ],
    "synthetic_samples": 301,
    "scenario_count": 5,
    "class_counts": {"stable": 216, "simulated_anomaly": 85},
    "leave_one_scenario_out": {"accuracy": 0.8737, "precision": 1.0, "recall": 0.5529},
    "operational": False,
}

PRIORITY_CORRIDORS = [
    {"name": "Douala–Bangui", "countries": ["Cameroon", "Central African Republic"],
     "collect": ["port exit", "checkpoint passage", "border and customs events", "stops", "handover", "delivery"]},
    {"name": "Douala–N'Djamena", "countries": ["Cameroon", "Chad"],
     "collect": ["port exit", "checkpoint passage", "border events", "stops", "handover", "delivery"]},
    {"name": "Pointe-Noire–Brazzaville", "countries": ["Republic of the Congo"],
     "collect": ["port call", "terminal operations", "rail/road legs", "cargo handover"]},
]

UNVERIFIED_DATA_HOLDER_LEADS = [
    {"country": "Gabon", "targets": ["Owendo port authority", "port-call and incident logs"]},
    {"country": "Equatorial Guinea", "targets": ["Malabo and Bata port authorities", "transport event records"]},
    {"country": "Chad", "targets": ["transport ministry", "customs and Douala–N'Djamena corridor operators"]},
    {"country": "Central African Republic", "targets": ["transport ministry", "customs and Douala–Bangui/Kribi corridor operators"]},
    {"country": "Democratic Republic of the Congo", "targets": ["OGEFREM", "Matadi/Boma port authorities", "river and rail operators"]},
]

GOVERNANCE_REQUIREMENTS = [
    "record publisher, source URL, extraction timestamp, covered period, format, licence and known limitations",
    "obtain written authorization and permitted-use terms for storage, model training, sharing and retention",
    "pseudonymize trip and asset identifiers and keep a documented correction/validation owner",
    "pilot an anonymized extract and data dictionary before paying for larger commercial feeds",
]


def _matches(query: str, item: dict) -> bool:
    q = query.casefold()
    aliases = {
        "Cameroon": ("cameroun", "kribi", "douala", "pak", "cncc", "cnsc"),
        "Republic of the Congo": ("congo", "pointe-noire", "pointe noire"),
        "Democratic Republic of the Congo": ("rdc", "matadi", "kinshasa"),
        "Central Africa regional": ("afrique centrale", "afrique central", "cresmac"),
        "Cameroon and Central African corridors": (
            "douala", "bangui", "n'djamena", "ndjamena", "tchad", "rca",
        ),
    }.get(item["country"], ())
    query_tokens = set(re.findall(r"[\wÀ-ÿ]+", q))
    source_tokens = set(re.findall(r"[\wÀ-ÿ]+", (
        item["country"] + " " + item["source"] + " " + item["source_type"]
    ).casefold()))
    return any(term in q for term in aliases) or bool(query_tokens & source_tokens)


def regional_data_agent(arguments: dict, _identity: dict, _registry: AgentRegistry) -> AgentResult:
    query = str(arguments.get("query") or "").strip()[:500]
    if not query:
        return AgentResult("central_africa_data", "invalid", error="query requise")

    selected = [item.copy() for item in SOURCE_CATALOG if _matches(query, item)]
    query_tokens = set(re.findall(r"[\wÀ-ÿ]+", query.casefold()))
    broad_query = bool(query_tokens & {
        "afrique", "centrale", "central", "dataset", "datasets", "donnée",
        "données", "donnee", "donnees", "training", "entraînement",
        "entrainement", "modèle", "modèles", "modele", "modeles",
        "corridor", "corridors", "incident", "incidents", "eta", "arrivée",
        "arrivee", "readiness", "disponibles", "data", "port", "ports",
    })
    specific_place_tokens = {
        "cameroun", "cameroon", "kribi", "douala", "pak", "cncc", "cnsc",
        "pointe", "noire", "congo", "matadi", "ogefrem", "rdc", "cresmac",
        "gabon", "owendo", "malabo", "bata", "guinee", "equatoriale",
        "tchad", "chad", "bangui", "rca", "n'djamena", "ndjamena",
    }
    if broad_query and not (query_tokens & specific_place_tokens):
        selected = [item.copy() for item in SOURCE_CATALOG]

    # Use the supplied regional inventory as supporting evidence and retain
    # its file/line provenance; never treat prose or aggregate figures as labels.
    from app.knowledge.rag import search_knowledge
    passages = search_knowledge(query)
    return AgentResult(
        "central_africa_data", "success" if selected or passages else "empty",
        data={
            "query": query,
            "source_catalog": selected,
            "regional_inventory_passages": passages,
            "eta_training_fields": ETA_REQUIRED_FIELDS,
            "incident_training_fields": INCIDENT_REQUIRED_FIELDS,
            "handover_training_fields": TRANSFER_REQUIRED_FIELDS,
            "model_paths": MODEL_PATHS,
            "current_anomaly_model": CURRENT_ANOMALY_MODEL,
            "priority_corridors": PRIORITY_CORRIDORS,
            "unverified_data_holder_leads": UNVERIFIED_DATA_HOLDER_LEADS,
            "governance_requirements": GOVERNANCE_REQUIREMENTS,
            "training_readiness": {
                "anomaly": "experimental_synthetic_only; current classifier is not validated on field incidents",
                "eta": "not_ready_from_aggregate_or_schedule_documents_alone",
                "incidents": "documented_cases_must_be_curated_with_confirmation_status; rare cases need normal journeys too",
                "current_knowledge_file": "retrieval_context_only; not sensor/ETA training rows",
            },
            "collection_workflow": [
                "archive the source URL, publisher, extraction time, coverage, format, licence, and known limitations",
                "request authorized anonymized event-level extracts and their data dictionaries from relevant port, freight, and incident authorities",
                "validate a small corridor sample for complete journeys, timestamps, identifiers, and label evidence before model fitting",
                "split evaluation by time and corridor and report error/recall plus false alerts; do not score against another system's predicted ETA",
            ],
            "incident_statuses": ["reported", "investigation_ongoing", "confirmed", "cause_confirmed", "inconclusive"],
            "source_validation_status": "user_supplied_inventory_not_independently_rechecked",
        },
        provenance=[
            {"source": item["source"], "country": item["country"], "url": item["url"],
             "status": "user_supplied_candidate_source_not_independently_rechecked"}
            for item in selected
        ] + passages,
    )


def register_regional_data_agent(registry: AgentRegistry) -> None:
    registry.register(AgentSpec(
        "central_africa_data", "1.0", "Données et préparation des modèles en Afrique centrale",
        "regional.data.readiness", "Identifier les sources publiques recensées, distinguer données agrégées, horaires et observations réelles, et définir les champs et validations requis pour les modèles ETA, anomalies et incidents.",
        {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
        DOCUMENT_ROLES, regional_data_agent,
        output_schema={"type": "object", "required": ["source_catalog", "eta_training_fields", "incident_training_fields", "training_readiness", "source_validation_status"]},
        tools_or_services=("regional_source_catalog", "knowledge_base", "model_data_requirements"),
        limitations=("L'inventaire provient d'un texte fourni par l'équipe et n'a pas été indépendamment vérifié ici.", "Les publications agrégées et horaires prévisionnels ne constituent pas des trajectoires individuelles étiquetées.", "L'agent ne télécharge pas de données, n'obtient pas de droits, n'entraîne ni ne déploie un modèle."),
    ))

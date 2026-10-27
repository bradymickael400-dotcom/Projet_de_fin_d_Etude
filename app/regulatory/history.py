"""Versioned legal-source catalogue and append-only ARGOS decision history."""

import json
import re
from uuid import uuid4

from sqlalchemy import text

from app.extensions import db


AGENT_SOURCE = {
    "iot_monitor": "ARGOS_IOT_TELEMETRY",
    "gps_route": "ARGOS_GPS_POSITION",
    "risk_assessor": "ARGOS_AGENT_RULES",
    "knowledge_retriever": "ARGOS_AGENT_RULES",
    "assistant": "ARGOS_AGENT_RULES",
    "report": "ARGOS_AGENT_RULES",
    "thresholds": "ARGOS_THRESHOLD_RULES",
}


def _sources(rows):
    output = []
    for row in rows:
        item = dict(row._mapping)
        for key, value in list(item.items()):
            if hasattr(value, "isoformat"):
                item[key] = value.isoformat()
        output.append(item)
    return output


def search_regulatory_sources(query, limit=8):
    """Lexically rank curated sources without claiming legal applicability."""
    tokens = {item.casefold() for item in re.findall(r"[\wÀ-ÿ'-]{3,}", str(query or ""))}
    rows = db.session.execute(text("""
        SELECT source_key,title,source_type,authority,jurisdiction,transport_modes,
               official_url,adoption_date,effective_date,legal_status,
               applicability_conditions,summary,verified_at
        FROM regulatory_sources ORDER BY source_key
    """)).fetchall()
    if not tokens:
        return []
    ranked = []
    for row in _sources(rows):
        haystack = " ".join(str(row.get(key) or "") for key in (
            "title", "source_type", "authority", "jurisdiction", "transport_modes", "summary"
        )).casefold()
        score = sum(1 for token in tokens if token in haystack)
        if score:
            ranked.append((score, row))
    ranked.sort(key=lambda item: (-item[0], item[1]["source_key"]))
    result = []
    for score, row in ranked[:max(1, min(int(limit), 20))]:
        row["relevance_matches"] = score
        row["applicability_status"] = "TO_VERIFY"
        result.append(row)
    return result


def list_regulatory_sources(query="", jurisdiction=None, mode=None):
    sources = search_regulatory_sources(query, 20) if query else _sources(db.session.execute(text("""
        SELECT source_key,title,source_type,authority,jurisdiction,transport_modes,
               official_url,adoption_date,effective_date,legal_status,
               applicability_conditions,summary,verified_at
        FROM regulatory_sources ORDER BY jurisdiction,title
    """)).fetchall())
    if jurisdiction:
        needle = str(jurisdiction).casefold()
        sources = [s for s in sources if needle in str(s.get("jurisdiction") or "").casefold()]
    if mode:
        sources = [s for s in sources if mode in (s.get("transport_modes") or [])]
    return sources


def record_decision(*, identity=None, black_box_id=None, container_id=None,
                    subject_type="black_box", subject_id=None, event_type,
                    action, reaction="", remarks=None, source_keys=None,
                    applicability_status="NOT_ASSESSED", trace_id=None):
    """Append a trace event. Caller controls transaction and commits its unit."""
    identity = identity or {}
    keys = list(dict.fromkeys(str(k) for k in (source_keys or []) if k))
    if not keys:
        keys = [AGENT_SOURCE.get(event_type, "ARGOS_AGENT_RULES")]
    if "ARGOS_AGENT_RULES" not in keys and event_type in {"AI_RESPONSE", "AI_AGENT_ACTION", "AI_REPORT"}:
        keys.append("ARGOS_AGENT_RULES")
    uid = str(uuid4())
    db.session.execute(text("""
        INSERT INTO decision_history
            (history_uid,trace_id,black_box_id,container_id,subject_type,subject_id,
             event_type,actor_role,actor_id,action,reaction,ai_remarks,source_keys,applicability_status)
        VALUES (CAST(:uid AS uuid),CAST(:trace_id AS uuid),:box,:container,:subject_type,:subject_id,
                :event_type,:role,:actor,:action,:reaction,CAST(:remarks AS jsonb),
                CAST(:sources AS jsonb),:applicability)
    """), {
        "uid": uid, "trace_id": trace_id, "box": black_box_id,
        "container": str(container_id) if container_id is not None else None,
        "subject_type": subject_type, "subject_id": str(subject_id) if subject_id is not None else uid,
        "event_type": event_type, "role": str(identity.get("role") or "system"),
        "actor": str(identity.get("user_id") or "system"),
        "action": str(action)[:4000], "reaction": str(reaction)[:8000],
        "remarks": json.dumps(remarks or {}, ensure_ascii=False, default=str),
        "sources": json.dumps(keys, ensure_ascii=False), "applicability": applicability_status,
    })
    return uid


def history_for_box(black_box_id, limit=100):
    rows = db.session.execute(text("""
        SELECT history_uid,trace_id,black_box_id,container_id,subject_type,subject_id,
               event_type,actor_role,actor_id,action,reaction,ai_remarks,source_keys,
               applicability_status,created_at
        FROM decision_history WHERE black_box_id=:box
        ORDER BY created_at DESC,id DESC LIMIT :limit
    """), {"box": black_box_id, "limit": max(1, min(int(limit), 250))}).fetchall()
    history = _sources(rows)
    keys = sorted({key for row in history for key in (row.get("source_keys") or [])})
    source_by_key = {}
    if keys:
        source_rows = db.session.execute(text("""
            SELECT source_key,title,source_type,authority,jurisdiction,official_url,
                   legal_status,applicability_conditions,summary,verified_at
            FROM regulatory_sources WHERE source_key = ANY(CAST(:keys AS varchar[]))
        """), {"keys": keys}).fetchall()
        source_by_key = {row.source_key: dict(row._mapping) for row in source_rows}
    for row in history:
        row["sources"] = [source_by_key[key] for key in (row.get("source_keys") or []) if key in source_by_key]
        created_at = row.get("created_at")
        row["created_at"] = created_at.isoformat() if hasattr(created_at, "isoformat") else created_at
    return history

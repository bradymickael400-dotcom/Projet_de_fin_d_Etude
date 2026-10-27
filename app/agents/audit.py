"""Journal structuré des appels LLM et des capacités consultées."""

import json
import logging

from sqlalchemy import text

from app.extensions import db

logger = logging.getLogger(__name__)


def persist_agent_run(trace_id, identity, status, agents, sources, error_code=None):
    """Persiste la trace sans enregistrer la question, les secrets ou une CoT."""
    try:
        db.session.execute(text("""
            INSERT INTO ai_agent_runs
                (trace_id, actor_role, actor_id, status, agents_consulted,
                 sources, error_code)
            VALUES
                (:trace_id, :actor_role, :actor_id, :status,
                 CAST(:agents AS JSONB), CAST(:sources AS JSONB), :error_code)
        """), {
            "trace_id": trace_id,
            "actor_role": str(identity.get("role") or ""),
            "actor_id": str(identity.get("user_id") or ""),
            "status": status,
            "agents": json.dumps(agents, ensure_ascii=False),
            "sources": json.dumps(sources, ensure_ascii=False),
            "error_code": error_code,
        })
        db.session.commit()
        return True
    except Exception:
        db.session.rollback()
        logger.exception("Échec de persistance du journal IA trace_id=%s", trace_id)
        return False

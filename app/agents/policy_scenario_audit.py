"""Persistance des rejeux synthétiques de scénarios institutionnels."""

import json
import logging

from sqlalchemy import text

from app.extensions import db

logger = logging.getLogger(__name__)


def persist_policy_scenario(result: dict, identity: dict) -> bool:
    try:
        db.session.execute(text("""
            INSERT INTO brady.policy_scenario_runs
                (trace_id, scenario_id, actor_role, actor_id, synthetic, result)
            VALUES
                (:trace_id, :scenario_id, :actor_role, :actor_id, TRUE, CAST(:result AS JSONB))
        """), {
            "trace_id": result["trace_id"],
            "scenario_id": result["scenario_id"],
            "actor_role": str(identity.get("role") or ""),
            "actor_id": str(identity.get("user_id") or ""),
            "result": json.dumps(result, ensure_ascii=False),
        })
        db.session.commit()
        return True
    except Exception:
        db.session.rollback()
        logger.exception("Échec de persistance scénario synthétique trace_id=%s", result.get("trace_id"))
        return False

"""API read-only du catalogue de sources et de l’historique de décisions."""

from flask import Blueprint, jsonify, request

from app.regulatory.history import history_for_box, list_regulatory_sources
from app.security import current_identity

regulatory_bp = Blueprint("regulatory", __name__)


@regulatory_bp.get("/api/regulatory/sources")
def regulatory_sources():
    identity = current_identity()
    if not identity.get("role"):
        return jsonify({"error": "Authentification requise"}), 401
    query = (request.args.get("q") or "").strip()[:500]
    jurisdiction = (request.args.get("jurisdiction") or "").strip()[:100] or None
    mode = (request.args.get("mode") or "").strip()[:40] or None
    try:
        return jsonify({"sources": list_regulatory_sources(query, jurisdiction, mode)})
    except Exception:
        from flask import current_app
        current_app.logger.exception("Lecture du registre réglementaire impossible")
        return jsonify({"error": "Registre réglementaire indisponible"}), 503


@regulatory_bp.get("/api/regulatory/history")
def regulatory_history():
    identity = current_identity()
    if not identity.get("role"):
        return jsonify({"error": "Authentification requise"}), 401
    try:
        box_id = int(request.args.get("box_id", ""))
    except (TypeError, ValueError):
        return jsonify({"error": "box_id invalide"}), 400
    if box_id <= 0:
        return jsonify({"error": "box_id invalide"}), 400
    try:
        from app.routes.dashboard import _visible_boites_for
        role, user_id = identity.get("role"), identity.get("user_id")
        visible = _visible_boites_for(role, user_id)
        if visible is not None and str(box_id) not in {str(value) for value in visible}:
            return jsonify({"error": "Dossier introuvable"}), 404
        from app.extensions import db
        from sqlalchemy import text
        box_exists = db.session.execute(text("SELECT 1 FROM boite_noir WHERE id_boite=:id"), {"id": box_id}).scalar()
        if not box_exists:
            return jsonify({"error": "Dossier introuvable"}), 404
        return jsonify({"history": history_for_box(box_id)})
    except Exception:
        from flask import current_app
        current_app.logger.exception("Lecture historique réglementaire impossible")
        return jsonify({"error": "Historique du dossier indisponible"}), 503

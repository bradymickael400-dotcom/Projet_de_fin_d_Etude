import json

from flask import Blueprint, request, jsonify
from app.utils import _hash_block
from sqlalchemy import text # type: ignore
from app import db
from app.utils import *

blockchain_bp = Blueprint("blockchain", __name__)

def _visible_boites_for(role, user_id):
    if role in (None, "", "superadmin"):
        return None
    if not user_id:
        return []
    if role == "owner":
        return get_boites_for_owner(user_id)
    if role == "company":
        return get_boites_for_agency(user_id)
    if role == "client":
        return get_boite_for_client(user_id)
    if role == "driver":
        return get_boite_for_driver(user_id)
    return []

def _append_boites_filter(query, params, boites):
    if boites is None:
        return query, True
    if not boites:
        return query, False
    placeholders = ",".join([f":b{i}" for i in range(len(boites))])
    params.update({f"b{i}": v for i, v in enumerate(boites)})
    return f"{query} AND id_boite IN ({placeholders})", True

@blockchain_bp.route("/api/blockchain/events", methods=["GET"])
def get_blockchain_events():
    role = request.args.get("role", "")
    user_id = request.args.get("user_id", "")
    
    # SÉCURITÉ : Chauffeurs et Clients n'ont pas accès à la Blockchain
    if role in ["driver", "client"]:
        return jsonify({"blocks": [], "total": 0, "page": 1, "per_page": 30, "error": "Accès refusé"})

    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 30))
    etype = request.args.get("type", "")
    boite = request.args.get("boite", "")
    offset = (page - 1) * per_page

    try:
        query = "SELECT * FROM blockchain_argos WHERE 1=1"
        params = {}
        query, allowed = _append_boites_filter(query, params, _visible_boites_for(role, user_id))
        if not allowed:
            return jsonify({"blocks": [], "total": 0, "page": page, "per_page": per_page})
        if etype:
            query += " AND event_type = :type"
            params["type"] = etype
        if boite:
            query += " AND id_boite = :boite"
            params["boite"] = boite

        query += " ORDER BY block_index DESC LIMIT :limit OFFSET :offset"
        params["limit"] = per_page
        params["offset"] = offset

        rows = db.session.execute(text(query), params).fetchall()
        
        total_query = "SELECT COUNT(*) FROM blockchain_argos WHERE 1=1"
        total_query, _ = _append_boites_filter(total_query, params, _visible_boites_for(role, user_id))
        if etype: total_query += " AND event_type = :type"
        if boite: total_query += " AND id_boite = :boite"
        
        total = db.session.execute(text(total_query), params).scalar()

        blocks = []
        for r in rows:
            d = dict(r._mapping)
            d['horodatage'] = d['horodatage'].isoformat() if d['horodatage'] else None
            blocks.append(d)

        return jsonify({"blocks": blocks, "total": total, "page": page, "per_page": per_page})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    

@blockchain_bp.route("/api/blockchain/stats", methods=["GET"])
def blockchain_stats(): # type: ignore
    role = request.args.get("role", "")
    user_id = request.args.get("user_id", "")
    query = "FROM blockchain_argos WHERE 1=1"
    params = {}
    query, allowed = _append_boites_filter(query, params, _visible_boites_for(role, user_id))
    if not allowed:
        return jsonify({"total_blocks": 0, "by_type": {}})
    total = db.session.execute(text(f"SELECT COUNT(*) {query}"), params).scalar() or 0
    by_type = db.session.execute(text(
        f"SELECT event_type, COUNT(*) {query} GROUP BY event_type"
    ), params).fetchall()
    return jsonify({"total_blocks": total, "by_type": {r[0]: r[1] for r in by_type}})

@blockchain_bp.route("/api/blockchain/verify", methods=["GET"])
def verify_blockchain():
    rows = db.session.execute(text("""
        SELECT block_index, previous_hash, block_hash, horodatage, payload
        FROM blockchain_argos ORDER BY block_index
    """)).fetchall()
    errors = []
    for i, r in enumerate(rows):
        if i == 0: continue
        prev = rows[i - 1]
        p = r[4]
        if isinstance(p, str):
            try: p = json.loads(p)
            except: p = {}
        expected = _hash_block(r[0], prev[2], str(r[3]), p)
        if expected != r[2]:
            errors.append({"block": r[0], "issue": "hash_mismatch"})
    return jsonify({"valid": len(errors) == 0, "total_blocks": len(rows), "errors": errors})

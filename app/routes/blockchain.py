import json

from flask import Blueprint, request, jsonify
from app.utils import _hash_block
from sqlalchemy import text # type: ignore
from app import db
from app.utils import *

blockchain_bp = Blueprint("blockchain", __name__)

@blockchain_bp.route("/api/blockchain/events", methods=["GET"])
def get_blockchain_events():
    role = request.args.get("role", "")
    
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
    total = db.session.execute(text("SELECT COUNT(*) FROM blockchain_argos")).scalar() or 0
    by_type = db.session.execute(text(
        "SELECT event_type, COUNT(*) FROM blockchain_argos GROUP BY event_type"
    )).fetchall()
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
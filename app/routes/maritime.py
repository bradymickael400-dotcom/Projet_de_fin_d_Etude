"""Routes Flask du module maritime ARGOS.

Le module couvre la validation de conteneurs, la création de voyages,
le suivi hybride et la création de litiges associés aux trajets.
"""
from datetime import datetime
from decimal import Decimal

from flask import Blueprint, jsonify, request
from sqlalchemy import text

from app import db
from app.utils import _sceller_evenement, get_caller_identity

maritime_bp = Blueprint("maritime", __name__)


def _jsonable(value):
    if isinstance(value, (datetime,)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return value


def _row_to_dict(row):
    return {k: _jsonable(v) for k, v in dict(row._mapping).items()}


@maritime_bp.route("/api/container/validate", methods=["POST"])
def validate_container():
    d = request.get_json() or {}
    container_number = (d.get("container_number") or "").upper().replace(" ", "").replace("-", "")
    fetch_bic = d.get("fetch_bic", True)
    if not container_number:
        return jsonify({"error": "container_number requis"}), 400

    from app.services.bic_service import get_bic_service, validate_iso6346

    valid, reason = validate_iso6346(container_number)
    response = {
        "container_number": container_number,
        "iso6346_valid": valid,
        "validation_msg": reason,
        "bic_specs": None,
    }

    if valid and fetch_bic:
        cached = db.session.execute(text(
            "SELECT * FROM container_specs_bic WHERE container_number = :c"
        ), {"c": container_number}).fetchone()
        if cached:
            specs = _row_to_dict(cached)
            specs["source"] = "cache"
            response["bic_specs"] = specs
        else:
            try:
                svc = get_bic_service()
                specs = svc.fetch_container_specs(container_number)
                if specs:
                    svc.save_to_db(specs)
                    specs["source"] = "bic_api"
                    response["bic_specs"] = specs
            except Exception as e:
                response["bic_warning"] = f"BIC API indisponible : {e}"

    return jsonify(response)


@maritime_bp.route("/api/voyage/create", methods=["POST"])
def create_voyage():
    role, user_id = get_caller_identity()
    if role in ("client", "driver"):
        return jsonify({"error": "Accès refusé"}), 403

    d = request.get_json() or {}
    if not d.get("voyage_number"):
        return jsonify({"error": "voyage_number requis"}), 400

    try:
        if d.get("imo_number") and d.get("vessel_name"):
            db.session.execute(text("""
                INSERT INTO vessel (imo_number, vessel_name, operator_name)
                VALUES (:imo, :name, :operator)
                ON CONFLICT (imo_number) DO UPDATE SET
                    vessel_name = EXCLUDED.vessel_name,
                    operator_name = COALESCE(EXCLUDED.operator_name, vessel.operator_name),
                    updated_at = NOW()
            """), {
                "imo": d["imo_number"],
                "name": d["vessel_name"],
                "operator": d.get("shipping_line"),
            })

        voyage_id = db.session.execute(text("""
            INSERT INTO maritime_voyage
                (voyage_number, imo_number, bl_number, booking_reference,
                 pol_locode, pod_locode, etd, eta, shipping_line,
                 tracking_provider, voyage_status)
            VALUES
                (:vnum, :imo, :bl, :booking, :pol, :pod, :etd, :eta,
                 :line, :provider, 'planned')
            RETURNING id
        """), {
            "vnum": d.get("voyage_number"),
            "imo": d.get("imo_number"),
            "bl": d.get("bl_number"),
            "booking": d.get("booking_reference"),
            "pol": d.get("pol_locode"),
            "pod": d.get("pod_locode"),
            "etd": d.get("etd"),
            "eta": d.get("eta"),
            "line": d.get("shipping_line"),
            "provider": d.get("tracking_provider"),
        }).scalar()

        from app.services.bic_service import validate_iso6346

        for cont in d.get("containers") or []:
            cnum = (cont.get("container_number") or "").upper().replace(" ", "").replace("-", "")
            valid, _ = validate_iso6346(cnum)
            if not valid:
                continue
            db.session.execute(text("""
                INSERT INTO bic_owner_prefix (prefix, company_name)
                VALUES (:prefix, :prefix)
                ON CONFLICT DO NOTHING
            """), {"prefix": cnum[:4]})
            db.session.execute(text("""
                INSERT INTO container_specs_bic (container_number, owner_prefix)
                VALUES (:cnum, :prefix)
                ON CONFLICT DO NOTHING
            """), {"cnum": cnum, "prefix": cnum[:4]})
            db.session.execute(text("""
                INSERT INTO container_voyage_assignment
                    (container_number, id_boite, voyage_id,
                     seal_number, hs_code, cargo_description)
                VALUES (:cnum, :boite, :vid, :seal, :hs, :desc)
                ON CONFLICT (container_number, voyage_id) DO NOTHING
            """), {
                "cnum": cnum,
                "boite": cont.get("id_boite"),
                "vid": voyage_id,
                "seal": cont.get("seal_number"),
                "hs": cont.get("hs_code"),
                "desc": cont.get("cargo_description"),
            })

        db.session.commit()
        _sceller_evenement("CREATION_VOYAGE", None, {
            "voyage_id": voyage_id,
            "created_by_role": role,
            "created_by": user_id,
            "bl_number": d.get("bl_number"),
            "imo_number": d.get("imo_number"),
            "pol": d.get("pol_locode"),
            "pod": d.get("pod_locode"),
        })
        return jsonify({"status": "success", "voyage_id": voyage_id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@maritime_bp.route("/api/container/position/<id_boite>", methods=["GET"])
def get_hybrid_container_position(id_boite):
    voyage_id = request.args.get("voyage_id", type=int)
    from app.services.positioning_service import get_hybrid_position
    return jsonify(get_hybrid_position(id_boite, voyage_id))


@maritime_bp.route("/api/voyage/<int:voyage_id>/tracking", methods=["GET"])
def get_voyage_tracking(voyage_id):
    voyage = db.session.execute(text(
        "SELECT * FROM maritime_voyage WHERE id = :id"
    ), {"id": voyage_id}).fetchone()
    if not voyage:
        return jsonify({"error": "Voyage introuvable"}), 404

    containers = db.session.execute(text("""
        SELECT container_number FROM container_voyage_assignment
        WHERE voyage_id = :vid AND container_number IS NOT NULL
    """), {"vid": voyage_id}).fetchall()

    results = []
    try:
        from app.services.maritime_service import get_maritime_adapter
        adapter = get_maritime_adapter()
        voyage_data = dict(voyage._mapping)
        for cont in containers:
            tracking = adapter.get_container_tracking(cont[0], voyage_data.get("bl_number"))
            if tracking:
                results.append(tracking)
        if voyage_data.get("imo_number"):
            pos = adapter.get_vessel_position(voyage_data["imo_number"])
            if pos:
                from app.services.positioning_service import _save_ais_position
                _save_ais_position(voyage_data["imo_number"], pos)
    except EnvironmentError as e:
        return jsonify({"warning": str(e), "containers": []}), 200
    except Exception as e:
        return jsonify({"warning": f"Tracking indisponible : {e}", "containers": results}), 200

    return jsonify({"voyage_id": voyage_id, "containers": results})


@maritime_bp.route("/api/litige/create", methods=["POST"])
def create_litige():
    role, _ = get_caller_identity()
    if role in ("client", "driver"):
        return jsonify({"error": "Accès refusé"}), 403
    d = request.get_json() or {}
    try:
        event_ts = d.get("event_ts")
        if isinstance(event_ts, str) and event_ts:
            event_ts = datetime.fromisoformat(event_ts.replace("Z", "+00:00"))
        else:
            event_ts = datetime.utcnow()
        from app.services.positioning_service import create_geolocalized_litige
        litige_id = create_geolocalized_litige(
            id_boite=d.get("id_boite"),
            iot_event_id=d.get("iot_event_id"),
            alert_type=d.get("alert_type") or "MANUEL",
            alert_values=d.get("alert_values") or {},
            event_ts=event_ts,
            iot_lat=d.get("iot_lat"),
            iot_lon=d.get("iot_lon"),
        )
        return jsonify({"status": "success", "litige_id": litige_id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@maritime_bp.route("/api/litiges", methods=["GET"])
def get_litiges():
    role, user_id = get_caller_identity()
    where, params = [], {}
    if role == "owner":
        from app.utils import get_boites_for_owner
        boites = get_boites_for_owner(user_id)
        if not boites:
            return jsonify([])
        placeholders = ",".join([f":b{i}" for i in range(len(boites))])
        where.append(f"id_boite IN ({placeholders})")
        params.update({f"b{i}": v for i, v in enumerate(boites)})
    elif role == "company":
        from app.utils import get_boites_for_agency
        boites = get_boites_for_agency(user_id)
        if not boites:
            return jsonify([])
        placeholders = ",".join([f":b{i}" for i in range(len(boites))])
        where.append(f"id_boite IN ({placeholders})")
        params.update({f"b{i}": v for i, v in enumerate(boites)})
    elif role in ("driver", "client"):
        return jsonify({"error": "Accès refusé"}), 403

    wh = f"WHERE {' AND '.join(where)}" if where else ""
    rows = db.session.execute(text(f"""
        SELECT * FROM litige_alerte {wh}
        ORDER BY event_ts DESC LIMIT 50
    """), params).fetchall()
    return jsonify([_row_to_dict(r) for r in rows])


@maritime_bp.route("/api/port/auth/containers", methods=["GET"])
def port_authority_view():
    role, user_id = get_caller_identity()
    if role != "port_authority":
        return jsonify({"error": "Accès réservé aux autorités portuaires"}), 403

    agent = db.session.execute(text(
        "SELECT port_locode FROM port_authority_user WHERE id = :uid"
    ), {"uid": user_id}).fetchone()
    if not agent:
        return jsonify({"error": "Agent portuaire introuvable"}), 404

    rows = db.session.execute(text("""
        SELECT
            cva.container_number, cva.id_boite, cva.seal_number,
            cva.hs_code, cva.cargo_description, cva.customs_status,
            cva.customs_cleared_at,
            mv.id AS voyage_id, mv.voyage_number, mv.bl_number, mv.shipping_line,
            mv.eta, mv.etd, mv.voyage_status,
            v.vessel_name, v.imo_number,
            pol.port_name AS pol_name, pod.port_name AS pod_name
        FROM container_voyage_assignment cva
        JOIN maritime_voyage mv ON mv.id = cva.voyage_id
        LEFT JOIN vessel v ON v.imo_number = mv.imo_number
        LEFT JOIN port pol ON pol.locode = mv.pol_locode
        LEFT JOIN port pod ON pod.locode = mv.pod_locode
        WHERE mv.pod_locode = :locode
          AND mv.voyage_status IN ('loaded', 'at_sea', 'arrived')
        ORDER BY mv.eta ASC
    """), {"locode": agent[0]}).fetchall()
    return jsonify([_row_to_dict(r) for r in rows])


@maritime_bp.route("/api/port/auth/customs", methods=["POST"])
def update_customs_status():
    role, user_id = get_caller_identity()
    if role != "port_authority":
        return jsonify({"error": "Accès réservé aux autorités portuaires"}), 403

    d = request.get_json() or {}
    action = d.get("action")
    if action not in ("clear", "hold", "reject"):
        return jsonify({"error": "action doit être : clear | hold | reject"}), 400
    status_map = {"clear": "cleared", "hold": "held", "reject": "rejected"}

    db.session.execute(text("""
        UPDATE container_voyage_assignment
        SET customs_status = :status,
            customs_cleared_by = :by,
            customs_cleared_at = NOW()
        WHERE container_number = :cont
          AND voyage_id = :vid
    """), {
        "status": status_map[action],
        "by": user_id,
        "cont": (d.get("container_number") or "").upper(),
        "vid": d.get("voyage_id"),
    })
    db.session.commit()
    _sceller_evenement(f"CUSTOMS_{action.upper()}", d.get("container_number"), {
        "voyage_id": d.get("voyage_id"),
        "agent": user_id,
        "notes": d.get("notes"),
    })
    return jsonify({"status": "success", "customs_status": status_map[action]})

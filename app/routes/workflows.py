"""Workflows metier ARGOS: documents professionnels et destockage consensuel."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4
import io
import json
import math

from flask import Blueprint, jsonify, request, send_file
from sqlalchemy import text

from app import db
from app.security import current_identity, issue_access_token, roles_required
from app.services.report_service import generate_contract_pdf, generate_inventory_pdf


workflow_bp = Blueprint("workflows", __name__)


def _identity():
    identity = current_identity()
    return str(identity.get("role", "")), str(identity.get("user_id", ""))


def _can_access_container(role, user_id, container_id):
    if role == "superadmin":
        return True
    query_by_role = {
        "owner": """
            SELECT 1 FROM boite_noir b
            LEFT JOIN black_box_container_assignments a ON a.black_box_id=b.id_boite
            WHERE CAST(b.id_proprietaire AS TEXT)=:uid
              AND (b.id_conteneurs=:container OR a.container_id=:container)
        """,
        "client": """
            SELECT 1 FROM shipments WHERE container_id=:container AND client_id=:uid
            UNION ALL
            SELECT 1 FROM abonner a JOIN boite_noir b ON b.id_boite=a.id_boite
            LEFT JOIN black_box_container_assignments x ON x.black_box_id=b.id_boite
            WHERE a.id_cni=:uid AND (b.id_conteneurs=:container OR x.container_id=:container)
        """,
        "driver": """
            SELECT 1 FROM shipments WHERE container_id=:container AND driver_id=:uid
            UNION ALL
            SELECT 1 FROM colis co JOIN abonner a ON a.id_cni=co.id_cni_client
            JOIN boite_noir b ON b.id_boite=a.id_boite
            LEFT JOIN black_box_container_assignments x ON x.black_box_id=b.id_boite
            WHERE co.id_cni_transporteur=:uid AND (b.id_conteneurs=:container OR x.container_id=:container)
        """,
        "company": """
            SELECT 1 FROM shipments WHERE container_id=:container AND company_id=:uid
            UNION ALL
            SELECT 1 FROM agence_abonnement aa JOIN boite_noir b ON b.id_boite=aa.id_boite
            LEFT JOIN black_box_container_assignments x ON x.black_box_id=b.id_boite
            WHERE CAST(aa.id_agence AS TEXT)=:uid AND (b.id_conteneurs=:container OR x.container_id=:container)
        """,
    }
    query = query_by_role.get(role)
    if not query:
        return False
    return bool(db.session.execute(text(query), {"container": container_id, "uid": user_id}).scalar())


@workflow_bp.route("/api/documents/inventory.pdf", methods=["POST"])
def inventory_pdf_preview():
    role, user_id = _identity()
    payload = request.get_json(silent=True) or {}
    container_id = str(payload.get("container_id") or "")
    if not container_id:
        return jsonify({"error": "container_id requis"}), 400
    if not _can_access_container(role, user_id, container_id):
        return jsonify({"error": "Acces refuse a ce conteneur"}), 403
    pdf = generate_inventory_pdf(payload)
    return send_file(
        io.BytesIO(pdf), mimetype="application/pdf", as_attachment=True,
        download_name=f"inventaire_{container_id}.pdf",
    )


@workflow_bp.route("/api/documents/contracts/preview.pdf", methods=["POST"])
@roles_required("superadmin")
def contract_pdf_preview():
    payload = request.get_json(silent=True) or {}
    pdf = generate_contract_pdf(payload)
    number = payload.get("contract_number") or "brouillon"
    return send_file(
        io.BytesIO(pdf), mimetype="application/pdf", as_attachment=True,
        download_name=f"contrat_argos_{number}.pdf",
    )


@workflow_bp.route("/api/contracts/<contract_uid>/document.pdf", methods=["GET"])
def contract_document(contract_uid):
    role, user_id = _identity()
    row = db.session.execute(text("""
        SELECT c.*,p.nom_agence,p.niu,p.login,p.lieu_residence,p.lat,p.lon
        FROM contracts c
        LEFT JOIN proprietaire_conteneur p ON CAST(p.id AS TEXT)=c.company_id
        WHERE c.contract_uid=CAST(:uid AS uuid)
    """), {"uid": contract_uid}).fetchone()
    if not row or not (role == "superadmin" or (role == "owner" and str(row.company_id) == user_id)):
        return jsonify({"error": "Contrat introuvable"}), 404
    pdf = generate_contract_pdf({
        "contract_number": row.contract_number, "company_name": row.nom_agence,
        "starts_on": row.starts_on.strftime("%d/%m/%Y"), "ends_on": row.ends_on.strftime("%d/%m/%Y"),
        "box_count": len(row.box_ids or []), "argos_signer": row.argos_signer_name,
        "argos_signed_at": row.argos_signed_at.strftime("%d/%m/%Y") if row.argos_signed_at else None,
        "company_signer": row.company_signer_name,
        "company_signed_at": row.company_signed_at.strftime("%d/%m/%Y") if row.company_signed_at else None,
        "terms": row.terms or {},
        "niu": row.niu,
        "login": row.login,
        "location": row.lieu_residence,
        "lat": row.lat,
        "lon": row.lon,
    })
    return send_file(io.BytesIO(pdf),mimetype="application/pdf",as_attachment=True,
                     download_name=f"contrat_{row.contract_number}.pdf")


@workflow_bp.route("/api/inventories/<inventory_uid>/document.pdf", methods=["GET"])
def inventory_document(inventory_uid):
    role, user_id = _identity()
    row = db.session.execute(text("""
        SELECT i.*,s.client_id,s.container_id,s.destination,s.cargo_name,s.currency
        FROM inventory_sheets i JOIN shipments s ON s.id=i.shipment_id
        WHERE i.inventory_uid=CAST(:uid AS uuid)
    """), {"uid": inventory_uid}).fetchone()
    if not row or not _can_access_container(role,user_id,row.container_id):
        return jsonify({"error": "Inventaire introuvable"}), 404
    items = db.session.execute(text("""
        SELECT article_reference,article_name,description,quantity,unit_price
        FROM inventory_items WHERE inventory_id=:id ORDER BY sort_order,id
    """), {"id": row.id}).fetchall()
    pdf = generate_inventory_pdf({
        "sheet_number": row.sheet_number, "prepared_by": row.prepared_by,
        "department": row.department, "date": row.inventory_date.strftime("%d/%m/%Y"),
        "container_id": row.container_id, "destination": row.destination, "currency": row.currency,
        "items": [{"reference": item.article_reference,"name": item.article_name,
                   "description": item.description,"quantity": float(item.quantity),
                   "unit_price": float(item.unit_price)} for item in items],
    })
    return send_file(io.BytesIO(pdf),mimetype="application/pdf",as_attachment=True,
                     download_name=f"inventaire_{row.sheet_number}.pdf")


@workflow_bp.route("/api/documents", methods=["GET"])
def list_documents():
    role, user_id = _identity()
    company_filter = request.args.get("company_id")
    if company_filter and role != "superadmin":
        return jsonify({"error": "Acces refuse"}), 403
    documents = []
    contracts = db.session.execute(text("""
        SELECT contract_uid,contract_number,title,status,company_id,created_at
        FROM contracts
        WHERE (:role='superadmin' OR (:role='owner' AND company_id=:uid))
          AND (:company_id IS NULL OR company_id=:company_id)
        ORDER BY created_at DESC
    """), {"role": role, "uid": user_id, "company_id": company_filter}).fetchall()
    documents.extend({
        "uid": str(row.contract_uid), "category": "CONTRACT", "title": row.title,
        "reference": row.contract_number, "status": row.status, "created_at": row.created_at.isoformat(),
        "download_url": f"/api/contracts/{row.contract_uid}/document.pdf",
    } for row in contracts)
    inventories = db.session.execute(text("""
        SELECT i.inventory_uid,i.sheet_number,i.created_at,s.container_id
        FROM inventory_sheets i JOIN shipments s ON s.id=i.shipment_id ORDER BY i.created_at DESC
    """)).fetchall()
    for row in inventories:
        if _can_access_container(role,user_id,row.container_id):
            documents.append({"uid":str(row.inventory_uid),"category":"INVENTORY",
                              "title":f"Inventaire {row.container_id}","reference":row.sheet_number,
                              "status":"AVAILABLE","created_at":row.created_at.isoformat(),
                              "download_url":f"/api/inventories/{row.inventory_uid}/document.pdf"})
    reports = db.session.execute(text("""
        SELECT report_uid,title,category,container_id,created_at FROM generated_reports ORDER BY created_at DESC
    """)).fetchall()
    for row in reports:
        if row.container_id and _can_access_container(role,user_id,row.container_id):
            documents.append({"uid":str(row.report_uid),"category":"REPORT","title":row.title,
                              "reference":str(row.report_uid)[:8].upper(),"status":"AVAILABLE",
                              "created_at":row.created_at.isoformat(),
                              "download_url":f"/api/reports/{row.report_uid}/download"})
    documents.sort(key=lambda item:item["created_at"],reverse=True)
    return jsonify(documents)


@workflow_bp.route("/api/contracts/pending", methods=["GET"])
@roles_required("owner")
def pending_contract():
    _, user_id = _identity()
    row = db.session.execute(text("""
        SELECT contract_uid,contract_number,title,status,starts_on,ends_on,terms,box_ids,
               argos_signer_name,argos_signed_at,created_at
        FROM contracts WHERE company_id=:company AND status='PENDING_ACCEPTANCE'
        ORDER BY created_at DESC LIMIT 1
    """), {"company": user_id}).fetchone()
    if not row:
        return jsonify({"contract": None}), 404
    result = dict(row._mapping)
    for key, value in list(result.items()):
        if hasattr(value, "isoformat"):
            result[key] = value.isoformat()
    return jsonify({"contract": result})


@workflow_bp.route("/api/contracts/<contract_uid>/decision", methods=["POST"])
@roles_required("owner")
def decide_contract(contract_uid):
    identity = current_identity()
    user_id = str(identity.get("user_id"))
    payload = request.get_json(silent=True) or {}
    decision = str(payload.get("decision") or "").upper()
    signer = str(payload.get("signer_name") or "").strip()
    accepted_terms = bool(payload.get("accepted_terms"))
    if decision not in ("ACCEPT", "REJECT"):
        return jsonify({"error": "decision doit etre ACCEPT ou REJECT"}), 400
    if decision == "ACCEPT" and (not accepted_terms or len(signer) < 2):
        return jsonify({"error": "Lecture des termes et nom du signataire requis"}), 400
    row = db.session.execute(text("""
        SELECT id,status FROM contracts
        WHERE contract_uid=CAST(:uid AS uuid) AND company_id=:company FOR UPDATE
    """), {"uid": contract_uid, "company": user_id}).fetchone()
    if not row or row.status != "PENDING_ACCEPTANCE":
        db.session.rollback()
        return jsonify({"error": "Contrat introuvable ou deja traite"}), 409
    if decision == "ACCEPT":
        db.session.execute(text("""
            UPDATE contracts SET status='ACCEPTED',company_signer_name=:signer,
                company_signed_at=NOW(),accepted_ip=CAST(:ip AS inet),updated_at=NOW() WHERE id=:id
        """), {"signer": signer, "ip": request.remote_addr, "id": row.id})
        db.session.execute(text("""
            UPDATE identity_registry SET terms_accepted_at=NOW(),updated_at=NOW()
            WHERE actor_role='owner' AND actor_id=:actor
        """), {"actor": user_id})
        status = "ACCEPTED"
    else:
        db.session.execute(text("""
            UPDATE contracts SET status='REJECTED',rejection_reason=:reason,updated_at=NOW() WHERE id=:id
        """), {"reason": str(payload.get("reason") or "Refus par le signataire"), "id": row.id})
        db.session.execute(text("""
            UPDATE boite_noir SET id_proprietaire=NULL,status='unassigned'
            WHERE id_boite IN (
                SELECT CAST(value AS INTEGER) FROM contracts c, jsonb_array_elements_text(c.box_ids)
                WHERE c.id=:id
            ) AND id_conteneurs IS NULL
        """), {"id": row.id})
        status = "REJECTED"
    db.session.commit()
    if status == "ACCEPTED":
        token = issue_access_token(
            identity.get("role"), identity.get("user_id"), identity.get("login"),
            identity.get("display_name"), "full",
        )
        return jsonify({"status": status, "access_token": token})
    return jsonify({"status": status})


def _eligible_voters(container_id, black_box_id):
    voters = []
    owner = db.session.execute(text("""
        SELECT CAST(id_proprietaire AS TEXT) FROM boite_noir WHERE id_boite=:box
    """), {"box": black_box_id}).scalar()
    if owner:
        voters.append(("owner", str(owner)))
    shipment = db.session.execute(text("""
        SELECT client_id, driver_id, company_id FROM shipments
        WHERE container_id=:container AND status NOT IN ('COMPLETED','CANCELLED')
        ORDER BY created_at DESC LIMIT 1
    """), {"container": container_id}).fetchone()
    if shipment:
        for role, actor_id in zip(("client", "driver", "company"), shipment):
            if actor_id:
                voters.append((role, str(actor_id)))
    return list(dict.fromkeys(voters))


@workflow_bp.route("/api/destocking/requests", methods=["POST"])
def create_destocking_request():
    role, user_id = _identity()
    payload = request.get_json(silent=True) or {}
    container_id = str(payload.get("container_id") or "").strip()
    reason = str(payload.get("reason") or "").strip()
    if not container_id or not reason:
        return jsonify({"error": "container_id et motif requis"}), 400
    if role == "driver" or not _can_access_container(role, user_id, container_id):
        return jsonify({"error": "Vous ne pouvez pas initier ce destockage"}), 403
    box = db.session.execute(text("""
        SELECT id_boite FROM boite_noir
        WHERE id_conteneurs=:container AND COALESCE(archived,FALSE)=FALSE LIMIT 1
    """), {"container": container_id}).scalar()
    if not box:
        return jsonify({"error": "Aucune boite active sur ce conteneur"}), 409
    voters = _eligible_voters(container_id, box)
    if not voters:
        return jsonify({"error": "Aucun acteur eligible au vote"}), 409
    required = math.floor(len(voters) / 2) + 1
    deadline = datetime.now(timezone.utc) + timedelta(hours=int(payload.get("vote_hours") or 24))
    try:
        request_id = db.session.execute(text("""
            INSERT INTO destocking_requests
                (shipment_id,container_id,black_box_id,initiated_by_role,initiated_by_id,
                 reason,eligible_voter_count,required_approvals,vote_deadline)
            VALUES ((SELECT id FROM shipments WHERE container_id=:container
                     AND status NOT IN ('COMPLETED','CANCELLED') ORDER BY created_at DESC LIMIT 1),
                    :container,:box,:role,:uid,:reason,:count,:required,:deadline)
            RETURNING id
        """), {
            "container": container_id, "box": box, "role": role, "uid": user_id,
            "reason": reason, "count": len(voters), "required": required, "deadline": deadline,
        }).scalar()
        for voter_role, voter_id in voters:
            db.session.execute(text("""
                INSERT INTO destocking_votes (request_id,voter_role,voter_id)
                VALUES (:request_id,:role,:uid) ON CONFLICT DO NOTHING
            """), {"request_id": request_id, "role": voter_role, "uid": voter_id})
        db.session.execute(text("""
            INSERT INTO notifications(type,message,cible_role,id_boite,initiator_id)
            VALUES ('DESTOCKING_VOTE',:message,'all',:box,:uid)
        """), {"message": f"Validation requise pour le destockage de {container_id}: {reason}", "box": box, "uid": user_id})
        db.session.commit()
        return jsonify({
            "status": "success", "request_id": request_id, "voters": len(voters),
            "required_approvals": required, "vote_deadline": deadline.isoformat(),
        }), 201
    except Exception as exc:
        db.session.rollback()
        return jsonify({"error": "Impossible de creer la demande", "code": "DESTOCKING_CREATE_FAILED"}), 500


@workflow_bp.route("/api/destocking/requests/<int:request_id>", methods=["GET"])
def get_destocking_request(request_id):
    role, user_id = _identity()
    row = db.session.execute(text("SELECT * FROM destocking_requests WHERE id=:id"), {"id": request_id}).fetchone()
    if not row or not _can_access_container(role, user_id, row.container_id):
        return jsonify({"error": "Demande introuvable"}), 404
    votes = db.session.execute(text("""
        SELECT voter_role, decision, voted_at FROM destocking_votes WHERE request_id=:id
        ORDER BY voter_role
    """), {"id": request_id}).fetchall()
    result = dict(row._mapping)
    result["votes"] = [dict(v._mapping) for v in votes]
    for key, value in list(result.items()):
        if isinstance(value, datetime):
            result[key] = value.isoformat()
    return jsonify(result)


@workflow_bp.route("/api/destocking/requests/<int:request_id>/vote", methods=["POST"])
def vote_destocking_request(request_id):
    role, user_id = _identity()
    decision = str((request.get_json(silent=True) or {}).get("decision") or "").upper()
    if decision not in ("APPROVE", "REJECT"):
        return jsonify({"error": "decision doit etre APPROVE ou REJECT"}), 400
    request_row = db.session.execute(text("""
        SELECT * FROM destocking_requests WHERE id=:id FOR UPDATE
    """), {"id": request_id}).fetchone()
    if not request_row or request_row.status != "PENDING_VOTES":
        db.session.rollback()
        return jsonify({"error": "Vote ferme ou demande introuvable"}), 409
    vote = db.session.execute(text("""
        SELECT id,decision FROM destocking_votes
        WHERE request_id=:id AND voter_role=:role AND voter_id=:uid FOR UPDATE
    """), {"id": request_id, "role": role, "uid": user_id}).fetchone()
    if not vote:
        db.session.rollback()
        return jsonify({"error": "Vous ne faites pas partie des votants"}), 403
    if vote.decision:
        db.session.rollback()
        return jsonify({"error": "Votre vote est deja enregistre"}), 409
    db.session.execute(text("""
        UPDATE destocking_votes SET decision=:decision,voted_at=NOW() WHERE id=:id
    """), {"decision": decision, "id": vote.id})
    counts = db.session.execute(text("""
        SELECT COUNT(*) FILTER (WHERE decision='APPROVE'),
               COUNT(*) FILTER (WHERE decision='REJECT'), COUNT(*)
        FROM destocking_votes WHERE request_id=:id
    """), {"id": request_id}).fetchone()
    approvals, rejections, total = int(counts[0]), int(counts[1]), int(counts[2])
    new_status = "PENDING_VOTES"
    detach_at = None
    if approvals >= request_row.required_approvals:
        new_status = "APPROVED"
        detach_at = datetime.now(timezone.utc) + timedelta(hours=24)
    elif rejections > total - request_row.required_approvals:
        new_status = "REJECTED"
    db.session.execute(text("""
        UPDATE destocking_requests SET status=:status, decided_at=CASE WHEN :status!='PENDING_VOTES' THEN NOW() ELSE NULL END,
               detach_at=:detach_at, updated_at=NOW() WHERE id=:id
    """), {"status": new_status, "detach_at": detach_at, "id": request_id})
    if new_status == "APPROVED":
        db.session.execute(text("""
            INSERT INTO background_jobs(job_uid,job_type,payload,run_at)
            VALUES(CAST(:uid AS uuid),'DETACH_AFTER_DESTOCKING',CAST(:payload AS jsonb),:run_at)
        """), {"uid": str(uuid4()), "payload": json.dumps({"request_id": request_id}), "run_at": detach_at})
    db.session.commit()
    return jsonify({
        "status": new_status, "approvals": approvals, "rejections": rejections,
        "required_approvals": request_row.required_approvals,
        "detach_at": detach_at.isoformat() if detach_at else None,
    })

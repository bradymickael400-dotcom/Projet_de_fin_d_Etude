
"""Gestion des utilisateurs, clients, transporteurs et entreprises.

Ce module expose les endpoints d’inscription, de consultation et de mise à jour
pour les différents profils accessibles depuis l’interface ARGOS.
"""

import os
import time
import json
import uuid
from datetime import datetime
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename
from flask import Blueprint, current_app, request, jsonify, url_for, render_template
from sqlalchemy import text # type: ignore

from app import db
from app.utils import _sceller_evenement, get_boites_for_owner
from app.utils import *
from app.routes.auth import _login_exists, _login_suggestions
from app.security import roles_required
from app.modules.iot.iot_service import provision_device

users_bp = Blueprint("users", __name__)


def _duplicate_login_response(login):
    normalized = (login or "").strip()
    if normalized and _login_exists(normalized):
        return jsonify({
            "error": "Ce login est deja utilise par un autre compte.",
            "code": "LOGIN_ALREADY_EXISTS",
            "suggestions": _login_suggestions(normalized),
        }), 409
    return None


def _ensure_client_cni_file_column():
    try:
        db.session.execute(text("ALTER TABLE client ADD COLUMN IF NOT EXISTS cni_file TEXT"))
        db.session.commit()
    except Exception:
        db.session.rollback()


def _ensure_transporteur_schema():
    try:
        db.session.execute(text("ALTER TABLE transporteur ADD COLUMN IF NOT EXISTS id_boite TEXT"))
        db.session.execute(text("ALTER TABLE transporteur ADD COLUMN IF NOT EXISTS blocked BOOLEAN DEFAULT FALSE"))
        db.session.execute(text("ALTER TABLE transporteur ADD COLUMN IF NOT EXISTS id_boites TEXT DEFAULT '[]'"))
        db.session.execute(text("ALTER TABLE transporteur ADD COLUMN IF NOT EXISTS cni_file TEXT"))
        db.session.execute(text(
            """
            CREATE TABLE IF NOT EXISTS driver_messages (
                id SERIAL PRIMARY KEY,
                id_cni TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
            """
        ))
        db.session.commit()
    except Exception:
        db.session.rollback()


def _ensure_client_created_by():
    try:
        db.session.execute(text("ALTER TABLE client ADD COLUMN IF NOT EXISTS created_by TEXT"))
        db.session.commit()
    except Exception:
        db.session.rollback()


def _ensure_company_schema():
    try:
        db.session.execute(text("ALTER TABLE proprietaire_conteneur ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITH TIME ZONE"))
        db.session.execute(text("ALTER TABLE proprietaire_conteneur ADD COLUMN IF NOT EXISTS deleted_by TEXT"))
        db.session.execute(text("ALTER TABLE proprietaire_conteneur ADD COLUMN IF NOT EXISTS delete_reason TEXT"))
        db.session.execute(text("ALTER TABLE agence_utilisatrice ADD COLUMN IF NOT EXISTS created_by TEXT DEFAULT 'system'"))
        db.session.commit()
    except Exception:
        db.session.rollback()


def _ensure_account_delete_schema():
    try:
        db.session.execute(text("ALTER TABLE proprietaire_conteneur ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITH TIME ZONE"))
        db.session.execute(text("ALTER TABLE proprietaire_conteneur ADD COLUMN IF NOT EXISTS deleted_by TEXT"))
        db.session.execute(text("ALTER TABLE proprietaire_conteneur ADD COLUMN IF NOT EXISTS delete_reason TEXT"))
        db.session.execute(text("ALTER TABLE client ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITH TIME ZONE"))
        db.session.execute(text("ALTER TABLE client ADD COLUMN IF NOT EXISTS deleted_by TEXT"))
        db.session.execute(text("ALTER TABLE client ADD COLUMN IF NOT EXISTS delete_reason TEXT"))
        db.session.execute(text("ALTER TABLE transporteur ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITH TIME ZONE"))
        db.session.execute(text("ALTER TABLE transporteur ADD COLUMN IF NOT EXISTS deleted_by TEXT"))
        db.session.execute(text("ALTER TABLE transporteur ADD COLUMN IF NOT EXISTS delete_reason TEXT"))
        db.session.execute(text("ALTER TABLE abonner ADD COLUMN IF NOT EXISTS fin_a TIMESTAMP WITH TIME ZONE"))
        db.session.execute(text("""
            CREATE OR REPLACE FUNCTION sync_identity_registry() RETURNS trigger LANGUAGE plpgsql AS $$
            DECLARE
                v_actor_role text := TG_ARGV[0];
                v_id_column text := TG_ARGV[1];
                v_actor_id text;
                v_normalized text;
                v_shown text;
            BEGIN
                IF TG_OP='DELETE' THEN
                    v_actor_id := to_jsonb(OLD)->>v_id_column;
                    DELETE FROM identity_registry r
                    WHERE r.actor_role=v_actor_role AND r.actor_id=v_actor_id;
                    RETURN OLD;
                END IF;

                v_actor_id := to_jsonb(NEW)->>v_id_column;
                v_normalized := lower(trim(to_jsonb(NEW)->>'login'));
                IF v_normalized IS NULL OR v_normalized='' THEN
                    RAISE EXCEPTION 'login obligatoire';
                END IF;

                v_shown := COALESCE(
                    to_jsonb(NEW)->>'nom_agence',
                    to_jsonb(NEW)->>'full_name',
                    trim(COALESCE(to_jsonb(NEW)->>'prenom','') || ' ' || COALESCE(to_jsonb(NEW)->>'nom','')),
                    to_jsonb(NEW)->>'login'
                );

                IF TG_OP='UPDATE' THEN
                    DELETE FROM identity_registry r
                    WHERE r.actor_role=v_actor_role AND r.actor_id=v_actor_id;
                END IF;

                INSERT INTO identity_registry(login_normalized,actor_role,actor_id,display_name)
                VALUES(v_normalized,v_actor_role,v_actor_id,NULLIF(trim(v_shown),''));
                RETURN NEW;
            END $$;
        """))
        db.session.commit()
    except Exception:
        db.session.rollback()


def _seal_deletion_event(event_type, entity_id, payload):
    try:
        _sceller_evenement(event_type, None, {
            **(payload or {}),
            "entity_id": str(entity_id),
            "deleted_at": datetime.utcnow().isoformat(),
        })
    except Exception as exc:
        current_app.logger.warning("Blockchain deletion seal failed: %s", exc)


def _create_company_modification_contract(company_id, changes, actor_id):
    company = db.session.execute(text("""
        SELECT id, nom_agence, addresse_mail, lieu_residence
        FROM proprietaire_conteneur WHERE id=:id
    """), {"id": company_id}).fetchone()
    if not company:
        return None
    box_ids = db.session.execute(text("""
        SELECT id_boite FROM boite_noir
        WHERE id_proprietaire=:id AND COALESCE(archived,FALSE)=FALSE
        ORDER BY id_boite
    """), {"id": company_id}).fetchall()
    contract_number = f"ARGOS-MOD-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
    return db.session.execute(text("""
        INSERT INTO contracts
            (company_id,contract_number,title,status,starts_on,ends_on,terms,box_ids,
             argos_signer_name,argos_signed_at,created_by)
        VALUES (:company,:number,:title,'PENDING_ACCEPTANCE',CURRENT_DATE,
                CURRENT_DATE + INTERVAL '12 months',CAST(:terms AS jsonb),
                CAST(:boxes AS jsonb),'Direction generale ARGOS',NOW(),:created_by)
        RETURNING contract_uid
    """), {
        "company": str(company_id),
        "number": contract_number,
        "title": f"Contrat de modification profil - {company.nom_agence}",
        "terms": json.dumps({
            "type": "PROFILE_MODIFICATION",
            "changes": changes,
            "email": company.addresse_mail,
            "location": company.lieu_residence,
        }),
        "boxes": json.dumps([int(row[0]) for row in box_ids]),
        "created_by": str(actor_id),
    }).scalar()

# ═══════════════════════════════════════════════════════════════════
#  LISTES (companies, clients, drivers) — avec restriction
# ═══════════════════════════════════════════════════

@users_bp.route("/api/companies", methods=["GET"])
@roles_required("superadmin")
def get_companies():
    _ensure_company_schema()
    # Superadmin uniquement — les owners voient leurs propres données via dashboard/owner
    rows = db.session.execute(text("""
        SELECT p.id, p.niu, p.nom_agence, p.login, p.addresse_mail,
               p.lieu_residence, p.lat, p.lon, p.nbr_boite, p.created_at,
               COUNT(DISTINCT b.id_boite) AS nb_boites,
               COUNT(DISTINCT a.numero_a) AS nb_abonnes
        FROM proprietaire_conteneur p
        LEFT JOIN boite_noir b ON b.id_proprietaire = p.id
        LEFT JOIN abonner a ON a.id_boite = b.id_boite AND a.status='Actif'
        WHERE p.deleted_at IS NULL
        GROUP BY p.id ORDER BY p.id DESC
    """)).fetchall()
    return jsonify([dict(r._mapping) for r in rows])


@users_bp.route("/api/companies/<int:company_id>", methods=["DELETE"])
@roles_required("superadmin")
def delete_company(company_id):
    try:
        _ensure_account_delete_schema()
        role, actor_id = get_caller_identity()
        data = request.get_json(silent=True) or {}
        reason = (data.get("reason") or "Suppression compte entreprise").strip()
        company = db.session.execute(text("""
            SELECT id, nom_agence FROM proprietaire_conteneur
            WHERE id=:id AND deleted_at IS NULL FOR UPDATE
        """), {"id": company_id}).fetchone()
        if not company:
            return jsonify({"error": "Entreprise introuvable"}), 404

        box_rows = db.session.execute(text("""
            SELECT id_boite FROM boite_noir
            WHERE id_proprietaire=:id AND COALESCE(archived,FALSE)=FALSE
            FOR UPDATE
        """), {"id": company_id}).fetchall()
        box_ids = [int(row.id_boite) for row in box_rows]

        inactive_subscriptions = 0
        if box_ids:
            box_params = {f"box{i}": value for i, value in enumerate(box_ids)}
            box_placeholders = ",".join(f":box{i}" for i in range(len(box_ids)))
            inactive_result = db.session.execute(text("""
                UPDATE abonner
                SET status='Inactif', fin_a=COALESCE(fin_a,NOW())
                WHERE id_boite IN (""" + box_placeholders + """) AND status='Actif'
            """), box_params)
            inactive_subscriptions = getattr(inactive_result, "rowcount", 0) or 0

            db.session.execute(text("""
                UPDATE boite_noir
                SET id_proprietaire=NULL,
                    id_conteneurs=NULL,
                    status='unassigned',
                    updated_at=NOW()
                WHERE id_boite IN (""" + box_placeholders + """)
            """), box_params)

        db.session.execute(text("""
            UPDATE shipments
            SET status='CANCELLED', updated_at=NOW()
            WHERE company_id=CAST(:company_id AS TEXT)
              AND status IN ('PLANNED','LOADED','IN_TRANSIT','ARRIVED','DESTOCKING')
        """), {"company_id": company_id})

        db.session.execute(text("""
            UPDATE contracts
            SET status='CANCELLED', updated_at=NOW()
            WHERE company_id=CAST(:company_id AS TEXT)
              AND status IN ('DRAFT','PENDING_ACCEPTANCE','ACCEPTED')
        """), {"company_id": company_id})

        result = db.session.execute(text("""
            UPDATE proprietaire_conteneur
            SET deleted_at=NOW(), deleted_by=:actor, delete_reason=:reason,
                login=COALESCE(login,'') || '__deleted__' || :suffix
            WHERE id=:id AND deleted_at IS NULL
        """), {"id": company_id, "actor": f"{role}:{actor_id}", "reason": reason, "suffix": str(uuid.uuid4())[:8]})
        if getattr(result, "rowcount", 0) == 0:
            db.session.rollback()
            return jsonify({"error": "Entreprise introuvable"}), 404

        db.session.commit()
        _seal_deletion_event("COMPTE_ENTREPRISE_SUPPRIME", company_id, {
            "type": "company",
            "company_id": company_id,
            "nom_agence": company.nom_agence,
            "boites_liberees": box_ids,
            "abonnements_desactives": inactive_subscriptions,
            "deleted_by": f"{role}:{actor_id}",
            "reason": reason,
        })
        return jsonify({
            "status": "success",
            "message": "Compte entreprise supprime et boites liberees.",
            "company_id": company_id,
            "boites_liberees": box_ids,
            "abonnements_desactives": inactive_subscriptions,
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@users_bp.route("/api/companies/<int:company_id>/documents", methods=["GET"])
@roles_required("superadmin")
def get_company_documents(company_id):
    documents = []
    rows = db.session.execute(text("""
        SELECT contract_uid, contract_number, title, status, created_at
        FROM contracts
        WHERE company_id=CAST(:company_id AS TEXT)
        ORDER BY created_at DESC
    """), {"company_id": company_id}).fetchall()
    documents.extend({
        "uid": str(row.contract_uid),
        "category": "CONTRACT",
        "title": row.title,
        "reference": row.contract_number,
        "status": row.status,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "download_url": f"/api/contracts/{row.contract_uid}/document.pdf",
    } for row in rows)

    reports = db.session.execute(text("""
        SELECT r.report_uid, r.title, r.category, r.container_id, r.created_at
        FROM generated_reports r
        LEFT JOIN boite_noir b ON b.id_boite=r.black_box_id
        WHERE CAST(b.id_proprietaire AS TEXT)=CAST(:company_id AS TEXT)
        ORDER BY r.created_at DESC
    """), {"company_id": company_id}).fetchall()
    documents.extend({
        "uid": str(row.report_uid),
        "category": row.category or "REPORT",
        "title": row.title,
        "reference": row.container_id or str(row.report_uid)[:8].upper(),
        "status": "AVAILABLE",
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "download_url": f"/api/reports/{row.report_uid}/download",
    } for row in reports)

    inventories = db.session.execute(text("""
        SELECT i.inventory_uid, i.sheet_number, i.created_at, s.container_id
        FROM inventory_sheets i
        JOIN shipments s ON s.id=i.shipment_id
        WHERE CAST(s.company_id AS TEXT)=CAST(:company_id AS TEXT)
        ORDER BY i.created_at DESC
    """), {"company_id": company_id}).fetchall()
    documents.extend({
        "uid": str(row.inventory_uid),
        "category": "INVENTORY",
        "title": f"Inventaire {row.container_id}",
        "reference": row.sheet_number,
        "status": "AVAILABLE",
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "download_url": f"/api/inventories/{row.inventory_uid}/document.pdf",
    } for row in inventories)

    documents.sort(key=lambda item: item.get("created_at") or "", reverse=True)
    return jsonify(documents)

@users_bp.route("/api/clients", methods=["GET"])
def get_clients():
    role, user_id = get_caller_identity()
    if not role or not user_id:
        return jsonify({"error": "Accès non autorisé"}), 401
    _ensure_client_cni_file_column()
    _ensure_account_delete_schema()
    if role == "owner":
        # Owner voit uniquement ses abonnés
        boites = get_boites_for_owner(user_id)
        if not boites:
            return jsonify([])
        placeholders = ",".join([f":b{i}" for i in range(len(boites))])
        rows = db.session.execute(text(f"""
            SELECT cl.id_cni, cl.nom, cl.prenom, cl.login, cl.address_mail, cl.cni_file,
                   NULL AS contact, cl.created_at,
                   a.numero_a, a.id_boite, a.type_abonnement AS type_a,
                   a.created_at AS debut_a, NULL::timestamp AS fin_a,
                   a.status, NULL::numeric AS frais
            FROM client cl
            JOIN abonner a ON a.id_cni = cl.id_cni
            WHERE a.id_boite IN ({placeholders}) AND cl.deleted_at IS NULL
            ORDER BY cl.created_at DESC
        """), {f"b{i}": v for i, v in enumerate(boites)}).fetchall()
    elif role == "client":
        # Client voit uniquement ses propres données
        rows = db.session.execute(text("""
            SELECT cl.id_cni, cl.nom, cl.prenom, cl.login, cl.address_mail, cl.cni_file,
                   NULL AS contact, cl.created_at,
                   a.numero_a, a.id_boite, a.type_abonnement AS type_a,
                   a.created_at AS debut_a, NULL::timestamp AS fin_a,
                   a.status, NULL::numeric AS frais
            FROM client cl
            LEFT JOIN abonner a ON a.id_cni = cl.id_cni
            WHERE cl.id_cni = :uid AND cl.deleted_at IS NULL
        """), {"uid": user_id}).fetchall()
    elif role == "company":
        boites = get_boites_for_agency(user_id)
        if not boites:
            return jsonify([])
        placeholders = ",".join([f":cb{i}" for i in range(len(boites))])
        rows = db.session.execute(text(f"""
            SELECT cl.id_cni,cl.nom,cl.prenom,cl.login,cl.address_mail,cl.cni_file,
                   NULL AS contact,cl.created_at,a.numero_a,a.id_boite,
                   a.type_abonnement AS type_a,a.created_at AS debut_a,
                   a.fin_a,NULL::numeric AS frais,a.status
            FROM client cl JOIN abonner a ON a.id_cni=cl.id_cni
            WHERE a.id_boite IN ({placeholders}) AND cl.deleted_at IS NULL ORDER BY cl.created_at DESC
        """), {f"cb{i}": value for i, value in enumerate(boites)}).fetchall()
    elif role == "superadmin":
        rows = db.session.execute(text("""
            SELECT cl.id_cni, cl.nom, cl.prenom, cl.login, cl.address_mail, cl.cni_file,
                   NULL AS contact, cl.created_at,
                   a.numero_a, a.id_boite, a.type_abonnement AS type_a,
                   a.created_at AS debut_a, NULL::timestamp AS fin_a,
                   a.status, NULL::numeric AS frais
            FROM client cl
            LEFT JOIN abonner a ON a.id_cni = cl.id_cni
            WHERE cl.deleted_at IS NULL
            ORDER BY cl.created_at DESC
        """)).fetchall()
    else:
        return jsonify({"error": "Acces refuse"}), 403
    result = [dict(r._mapping) for r in rows]
    client_ids = list({str(item["id_cni"]) for item in result if item.get("id_cni")})
    shipment_summary = {}
    if client_ids:
        summaries = db.session.execute(text("""
            SELECT client_id,COALESCE(SUM(declared_value),0) AS total_value,
                   ARRAY_AGG(DISTINCT destination) FILTER (WHERE destination IS NOT NULL) AS destinations,
                   ARRAY_AGG(DISTINCT cargo_name) FILTER (WHERE cargo_name IS NOT NULL) AS cargo_names,
                   COUNT(*) AS shipment_count
            FROM shipments WHERE client_id=ANY(:client_ids) GROUP BY client_id
        """), {"client_ids": client_ids}).fetchall()
        shipment_summary = {str(row.client_id): row for row in summaries}
    for item in result:
        summary = shipment_summary.get(str(item.get("id_cni")))
        item["cargo_value"] = float(summary.total_value) if summary else 0
        item["destinations"] = list(summary.destinations or []) if summary else []
        item["cargo_names"] = list(summary.cargo_names or []) if summary else []
        item["shipment_count"] = int(summary.shipment_count) if summary else 0
    return jsonify(result)

@users_bp.route("/api/drivers", methods=["GET"])
def get_drivers():
    role, user_id = get_caller_identity()
    try:
        _ensure_account_delete_schema()
        select_columns = """
            SELECT DISTINCT t.id_cni,t.nom,t.prenom,t.login,t.contact,
                   t.id_boite,t.id_boites,t.blocked,t.created_at
            FROM transporteur t
        """
        params = {}
        if role == "superadmin":
            sql = select_columns + " WHERE t.deleted_at IS NULL ORDER BY t.created_at DESC"
        elif role == "driver":
            sql = select_columns + " WHERE t.id_cni=:uid AND t.deleted_at IS NULL"
            params["uid"] = user_id
        elif role == "client":
            sql = select_columns + " JOIN colis co ON co.id_cni_transporteur=t.id_cni WHERE co.id_cni_client=:uid AND t.deleted_at IS NULL"
            params["uid"] = user_id
        elif role in ("owner", "company"):
            boites = get_boites_for_owner(user_id) if role == "owner" else get_boites_for_agency(user_id)
            if not boites:
                return jsonify([])
            placeholders = ",".join(f":db{i}" for i in range(len(boites)))
            params.update({f"db{i}": value for i, value in enumerate(boites)})
            sql = select_columns + f"""
                JOIN colis co ON co.id_cni_transporteur=t.id_cni
                JOIN abonner a ON a.id_cni=co.id_cni_client
                WHERE a.id_boite IN ({placeholders}) AND t.deleted_at IS NULL
                ORDER BY t.created_at DESC
            """
        else:
            return jsonify({"error": "Acces refuse"}), 403
        rows = db.session.execute(text(sql), params).fetchall()
        return jsonify([dict(r._mapping) for r in rows])
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@users_bp.route("/api/clients/<path:id_cni>", methods=["DELETE"])
@roles_required("superadmin", "owner")
def delete_client_account(id_cni):
    try:
        _ensure_account_delete_schema()
        role, actor_id = get_caller_identity()
        data = request.get_json(silent=True) or {}
        reason = (data.get("reason") or "Suppression compte client").strip()
        client = db.session.execute(text("""
            SELECT id_cni, nom, prenom, login FROM client
            WHERE id_cni=:id AND deleted_at IS NULL FOR UPDATE
        """), {"id": id_cni}).fetchone()
        if not client:
            return jsonify({"error": "Client introuvable"}), 404

        box_rows = db.session.execute(text("""
            SELECT DISTINCT id_boite FROM abonner
            WHERE id_cni=:id AND status='Actif'
        """), {"id": id_cni}).fetchall()
        box_ids = [row.id_boite for row in box_rows]
        if role == "owner":
            visible = {str(value) for value in (get_boites_for_owner(actor_id) or [])}
            if not box_ids or any(str(value) not in visible for value in box_ids):
                return jsonify({"error": "Accès refusé pour ce client"}), 403

        db.session.execute(text("""
            UPDATE abonner SET status='Inactif', fin_a=COALESCE(fin_a,NOW())
            WHERE id_cni=:id AND status='Actif'
        """), {"id": id_cni})
        db.session.execute(text("""
            UPDATE shipments SET status='CANCELLED', updated_at=NOW()
            WHERE client_id=:id AND status IN ('PLANNED','LOADED','IN_TRANSIT','ARRIVED','DESTOCKING')
        """), {"id": id_cni})
        result = db.session.execute(text("""
            UPDATE client
            SET deleted_at=NOW(), deleted_by=:actor, delete_reason=:reason,
                login=COALESCE(login,'') || '__deleted__' || :suffix
            WHERE id_cni=:id AND deleted_at IS NULL
        """), {"id": id_cni, "actor": f"{role}:{actor_id}", "reason": reason, "suffix": str(uuid.uuid4())[:8]})
        if getattr(result, "rowcount", 0) == 0:
            db.session.rollback()
            return jsonify({"error": "Client introuvable"}), 404
        db.session.commit()
        _seal_deletion_event("COMPTE_CLIENT_SUPPRIME", id_cni, {
            "type": "client",
            "id_cni": id_cni,
            "nom": f"{client.nom or ''} {client.prenom or ''}".strip(),
            "boites": box_ids,
            "deleted_by": f"{role}:{actor_id}",
            "reason": reason,
        })
        return jsonify({"status": "success", "message": "Compte client supprimé.", "id_cni": id_cni, "boites_liberees": box_ids}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@users_bp.route("/api/drivers/<path:id_cni>", methods=["DELETE"])
@roles_required("superadmin", "owner")
def delete_driver_account(id_cni):
    try:
        _ensure_account_delete_schema()
        role, actor_id = get_caller_identity()
        data = request.get_json(silent=True) or {}
        reason = (data.get("reason") or "Suppression compte chauffeur").strip()
        driver = db.session.execute(text("""
            SELECT id_cni, nom, prenom, login, id_boite, id_boites FROM transporteur
            WHERE id_cni=:id AND deleted_at IS NULL FOR UPDATE
        """), {"id": id_cni}).fetchone()
        if not driver:
            return jsonify({"error": "Chauffeur introuvable"}), 404

        assigned = []
        if driver.id_boite:
            assigned.append(driver.id_boite)
        if driver.id_boites:
            try:
                parsed = json.loads(driver.id_boites)
                if isinstance(parsed, list):
                    assigned.extend(parsed)
            except Exception:
                pass
        assigned = list(dict.fromkeys([value for value in assigned if value]))
        if role == "owner":
            visible = {str(value) for value in (get_boites_for_owner(actor_id) or [])}
            if assigned and any(str(value) not in visible for value in assigned):
                return jsonify({"error": "Accès refusé pour ce chauffeur"}), 403

        db.session.execute(text("""
            UPDATE colis SET id_cni_transporteur=NULL
            WHERE id_cni_transporteur=:id
        """), {"id": id_cni})
        result = db.session.execute(text("""
            UPDATE transporteur
            SET deleted_at=NOW(), deleted_by=:actor, delete_reason=:reason,
                blocked=TRUE, id_boite=NULL, id_boites='[]',
                login=COALESCE(login,'') || '__deleted__' || :suffix
            WHERE id_cni=:id AND deleted_at IS NULL
        """), {"id": id_cni, "actor": f"{role}:{actor_id}", "reason": reason, "suffix": str(uuid.uuid4())[:8]})
        if getattr(result, "rowcount", 0) == 0:
            db.session.rollback()
            return jsonify({"error": "Chauffeur introuvable"}), 404
        db.session.commit()
        _seal_deletion_event("COMPTE_CHAUFFEUR_SUPPRIME", id_cni, {
            "type": "driver",
            "id_cni": id_cni,
            "nom": f"{driver.nom or ''} {driver.prenom or ''}".strip(),
            "boites": assigned,
            "deleted_by": f"{role}:{actor_id}",
            "reason": reason,
        })
        return jsonify({"status": "success", "message": "Compte chauffeur supprimé.", "id_cni": id_cni, "boites_liberees": assigned}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
    # if role == "driver":
    #     rows = db.session.execute(text("""
    #         SELECT t.id_cni, t.nom_chauffeurs, t.login, t.created_at,
    #                co.id_colis, co.nom_colis, co.lieux_expedition,
    #                co.lieux_receptions, co.moyen_transport
    #         FROM transporteur t
    #         LEFT JOIN colis co ON co.id_cni_transporteur = t.id_cni
    #         WHERE t.id_cni = :uid
    #     """), {"uid": user_id}).fetchall()
    # elif role == "owner":
    #     boites = get_boites_for_owner(user_id)
    #     if not boites:
    #         return jsonify([])
    #     placeholders = ",".join([f":b{i}" for i in range(len(boites))])
    #     rows = db.session.execute(text(f"""
    #         SELECT DISTINCT t.id_cni, t.nom_chauffeurs, t.login, t.created_at,
    #                co.id_colis, co.nom_colis, co.lieux_expedition,
    #                co.lieux_receptions, co.moyen_transport
    #         FROM transporteur t
    #         JOIN colis co ON co.id_cni_transporteur = t.id_cni
    #         JOIN abonner a ON a.id_cni = co.id_cni_client
    #         WHERE a.id_boite IN ({placeholders})
    #         ORDER BY t.created_at DESC
    #     """), {f"b{i}": v for i, v in enumerate(boites)}).fetchall()
    # else:
    #     rows = db.session.execute(text("""
    #         SELECT t.id_cni, t.nom_chauffeurs, t.login, t.created_at,
    #                co.id_colis, co.nom_colis, co.lieux_expedition,
    #                co.lieux_receptions, co.moyen_transport
    #         FROM transporteur t
    #         LEFT JOIN colis co ON co.id_cni_transporteur = t.id_cni
    #         ORDER BY t.created_at DESC
    #     """)).fetchall()
    # return jsonify([dict(r._mapping) for r in rows])

# Remplace la route existante par celle-ci
@users_bp.route("/api/register_user_file", methods=["POST"])
@roles_required("superadmin", "owner")
def register_user_file():
    try:
        _ensure_client_cni_file_column()
        _ensure_client_created_by()
        f       = request.form
        nom_ag  = f.get("nom_agence")
        login   = f.get("login")
        pwd     = f.get("password")
        email   = f.get("email") or f.get("address_mail")
        niu     = f.get("niu") or f.get("id_cni")
        nom     = f.get("nom")
        prenom  = f.get("prenom")
        contact = f.get("contact") or f.get("phone")
        created_by = f.get("created_by") or f.get("user_id") or "system"
        
        # Données d'affiliation extraites du formulaire étendu
        id_boite = f.get("id_boite")
        type_a   = f.get("type_a", "Mensuel")
        role, actor_id = get_caller_identity()
        if role == "owner" and id_boite and str(id_boite) not in {str(value) for value in get_boites_for_owner(actor_id)}:
            return jsonify({"error": "Cette boite n'appartient pas a votre entreprise"}), 403

        file    = request.files.get("cni")
        saved   = None
        if not login or not pwd:
            return jsonify({"error": "login et mot de passe requis."}), 400
        duplicate = _duplicate_login_response(login)
        if duplicate:
            return duplicate

        if file and file.filename:
            folder = os.path.join(current_app.root_path, "static", "img")
            os.makedirs(folder, exist_ok=True)
            fname  = secure_filename(f"{niu or login}_{int(time.time())}_{file.filename}") # type: ignore
            file.save(os.path.join(folder, fname))
            saved  = url_for("static", filename=f"img/{fname}")

        pwd_hash = generate_password_hash(pwd)
        if nom_ag:
            db.session.execute(text("""
                INSERT INTO agence_utilisatrice (niu,nom_agence,login,password,addresse_mail)
                VALUES (:niu,:nom,:login,:pw_hash,:email)
            """), {"niu": niu, "nom": nom_ag, "login": login, "pw_hash": pwd_hash, "email": email})
        else:
            # 1. Insertion du compte utilisateur au sein de la table client
            db.session.execute(text("""
                INSERT INTO client (id_cni,login,password,nom,prenom,address_mail,cni_file,created_by)
                VALUES (:id_cni,:login,:pw_hash,:nom,:prenom,:email,:cni_file,:created_by)
            """), {"id_cni": niu, "login": login, "pw_hash": pwd_hash, "nom": nom, "prenom": prenom, "email": email, "cni_file": saved, "created_by": created_by})

            # 2. Création immédiate de l'abonnement si une boîte noire est fournie
            #    (numero_a est SERIAL : on le laisse s'auto-incrémenter)
            if id_boite:
                db.session.execute(text("""
                    INSERT INTO abonner (id_cni, id_boite, type_abonnement, status)
                    VALUES (:cni, :boite, :type, 'Actif')
                """), {"cni": niu, "boite": id_boite, "type": type_a})
                
                # 3. Activation automatique de l'état du conteneur lié à cette boîte noire
                db.session.execute(text("""
                    UPDATE conteneurs SET status = 'ok'
                    FROM boite_noir b 
                    WHERE b.id_conteneurs = conteneurs.id_conteneurs AND b.id_boite = :boite
                """), {"boite": id_boite})

                # 4. Si une destination ou une description est fournie, enregistrer un colis lié
                dest = f.get("destination") or ''
                desc = f.get("description") or ''
                plomb = f.get("num_plomb") or ''
                colis_id = None
                if dest or desc or plomb:
                    colis_id = db.session.execute(text("""
                        INSERT INTO colis (id_cni_client, id_cni_transporteur, num_plom, desc_colis, status, destination)
                        VALUES (:cni, NULL, :plomb, :desc, 'En Transit', :dest)
                        RETURNING id_colis
                    """), {"cni": niu, "plomb": plomb, "desc": desc, "dest": dest}).scalar()

                box = db.session.execute(text("""
                    SELECT b.id_conteneurs,b.id_proprietaire FROM boite_noir b WHERE b.id_boite=:box
                """), {"box": id_boite}).fetchone()
                if box and box.id_conteneurs:
                    thresholds = {
                        "temp_min": f.get("temp_min"), "temp_max": f.get("temp_max"),
                        "humi_min": f.get("humi_min"), "humi_max": f.get("humi_max"),
                        "choc_max": f.get("choc_max"), "pression_min": f.get("pression_min"),
                        "pression_max": f.get("pression_max"),
                    }
                    thresholds = {key: float(value) for key,value in thresholds.items() if value not in (None,"")}
                    db.session.execute(text("""
                        INSERT INTO seuils_alerte(id_boite,temp_min,temp_max,humi_min,humi_max,choc_max,pression_min,pression_max)
                        VALUES(:box,:temp_min,:temp_max,:humi_min,:humi_max,:choc_max,:pression_min,:pression_max)
                        ON CONFLICT(id_boite) DO UPDATE SET temp_min=EXCLUDED.temp_min,temp_max=EXCLUDED.temp_max,
                          humi_min=EXCLUDED.humi_min,humi_max=EXCLUDED.humi_max,choc_max=EXCLUDED.choc_max,
                          pression_min=EXCLUDED.pression_min,pression_max=EXCLUDED.pression_max,updated_at=NOW()
                    """), {"box": id_boite, "temp_min": thresholds.get("temp_min"), "temp_max": thresholds.get("temp_max"),
                            "humi_min": thresholds.get("humi_min"), "humi_max": thresholds.get("humi_max"),
                            "choc_max": thresholds.get("choc_max"), "pression_min": thresholds.get("pression_min"),
                            "pression_max": thresholds.get("pression_max")})
                    cargo_name = f.get("cargo_name") or desc or "Marchandise"
                    cargo_type = f.get("cargo_type") or "Non precise"
                    declared_value = float(f.get("cargo_value") or 0)
                    shipment_id = db.session.execute(text("""
                        INSERT INTO shipments(client_id,container_id,black_box_id,company_id,cargo_name,cargo_type,
                            declared_value,destination,status,thresholds,created_by)
                        VALUES(:client,:container,:box,:company,:name,:type,:value,:destination,'IN_TRANSIT',
                            CAST(:thresholds AS jsonb),:created_by) RETURNING id
                    """), {"client": niu,"container":box.id_conteneurs,"box":id_boite,
                            "company":str(box.id_proprietaire) if box.id_proprietaire else None,
                            "name":cargo_name,"type":cargo_type,"value":declared_value,"destination":dest or "Non precise",
                            "thresholds":json.dumps(thresholds),"created_by":f"{role}:{actor_id}"}).scalar()
                    inventory_uid = str(uuid.uuid4())
                    sheet_number = f"INV-{datetime.utcnow().strftime('%Y%m%d')}-{inventory_uid[:8].upper()}"
                    inventory_id = db.session.execute(text("""
                        INSERT INTO inventory_sheets(inventory_uid,shipment_id,sheet_number,prepared_by,department)
                        VALUES(CAST(:uid AS uuid),:shipment,:number,:prepared,'Logistique') RETURNING id
                    """), {"uid":inventory_uid,"shipment":shipment_id,"number":sheet_number,
                            "prepared":f"{prenom or ''} {nom or ''}".strip() or login}).scalar()
                    db.session.execute(text("""
                        INSERT INTO inventory_items(inventory_id,article_reference,article_name,description,quantity,unit_price)
                        VALUES(:inventory,:reference,:name,:description,1,:value)
                    """), {"inventory":inventory_id,"reference":plomb or f"COL-{colis_id or shipment_id}",
                            "name":cargo_name,"description":desc,"value":declared_value})

        db.session.commit()
        return jsonify({"status": "success", "file_url": saved,
                        "inventory_uid": locals().get("inventory_uid"),
                        "shipment_id": locals().get("shipment_id")}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "error": str(e)}), 500


@users_bp.route("/api/register_driver", methods=["POST"])
@roles_required("superadmin", "owner")
def register_driver():
    file = None
    if request.content_type and request.content_type.startswith('multipart/form-data'):
        f = request.form
        id_cni = f.get('id_cni')
        login = f.get('login')
        password = f.get('password')
        nom = f.get('nom')
        prenom = f.get('prenom')
        contact = f.get('contact')
        id_boite = f.get('id_boite')
        file = request.files.get('cni')
    else:
        d = request.get_json() or {}
        id_cni = d.get('id_cni')
        login = d.get('login')
        password = d.get('password')
        nom = d.get('nom')
        prenom = d.get('prenom')
        contact = d.get('contact')
        id_boite = d.get('id_boite')

    if not id_cni or not login or not password:
        return jsonify({"error": "id_cni, login et mot de passe sont requis."}), 400
    duplicate = _duplicate_login_response(login)
    if duplicate:
        return duplicate

    try:
        _ensure_transporteur_schema()
        saved = None
        if file and file.filename:
            folder = os.path.join(current_app.root_path, "static", "img")
            os.makedirs(folder, exist_ok=True)
            fname = secure_filename(f"{id_cni or login}_{int(time.time())}_{file.filename}")
            file.save(os.path.join(folder, fname))
            saved = url_for("static", filename=f"img/{fname}")

        pw_hash = generate_password_hash(password)
        db.session.execute(text("""
            INSERT INTO transporteur (id_cni, login, password, nom, prenom, contact, id_boite, cni_file)
            VALUES (:id_cni, :login, :password, :nom, :prenom, :contact, :id_boite, :cni_file)
        """), {"id_cni": id_cni, "login": login, "password": pw_hash,
               "nom": nom, "prenom": prenom, "contact": contact, "id_boite": id_boite, "cni_file": saved})
        db.session.commit()
        return jsonify({"status": "success"}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@users_bp.route("/api/driver/manage", methods=["POST"])
@roles_required("superadmin", "owner")
def manage_driver():
    import json
    d = request.get_json() or {}
    id_cni = d.get('id_cni')
    id_boite = d.get('id_boite')
    id_boites = d.get('id_boites', [])
    blocked = bool(d.get('blocked', False))
    if not id_cni:
        return jsonify({"error": "Identifiant du chauffeur requis."}), 400
    try:
        _ensure_transporteur_schema()
        # Si id_boites est fourni (array), on le stocke en JSON et on met id_boite à NULL
        # Sinon on stocke id_boite seul et id_boites reste []
        if id_boites and isinstance(id_boites, list) and len(id_boites) > 0:
            boites_json = json.dumps(id_boites)
            result = db.session.execute(text(
                "UPDATE transporteur SET id_boite = NULL, id_boites = :id_boites, blocked = :blocked WHERE id_cni = :id_cni"
            ), {"id_boites": boites_json, "blocked": blocked, "id_cni": id_cni})
            updated = getattr(result, "rowcount", 0)
        else:
            result = db.session.execute(text(
                "UPDATE transporteur SET id_boite = :id_boite, id_boites = '[]', blocked = :blocked WHERE id_cni = :id_cni"
            ), {"id_boite": id_boite, "blocked": blocked, "id_cni": id_cni})
            updated = getattr(result, "rowcount", 0)
        db.session.commit()
        if updated == 0:
            return jsonify({"error": "Chauffeur introuvable."}), 404
        return jsonify({"status": "success"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@users_bp.route("/api/driver/message", methods=["POST"])
@roles_required("superadmin", "owner")
def send_driver_message():
    d = request.get_json() or {}
    id_cni = d.get('id_cni')
    message = (d.get('message') or '').strip()
    if not id_cni or not message:
        return jsonify({"error": "Chauffeur et message requis."}), 400
    try:
        _ensure_transporteur_schema()
        exists = db.session.execute(text("SELECT 1 FROM transporteur WHERE id_cni = :id_cni"), {"id_cni": id_cni}).scalar()
        if not exists:
            return jsonify({"error": "Chauffeur introuvable."}), 404
        db.session.execute(text(
            "INSERT INTO driver_messages (id_cni, message) VALUES (:id_cni, :message)"
        ), {"id_cni": id_cni, "message": message})
        db.session.commit()
        return jsonify({"status": "success"}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@users_bp.route("/api/iot/register-account", methods=["POST"])
def register_iot_account():
    d = request.get_json() or {}
    if not d.get("login") or not d.get("password"):
        return jsonify({"error": "login et mot de passe requis."}), 400

    duplicate = _duplicate_login_response(d.get("login"))
    if duplicate:
        return duplicate

    try:
        _ensure_client_created_by()
        password_hash = generate_password_hash(d.get("password", ""))
        created_by = d.get("created_by") or d.get("user_id") or "system"
        db.session.execute(text("""
            INSERT INTO client (id_cni,login,password,nom,prenom,address_mail,created_by)
            VALUES (:id_cni,:login,:password_hash,:nom,:prenom,:email,:created_by)
        """), {
            "id_cni": d.get("id_cni") or str(uuid.uuid4())[:12],
            "login": d.get("login"),
            "password_hash": password_hash,
            "nom": d.get("nom") or d.get("company") or "Client",
            "prenom": d.get("prenom") or "",
            "email": d.get("email") or "",
            "created_by": created_by,
        })

        iot_result = None
        should_provision_iot = bool(
            d.get("provision_iot")
            or d.get("provisionDevice")
            or d.get("device_uid")
            or d.get("deviceUid")
            or d.get("hardware_serial")
            or d.get("hardwareSerial")
            or d.get("firmware_version")
            or d.get("firmwareVersion")
            or d.get("protocol_version")
            or d.get("protocolVersion")
            or d.get("black_box_id")
            or d.get("blackBoxId")
        )
        if should_provision_iot:
            iot_result = provision_device(
                {
                    "device_uid": d.get("device_uid") or d.get("deviceUid"),
                    "hardware_serial": d.get("hardware_serial") or d.get("hardwareSerial"),
                    "firmware_version": d.get("firmware_version") or d.get("firmwareVersion"),
                    "protocol_version": d.get("protocol_version") or d.get("protocolVersion"),
                    "black_box_id": d.get("black_box_id") or d.get("blackBoxId"),
                },
                actor_role="superadmin",
                actor_id=str(created_by),
                commit=False,
            )

        db.session.commit()
        response = {"status": "success", "message": "Compte créé"}
        if iot_result:
            response["iot"] = iot_result
        return jsonify(response), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@users_bp.route("/api/register_user", methods=["POST"])
@roles_required("superadmin", "owner")
def register_user():
    d = request.get_json() or {}
    if not d.get("login") or not d.get("password"):
        return jsonify({"error": "login et mot de passe requis."}), 400
    duplicate = _duplicate_login_response(d.get("login"))
    if duplicate:
        return duplicate
    try:
        _ensure_client_created_by()
        password_hash = generate_password_hash(d.get("password", ""))
        created_by = d.get("created_by") or d.get("user_id") or "system"
        if d.get("nom_agence"):
            db.session.execute(text("""
                INSERT INTO agence_utilisatrice
                    (niu,nom_agence,login,password,addresse_mail)
                VALUES (:niu,:nom_agence,:login,:password_hash,:email)
            """), {**d, "password_hash": password_hash})
        else:
            db.session.execute(text("""
                INSERT INTO client (id_cni,login,password,nom,prenom,address_mail,created_by)
                VALUES (:id_cni,:login,:password_hash,:nom,:prenom,:email,:created_by)
            """), {**d, "password_hash": password_hash, "created_by": created_by})

        should_provision_iot = bool(
            d.get("provision_iot") or d.get("provisionDevice") or d.get("device_uid") or d.get("deviceUid")
            or d.get("hardware_serial") or d.get("hardwareSerial")
        )
        iot_result = None
        if should_provision_iot:
            role, user_id = get_caller_identity()
            iot_result = provision_device(
                {
                    "device_uid": d.get("device_uid") or d.get("deviceUid"),
                    "hardware_serial": d.get("hardware_serial") or d.get("hardwareSerial"),
                    "firmware_version": d.get("firmware_version") or d.get("firmwareVersion"),
                    "protocol_version": d.get("protocol_version") or d.get("protocolVersion"),
                    "black_box_id": d.get("black_box_id") or d.get("blackBoxId"),
                },
                actor_role=role,
                actor_id=str(user_id),
                commit=False,
            )

        db.session.commit()
        response = {"status": "success"}
        if iot_result:
            response["iot"] = iot_result
        return jsonify(response), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# oute de création de Colis/Abonnement avec Garde-fou

@users_bp.route("/api/abonnement/nouveau", methods=["POST"])
@roles_required("superadmin", "owner")
def register_colis():
    d = request.get_json() or {}
    id_cni_client = d.get("id_cni")
    id_boite = d.get("id_boite")
    destination = d.get("destination", "Non spécifié")
    force_update = d.get("force_update", False)
    
    if not id_cni_client or not id_boite:
        return jsonify({"error": "id_cni et id_boite requis."}), 400

    try:
        # 🛑 GARDE-FOU : Vérifier si ce client a DÉJÀ un abonnement actif sur une boîte
        transit_actif = db.session.execute(text("""
            SELECT numero_a FROM abonner WHERE id_cni = :cni AND status = 'Actif'
        """), {"cni": id_cni_client}).fetchone()

        if transit_actif and not force_update:
            return jsonify({
                "status": "confirm_required", 
                "message": "Ce client a déjà un transit en cours. Voulez-vous archiver l'ancien et démarrer un nouveau trajet ?"
            }), 202

        # 1. Enregistrer ou Mettre à jour le Client
        d["password_hash"] = generate_password_hash(d.get("password", ""))
        db.session.execute(text("""
            INSERT INTO client (id_cni, nom, prenom, address_mail, login, password)
            VALUES (:id_cni, :nom, :prenom, :email, :login, :password_hash)
            ON CONFLICT (id_cni) DO UPDATE SET 
            nom=EXCLUDED.nom, prenom=EXCLUDED.prenom, address_mail=EXCLUDED.address_mail
        """), d)

        # 2. Si forcé, on archive l'ancien abonnement
        if force_update:
            db.session.execute(text("UPDATE abonner SET status = 'Terminé' WHERE id_cni = :cni"), {"cni": id_cni_client})

        # 3. Créer le nouvel Abonnement
        id_abo = db.session.execute(text("""
            INSERT INTO abonner (id_cni, id_boite, type_abonnement, status)
            VALUES (:cni, :boite, :type_abo, 'Actif') RETURNING numero_a
        """), {"cni": id_cni_client, "boite": id_boite, "type_abo": d.get("type_abonnement")}).scalar()

        # 4. Enregistrer le Colis avec la Destination
        db.session.execute(text("""
            INSERT INTO colis (id_cni_client, id_cni_transporteur, num_plom, desc_colis, status, destination)
            VALUES (:cni, :transp, :plom, :desc, 'En Transit', :dest)
        """), {"cni": id_cni_client, "transp": d.get("id_transporteur"), "plom": d.get("num_plomb"), "desc": d.get("description"), "dest": destination})

        db.session.commit()
        _sceller_evenement("NOUVEAU_COLIS", id_boite, {"client": id_cni_client, "destination": destination})
        return jsonify({"status": "success", "message": "Colis et abonnement enregistrés avec succès."}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "error": str(e)}), 500


# ═══════════════════════════════════════════════════════════════════
#  NEW ROUTES: UPDATE PROFILES, EXTEND SUBSCRIPTIONS, ADD CONTAINERS
# ═══════════════════════════════════════════════════════════════════

@users_bp.route("/api/client/update", methods=["POST"])
@roles_required("superadmin", "owner")
def update_client():
    d = request.get_json() or {}
    id_cni = d.get('id_cni')
    if not id_cni:
        return jsonify({"error": "id_cni requis"}), 400
    try:
        _ensure_client_cni_file_column()
        _ensure_client_created_by()
        nom = d.get('nom')
        prenom = d.get('prenom')
        email = d.get('email')
        phone = d.get('phone')
        type_a = d.get('type_a')
        boites = d.get('boites', [])  # Can be an array but stored as comma-separated
        
        # Basic update
        updates = []
        params = {"id_cni": id_cni}
        if nom is not None:
            updates.append("nom = :nom")
            params["nom"] = nom
        if prenom is not None:
            updates.append("prenom = :prenom")
            params["prenom"] = prenom
        if email is not None:
            updates.append("address_mail = :email")
            params["email"] = email
        
        if updates:
            sql = "UPDATE client SET " + ", ".join(updates) + " WHERE id_cni = :id_cni"
            result = db.session.execute(text(sql), params)
            if getattr(result, "rowcount", 0) == 0:
                return jsonify({"error": "Client introuvable"}), 404
        
        # Handle multiple boîtes if provided
        if boites and len(boites) > 0:
            # Remove existing subscriptions if any
            db.session.execute(text("DELETE FROM abonner WHERE id_cni = :cni AND status != 'Terminé'"), {"cni": id_cni})
            # Create new subscriptions for each boîte
            for boite in boites:
                db.session.execute(text("""
                    INSERT INTO abonner (id_cni, id_boite, type_abonnement, status)
                    VALUES (:cni, :boite, :type_a, 'Actif')
                """), {"cni": id_cni, "boite": boite, "type_a": type_a or "Mensuel"})
        
        db.session.commit()
        return jsonify({"status": "success"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@users_bp.route("/api/driver/update", methods=["POST"])
@roles_required("superadmin", "owner")
def update_driver():
    d = request.get_json() or {}
    id_cni = d.get('id_cni')
    if not id_cni:
        return jsonify({"error": "id_cni requis"}), 400
    try:
        _ensure_transporteur_schema()
        nom = d.get('nom')
        login = d.get('login')
        contact = d.get('contact')
        moyen_transport = d.get('moyen_transport')
        
        updates = []
        params = {"id_cni": id_cni}
        if nom is not None:
            updates.append("nom_chauffeurs = :nom")
            params["nom"] = nom
        if login is not None:
            updates.append("login = :login")
            params["login"] = login
        if contact is not None:
            updates.append("contact = :contact")
            params["contact"] = contact
        if moyen_transport is not None:
            updates.append("moyen_transport = :moyen_transport")
            params["moyen_transport"] = moyen_transport
        
        if updates:
            sql = "UPDATE transporteur SET " + ", ".join(updates) + " WHERE id_cni = :id_cni"
            result = db.session.execute(text(sql), params)
            if getattr(result, "rowcount", 0) == 0:
                return jsonify({"error": "Chauffeur introuvable"}), 404
        
        db.session.commit()
        return jsonify({"status": "success"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@users_bp.route("/api/company/update", methods=["POST"])
@roles_required("superadmin")
def update_company():
    d = request.get_json() or {}
    company_id = d.get('id')
    if not company_id:
        return jsonify({"error": "id requis"}), 400
    try:
        _ensure_company_schema()
        nom_agence = d.get('nom_agence')
        niu = d.get('niu')
        email = d.get('email')
        lieu_residence = d.get('lieu_residence')
        
        updates = []
        params = {"id": company_id}
        if nom_agence is not None:
            updates.append("nom_agence = :nom_agence")
            params["nom_agence"] = nom_agence
        if niu is not None:
            updates.append("niu = :niu")
            params["niu"] = niu
        if email is not None:
            updates.append("addresse_mail = :email")
            params["email"] = email
        if lieu_residence is not None:
            updates.append("lieu_residence = :lieu_residence")
            params["lieu_residence"] = lieu_residence
        
        changes = {key: value for key, value in {
            "nom_agence": nom_agence,
            "niu": niu,
            "email": email,
            "lieu_residence": lieu_residence,
        }.items() if value is not None}
        contract_uid = None
        if updates:
            sql = "UPDATE proprietaire_conteneur SET " + ", ".join(updates) + " WHERE id = :id"
            result = db.session.execute(text(sql), params)
            if getattr(result, "rowcount", 0) == 0:
                return jsonify({"error": "Entreprise introuvable"}), 404
            contract_uid = _create_company_modification_contract(company_id, changes, get_caller_identity()[1])
        
        db.session.commit()
        return jsonify({"status": "success", "contract_uid": str(contract_uid) if contract_uid else None}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@users_bp.route("/api/client/extend", methods=["POST"])
@roles_required("superadmin", "owner")
def extend_client_subscription():
    d = request.get_json() or {}
    id_cni = d.get('id_cni')
    try:
        days = int(d.get('days', 0) or 0)
    except (TypeError, ValueError):
        days = 0
    try:
        amount = int(d.get('amount', 0) or 0)
    except (TypeError, ValueError):
        amount = 0
    
    if not id_cni or days <= 0:
        return jsonify({"error": "id_cni et days (> 0) requis"}), 400
    
    try:
        _ensure_client_cni_file_column()
        # Récupère l'abonnement actif du client
        abo = db.session.execute(text("""
            SELECT numero_a, fin_a, created_at FROM abonner 
            WHERE id_cni = :cni AND status = 'Actif' LIMIT 1
        """), {"cni": id_cni}).fetchone()
        
        if not abo:
            return jsonify({"error": "Aucun abonnement actif pour ce client"}), 404
        
        # Calculer la nouvelle date de fin
        from datetime import datetime, timedelta
        current_end = abo[1] if abo[1] else datetime.now()
        new_end = current_end + timedelta(days=days)
        
        # Mise à jour (on simule avec une date de renouvellement)
        # Note: s'il n'y a pas de colonne fin_a, on la crée dynamiquement
        try:
            db.session.execute(text("""
                ALTER TABLE abonner ADD COLUMN IF NOT EXISTS fin_a TIMESTAMP
            """))
            db.session.commit()
        except:
            pass
        
        # Update subscription
        db.session.execute(text("""
            UPDATE abonner SET fin_a = :fin_a WHERE numero_a = :numero_a
        """), {"fin_a": new_end, "numero_a": abo[0]})
        
        db.session.commit()
        return jsonify({"status": "success", "new_end_date": new_end.isoformat()}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@users_bp.route("/api/client/add_containers", methods=["POST"])
@roles_required("superadmin", "owner")
def add_containers_to_client():
    d = request.get_json() or {}
    id_cni = d.get('id_cni')
    try:
        count = int(d.get('count', 1) or 1)
    except (TypeError, ValueError):
        count = 1
    container_type = d.get('type', 'DRY')
    
    if not id_cni or count <= 0:
        return jsonify({"error": "id_cni et count (> 0) requis"}), 400
    
    try:
        _ensure_client_cni_file_column()
        
        # Vérify that client exists
        client = db.session.execute(text("SELECT id_cni FROM client WHERE id_cni = :cni"), {"cni": id_cni}).fetchone()
        if not client:
            return jsonify({"error": "Client introuvable"}), 404
        
        # Get client's current active subscription
        abo = db.session.execute(text("""
            SELECT numero_a, id_boite FROM abonner 
            WHERE id_cni = :cni AND status = 'Actif' LIMIT 1
        """), {"cni": id_cni}).fetchone()
        
        if not abo:
            return jsonify({"error": "Le client n'a pas d'abonnement actif"}), 404
        
        id_boite = abo[1]
        added_containers = []
        
        # Create new container entries (simulated with boite_noir entries)
        for i in range(count):
            # Generate a new container ID
            container_id = f"{id_boite}_C{i+1}_{int(time.time())}"
            
            # Try to insert into conteneurs table
            try:
                db.session.execute(text("""
                    INSERT INTO conteneurs (id_conteneurs, type_conteneurs, status)
                    VALUES (:id_conteneurs, :type_conteneurs, 'ok')
                """), {"id_conteneurs": container_id, "type_conteneurs": container_type})
            except:
                pass  # Table might not exist or constraint failure
            
            added_containers.append(container_id)

        db.session.commit()
        return jsonify({"status": "success", "containers_added": added_containers}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# Ajoute ceci en dessous de tes autres routes (comme celle pour l'index)
@users_bp.route('/presentations')
def presentations():
    return render_template('presentation.html')

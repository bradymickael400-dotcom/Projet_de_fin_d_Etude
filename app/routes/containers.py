
"""API de gestion des conteneurs et de leur visibilité selon le rôle utilisateur."""

import os
import uuid
import json
import socket
from urllib.parse import urlsplit, urlunsplit
from datetime import datetime
from flask import Blueprint, current_app, request, jsonify, make_response
from werkzeug.security import generate_password_hash
from app.utils import (
    _hash_block, _sceller_evenement,
    get_boite_for_client, get_boite_for_driver, get_boites_for_owner,
    get_boites_for_agency, get_caller_identity,
)
from sqlalchemy import text # type: ignore
from app import db, limiter
from app.utils import *
from app.routes.auth import _login_exists, _login_suggestions
from app.security import roles_required

cnt_bp = Blueprint("containers", __name__)


def _send_container_id_to_prototype(box_id, container_id, requested_by):
    """Publie l'identifiant uniquement vers le prototype actif de la boîte."""
    if not box_id or not container_id:
        return {"status": "not_requested"}
    try:
        from app.modules.iot.iot_command_service import create_device_command

        command = create_device_command(
            int(box_id),
            "ASSIGN_CONTAINER",
            {"containerId": str(container_id), "replace": True},
            requested_by_user_id=str(requested_by or ""),
            allow_fallback=False,
        )
        return {
            "status": "published",
            "deviceUid": command.get("deviceUid"),
            "commandUid": command.get("commandUid"),
            "containerId": str(container_id),
        }
    except Exception as exc:
        db.session.rollback()
        return {
            "status": "pending_device_enrollment",
            "containerId": str(container_id),
            "message": str(exc),
        }


def _contract_access_url(contract_uid):
    configured = current_app.config.get("PUBLIC_BASE_URL", "").strip() if current_app else ""
    if configured:
        base = configured.rstrip("/")
    else:
        base = request.url_root.rstrip("/")
        parts = urlsplit(base)
        host = parts.hostname or ""
        if host in ("127.0.0.1", "localhost", "0.0.0.0"):
            lan_ip = _local_lan_ip()
            if lan_ip:
                port = f":{parts.port}" if parts.port else ""
                base = urlunsplit((parts.scheme, f"{lan_ip}{port}", parts.path.rstrip("/"), "", ""))
    return f"{base}/?contract={contract_uid}"


def _local_lan_ip():
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("8.8.8.8", 80))
        ip_address = sock.getsockname()[0]
        sock.close()
        return ip_address
    except Exception:
        try:
            return socket.gethostbyname(socket.gethostname())
        except Exception:
            return ""


def _notify_company_contract(owner_id, company_name, email, contract_uid, contract_number):
    contract_url = _contract_access_url(contract_uid)
    message = (
        f"Nouveau contrat ARGOS {contract_number} a accepter pour {company_name}. "
        f"Lien: {contract_url}"
    )
    db.session.execute(text("""
        INSERT INTO notifications(type,message,cible_role,initiator_id)
        VALUES ('CONTRACT_PENDING_ACCEPTANCE',:message,:target,:contract_uid)
    """), {
        "message": message,
        "target": str(owner_id),
        "contract_uid": str(contract_uid),
    })
    if email:
        send_email_background(
            [email],
            f"Contrat ARGOS {contract_number} a accepter",
            (
                f"Bonjour {company_name},\n\n"
                f"Votre contrat ARGOS {contract_number} est pret a etre consulte et accepte.\n"
                f"Connectez-vous avec le compte entreprise cree puis ouvrez ce lien:\n{contract_url}\n\n"
                "ARGOS"
            ),
            severity="warning",
            action_url=contract_url,
            action_label="Consulter le contrat",
        )
    return contract_url


def _ensure_owner_contact_schema():
    try:
        db.session.execute(text("ALTER TABLE proprietaire_conteneur ADD COLUMN IF NOT EXISTS contact TEXT"))
        db.session.commit()
    except Exception:
        db.session.rollback()


def _notification_config_status(email=None, phone=None):
    provider = (os.getenv("NOTIFICATION_PROVIDER") or "smtp").strip().lower()
    if provider == "infobip":
        infobip_ready = bool(os.getenv("INFOBIP_BASE_URL", "").strip() and os.getenv("INFOBIP_API_KEY", "").strip())
        return {
            "provider": "infobip",
            "email_requested": bool(email),
            "email_configured": bool(infobip_ready and os.getenv("INFOBIP_EMAIL_FROM", "").strip()),
        }
    return {
        "provider": provider,
        "email_requested": bool(email),
        "email_configured": bool((os.getenv("SMTP_FROM_EMAIL") or os.getenv("SMTP_USER") or "").strip() and (os.getenv("SMTP_PASSWORD") or "").strip()),
    }


def _notify_company_account(owner_id, company_name, email, phone, login, password, contract_url=None, contract_number=None):
    title = f"Compte ARGOS cree pour {company_name}"
    contract_block = ""
    if contract_url:
        contract_block = (
            f"\nContrat a consulter et accepter: {contract_number or 'contrat ARGOS'}\n"
            f"Lien: {contract_url}\n"
        )
    message = (
        f"Bonjour {company_name},\n\n"
        "Votre compte ARGOS a ete cree.\n"
        f"Identifiant: {login or 'non renseigne'}\n"
        f"Mot de passe: {password or 'mot de passe conserve / non modifie'}\n\n"
        f"{contract_block}\n"
        "Connectez-vous a la plateforme ARGOS pour consulter vos boites et contrats.\n\n"
        "ARGOS"
    )
    db.session.execute(text("""
        INSERT INTO notifications(type,message,cible_role,initiator_id)
        VALUES ('COMPANY_ACCOUNT_CREATED',:message,:target,:owner_id)
    """), {
        "message": f"Compte entreprise cree: {company_name}",
        "target": str(owner_id),
        "owner_id": str(owner_id),
    })
    db.session.commit()
    email_sent = send_email_background(
        [email], title, message,
        severity="success",
        action_url=get_public_base_url(),
        action_label="Se connecter à ARGOS",
    ) if email else False
    status = _notification_config_status(email, phone)
    status.update({
        "email_sent": bool(email_sent),
    })
    return status


def _notify_expired_contracts():
    """Marque les contrats expires et notifie le superadmin une seule fois."""
    try:
        expired = db.session.execute(text("""
            SELECT c.id, c.company_id, c.contract_number, c.title, p.nom_agence
            FROM contracts c
            LEFT JOIN proprietaire_conteneur p ON CAST(p.id AS TEXT)=c.company_id
            WHERE c.ends_on < CURRENT_DATE
              AND c.status IN ('PENDING_ACCEPTANCE','ACCEPTED')
              AND NOT EXISTS (
                  SELECT 1 FROM notifications n
                  WHERE n.type='CONTRACT_EXPIRED'
                    AND n.initiator_id=CAST(c.id AS TEXT)
              )
        """)).fetchall()
        for row in expired:
            db.session.execute(text("""
                UPDATE contracts SET status='EXPIRED', updated_at=NOW() WHERE id=:id
            """), {"id": row.id})
            db.session.execute(text("""
                INSERT INTO notifications(type,message,cible_role,initiator_id)
                VALUES ('CONTRACT_EXPIRED',:message,'superadmin',:contract_id)
            """), {
                "message": f"Contrat expire: {row.contract_number} - {row.nom_agence or row.title}",
                "contract_id": str(row.id),
            })
        if expired:
            db.session.commit()

        expired_boxes = db.session.execute(text("""
            SELECT b.id_boite, b.numero_serie, b.id_proprietaire, p.nom_agence
            FROM boite_noir b
            LEFT JOIN proprietaire_conteneur p ON p.id=b.id_proprietaire
            WHERE b.deployment_date IS NOT NULL
              AND COALESCE(b.archived,FALSE)=FALSE
              AND b.status <> 'off'
              AND b.deployment_date
                    + (GREATEST(COALESCE(NULLIF(regexp_replace(CAST(b.expected_duration AS TEXT), '[^0-9]', '', 'g'), ''), '30')::INTEGER, 1) * INTERVAL '1 day')
                  < NOW()
              AND NOT EXISTS (
                  SELECT 1 FROM notifications n
                  WHERE n.type='BLACK_BOX_EXPIRED'
                    AND n.initiator_id='box:' || CAST(b.id_boite AS TEXT)
              )
        """)).fetchall()
        for row in expired_boxes:
            db.session.execute(text("""
                INSERT INTO notifications(type,message,cible_role,id_boite,initiator_id)
                VALUES ('BLACK_BOX_EXPIRED',:message,'superadmin',:box_id,:initiator)
            """), {
                "message": f"Boite expiree: {row.numero_serie or row.id_boite} - {row.nom_agence or 'sans entreprise'}",
                "box_id": row.id_boite,
                "initiator": f"box:{row.id_boite}",
            })
        if expired_boxes:
            db.session.commit()
    except Exception:
        db.session.rollback()


def _ensure_boite_serial_schema():
    try:
        db.session.execute(text("CREATE SEQUENCE IF NOT EXISTS brady.boite_serial_seq START WITH 1 INCREMENT BY 1"))
        db.session.execute(text("""
            CREATE OR REPLACE FUNCTION brady.argos_next_boite_serial(prefix text DEFAULT 'BB')
            RETURNS text
            LANGUAGE plpgsql
            AS $$
            DECLARE
                n bigint;
                clean_prefix text;
                suffix text;
            BEGIN
                clean_prefix := upper(left(regexp_replace(coalesce(prefix, 'BB'), '[^A-Za-z]', '', 'g') || 'BB', 2));
                n := nextval('brady.boite_serial_seq');
                suffix := chr(65 + (((n - 1) / 26) % 26)::int) || chr(65 + ((n - 1) % 26)::int);
                RETURN clean_prefix || '-' || lpad(n::text, 6, '0') || '-' || suffix;
            END;
            $$;
        """))
        db.session.execute(text("ALTER TABLE boite_noir ADD COLUMN IF NOT EXISTS numero_serie VARCHAR(20)"))
        db.session.execute(text("ALTER TABLE boite_noir ALTER COLUMN numero_serie SET DEFAULT brady.argos_next_boite_serial('BB')"))
        db.session.execute(text("""
            UPDATE boite_noir
            SET numero_serie = brady.argos_next_boite_serial('BB')
            WHERE numero_serie IS NULL OR TRIM(numero_serie) = ''
        """))
        db.session.execute(text("""
            CREATE UNIQUE INDEX IF NOT EXISTS uq_boite_noir_numero_serie
            ON boite_noir(numero_serie)
        """))
        db.session.commit()
    except Exception:
        db.session.rollback()


def _ensure_container_create_schema():
    try:
        db.session.execute(text("ALTER TABLE conteneurs ADD COLUMN IF NOT EXISTS technical_info JSONB DEFAULT '{}'::jsonb"))
        db.session.execute(text("ALTER TABLE conteneurs ADD COLUMN IF NOT EXISTS bic_registered BOOLEAN DEFAULT FALSE"))
        db.session.execute(text("ALTER TABLE conteneurs ADD COLUMN IF NOT EXISTS local_only BOOLEAN DEFAULT FALSE"))
        db.session.execute(text("ALTER TABLE conteneurs ADD COLUMN IF NOT EXISTS bic_validation_msg TEXT"))
        db.session.execute(text("ALTER TABLE conteneurs ADD COLUMN IF NOT EXISTS created_by TEXT"))
        db.session.commit()
    except Exception:
        db.session.rollback()


def _request_boolean(value):
    """Interprète correctement les booléens JSON et ceux envoyés par formulaire."""
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    return str(value or "").strip().lower() in {"1", "true", "yes", "oui", "on", "hors_bic", "non_bic"}


def _has_inventory_access(id_boite):
    role, user_id = get_caller_identity()
    if role in (None, "", "superadmin"):
        return True
    if role == "owner":
        return str(id_boite) in [str(x) for x in (get_boites_for_owner(user_id) or [])]
    if role == "company":
        return str(id_boite) in [str(x) for x in (get_boites_for_agency(user_id) or [])]
    if role == "client":
        return str(id_boite) in [str(x) for x in (get_boite_for_client(user_id) or [])]
    if role == "driver":
        return str(id_boite) in [str(x) for x in (get_boite_for_driver(user_id) or [])]
    if role == "port_authority":
        return str(id_boite) in [str(x) for x in (get_boites_for_port_authority(user_id) or [])]
    return False

# ═══════════════════════════════════════════════════════════
#  CONTENEURS — avec restriction rôle
# ═══════════════════════════════════════════════════════════
@cnt_bp.route("/api/containers/all", methods=["GET"])
def get_all_containers():
    role, user_id = get_caller_identity()
    _ensure_container_create_schema()
    _ensure_boite_serial_schema()
    from app.modules.iot.repository import ensure_iot_schema
    ensure_iot_schema()

    # 1. CORRECTION : On ne bloque pas si user_id est vide (car le superadmin n'en a pas toujours un)
    # On vérifie seulement que le rôle existe.
    if not role:
        return jsonify({"error": "Requête non authentifiée"}), 401

    # Filtrage strict selon les droits
    boites_filter = None
    if role == "owner":
        boites_filter = get_boites_for_owner(user_id)
    elif role == "company":
        boites_filter = get_boites_for_agency(user_id)
    elif role == "client":
        boites_filter = get_boite_for_client(user_id)
    elif role == "driver":
        boites_filter = get_boite_for_driver(user_id)
    elif role == "port_authority":
        boites_filter = get_boites_for_port_authority(user_id)

    # Requête SQL
    base_sql = """
        SELECT c.id_conteneurs, '' AS resistance, c.taile_perimetre,
               c.type_conteneurs, c.status AS db_status,
               COALESCE(c.bic_registered,FALSE) AS bic_registered,
               COALESCE(c.local_only,FALSE) AS local_only,
               c.bic_validation_msg,
               b.id_boite, b.numero_serie, b.type_boite, b.versions,
               e.temperature, e.humidite, e.pressions,
               e.vitesse, e.chocs, e.lat, e.lon,
               e.notif, e.log_action, e.horodatage,
               e.device_uid, e.sequence, e.battery_level, e.heading,
               sr.light_level, sr.sound_level, sr.distance_cm,
               sr.acceleration_x, sr.acceleration_y, sr.acceleration_z,
               sr.flame_detected, sr.door_open, sr.security_alarm, sr.modes,
               a.status AS abo_status
        FROM conteneurs c
        LEFT JOIN boite_noir b ON b.id_conteneurs = c.id_conteneurs
        LEFT JOIN abonner a ON a.id_boite = b.id_boite AND a.status = 'Actif'
        LEFT JOIN LATERAL (
            SELECT * FROM evenement_save
            WHERE id_boite = b.id_boite
            ORDER BY horodatage DESC LIMIT 1
        ) e ON TRUE
        LEFT JOIN LATERAL (
            SELECT light_level, sound_level, distance_cm,
                   acceleration_x, acceleration_y, acceleration_z,
                   flame_detected, door_open, security_alarm, modes
            FROM sensor_readings
            WHERE black_box_id = b.id_boite
              AND container_id = c.id_conteneurs
            ORDER BY measured_at DESC LIMIT 1
        ) sr ON TRUE
    """
    
    params = {}
    if boites_filter is not None:
        if not boites_filter:
            return jsonify([]) # Retourne un tableau vide si aucune boîte
        placeholders = ",".join([f":b{i}" for i in range(len(boites_filter))])
        base_sql += f" WHERE b.id_boite IN ({placeholders})"
        params = {f"b{i}": v for i, v in enumerate(boites_filter)}
        
    rows = db.session.execute(text(base_sql + " ORDER BY c.id_conteneurs"), params).fetchall()
    
    # 2. CORRECTION : On renvoie TOUTES les données dont ton script.js a besoin
    result = []
    for r in rows:
        m = dict(r._mapping)
        alerts = []
        if m.get("notif"):
            try: alerts = json.loads(m["notif"])
            except: pass
            
        has_data = m.get("temperature") is not None
        status = m.get("db_status") or "off"
        abo_status = m.get('abo_status')
        if has_data:
            status = "danger" if len(alerts) >= 2 else ("warning" if alerts else "ok")
        elif not status:
            status = "off"
            
        result.append({
            "id":               m["id_conteneurs"],
            "id_boite":         m.get("id_boite") or "",
            "numero_serie":     m.get("numero_serie") or "",
            "boite_label":      m.get("numero_serie") or m.get("id_boite") or "",
            "type_conteneurs":  m.get("type_conteneurs") or "",
            "bic_registered":   bool(m.get("bic_registered")),
            "local_only":       bool(m.get("local_only")),
            "bic_classification": "HORS_BIC" if m.get("local_only") else "BIC",
            "bic_validation_msg": m.get("bic_validation_msg") or "",
            "resistance":       m.get("resistance") or "",
            "taile_perimetre":  m.get("taile_perimetre") or "",
            "type_boite":       m.get("type_boite") or "",
            "versions":         m.get("versions") or "",
            "status":           status,
            "temp":             float(m["temperature"]) if has_data else None,
            "humidity":         float(m["humidite"]) if m.get("humidite") is not None else None,
            "pressure":         float(m["pressions"]) if m.get("pressions") is not None else None,
            "speed":            float(m["vitesse"]) if m.get("vitesse") is not None else 0,
            "shock":            float(m["chocs"]) if m.get("chocs") is not None else 0,
            "light":            float(m["light_level"]) if m.get("light_level") is not None else None,
            "sound":            float(m["sound_level"]) if m.get("sound_level") is not None else None,
            "distance":         float(m["distance_cm"]) if m.get("distance_cm") is not None else None,
            "acceleration_x":   float(m["acceleration_x"]) if m.get("acceleration_x") is not None else None,
            "acceleration_y":   float(m["acceleration_y"]) if m.get("acceleration_y") is not None else None,
            "acceleration_z":   float(m["acceleration_z"]) if m.get("acceleration_z") is not None else None,
            "flame_detected":   bool(m.get("flame_detected")),
            "door_open":        bool(m.get("door_open")),
            "security_alarm":   bool(m.get("security_alarm")),
            "security_enabled": bool((m.get("modes") or {}).get("securityEnabled"))
                                  if isinstance(m.get("modes"), dict) else False,
            "lat":              float(m["lat"]) if m.get("lat") is not None else None,
            "lon":              float(m["lon"]) if m.get("lon") is not None else None,
            "alerts":           alerts,
            "log_action":       m.get("log_action") or "",
            "lastUpdate":       m["horodatage"].strftime("%H:%M:%S") if m.get("horodatage") else "--",
            "measured_at":      m["horodatage"].isoformat() if m.get("horodatage") else None,
            "device_uid":       m.get("device_uid"),
            "sequence":         m.get("sequence"),
            "battery_level":    float(m["battery_level"]) if m.get("battery_level") is not None else None,
            "heading":          float(m["heading"]) if m.get("heading") is not None else None,
        })
        
    return jsonify(result)

@cnt_bp.route("/api/containers/available", methods=["GET"])
@cnt_bp.route("/api/containers/disponibles", methods=["GET"])  # alias utilisé par le frontend
def get_available_containers():
    role, user_id = get_caller_identity()
    company_id = request.args.get("company_id") or request.args.get("id_proprietaire") or ""
    params = {"company_id": company_id} if company_id else {}

    base_sql = """
        SELECT c.id_conteneurs, c.taile_perimetre, c.type_conteneurs
        FROM conteneurs c
        WHERE c.status = 'ok'
          AND NOT EXISTS (
              SELECT 1 FROM boite_noir b
              WHERE b.id_conteneurs = c.id_conteneurs
                AND COALESCE(b.archived, FALSE) = FALSE
          )
    """

    if company_id:
        # La table conteneurs ne possède pas de colonne id_proprietaire dans la DB actuelle.
        # On filtre donc de façon compatible avec le schéma réel : par boîte associée au propriétaire.
        base_sql += """
            AND EXISTS (
                SELECT 1
                FROM boite_noir b2
                WHERE b2.id_conteneurs = c.id_conteneurs
                  AND COALESCE(b2.archived, FALSE) = FALSE
                  AND CAST(b2.id_proprietaire AS TEXT) = :company_id
            )
        """
        params = {**params, "company_id": str(company_id)}

    rows = db.session.execute(text(base_sql), params).fetchall()
    return jsonify([{"id": r[0], "taile_perimetre": r[1], "type_conteneurs": r[2]} for r in rows])


@cnt_bp.route("/api/containers/create", methods=["POST"])
@roles_required("superadmin", "owner")
def create_container_direct():
    """Crée un conteneur, vérifie ISO/BIC et l'assigne optionnellement à une boîte libre."""
    role, user_id = get_caller_identity()
    _ensure_container_create_schema()
    _ensure_boite_serial_schema()

    data = request.get_json(silent=True) or {}
    container_id = (data.get("id_conteneurs") or data.get("container_id") or "").upper().replace(" ", "").replace("-", "")
    company_id = data.get("id_proprietaire") or data.get("company_id")
    box_id = data.get("id_boite") or data.get("box_id") or None
    type_conteneurs = data.get("type_conteneurs") or data.get("container_type") or "DRY"
    technical_info = data.get("technical_info") or {}
    classification = str(data.get("bic_classification") or data.get("classification") or "").strip().upper()
    non_bic = (
        classification in {"HORS_BIC", "NON_BIC", "LOCAL"}
        or _request_boolean(data.get("non_bic"))
        or _request_boolean(data.get("is_non_bic"))
        or _request_boolean(data.get("hors_bic"))
        or _request_boolean(data.get("local_only_ack"))
        or _request_boolean(data.get("local_only"))
    )

    if not container_id:
        return jsonify({"error": "Numero d'identification du conteneur requis."}), 400
    if len(container_id) < 4:
        return jsonify({
            "error": "Un identifiant Hors BIC doit contenir au moins 4 caractères.",
            "code": "CONTAINER_ID_TOO_SHORT",
        }), 400
    if len(container_id) > 100:
        return jsonify({"error": "L'identifiant du conteneur ne peut pas dépasser 100 caractères."}), 400
    if role == "owner":
        company_id = user_id

    try:
        from app.services.bic_service import get_bic_service, validate_iso6346

        if non_bic:
            valid, validation_msg = False, "Conteneur déclaré Hors BIC par l'utilisateur"
        else:
            valid, validation_msg = validate_iso6346(container_id)
        # Un identifiant libre d'au moins quatre caractères est automatiquement
        # classé Hors BIC. Il ne doit jamais être rejeté à cause d'ISO 6346.
        if not non_bic and not valid:
            non_bic = True
            validation_msg = "Identifiant non ISO 6346, classé automatiquement Hors BIC"

        bic_specs = None if non_bic else db.session.execute(text("""
            SELECT * FROM container_specs_bic WHERE container_number=:container_id
        """), {"container_id": container_id}).fetchone()
        bic_registered = bool(bic_specs)
        bic_warning = None
        if not non_bic and not bic_registered:
            try:
                svc = get_bic_service()
                specs = svc.fetch_container_specs(container_id)
                if specs:
                    svc.save_to_db(specs)
                    bic_registered = True
            except Exception as exc:
                bic_warning = str(exc)

        if not non_bic and not bic_registered:
            return jsonify({
                "error": "Ce conteneur n'est pas enregistré dans BIC/BoxTech. Cochez « Pas du BIC » pour utiliser un identifiant libre.",
                "code": "BIC_CONFIRM_REQUIRED",
                "iso6346_valid": True,
                "bic_registered": False,
                "bic_warning": bic_warning,
            }), 409

        if bic_registered:
            specs_map = dict(bic_specs._mapping) if bic_specs is not None else specs
            technical_info.update({
                "dimensions": specs_map.get("type_code") or technical_info.get("dimensions", ""),
                "max_gross_mass_kg": specs_map.get("max_gross_mass_kg"),
                "tare_mass_kg": specs_map.get("tare_mass_kg"),
                "capacity_m3": specs_map.get("capacity_m3"),
                "manufacture_year": specs_map.get("manufacture_year"),
                "internal_length_mm": specs_map.get("internal_length_mm"),
                "internal_width_mm": specs_map.get("internal_width_mm"),
                "internal_height_mm": specs_map.get("internal_height_mm"),
                "external_length_mm": specs_map.get("external_length_mm"),
                "external_width_mm": specs_map.get("external_width_mm"),
                "external_height_mm": specs_map.get("external_height_mm"),
                "door_width_mm": specs_map.get("door_width_mm"),
                "door_height_mm": specs_map.get("door_height_mm"),
                "source": "BIC BoxTech",
            })

        existing = db.session.execute(text("""
            SELECT id_conteneurs FROM conteneurs WHERE id_conteneurs=:container_id
        """), {"container_id": container_id}).fetchone()
        if existing:
            return jsonify({"error": "Ce conteneur existe deja dans ARGOS."}), 409

        if box_id:
            box = db.session.execute(text("""
                SELECT id_boite, id_proprietaire, id_conteneurs
                FROM boite_noir
                WHERE id_boite=:box_id AND COALESCE(archived,FALSE)=FALSE
                FOR UPDATE
            """), {"box_id": box_id}).fetchone()
            if not box:
                return jsonify({"error": "Boite noire introuvable ou archivee."}), 404
            if box.id_conteneurs:
                return jsonify({"error": "Cette boite noire est deja liee a un conteneur."}), 409
            if role == "owner" and str(box.id_proprietaire) != str(company_id):
                return jsonify({"error": "Cette boite noire n'appartient pas a votre entreprise."}), 403
            if role == "superadmin" and company_id and box.id_proprietaire and str(box.id_proprietaire) != str(company_id):
                return jsonify({"error": "Cette boite noire appartient deja a une autre entreprise."}), 409
            if role == "superadmin" and not company_id and box.id_proprietaire:
                return jsonify({"error": "Sans entreprise selectionnee, choisissez une boite sans entreprise ou aucune assignation."}), 409

        db.session.execute(text("""
            INSERT INTO conteneurs
                (id_conteneurs, taile_perimetre, type_conteneurs, status,
                 technical_info, bic_registered, local_only, bic_validation_msg, created_by)
            VALUES
                (:container_id, :perimeter, :type_conteneurs, 'ok',
                 CAST(:technical_info AS jsonb), :bic_registered, :local_only,
                 :bic_validation_msg, :created_by)
        """), {
            "container_id": container_id,
            "perimeter": technical_info.get("dimensions") or technical_info.get("perimetre") or "",
            "type_conteneurs": type_conteneurs,
            "technical_info": json.dumps(technical_info),
            "bic_registered": bic_registered,
            "local_only": bool(non_bic),
            "bic_validation_msg": validation_msg if bic_registered else "Déclaré par l'utilisateur comme non-BIC",
            "created_by": f"{role}:{user_id}",
        })

        assigned_box = None
        if box_id:
            db.session.execute(text("""
                UPDATE boite_noir
                SET id_conteneurs=:container_id,
                    id_proprietaire=COALESCE(id_proprietaire, :company_id),
                    status='active',
                    updated_at=NOW()
                WHERE id_boite=:box_id
            """), {"container_id": container_id, "company_id": company_id, "box_id": box_id})
            assigned_box = int(box_id)

        db.session.commit()
        _sceller_evenement("CONTENEUR_CREE", assigned_box, {
            "id_conteneurs": container_id,
            "id_proprietaire": company_id,
            "id_boite": assigned_box,
            "type_conteneurs": type_conteneurs,
            "bic_registered": bic_registered,
            "local_only": bool(non_bic),
            "created_by": f"{role}:{user_id}",
        })
        device_assignment = _send_container_id_to_prototype(
            assigned_box,
            container_id,
            f"{role}:{user_id}",
        )
        return jsonify({
            "status": "success",
            "id_conteneurs": container_id,
            "id_boite": assigned_box,
            "device_assignment": device_assignment,
            "bic_registered": bic_registered,
            "local_only": bool(non_bic),
            "bic_classification": "HORS_BIC" if non_bic else "BIC",
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@cnt_bp.route("/api/containers/positions", methods=["GET"])
def get_positions():
    role, user_id = get_caller_identity()
    role = role or "superadmin"
    boites_filter = None
    if role == "owner":   boites_filter = get_boites_for_owner(user_id)
    elif role == "company": boites_filter = get_boites_for_agency(user_id)
    elif role == "client": boites_filter = get_boite_for_client(user_id)
    elif role == "driver": boites_filter = get_boite_for_driver(user_id)
    elif role == "port_authority": boites_filter = get_boites_for_port_authority(user_id)

    sql = """
        SELECT DISTINCT ON (id_boite)
            id_boite, lat, lon, temperature, vitesse, chocs, notif, horodatage
        FROM evenement_save
        WHERE lat IS NOT NULL AND lon IS NOT NULL
    """
    params = {}
    if boites_filter is not None:
        if not boites_filter:
            return jsonify([])
        placeholders = ",".join([f":b{i}" for i in range(len(boites_filter))])
        sql += f" AND id_boite IN ({placeholders})"
        params = {f"b{i}": v for i, v in enumerate(boites_filter)}
    sql += " ORDER BY id_boite, horodatage DESC"

    rows = db.session.execute(text(sql), params).fetchall()
    result = []
    for r in rows:
        alerts = []
        if r[6]:
            try: alerts = json.loads(r[6])
            except: pass
        result.append({
            "id_boite": r[0], "lat": float(r[1]), "lon": float(r[2]),
            "temp": float(r[3]) if r[3] else None,
            "speed": float(r[4]) if r[4] else 0,
            "shock": float(r[5]) if r[5] else 0,
            "alerts": alerts, "ts": str(r[7]),
        })
    return jsonify(result)

#  route 
@cnt_bp.route("/api/sell_containers", methods=["POST"])
@roles_required("superadmin")
def api_sell_containers():
    try:
        _ensure_owner_contact_schema()
        d = request.get_json()
        nom_agence = d.get("nom_agence")
        login      = d.get("login")
        password   = d.get("password")
        email      = d.get("email")
        phone      = d.get("phone") or d.get("contact") or d.get("telephone")
        niu        = d.get("niu")
        loc        = d.get("location")
        lat        = d.get("lat", 0)
        lon        = d.get("lon", 0)
        ids        = d.get("conteneurs_ids", [])
        box_ids    = [int(value) for value in (d.get("boite_ids") or [])]
        type_abo   = d.get("type_abonnement", "monthly")
        type_cont  = d.get("type_conteneur", "")
        perim      = d.get("perim", "")
        force_update = d.get("force_update", False) # NOUVEAU: Le garde-fou

        existing = None
        if login or niu:
            existing = db.session.execute(text(
                "SELECT id FROM proprietaire_conteneur WHERE login=:l OR niu=:n"
            ), {"l": login, "n": niu}).fetchone()

        if not existing and login and _login_exists(login):
            return jsonify({
                "error": "Ce login est deja utilise.",
                "code": "LOGIN_ALREADY_EXISTS",
                "suggestions": _login_suggestions(login),
            }), 409

        # 🛑 GARDE-FOU : L'entreprise existe, on demande confirmation au Front-end
        if existing and not force_update:
            return jsonify({
                "status": "confirm_required", 
                "message": "Cette entreprise existe déjà. Voulez-vous effectuer une mise à jour et lui attribuer ces nouveaux conteneurs ?"
            }), 202

        # 1. CRÉATION OU MISE À JOUR DE L'ENTREPRISE
        pw_hash = generate_password_hash(password) if password else None
        if existing:
            owner_id = existing[0]
            db.session.execute(text("""
                UPDATE proprietaire_conteneur
                SET nom_agence=:nom, addresse_mail=:email, lieu_residence=:loc,
                    lat=:lat, lon=:lon, contact=:phone, nbr_boite=nbr_boite + :nb
                WHERE id=:id
            """), {"nom": nom_agence, "email": email, "loc": loc,
                   "lat": lat, "lon": lon, "phone": phone, "nb": len(box_ids or ids), "id": owner_id})
            if pw_hash:
                db.session.execute(text(
                    "UPDATE proprietaire_conteneur SET password=:pw_hash WHERE id=:id"
                ), {"pw_hash": pw_hash, "id": owner_id})
        else:
            owner_id = db.session.execute(text("""
                INSERT INTO proprietaire_conteneur
                    (niu,nom_agence,login,password,addresse_mail,lieu_residence,lat,lon,contact,nbr_boite)
                VALUES (:niu,:nom,:login,:pw_hash,:email,:loc,:lat,:lon,:phone,:nb)
                RETURNING id
            """), {"niu": niu, "nom": nom_agence, "login": login, "pw_hash": pw_hash,
                   "email": email, "loc": loc, "lat": lat, "lon": lon, "phone": phone, "nb": len(box_ids or ids)}).scalar()

        boites_crees = []

        if box_ids:
            locked_boxes = db.session.execute(text("""
                SELECT id_boite, id_proprietaire FROM boite_noir
                WHERE id_boite = ANY(:box_ids)
                  AND id_proprietaire IS NULL
                  AND COALESCE(archived,FALSE)=FALSE
                FOR UPDATE
            """), {"box_ids": box_ids}).fetchall()
            locked_ids = {int(row[0]) for row in locked_boxes}
            if locked_ids != set(box_ids):
                db.session.rollback()
                return jsonify({
                    "error": "Une ou plusieurs boites appartiennent deja a une entreprise ou ne sont plus disponibles.",
                    "available_selected": sorted(locked_ids),
                }), 409
            db.session.execute(text("""
                UPDATE boite_noir SET id_proprietaire=:owner_id, status='unassigned', updated_at=NOW()
                WHERE id_boite = ANY(:box_ids)
            """), {"owner_id": owner_id, "box_ids": box_ids})
            contract_number = f"ARGOS-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
            contract_start = d.get("contract_start") or datetime.utcnow().date().isoformat()
            contract_months = max(1, min(int(d.get("contract_months") or 12), 120))
            contract_uid = db.session.execute(text("""
                INSERT INTO contracts
                    (company_id,contract_number,title,status,starts_on,ends_on,terms,box_ids,
                     argos_signer_name,argos_signed_at,created_by)
                VALUES (:company,:number,:title,'PENDING_ACCEPTANCE',CAST(:start AS date),
                        CAST(:start AS date) + (:months * INTERVAL '1 month'),
                        CAST(:terms AS jsonb),CAST(:boxes AS jsonb),'Direction generale ARGOS',NOW(),:created_by)
                RETURNING contract_uid
            """), {
                "company": str(owner_id), "number": contract_number,
                "title": f"Contrat de services ARGOS - {nom_agence}", "start": contract_start,
                "months": contract_months,
                "terms": json.dumps({
                    "email": email,
                    "phone": phone,
                    "location": loc,
                    "lat": lat,
                    "lon": lon,
                    "login": login,
                    "niu": niu,
                    "contract_months": contract_months,
                }),
                "boxes": json.dumps(box_ids), "created_by": str(get_caller_identity()[1]),
            }).scalar()
            contract_url = _notify_company_contract(
                owner_id, nom_agence, email, contract_uid, contract_number,
            )
            db.session.commit()
            notification_status = _notify_company_account(
                owner_id, nom_agence, email, phone, login, password,
                contract_url=contract_url, contract_number=contract_number,
            )
            _sceller_evenement("VENTE_ATTRIBUTION", None, {
                "owner_id": owner_id, "boites": box_ids, "contract_number": contract_number,
            })
            return jsonify({
                "status": "success", "boites": box_ids, "owner_id": owner_id,
                "contract_uid": str(contract_uid), "contract_number": contract_number,
                "contract_status": "PENDING_ACCEPTANCE",
                "contract_url": contract_url,
                "notifications": notification_status,
            }), 201
        
        # 2. CRÉATION ET LIAISON DES CONTENEURS / BOÎTES NOIRES
        for cid in ids:
            db.session.execute(text("""
                INSERT INTO conteneurs (id_conteneurs, taile_perimetre, type_conteneurs, status)
                VALUES (:id, :p, :t, 'ok') ON CONFLICT DO NOTHING
            """), {"id": cid, "p": perim, "t": type_cont})
            
            bid = db.session.execute(text("""
                INSERT INTO boite_noir (id_conteneurs, type_boite, id_proprietaire)
                VALUES (:c, :t, :owner_id) RETURNING id_boite
            """), {"c": cid, "t": type_abo, "owner_id": owner_id}).scalar()
            boites_crees.append(bid)

        db.session.commit()
        notification_status = _notify_company_account(owner_id, nom_agence, email, phone, login, password)
        _sceller_evenement("VENTE_ATTRIBUTION", None, {
            "owner_id": owner_id, "conteneurs": ids, "type_abonnement": type_abo
        })
        return jsonify({"status": "success", "boites": boites_crees, "notifications": notification_status}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "error": str(e)}), 500

@cnt_bp.route("/api/notifications", methods=["GET"])
def get_notifications():
    """Récupère les notifications selon le rôle et l'ID de l'utilisateur."""
    role, user_id = get_caller_identity()
    role = role or "guest"
    try:
        if role == "superadmin":
            _notify_expired_contracts()
        params = {"role": role, "uid": str(user_id)}
        target_filter = "(cible_role=:role OR cible_role='all' OR cible_role=:uid)"
        if role == "superadmin":
            scope_filter = "TRUE"
        else:
            if role == "owner":
                allowed = get_boites_for_owner(user_id) or []
            elif role == "company":
                allowed = get_boites_for_agency(user_id) or []
            elif role == "client":
                allowed = get_boite_for_client(user_id) or []
            elif role == "driver":
                allowed = get_boite_for_driver(user_id) or []
            elif role == "port_authority":
                allowed = get_boites_for_port_authority(user_id) or []
            else:
                allowed = []
            if allowed:
                placeholders = []
                for index, box_id in enumerate(dict.fromkeys(allowed)):
                    key = f"notif_box_{index}"
                    params[key] = box_id
                    placeholders.append(f":{key}")
                # Le JOIN sur boite_noir impose une affectation à un conteneur.
                scope_filter = f"""(
                    id_boite IS NULL OR id_boite IN (
                      SELECT id_boite FROM boite_noir
                      WHERE id_conteneurs IS NOT NULL
                        AND id_boite IN ({','.join(placeholders)})
                    )
                )"""
            else:
                scope_filter = "id_boite IS NULL"
        sql = f"""
            SELECT * FROM notifications
            WHERE status='unread' AND {target_filter} AND {scope_filter}
            ORDER BY horodatage DESC LIMIT 15
        """
        rows = db.session.execute(text(sql), params).fetchall()
        
        results = []
        for r in rows:
            d = dict(r._mapping)
            d['horodatage'] = d['horodatage'].isoformat() if d['horodatage'] else None
            results.append(d)
        return jsonify(results)
    except Exception as e:
        return jsonify([])
    

@cnt_bp.route("/api/inventory/<id_boite>", methods=["GET"])
def get_inventory(id_boite):
    if not _has_inventory_access(id_boite):
        return jsonify({"error": "Accès refusé"}), 403

    rows = db.session.execute(text("""
        SELECT
            e.id_eventinit AS identifiant_evt,
            e.horodatage,
            e.temperature,
            e.humidite,
            e.pressions,
            e.vitesse,
            e.chocs,
            e.lat,
            e.lon,
            e.log_action,
            e.notif,
            e.created_at,
            b.id_conteneurs,
            c.type_conteneurs
        FROM evenement_save e
        LEFT JOIN boite_noir b ON b.id_boite = e.id_boite
        LEFT JOIN conteneurs c ON c.id_conteneurs = b.id_conteneurs
        WHERE e.id_boite = :boite
        ORDER BY COALESCE(e.horodatage, e.created_at) DESC
        LIMIT 200
    """), {"boite": id_boite}).fetchall()

    return jsonify([dict(r._mapping) for r in rows])


@cnt_bp.route("/api/inventory/<id_boite>/export/pdf", methods=["GET"])
def export_inventory_pdf(id_boite):
    if not _has_inventory_access(id_boite):
        return jsonify({"error": "Accès refusé"}), 403

    rows = db.session.execute(text("""
        SELECT
            e.id_eventinit AS identifiant_evt,
            e.horodatage,
            e.temperature,
            e.humidite,
            e.pressions,
            e.vitesse,
            e.chocs,
            e.lat,
            e.lon,
            e.log_action,
            e.notif,
            e.created_at,
            b.id_conteneurs,
            c.type_conteneurs
        FROM evenement_save e
        LEFT JOIN boite_noir b ON b.id_boite = e.id_boite
        LEFT JOIN conteneurs c ON c.id_conteneurs = b.id_conteneurs
        WHERE e.id_boite = :boite
        ORDER BY COALESCE(e.horodatage, e.created_at) DESC
        LIMIT 200
    """), {"boite": id_boite}).fetchall()

    try:
        from weasyprint import HTML
    except Exception:
        return jsonify({"error": "WeasyPrint non installé. Installer via pip install weasyprint."}), 500

    html_content = f"""
    <html><body style=\"font-family:Arial;color:#1a1d23;background:#f8fafc;padding:24px\">
      <h1 style=\"color:#007a99\">Inventaire ARGOS — {id_boite}</h1>
      <p>Généré le {datetime.utcnow().strftime('%d/%m/%Y %H:%M')} UTC</p>
      <table border=\"1\" cellpadding=\"6\" width=\"100%\" cellspacing=\"0\" style=\"border-collapse:collapse;\">
      <thead>
        <tr style=\"background:#e6f4fb;color:#0f172a;\">
          <th align=\"left\">Identifiant</th>
          <th align=\"left\">Date</th>
          <th align=\"left\">Température</th>
          <th align=\"left\">Humidité</th>
          <th align=\"left\">Pression</th>
          <th align=\"left\">Action</th>
        </tr>
      </thead>
      <tbody>
    """
    for r in rows:
        d = dict(r._mapping)
        html_content += f"""
        <tr>
          <td style=\"font-family:monospace;font-size:10px\">{d.get('identifiant_evt','—')}</td>
          <td>{d['horodatage'].strftime('%d/%m/%Y %H:%M') if d.get('horodatage') else '—'}</td>
          <td>{d.get('temperature','—')}°C</td>
          <td>{d.get('humidite','—')}%</td>
          <td>{d.get('pressions','—')} hPa</td>
          <td>{d.get('log_action','—')}</td>
        </tr>
        """
    html_content += "</tbody></table></body></html>"

    pdf = HTML(string=html_content).write_pdf()
    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=inventaire_{id_boite}.pdf'
    return response


@cnt_bp.route("/api/container/vider", methods=["POST"])
def request_vider():
    """Étape 1 : Un utilisateur demande le vidage. Le chauffeur est bloqué."""
    data = request.get_json()
    id_boite = data.get("id_boite")
    motif = data.get("motif", "Non spécifié")
    user_id = data.get("user_id", "inconnu")
    role = data.get("role", "inconnu")
    
    # 1. Le chauffeur ne peut PAS initier la demande
    if role == 'driver':
        return jsonify({"error": "Les chauffeurs ne sont pas autorisés à initier le vidage."}), 403

    try:
        # 2. Envoi de la notification de demande à TOUS les acteurs ('all')
        db.session.execute(text("""
            INSERT INTO notifications (type, message, cible_role, id_boite, initiator_id)
            VALUES ('VIDAGE_REQUEST', :msg, 'all', :id_boite, :uid)
        """), {
            "msg": f"Demande de vidange initiée. Motif : {motif}", 
            "id_boite": id_boite,
            "uid": str(user_id)
        })
        
        # Scellage optionnel dans la blockchain
        _sceller_evenement("VIDAGE_REQUEST", id_boite, {"motif": motif, "initiator": user_id})
        
        db.session.commit()
        return jsonify({"status": "success", "message": "Demande envoyée pour validation."})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
    


@cnt_bp.route("/api/container/vider/confirmer", methods=["POST"])
def confirm_vider():
    data = request.get_json()
    id_boite = data.get("id_boite")
    motif = data.get("motif", "Validation vidage")
    user_id = data.get("user_id", "inconnu")
    role = data.get("role", "inconnu")

    if not id_boite:
        return jsonify({"error": "id_boite requis."}), 400
    if role in ["driver", "client"]:
        return jsonify({"error": "Accès refusé."}), 403

    try:
        db.session.execute(text("""
            UPDATE conteneurs SET status='off'
            WHERE id_conteneurs = (
                SELECT id_conteneurs FROM boite_noir WHERE id_boite = :boite_id LIMIT 1
            )
        """), {"boite_id": id_boite})

        db.session.execute(text("""
            INSERT INTO notifications (type, message, cible_role, id_boite, initiator_id)
            VALUES ('VIDAGE_CONFIRMED', :msg, 'all', :id_boite, :uid)
        """), {
            "msg": f"Vidage confirmé. Motif : {motif}",
            "id_boite": id_boite,
            "uid": str(user_id)
        })

        _sceller_evenement("VIDAGE_CONFIRMED", id_boite, {"motif": motif, "confirmed_by": user_id})
        db.session.commit()
        return jsonify({"status": "success", "message": "Vidage confirmé."})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@cnt_bp.route("/api/container/vider/reponse", methods=["POST"])
def reponse_vider():
    """Étape 2 : Un acteur répond (Valider / Refuser). Activation de la sécurité si refusé."""
    data = request.get_json()
    id_boite = data.get("id_boite")
    action = data.get("action") # "valider" ou "refuser"
    notif_id = data.get("notif_id")
    initiator_id = data.get("initiator_id")
    
    try:
        # 1. Marquer la demande initiale comme "lue" pour qu'elle disparaisse
        db.session.execute(text("UPDATE notifications SET status='read' WHERE id=:nid"), {"nid": notif_id})
        
        if action == "valider":
            # L'initiateur reçoit "Je suis d'accord"
            db.session.execute(text("""
                INSERT INTO notifications (type, message, cible_role, id_boite)
                VALUES ('VIDAGE_RESPONSE', 'Je suis d''accord pour la vidange.', :cible, :id_boite)
            """), {"cible": initiator_id, "id_boite": id_boite})
            # On passe le conteneur en off
            db.session.execute(text("""
                UPDATE conteneurs SET status='off'
                WHERE id_conteneurs = (
                    SELECT id_conteneurs FROM boite_noir WHERE id_boite = :boite_id LIMIT 1
                )
            """), {"boite_id": id_boite})
            
        elif action == "refuser":
            # L'initiateur reçoit "Je ne suis pas d'accord"
            db.session.execute(text("""
                INSERT INTO notifications (type, message, cible_role, id_boite)
                VALUES ('VIDAGE_RESPONSE', 'Je ne suis pas d''accord pour la vidange.', :cible, :id_boite)
            """), {"cible": initiator_id, "id_boite": id_boite})
            
            # ACTIVATION DE LA SÉCURITÉ (Sur écoute)
            db.session.execute(text("""
                UPDATE conteneurs SET status='danger'
                WHERE id_conteneurs = (
                    SELECT id_conteneurs FROM boite_noir WHERE id_boite = :boite_id LIMIT 1
                )
            """), {"boite_id": id_boite})
            
            # Alerte globale informant de la mise sur écoute
            db.session.execute(text("""
                INSERT INTO notifications (type, message, cible_role, id_boite)
                VALUES ('SECURITY_ALERT', 'ALERTE : Vidange refusée, le système de sécurité est activé et le conteneur est sur écoute.', 'all', :id_boite)
            """), {"id_boite": id_boite})

        _sceller_evenement(f"VIDAGE_REPONSE_{action.upper()}", id_boite, {"initiator": initiator_id})
        db.session.commit()
        return jsonify({"status": "success"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
    

@cnt_bp.route("/api/container/lier", methods=["POST"])
def api_lier_container():
    d = request.get_json()
    id_boite = d.get("id_boite")
    id_conteneur = d.get("id_conteneur")
    try:
        # Assigne une nouvelle boîte noire à un conteneur
        db.session.execute(text("""
            UPDATE boite_noir
            SET id_conteneurs = :c
            WHERE id_boite = :b
        """), {"c": id_conteneur, "b": id_boite})
        
        db.session.execute(text("""
            UPDATE conteneurs SET status = 'ok' WHERE id_conteneurs = :c
        """), {"c": id_conteneur})

        new_session = str(uuid.uuid4())[:8].upper()
        db.session.execute(text("""
            INSERT INTO evenement_save (id_boite, log_action, session_id)
            VALUES (:b, 'CHANGEMENT_CONTENEUR', :sid)
        """), {"b": id_boite, "sid": new_session})
        
        db.session.commit()
        _sceller_evenement("CHANGEMENT_CONTENEUR", id_boite, {"nouveau_conteneur": id_conteneur, "new_session": new_session})
        return jsonify({"status": "success", "new_session_id": new_session})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
    
@cnt_bp.route('/api/ai/deepseek', methods=['POST'])
@limiter.limit("20/hour")
def ai_chat_deepseek():
    """Proxy optionnel vers DeepSeek LLM. Nécessite DEEPSEEK_API_KEY dans l'environnement.
    Le frontend n'appelle pas cette route par défaut ; elle reste un repli sûr pour DeepSeek."""
    data = request.get_json(silent=True) or {}
    user_message = data.get('message', '').strip()
    if not user_message:
        return jsonify({"error": "Le message est requis."}), 400

    api_key = os.getenv('DEEPSEEK_API_KEY')
    if not api_key:
        return jsonify({
            "reply": "Assistant IA non configuré côté serveur. Merci de définir DEEPSEEK_API_KEY.",
            "echo": user_message,
        }), 200
    try:
        import requests
        r = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": "deepseek-chat", "messages": [{"role": "user", "content": user_message}]},
            timeout=30,
        )
        resp_data = r.json()
        if r.status_code != 200:
            return jsonify({"error": resp_data.get('error') or resp_data}), r.status_code

        reply = None
        if isinstance(resp_data, dict):
            reply = resp_data.get('reply')
            if not reply and resp_data.get('choices'):
                choice = resp_data['choices'][0]
                if isinstance(choice, dict):
                    reply = (choice.get('message') or {}).get('content') or choice.get('text')
        if not reply:
            reply = str(resp_data)

        return jsonify({"reply": reply, "provider_response": resp_data}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 502

"""Utilitaires transverses ARGOS.

Ce module regroupe les fonctions d’authentification, de blockchain,
de notification et d’aide métier utilisées par plusieurs blueprints.
"""

import os
import html
from sqlalchemy import text # type: ignore
import json, hashlib, smtplib, threading, uuid
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from email.utils import formataddr
from datetime import datetime
from flask import current_app, has_app_context, has_request_context, request as flask_request

# from app import db # Import de la base de données

# 1. Fonctions de Blockchain
def _hash_block(index, prev_hash, ts, data):
    raw = f"{index}{prev_hash}{ts}{json.dumps(data, sort_keys=True, default=str)}"
    return hashlib.sha256(raw.encode()).hexdigest()

def init_blockchain():
    from app import db

    # ... copiez le contenu de init_blockchain ici ...
    try:
        # 1. Création de la table
        db.session.execute(text("""
            CREATE TABLE IF NOT EXISTS blockchain_argos (
                block_index   SERIAL PRIMARY KEY,
                previous_hash TEXT NOT NULL,
                block_hash    TEXT NOT NULL UNIQUE,
                horodatage    TIMESTAMPTZ DEFAULT NOW(),
                event_type    VARCHAR(100),
                id_boite      VARCHAR(15),
                payload       JSONB,
                external_anchor TEXT,
                anchor_status   TEXT
            )
        """))
        db.session.commit() # IMPORTANT : Forcer la validation de la création de table
        db.session.execute(text("ALTER TABLE blockchain_argos ADD COLUMN IF NOT EXISTS external_anchor TEXT"))
        db.session.execute(text("ALTER TABLE blockchain_argos ADD COLUMN IF NOT EXISTS anchor_status TEXT"))
        db.session.commit()
        
        # 2. Vérification et insertion du bloc Genèse
        exists = db.session.execute(text("SELECT COUNT(*) FROM blockchain_argos")).scalar()
        if exists == 0:
            gh = _hash_block(0, "0", datetime.utcnow().isoformat(), {"genesis": True})
            payload = json.dumps({"genesis": True})
            db.session.execute(text("""
                INSERT INTO blockchain_argos (previous_hash, block_hash, event_type, payload)
                VALUES ('0', :h, 'GENESIS', :payload)
            """), {"h": gh, "payload": payload})
            db.session.commit() # Validation de l'insertion
    except Exception as e:
        db.session.rollback()
        print(f"Erreur d'initialisation blockchain: {e}")

def _anchor_to_remote_blockchain(block_index, previous_hash, block_hash, event_type, id_boite, payload):
    service_url = os.getenv('BLOCKCHAIN_SERVICE_URL')
    if not service_url:
        return None
    try:
        import requests
        response = requests.post(service_url, json={
            'block_index': block_index,
            'previous_hash': previous_hash,
            'block_hash': block_hash,
            'event_type': event_type,
            'id_boite': id_boite,
            'payload': payload,
        }, timeout=20)
        response.raise_for_status()
        data = response.json() if response.headers.get('Content-Type', '').startswith('application/json') else {'status': 'ok'}
        return data.get('external_anchor') or data.get('anchor_id') or data.get('txid') or str(data)
    except Exception as e:
        print(f"Erreur d'ancrage blockchain externe : {e}")
        return None


def get_caller_identity():
    """Retourne uniquement l'identite verifiee par le jeton signe."""
    from app.security import current_identity
    identity = current_identity()
    return str(identity.get("role", "")), str(identity.get("user_id", ""))


def get_boites_for_port_authority(authority_id):
    """Retourne les boîtes visibles par une autorité portuaire selon son LOCODE."""
    from app import db

    if not authority_id:
        return []
    try:
        row = db.session.execute(text(
            "SELECT port_locode FROM port_authority_user WHERE CAST(id AS TEXT) = :uid"
        ), {"uid": str(authority_id)}).fetchone()
        if not row or not row[0]:
            return []

        locode = row[0]
        rows = db.session.execute(text("""
            SELECT DISTINCT cva.id_boite
            FROM container_voyage_assignment cva
            JOIN maritime_voyage mv ON mv.id = cva.voyage_id
            WHERE mv.pod_locode = :locode
              AND cva.id_boite IS NOT NULL
        """), {"locode": locode}).fetchall()
        voyage_boxes = [r[0] for r in rows]

        try:
            from app.services.positioning_service import get_boxes_with_recent_position_in_port_zone
            zone_boxes = get_boxes_with_recent_position_in_port_zone(locode)
        except Exception:
            zone_boxes = []

        return sorted({*voyage_boxes, *zone_boxes})
    except Exception:
        db.session.rollback()
        return []


def _sceller_evenement(event_type, id_boite, payload):
    from app import db

    """Scelle un événement dans la blockchain de façon atomique."""
    try:
        payload_clean = json.loads(json.dumps(payload or {}, default=str))
        with db.session.begin_nested():
            last_block = db.session.execute(text(
                "SELECT block_index, block_hash FROM blockchain_argos "
                "ORDER BY block_index DESC LIMIT 1 FOR UPDATE"
            )).fetchone()

            index = last_block.block_index + 1 if last_block else 1
            prev_hash = last_block.block_hash if last_block else "0"
            ts = datetime.utcnow().isoformat()
            new_hash = _hash_block(index, prev_hash, ts, payload_clean)

            db.session.execute(text("""
                INSERT INTO blockchain_argos
                    (block_index, previous_hash, block_hash, horodatage,
                     event_type, id_boite, payload)
                VALUES
                    (:idx, :prev, :hash, :ts, :type, :id, CAST(:payload AS jsonb))
            """), {
                "idx": index,
                "prev": prev_hash,
                "hash": new_hash,
                "ts": ts,
                "type": event_type,
                "id": id_boite,
                "payload": json.dumps(payload_clean),
            })
        db.session.commit()

        external_anchor = _anchor_to_remote_blockchain(
            index, prev_hash, new_hash, event_type, id_boite, payload_clean
        )
        if external_anchor:
            db.session.execute(text(
                "UPDATE blockchain_argos SET external_anchor = :anchor, anchor_status = 'anchored' WHERE block_index = :idx"
            ), {"anchor": external_anchor, "idx": index})
            db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"[BLOCKCHAIN ERROR] {e}")

# Alias : `seal_block` est le nom historique utilisé dans certains blueprints.
seal_block = _sceller_evenement

# 2. Fonctions de Mails & WhatsApp
def extraire_contacts(query_sql, emails, numeros):
    """Exécute une requête (email[, contact]) et accumule dans emails/numeros."""
    from app import db
    rows = db.session.execute(text(query_sql)).fetchall()
    for r in rows:
        if r[0]: emails.append(r[0])
        if len(r) > 1 and r[1]: numeros.append(r[1])


def _notification_provider():
    return (os.getenv("NOTIFICATION_PROVIDER") or "smtp").strip().lower()


def get_public_base_url():
    """Retourne l'URL publique canonique (VPS/tunnel) sans slash final."""
    configured = ""
    if has_app_context():
        configured = (current_app.config.get("PUBLIC_BASE_URL") or "").strip()
    configured = configured or (os.getenv("PUBLIC_BASE_URL") or "").strip()
    if configured:
        return configured.rstrip("/")
    if has_request_context():
        return flask_request.url_root.rstrip("/")
    return ""


_EMAIL_THEMES = {
    "success": {"color": "#15803d", "soft": "#dcfce7", "label": "Confirmation"},
    "critical": {"color": "#dc2626", "soft": "#fee2e2", "label": "Alerte critique"},
    "warning": {"color": "#d97706", "soft": "#fef3c7", "label": "Attention"},
    "info": {"color": "#0284c7", "soft": "#e0f2fe", "label": "Information"},
}


def _email_theme(severity):
    return _EMAIL_THEMES.get(str(severity or "info").lower(), _EMAIL_THEMES["info"])


def _email_html(title, content, severity="info", action_url=None, action_label=None, qr_png=None):
    """Construit le rendu HTML commun à tous les messages ARGOS."""
    theme = _email_theme(severity)
    safe_title = html.escape(str(title or "Notification ARGOS"))
    safe_content = html.escape(str(content or "")).replace("\n", "<br>")
    button = ""
    if action_url:
        button = (
            '<p style="margin:28px 0 6px">'
            f'<a href="{html.escape(str(action_url), quote=True)}" '
            f'style="display:inline-block;background:{theme["color"]};color:#ffffff;'
            'padding:13px 22px;border-radius:8px;text-decoration:none;font-weight:700;'
            'font-family:Arial,sans-serif">'
            f'{html.escape(action_label or "Ouvrir ARGOS")}</a></p>'
        )
    qr_note = ""
    if qr_png:
        qr_note = '<p style="margin:22px 0 0;color:#475569;font-size:13px">Le QR code sécurisé est joint à ce message.</p>'
    return f'''<!doctype html>
<html lang="fr"><body style="margin:0;padding:24px;background:#f1f5f9;font-family:Arial,Helvetica,sans-serif;color:#0f172a">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0"><tr><td align="center">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:640px;background:#ffffff;border-radius:14px;overflow:hidden;border:1px solid #dbeafe">
      <tr><td style="background:#071525;padding:22px 30px;color:#ffffff"><span style="font-size:22px;font-weight:800;letter-spacing:3px">AR<span style="color:#00d4ff">G</span>OS</span><span style="float:right;background:{theme["color"]};padding:6px 10px;border-radius:999px;font-size:12px;font-weight:700">{theme["label"]}</span></td></tr>
      <tr><td style="padding:32px 30px"><h1 style="margin:0 0 16px;font-size:24px;line-height:1.25;color:#0f172a">{safe_title}</h1>
        <div style="border-left:4px solid {theme["color"]};background:{theme["soft"]};padding:16px 18px;border-radius:0 8px 8px 0;line-height:1.65;font-size:15px">{safe_content}</div>{button}{qr_note}
      </td></tr>
      <tr><td style="padding:18px 30px;background:#f8fafc;color:#64748b;font-size:12px;line-height:1.5">Message automatique ARGOS · Plateforme de surveillance maritime intelligente.<br>Ne partagez jamais vos identifiants de connexion.</td></tr>
    </table>
  </td></tr></table>
</body></html>'''


def _infobip_base_url():
    return (os.getenv("INFOBIP_BASE_URL") or "").strip().rstrip("/")


def _infobip_headers(content_type=None):
    api_key = (os.getenv("INFOBIP_API_KEY") or "").strip()
    headers = {"Authorization": f"App {api_key}", "Accept": "application/json"}
    if content_type:
        headers["Content-Type"] = content_type
    return headers


def _infobip_is_configured():
    return bool(_infobip_base_url() and (os.getenv("INFOBIP_API_KEY") or "").strip())


def _send_email_infobip(destinataires, titre, contenu, severity="info", action_url=None,
                        action_label=None, qr_png=None):
    import requests

    if not destinataires:
        return False
    if not _infobip_is_configured():
        print("Infobip email non configure (INFOBIP_BASE_URL/INFOBIP_API_KEY absents) — envoi ignore.")
        return False

    from_email = (
        os.getenv("INFOBIP_EMAIL_FROM")
        or os.getenv("SMTP_FROM_EMAIL")
        or os.getenv("SMTP_USER")
        or ""
    ).strip()
    # Identité homogène dans tous les clients de messagerie.
    from_name = "ARGOS"
    if not from_email:
        print("Infobip email non configure (INFOBIP_EMAIL_FROM absent) — envoi ignore.")
        return False

    sender = f"{from_name} <{from_email}>" if from_name else from_email
    endpoint = f"{_infobip_base_url()}/email/3/send"
    sent_any = False
    for dest in destinataires:
        if not dest or "@" not in str(dest):
            continue
        try:
            response = requests.post(
                endpoint,
                headers=_infobip_headers(),
                data={
                    "from": sender,
                    "to": str(dest).strip(),
                    "subject": f"ARGOS — {titre}",
                    "text": contenu,
                    "html": _email_html(titre, contenu, severity, action_url, action_label, qr_png),
                },
                timeout=25,
            )
            response.raise_for_status()
            sent_any = True
        except Exception as exc:
            print(f"Erreur d'envoi d'email Infobip vers {dest}: {exc}")
    return sent_any


def send_email_background(destinataires, titre, contenu, qr_png=None, qr_filename="argos_qr.png",
                          severity="info", action_url=None, action_label=None):
    """Envoie un e-mail ARGOS HTML, avec version texte et QR optionnel."""
    if _notification_provider() == "infobip":
        return _send_email_infobip(
            destinataires, titre, contenu, severity, action_url, action_label, qr_png
        )

    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    sender_email = (os.getenv("SMTP_FROM_EMAIL") or os.getenv("SMTP_USER") or "").strip()
    sender_password = (os.getenv("SMTP_PASSWORD") or "").strip()

    if not destinataires:
        return False
    if not sender_email or not sender_password:
        print("SMTP non configuré (SMTP_FROM_EMAIL/SMTP_USER ou SMTP_PASSWORD absents) — envoi ignoré.")
        return False

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)

        sent_any = False
        for dest in destinataires:
            if not dest or "@" not in dest:
                continue
            msg = MIMEMultipart("mixed")
            msg['From'] = formataddr(("ARGOS", sender_email))
            msg['To'] = dest
            msg['Subject'] = f"ARGOS — {titre}"
            alternative = MIMEMultipart("alternative")
            alternative.attach(MIMEText(contenu, 'plain', 'utf-8'))
            alternative.attach(MIMEText(
                _email_html(titre, contenu, severity, action_url, action_label, qr_png),
                'html', 'utf-8'
            ))
            msg.attach(alternative)
            if qr_png:
                qr_part = MIMEImage(qr_png, _subtype="png")
                qr_part.add_header("Content-Disposition", "attachment", filename=qr_filename)
                msg.attach(qr_part)
            server.send_message(msg)
            sent_any = True

        server.quit()
        return sent_any
    except Exception as e:
        print(f"Erreur d'envoi d'email: {e}")
        return False


def send_whatsapp_background(numeros, titre, contenu):
    """Envoie un message WhatsApp via Infobip ou l'API officielle Meta."""
    import requests

    if _notification_provider() == "infobip":
        sender = (os.getenv("INFOBIP_WHATSAPP_SENDER") or "").strip()
        default_recipient = (os.getenv("WHATSAPP_DEFAULT_RECIPIENT", "") or "").strip()
        if not _infobip_is_configured() or not sender:
            print("Infobip WhatsApp non configure (INFOBIP_BASE_URL/API_KEY/SENDER absents) — envoi ignore.")
            return False

        recipients = [str(numero) for numero in numeros if numero]
        if not recipients and default_recipient:
            recipients = [default_recipient]
        if not recipients:
            print("Aucun destinataire WhatsApp configuré; envoi ignore.")
            return False

        endpoint = f"{_infobip_base_url()}/whatsapp/1/message/text"
        sent_any = False
        for numero in recipients:
            destination = "".join(ch for ch in str(numero) if ch.isdigit())
            if not destination:
                continue
            try:
                response = requests.post(
                    endpoint,
                    headers=_infobip_headers("application/json"),
                    json={
                        "from": sender,
                        "to": destination,
                        "messageId": f"argos-{uuid.uuid4().hex}",
                        "content": {
                            "text": f"ARGOS - {titre}\n\n{contenu}"
                        },
                        "callbackData": "ARGOS",
                    },
                    timeout=25,
                )
                response.raise_for_status()
                sent_any = True
            except Exception as exc:
                print(f"Erreur WhatsApp Infobip pour {destination}: {exc}")
        return sent_any

    token = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
    phone_number_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
    api_version = os.getenv("WHATSAPP_API_VERSION", "v23.0")
    default_recipient = (os.getenv("WHATSAPP_DEFAULT_RECIPIENT", "") or "").strip()
    if not token or not phone_number_id:
        print("WhatsApp Cloud non configure; envoi ignore.")
        return False

    recipients = [str(numero) for numero in numeros if numero]
    if not recipients and default_recipient:
        recipients = [default_recipient]
    if not recipients:
        print("Aucun destinataire WhatsApp configuré; envoi ignore.")
        return False

    endpoint = f"https://graph.facebook.com/{api_version}/{phone_number_id}/messages"
    sent_any = False
    for numero in recipients:
        destination = "".join(ch for ch in str(numero) if ch.isdigit())
        if not destination:
            continue
        try:
            response = requests.post(
                endpoint,
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json={
                    "messaging_product": "whatsapp",
                    "recipient_type": "individual",
                    "to": destination,
                    "type": "text",
                    "text": {"preview_url": False, "body": f"ARGOS - {titre}\n\n{contenu}"},
                },
                timeout=20,
            )
            response.raise_for_status()
            sent_any = True
        except Exception as exc:
            print(f"Erreur WhatsApp pour {destination}: {exc}")
    return sent_any


def get_boites_for_owner(owner_id):
    from app import db
    """Retourne les id_boite liés à un propriétaire."""
    if not owner_id:
        return []
    # NOUVELLE REQUÊTE : Plus besoin de JOIN compliqué !
    rows = db.session.execute(text("""
        SELECT id_boite FROM boite_noir 
        WHERE id_proprietaire = :oid
    """), {"oid": owner_id}).fetchall()
    
    return [r[0] for r in rows]

def get_boites_for_agency(agency_id):
    """Récupère TOUTES les boîtes auxquelles une agence est abonnée"""
    from app import db
    from sqlalchemy import text
    if not agency_id:
        return []
    try:
        rows = db.session.execute(text("""
            SELECT id_boite
            FROM agence_abonnement
            WHERE CAST(id_agence AS TEXT) = :aid
              AND LOWER(COALESCE(status, '')) = 'actif'
        """), {"aid": str(agency_id)}).fetchall()
        return [r[0] for r in rows]
    except Exception:
        db.session.rollback()
        return []

def get_boite_for_driver(cni):
    from app import db

    """Retourne les id_boite liés aux colis du transporteur."""
    if not cni:
        return []
    boites = []
    try:
        row = db.session.execute(text("""
            SELECT id_boite, id_boites
            FROM transporteur
            WHERE id_cni = :c
        """), {"c": cni}).fetchone()
        if row:
            if row[0]:
                boites.append(row[0])
            if row[1]:
                try:
                    boites.extend(json.loads(row[1]))
                except Exception:
                    pass
    except Exception:
        db.session.rollback()

    rows = db.session.execute(text("""
        SELECT DISTINCT a.id_boite FROM colis co
        JOIN abonner a ON a.id_cni = co.id_cni_client
        WHERE co.id_cni_transporteur = :c
    """), {"c": cni}).fetchall() # type: ignore
    boites.extend([r[0] for r in rows])
    return list(dict.fromkeys([b for b in boites if b not in (None, "")]))
    

def get_boite_for_client(cni):
    from app import db
    """Retourne les id_boite d'un client via abonner."""
    rows = db.session.execute(text(
        "SELECT id_boite FROM abonner WHERE id_cni=:c"
    ), {"c": cni}).fetchall()
    return [r[0] for r in rows]

def check_securite_et_seuils(id_boite, temp, chocs):
    from app import db
    
    """Vérifie si le conteneur est sur écoute (Sécurité) et gère les alertes de seuils."""
    try:
        # 1. ÉCOUTE DE SÉCURITÉ (Si le conteneur a été refusé au vidage et mis en 'danger')
        boite = db.session.execute(text("""
            SELECT c.status
            FROM conteneurs c
            JOIN boite_noir b ON b.id_conteneurs = c.id_conteneurs
            WHERE b.id_boite = :boite_id
            LIMIT 1
        """), {"boite_id": id_boite}).fetchone() # type: ignore
        
        if boite and boite.status == 'danger':
            db.session.execute(text("""
                INSERT INTO notifications (type, message, cible_role, id_boite)
                VALUES ('SECURITY_ALERT', :msg, 'all', :id)
            """), {"msg": f"Activité détectée sur écoute de sécurité: Temp={temp}°C, Choc={chocs}G", "id": id_boite}) # type: ignore
            
        # 2. VÉRIFICATION DES SEUILS MATÉRIELS
        seuils = db.session.execute(text("SELECT * FROM seuils_alerte WHERE id_boite=:id"), {"id": id_boite}).fetchone() # type: ignore
        if not seuils:
            db.session.commit()
            return []

        alertes = []
        if temp is not None and seuils.temp_max is not None:
            if float(temp) > float(seuils.temp_max):
                alertes.append(f"Température trop haute ({temp}°C > {seuils.temp_max})")
            elif seuils.temp_min is not None and float(temp) < float(seuils.temp_min):
                alertes.append(f"Température trop basse ({temp}°C < {seuils.temp_min})")

        if chocs is not None and seuils.choc_max is not None and float(chocs) > float(seuils.choc_max):
            alertes.append(f"Choc critique détecté ({chocs}G)")

        if alertes:
            msg = " | ".join(alertes)
            db.session.execute(text("""
                INSERT INTO notifications (type, message, cible_role, id_boite)
                VALUES ('THRESHOLD_ALERT', :msg, 'all', :id)
            """), {"msg": msg, "id": id_boite}) # type: ignore

        db.session.commit()
        return alertes
    except Exception as e:
        db.session.rollback()
        print(f"Erreur check_securite_et_seuils: {e}")
        return []

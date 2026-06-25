
import os
from sqlalchemy import text # type: ignore
import json, hashlib, smtplib, threading
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

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


def _sceller_evenement(event_type, id_boite, payload):
    from app import db

    """
    Scelle un événement dans la blockchain.
    """
    try:
        # 1. Récupérer le dernier bloc pour obtenir son hash
        last_block = db.session.execute(text(
            "SELECT block_index, block_hash FROM blockchain_argos ORDER BY block_index DESC LIMIT 1"
        )).fetchone()
        
        index = last_block.block_index + 1 if last_block else 1
        prev_hash = last_block.block_hash if last_block else "0"
        ts = datetime.utcnow().isoformat()
        
        # 2. Calculer le nouveau hash
        new_hash = _hash_block(index, prev_hash, ts, payload)
        
        # 3. Insérer dans la table blockchain
        db.session.execute(text("""
            INSERT INTO blockchain_argos 
            (block_index, previous_hash, block_hash, horodatage, event_type, id_boite, payload)
            VALUES (:idx, :prev, :hash, :ts, :type, :id, :payload)
        """), {
            "idx": index,
            "prev": prev_hash,
            "hash": new_hash,
            "ts": ts,
            "type": event_type,
            "id": id_boite,
            "payload": json.dumps(payload)
        })
        db.session.commit()

        external_anchor = _anchor_to_remote_blockchain(index, prev_hash, new_hash, event_type, id_boite, payload)
        if external_anchor:
            db.session.execute(text(
                "UPDATE blockchain_argos SET external_anchor = :anchor, anchor_status = 'anchored' WHERE block_index = :idx"
            ), {"anchor": external_anchor, "idx": index})
            db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Erreur lors du scellage blockchain : {e}")

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

def send_email_background(destinataires, titre, contenu):
    """ Envoie un email en arrière-plan pour ne pas bloquer l'application """
    # Identifiants SMTP lus depuis l'environnement (voir .env)
    SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SENDER_EMAIL = os.getenv("SMTP_USER")
    SENDER_PASSWORD = os.getenv("SMTP_PASSWORD")

    if not destinataires:
        return
    if not SENDER_EMAIL or not SENDER_PASSWORD:
        print("SMTP non configuré (SMTP_USER / SMTP_PASSWORD absents) — envoi ignoré.")
        return

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)

        for dest in destinataires:
            if not dest or "@" not in dest: continue
            msg = MIMEMultipart()
            msg['From'] = f"ARGOS Alertes <{SENDER_EMAIL}>"
            msg['To'] = dest
            msg['Subject'] = f"Annonce ARGOS : {titre}"
            msg.attach(MIMEText(contenu, 'plain'))
            server.send_message(msg)
            
        server.quit()
    except Exception as e:
        print(f"Erreur d'envoi d'email: {e}")


def send_whatsapp_background(numeros, titre, contenu):
    """ 
    Envoie un message WhatsApp. 
    Vous devez configurer un compte Twilio (ou autre) pour que cela fonctionne.
    """
    for numero in numeros:
        if not numero: continue
        # Exemple avec Twilio (Nécessite: pip install twilio)
        # from twilio.rest import Client
        # client = Client('TWILIO_ACCOUNT_SID', 'TWILIO_AUTH_TOKEN')
        # message = client.messages.create(
        #     from_='whatsapp:+14155238886',
        #     body=f"🚨 *ARGOS Info* 🚨\n\n*{titre}*\n\n{contenu}",
        #     to=f'whatsapp:{numero}'
        #  )
        print(f"Simulation WhatsApp envoyé à {numero}: {titre}")


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
    # On cherche dans la nouvelle table de liaison
    rows = db.session.execute(text(
        "SELECT id_boite FROM agence_abonnement WHERE id_agence = :aid AND status = 'actif'"
    ), {"aid": agency_id}).fetchall()
    return [r[0] for r in rows]

def get_boite_for_driver(cni):
    from app import db

    """Retourne les id_boite liés aux colis du transporteur."""
    rows = db.session.execute(text("""
        SELECT DISTINCT a.id_boite FROM colis co
        JOIN abonner a ON a.id_cni = co.id_cni_client
        WHERE co.id_cni_transporteur = :c
    """), {"c": cni}).fetchall() # type: ignore
    return [r[0] for r in rows]
    

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
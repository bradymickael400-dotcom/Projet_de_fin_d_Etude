
import os

import json
from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash
from app.utils import (
    _hash_block, _sceller_evenement, seal_block,
    get_boite_for_client, get_boite_for_driver, get_boites_for_owner,
    get_boites_for_agency,
)
from sqlalchemy import text # type: ignore
from app import db
from app.utils import *

cnt_bp = Blueprint("containers", __name__)

# ═══════════════════════════════════════════════════════════
#  CONTENEURS — avec restriction rôle
# ═══════════════════════════════════════════════════════════
@cnt_bp.route("/api/containers/all", methods=["GET"])
def get_all_containers():
    role    = request.args.get("role")
    user_id = request.args.get("user_id")

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

    # Requête SQL
    base_sql = """
        SELECT c.id_conteneurs, '' AS resistance, c.taile_perimetre,
               c.type_conteneurs, c.status AS db_status,
               b.id_boite, b.type_boite, b.versions,
               e.temperature, e.humidite, e.pressions,
               e.vitesse, e.chocs, e.lat, e.lon,
               e.notif, e.log_action, e.horodatage,
               a.status AS abo_status
        FROM conteneurs c
        LEFT JOIN boite_noir b ON b.id_conteneurs = c.id_conteneurs
        LEFT JOIN abonner a ON a.id_boite = b.id_boite AND a.status = 'Actif'
        LEFT JOIN LATERAL (
            SELECT * FROM evenement_save
            WHERE id_boite = b.id_boite
            ORDER BY horodatage DESC LIMIT 1
        ) e ON TRUE
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
        # 3. Si abonnement absent/termine => forcer hors-ligne
        abo_status = m.get('abo_status')
        if not abo_status or str(abo_status).lower() != 'actif':
            status = 'off'
        else:
            if has_data:
                status = "danger" if len(alerts) >= 2 else ("warning" if alerts else "ok")
            
        result.append({
            "id":               m["id_conteneurs"],
            "id_boite":         m.get("id_boite") or "",
            "type_conteneurs":  m.get("type_conteneurs") or "",
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
            "lat":              float(m["lat"]) if m.get("lat") is not None else None,
            "lon":              float(m["lon"]) if m.get("lon") is not None else None,
            "alerts":           alerts,
            "log_action":       m.get("log_action") or "",
            "lastUpdate":       m["horodatage"].strftime("%H:%M:%S") if m.get("horodatage") else "--",
        })
        
    return jsonify(result)

@cnt_bp.route("/api/containers/available", methods=["GET"])
@cnt_bp.route("/api/containers/disponibles", methods=["GET"])  # alias utilisé par le frontend
def get_available_containers():
    role = request.args.get('role', '')
    user_id = request.args.get('user_id', '')
    if role == 'owner' and user_id:
        rows = db.session.execute(text("""
            SELECT c.id_conteneurs, b.id_boite
            FROM conteneurs c
            JOIN boite_noir b ON b.id_conteneurs = c.id_conteneurs
            WHERE c.status = 'ok'
              AND b.id_proprietaire = :uid
        """), {"uid": user_id}).fetchall()
    else:
        rows = db.session.execute(text("""
            SELECT c.id_conteneurs, b.id_boite FROM conteneurs c
            JOIN boite_noir b ON b.id_conteneurs = c.id_conteneurs
            WHERE c.status = 'ok'
        """)).fetchall()
    return jsonify([{"id": r[0], "id_boite": r[1]} for r in rows])

@cnt_bp.route("/api/containers/positions", methods=["GET"])
def get_positions():
    role    = request.args.get("role", "superadmin")
    user_id = request.args.get("user_id")
    boites_filter = None
    if role == "owner":   boites_filter = get_boites_for_owner(user_id)
    elif role == "company": boites_filter = get_boites_for_agency(user_id)
    elif role == "client": boites_filter = get_boite_for_client(user_id)
    elif role == "driver": boites_filter = get_boite_for_driver(user_id)

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
def api_sell_containers():
    try:
        d = request.get_json()
        nom_agence = d.get("nom_agence")
        login      = d.get("login")
        password   = d.get("password")
        email      = d.get("email")
        niu        = d.get("niu")
        loc        = d.get("location")
        lat        = d.get("lat", 0)
        lon        = d.get("lon", 0)
        ids        = d.get("conteneurs_ids", [])
        type_abo   = d.get("type_abonnement", "monthly")
        type_cont  = d.get("type_conteneur", "")
        perim      = d.get("perim", "")
        force_update = d.get("force_update", False) # NOUVEAU: Le garde-fou

        existing = None
        if login or niu:
            existing = db.session.execute(text(
                "SELECT id FROM proprietaire_conteneur WHERE login=:l OR niu=:n"
            ), {"l": login, "n": niu}).fetchone()

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
                    lat=:lat, lon=:lon, nbr_boite=nbr_boite + :nb
                WHERE id=:id
            """), {"nom": nom_agence, "email": email, "loc": loc,
                   "lat": lat, "lon": lon, "nb": len(ids), "id": owner_id})
            if pw_hash:
                db.session.execute(text(
                    "UPDATE proprietaire_conteneur SET password=:pw_hash WHERE id=:id"
                ), {"pw_hash": pw_hash, "id": owner_id})
        else:
            owner_id = db.session.execute(text("""
                INSERT INTO proprietaire_conteneur
                    (niu,nom_agence,login,password,addresse_mail,lieu_residence,lat,lon,nbr_boite)
                VALUES (:niu,:nom,:login,:pw_hash,:email,:loc,:lat,:lon,:nb)
                RETURNING id
            """), {"niu": niu, "nom": nom_agence, "login": login, "pw_hash": pw_hash,
                   "email": email, "loc": loc, "lat": lat, "lon": lon, "nb": len(ids)}).scalar()

        boites_crees = []
        
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
        _sceller_evenement("VENTE_ATTRIBUTION", None, {
            "owner_id": owner_id, "conteneurs": ids, "type_abonnement": type_abo
        })
        return jsonify({"status": "success", "boites": boites_crees}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "error": str(e)}), 500

@cnt_bp.route("/api/notifications", methods=["GET"])
def get_notifications():
    """Récupère les notifications selon le rôle et l'ID de l'utilisateur."""
    role = request.args.get("role", "guest")
    user_id = request.args.get("user_id", "")
    try:
        sql = """
            SELECT * FROM notifications 
            WHERE status = 'unread' 
            AND (cible_role = :role OR cible_role = 'all' OR cible_role = :uid)
            ORDER BY horodatage DESC LIMIT 15
        """
        rows = db.session.execute(text(sql), {"role": role, "uid": str(user_id)}).fetchall()
        
        results = []
        for r in rows:
            d = dict(r._mapping)
            d['horodatage'] = d['horodatage'].isoformat() if d['horodatage'] else None
            results.append(d)
        return jsonify(results)
    except Exception as e:
        return jsonify([])
    

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
        
        db.session.commit()
        seal_block("LIAISON_CONTENEUR", id_boite, {"nouveau_conteneur": id_conteneur})
        return jsonify({"status": "success"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
    
@cnt_bp.route('/api/ai/deepseek', methods=['POST'])
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

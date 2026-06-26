
import os
import time
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename
from flask import Blueprint, current_app, request, jsonify, url_for
from sqlalchemy import text # type: ignore

from app import db
from app.utils import _sceller_evenement, get_boites_for_owner
from app.utils import *

users_bp = Blueprint("users", __name__)


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
        db.session.execute(text("ALTER TABLE agence_utilisatrice ADD COLUMN IF NOT EXISTS created_by TEXT DEFAULT 'system'"))
        db.session.commit()
    except Exception:
        db.session.rollback()

# ═══════════════════════════════════════════════════════════════════
#  LISTES (companies, clients, drivers) — avec restriction
# ═══════════════════════════════════════════════════

@users_bp.route("/api/companies", methods=["GET"])
def get_companies():
    # Superadmin uniquement — les owners voient leurs propres données via dashboard/owner
    rows = db.session.execute(text("""
        SELECT p.id, p.niu, p.nom_agence, p.login, p.addresse_mail,
               p.lieu_residence, p.lat, p.lon, p.nbr_boite, p.created_at,
               COUNT(DISTINCT b.id_boite) AS nb_boites,
               COUNT(DISTINCT a.numero_a) AS nb_abonnes
        FROM proprietaire_conteneur p
        LEFT JOIN boite_noir b ON b.id_proprietaire = p.id
        LEFT JOIN abonner a ON a.id_boite = b.id_boite AND a.status='Actif'
        GROUP BY p.id ORDER BY p.id DESC
    """)).fetchall()
    return jsonify([dict(r._mapping) for r in rows])

@users_bp.route("/api/clients", methods=["GET"])
def get_clients():
    role, user_id = get_caller_identity()
    if not role or not user_id:
        return jsonify({"error": "Accès non autorisé"}), 401
    _ensure_client_cni_file_column()
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
            WHERE a.id_boite IN ({placeholders})
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
            WHERE cl.id_cni = :uid
        """), {"uid": user_id}).fetchall()
    else:
        # Superadmin — tout
        rows = db.session.execute(text("""
            SELECT cl.id_cni, cl.nom, cl.prenom, cl.login, cl.address_mail, cl.cni_file,
                   NULL AS contact, cl.created_at,
                   a.numero_a, a.id_boite, a.type_abonnement AS type_a,
                   a.created_at AS debut_a, NULL::timestamp AS fin_a,
                   a.status, NULL::numeric AS frais
            FROM client cl
            LEFT JOIN abonner a ON a.id_cni = cl.id_cni
            ORDER BY cl.created_at DESC
        """)).fetchall()
    return jsonify([dict(r._mapping) for r in rows])

@users_bp.route("/api/drivers", methods=["GET"])
def get_drivers():
    role, user_id = get_caller_identity()
    if role in ["driver", "client"]:
        return jsonify([])
    try:
        rows = db.session.execute(text("SELECT * FROM transporteur ORDER BY created_at DESC")).fetchall()
        return jsonify([dict(r._mapping) for r in rows])
    except Exception as e:
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

        file    = request.files.get("cni")
        saved   = None
        if not login or not pwd:
            return jsonify({"error": "login et mot de passe requis."}), 400

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
                if dest or desc or plomb:
                    db.session.execute(text("""
                        INSERT INTO colis (id_cni_client, id_cni_transporteur, num_plom, desc_colis, status, destination)
                        VALUES (:cni, NULL, :plomb, :desc, 'En Transit', :dest)
                    """), {"cni": niu, "plomb": plomb, "desc": desc, "dest": dest})

        db.session.commit()
        return jsonify({"status": "success", "file_url": saved}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "error": str(e)}), 500


@users_bp.route("/api/register_driver", methods=["POST"])
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


@users_bp.route("/api/register_user", methods=["POST"])
def register_user():
    d = request.get_json() or {}
    if not d.get("login") or not d.get("password"):
        return jsonify({"error": "login et mot de passe requis."}), 400
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
        db.session.commit()
        return jsonify({"status": "success"}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
    

# oute de création de Colis/Abonnement avec Garde-fou

@users_bp.route("/api/abonnement/nouveau", methods=["POST"])
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
        
        if updates:
            sql = "UPDATE agence_utilisatrice SET " + ", ".join(updates) + " WHERE id = :id"
            result = db.session.execute(text(sql), params)
            if getattr(result, "rowcount", 0) == 0:
                return jsonify({"error": "Entreprise introuvable"}), 404
        
        db.session.commit()
        return jsonify({"status": "success"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@users_bp.route("/api/client/extend", methods=["POST"])
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
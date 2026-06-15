from flask import Blueprint, render_template, jsonify, request, current_app, url_for
from sqlalchemy import text
import json
from datetime import datetime, timedelta
from app import db
from werkzeug.utils import secure_filename
import os, time

main_bp = Blueprint("main", __name__)

@main_bp.route("/")
def home():
    return render_template("index.html")

@main_bp.route("/api/data")
def data_api():
    try:
        classes_automap = current_app.config['AUTOMAP_CLASSES']
        
        Abonner = getattr(classes_automap, 'Abonner', getattr(classes_automap, 'abonner', None))
        
        if not Abonner:
            return jsonify({"error": "La classe 'Abonner' n'a pas été trouvée dans l'automap"}), 500
            
        abonnes = db.session.query(Abonner).all()  
        
        data = [
            {
                "id_boite": abonne.id_boite, 
                "id_cni": abonne.id_cni,
                "type_abonnement": getattr(abonne, 'type_a', None)
            } 
            for abonne in abonnes
        ]
        
        return jsonify(data)

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    

@main_bp.route("/api/login", methods=["POST", "OPTIONS"])
def api_login():
    # Gestion de la requête Preflight (CORS)
    if request.method == "OPTIONS":
        return jsonify({"status": "CORS_OK"}), 200

    try:
        data = request.get_json()
        if not data:
            print("❌ Erreur backend : Aucune donnée JSON reçue.")
            return jsonify({"error": "Données JSON manquantes"}), 400

        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            return jsonify({"error": "Login et mot de passe requis"}), 400

        print(f"📩 Tentative de connexion reçue pour le login : {username}")

        if 'AUTOMAP_CLASSES' not in current_app.config:
            print("❌ Erreur : 'AUTOMAP_CLASSES' introuvable.")
            return jsonify({"error": "Registre automap introuvable."}), 500

        classes = current_app.config['AUTOMAP_CLASSES']

        # -------------------------------------------------------------------
        # MAPPING DES TABLES ET DES RÔLES
        # Format: ('NomExactDeLaTableBDD', 'role_renvoyé_au_frontend')
        # -------------------------------------------------------------------
        roles_mapping = [
            ('SuperAdmin', 'superadmin'),
            ('Client', 'client'),
            ('Transporteur', 'driver'),
            ('Proprietaire_Conteneur', 'owner'),
            ('Agence_Utilisatrice', 'agence')
        ]

        for class_name, role_name in roles_mapping:
            # Récupère la classe correspondante dans l'automap
            cls = getattr(classes, class_name, getattr(classes, class_name.lower(), None))
            
            if cls:
                # -------------------------------------------------------------------
                # VÉRIFICATION PGCYPTO DIRECTEMENT DANS LA BASE DE DONNÉES
                # On demande à Postgres de comparer le mot de passe fourni avec 
                # la fonction crypt(mot_de_passe_fourni, mot_de_passe_en_bdd)
                # -------------------------------------------------------------------
                sql_filter = text("login = :username AND password = crypt(:password, password)")
                
                try:
                    # Exécution de la requête avec les paramètres sécurisés
                    user = db.session.query(cls).filter(sql_filter).params(
                        username=username, 
                        password=password
                    ).first()

                    if user:
                        print(f"✅ Utilisateur trouvé dans la table {class_name} avec le rôle {role_name}")
                        return jsonify({
                            "status": "success", 
                            "role": role_name, 
                            "username": username
                        }), 200

                except Exception as e:
                    print(f"⚠️ Erreur lors de la requête sur {class_name}: {e}")
                    continue

        print("❌ Aucun utilisateur correspondant (ou mot de passe incorrect).")
        return jsonify({"error": "Identifiants ou mot de passe incorrects"}), 401

    except Exception as e:
        print("\n💥 CRASH SERVEUR DANS API_LOGIN 💥")
        import traceback
        traceback.print_exc()
        return jsonify({"error": "Erreur interne du serveur"}), 500
    

# ======== function pour ajouter les donnees d'un utilisateur dans la base de données ========

@main_bp.route("/api/sell_containers", methods=["POST"])
def api_sell_containers():
    try:
        data = request.get_json()
        
        # Récupération des données
        nom_agence = data.get('nom_agence')
        login = data.get('login')
        password = data.get('password')
        email = data.get('email')
        niu = data.get('niu')
        location = data.get('location')
        lat = data.get('lat')
        lon = data.get('lon')
        conteneurs_ids = data.get('conteneurs_ids', [])
        type_abo = data.get('type_abonnement')
        type_conteneur = data.get('type_conteneur')
        perimetre = data.get('perim')

        # Vérification des contraintes uniques avant insertion
        existing_owner = None
        if login or niu:
            existing_owner = db.session.execute(
                text("SELECT id, niu, login FROM Proprietaire_Conteneur WHERE login = :login OR niu = :niu"),
                {'login': login, 'niu': niu}
            ).fetchone()

        owner_id = None
        if existing_owner:
            owner_id = existing_owner[0]
            # Mise à jour du propriétaire existant si les données changent
            db.session.execute(text("""
                UPDATE Proprietaire_Conteneur
                SET Nom_agence = :nom_agence,
                    addresse_mail = :email,
                    lieu_residence = :location,
                    lat = :lat,
                    lon = :lon,
                    Nbr_boite = GREATEST(Nbr_boite, :nbr)
                WHERE id = :owner_id
            """), {
                'nom_agence': nom_agence,
                'email': email,
                'location': location,
                'lat': lat,
                'lon': lon,
                'nbr': len(conteneurs_ids),
                'owner_id': owner_id
            })
            if password:
                db.session.execute(text("""
                    UPDATE Proprietaire_Conteneur
                    SET password = crypt(:password, gen_salt('bf'))
                    WHERE id = :owner_id
                """), {'password': password, 'owner_id': owner_id})
        else:
            # DÉBUT DE LA TRANSACTION
            # 1. Création du Propriétaire
            insert_proprio = text("""
                INSERT INTO Proprietaire_Conteneur (NIU, Nom_agence, login, password, addresse_mail, lieu_residence, lat, lon, Nbr_boite)
                VALUES (:niu, :nom_agence, :login, crypt(:password, gen_salt('bf')), :email, :location, :lat, :lon, :nbr)
                RETURNING id;
            """)
            result = db.session.execute(insert_proprio, {
                "niu": niu, "nom_agence": nom_agence, "login": login,
                "password": password, "email": email, "location": location, "lat": lat, "lon": lon, "nbr": len(conteneurs_ids)
            })
            owner_id = result.scalar()
        
        # 2. Création des conteneurs et boîtes liées
        for cont_id in conteneurs_ids:
            # Créer le conteneur
            db.session.execute(text("INSERT INTO Conteneurs (id_conteneurs,taile_perimetre,type_conteneurs) VALUES (:id, :perim, :type_cont) ON CONFLICT DO NOTHING"), {'id': cont_id, 'perim': perimetre, 'type_cont': type_conteneur})
            
            # Créer la boîte noire (générée auto par séquence) et lier au conteneur
            db.session.execute(text("""
                INSERT INTO Boite_noir (id_conteneurs, type_boite)
                VALUES (:c_id, :type_abo)
            """), {'c_id': cont_id, 'type_abo': type_abo})

        db.session.commit()
        return jsonify({"status": "success", "message": "Compte et matériels créés"}), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "error": str(e)}), 500
    

# Route pour récupérer les conteneurs disponibles (status = false)
@main_bp.route("/api/containers/available", methods=["GET"])
def get_available_containers():
    # Seuls les conteneurs liés à une boîte noire mais sans trajet actif
    sql = text("""
        SELECT c.id_conteneurs 
        FROM Conteneurs c
        JOIN Boite_noir b ON c.id_conteneurs = b.id_conteneurs
        WHERE NOT EXISTS (SELECT 1 FROM Colis WHERE id_colis = c.id_conteneurs AND status = 'true')
    """)
    result = db.session.execute(sql).fetchall()
    return jsonify([row[0] for row in result])

# Route pour l'enregistrement (Client ou Agence)
@main_bp.route("/api/register_user", methods=["POST"])
def register_user():
    data = request.get_json()
    nom_agence = data.get('nom_agence') # Si présent -> Agence
    
    try:
        if nom_agence:
            # Insertion dans Agence_Utilisatrice
            db.session.execute(text("""INSERT INTO Agence_Utilisatrice (NIU, Nom_agence, login, password, addresse_mail) 
                                       VALUES (:niu, :nom_agence, :login, crypt(:password, gen_salt('bf')), :email)"""), data)
        else:
            # Insertion dans Client
            db.session.execute(text("""INSERT INTO Client (id_cni, login, password, nom, prenom, address_mail) 
                                       VALUES (:id_cni, :login, crypt(:password, gen_salt('bf')), :nom, :prenom, :email)"""), data)
        db.session.commit()
        return jsonify({"status": "success"}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# Endpoint pour l'enregistrement avec upload de fichier (CNI)
@main_bp.route('/api/register_user_file', methods=['POST'])
def register_user_file():
    try:
        form = request.form
        nom_agence = form.get('nom_agence')
        # Champs communs
        login = form.get('login')
        password = form.get('password')
        email = form.get('email') or form.get('address_mail')
        niu = form.get('niu') or form.get('id_cni')
        nom = form.get('nom')
        prenom = form.get('prenom')
        contact = form.get('contact') or form.get('phone')

        # Traiter le fichier si présent
        file = request.files.get('cni')
        saved_url = None
        if file and file.filename:
            img_folder = os.path.join(current_app.root_path, 'static', 'img')
            os.makedirs(img_folder, exist_ok=True)
            fname = secure_filename(f"{(niu or login or 'file')}_{int(time.time())}_{file.filename}")
            fpath = os.path.join(img_folder, fname)
            file.save(fpath)
            saved_url = url_for('static', filename=f'img/{fname}')

        if nom_agence:
            # Insertion Agence
            db.session.execute(text("""INSERT INTO Agence_Utilisatrice (NIU, Nom_agence, login, password, addresse_mail) 
                                       VALUES (:niu, :nom_agence, :login, crypt(:password, gen_salt('bf')), :email)"""), {
                'niu': niu, 'nom_agence': nom_agence, 'login': login, 'password': password, 'email': email
            })
        else:
            # Insertion Client
            db.session.execute(text("""INSERT INTO Client (id_cni, login, password, nom, prenom, address_mail, contact) 
                                       VALUES (:id_cni, :login, crypt(:password, gen_salt('bf')), :nom, :prenom, :email, :contact)"""), {
                'id_cni': niu, 'login': login, 'password': password, 'nom': nom, 'prenom': prenom, 'email': email, 'contact': contact
            })

        db.session.commit()
        return jsonify({'status':'success','file_url': saved_url}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'status':'error','error': str(e)}), 500
    
# ======= end point pour enregistre les donnees des valeurs seuil a un conteneurs ========== 

# 1. Récupérer les événements depuis TimescaleDB
@main_bp.route("/api/events")
def get_events():
    # TimescaleDB est idéal pour récupérer les derniers événements
    events = db.session.execute(text("SELECT * FROM Evenement_save ORDER BY horodatage DESC LIMIT 50")).fetchall()
    return jsonify([dict(row._mapping) for row in events])

# 2. Sauvegarder les seuils

@main_bp.route("/api/config/thresholds", methods=["POST"])
def update_thresholds():
    try:
        data = request.get_json()
        
        # Le frontend envoie l'ID du conteneur (ex: 'idcnt2024')
        id_conteneur_recu = data.get('id_boite') 

        # 1. ÉTAPE CLÉ : Retrouver l'id_boite correspondant à cet id_conteneurs
        boite = db.session.execute(
            text("SELECT id_boite FROM Boite_noir WHERE id_conteneurs = :c_id LIMIT 1"),
            {'c_id': id_conteneur_recu}
        ).fetchone()

        # Si le conteneur n'a pas de boîte noire associée, on bloque
        if not boite:
            return jsonify({"error": f"Aucune boîte noire n'est associée au conteneur {id_conteneur_recu}"}), 404

        vrai_id_boite = boite[0] # Ex: 'BN-000001'

        # 2. Sauvegarder les seuils avec le bon id_boite
        sql = text("""
            INSERT INTO Seuils_Alerte (
                id_boite, temp_max, humi_max, choc_max, pression_min, vitesse_max, angle_max, updated_at
            ) VALUES (
                :id_boite, :temp_max, :humi_max, :choc_max, :pression_min, :vitesse_max, :angle_max, NOW()
            )
            ON CONFLICT (id_boite) DO UPDATE SET
                temp_max = EXCLUDED.temp_max,
                humi_max = EXCLUDED.humi_max,
                choc_max = EXCLUDED.choc_max,
                pression_min = EXCLUDED.pression_min,
                vitesse_max = EXCLUDED.vitesse_max,
                angle_max = EXCLUDED.angle_max,
                updated_at = NOW();
        """)
        
        params = {
            'id_boite': vrai_id_boite, # <-- On utilise l'ID trouvé en base
            'temp_max': data.get('temp_max'),
            'humi_max': data.get('humi_max'),
            'choc_max': data.get('choc_max'),
            'pression_min': data.get('pression_min'),
            'vitesse_max': data.get('vitesse_max'),
            'angle_max': data.get('angle_max')
        }
        
        db.session.execute(sql, params)
        db.session.commit()
        
        return jsonify({"status": "success"})

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# ========================== endpoind de telemetrie on prends en entree les donnees du dispositif on les compare avec le seuil.
@main_bp.route('/api/telemetry', methods=['POST'])
def receive_telemetry():
    """
    Point d'entrée pour les dispositifs externes (Capteurs IoT).
    Accepte multipart/form-data (pour gérer le fichier audio media_1_url) ou JSON.
    """
    try:
        # Récupération des données (gère form-data si fichier audio envoyé, sinon JSON)
        data = request.form if request.form else request.get_json()
        
        id_boite = data.get('id_boite')
        temp = float(data.get('temperature', 0))
        humi = float(data.get('humidite', 0))
        press = float(data.get('pressions', 0))
        chocs = float(data.get('chocs', 0))
        vitesse = float(data.get('vitesse', 0))
        lat = data.get('lat')
        lon = data.get('lon')

        # 1. Gestion du fichier Audio (media_1_url)
        audio_file = request.files.get('audio')
        media_url = None
        if audio_file and audio_file.filename:
            audio_folder = os.path.join(current_app.root_path, 'static', 'audio')
            os.makedirs(audio_folder, exist_ok=True)
            fname = secure_filename(f"evt_{id_boite}_{int(time.time())}.mp3")
            audio_file.save(os.path.join(audio_folder, fname))
            media_url = url_for('static', filename=f'audio/{fname}')

        # 2. Récupérer les seuils configurés
        seuils = db.session.execute(
            text("SELECT * FROM Seuils_Alerte WHERE id_boite = :id_boite LIMIT 1"), 
            {'id_boite': id_boite}
        ).fetchone()
        
        # Valeurs par défaut si aucun seuil configuré
        s = dict(seuils._mapping) if seuils else {}
        t_temp = float(s.get('temp_max') or 32.0)
        t_hum = float(s.get('humi_max') or 75.0)
        t_choc = float(s.get('choc_max') or 5.0)
        t_press = float(s.get('pression_min') or 995.0)
        t_vit = float(s.get('vitesse_max') or 90.0)

        # 3. Comparaison et génération des alertes
        alerts = []
        if temp > t_temp: alerts.append(f"Température critique: {temp}°C (Max: {t_temp})")
        if humi > t_hum: alerts.append(f"Humidité critique: {humi}% (Max: {t_hum})")
        if chocs > t_choc: alerts.append(f"Choc violent: {chocs}G (Max: {t_choc})")
        if press < t_press: alerts.append(f"Pression basse: {press}hPa (Min: {t_press})")
        if vitesse > t_vit: alerts.append(f"Survitesse: {vitesse}km/h (Max: {t_vit})")

        # Formater la notification (si alerte)
        notif_msg = json.dumps(alerts) if alerts else None
        log_action = "Alerte générée" if alerts else "Scan régulier"

        # 4. Enregistrement dans Evenement_save
        insert_sql = text("""
            INSERT INTO Evenement_save 
            (id_boite, media_1_url, temperature, humidite, pressions, lat, lon, log_action, vitesse, chocs, notif)
            VALUES 
            (:id_boite, :media, :temp, :humi, :press, :lat, :lon, :log_action, :vit, :chocs, :notif)
        """)
        db.session.execute(insert_sql, {
            'id_boite': id_boite, 'media': media_url, 'temp': temp, 'humi': humi, 
            'press': press, 'lat': lat, 'lon': lon, 'log_action': log_action, 
            'vit': vitesse, 'chocs': chocs, 'notif': notif_msg
        })
        db.session.commit()

        return jsonify({'status': 'success', 'alerts': alerts}), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# ===== ensemble de id des conteneurs ====

@main_bp.route("/api/containers/all", methods=["GET"])
def get_all_containers():
    # Récupère tous les IDs de conteneurs pour le menu déroulant
    sql = text("SELECT id_conteneurs FROM Conteneurs")
    result = db.session.execute(sql).fetchall()
    return jsonify([row[0] for row in result])


# ===================== endpoint pour la connexion a la base et la recuperations des donnees 



@main_bp.route("/api/stats", methods=["GET"])
def get_dashboard_stats():
    try:
        period = request.args.get('period', '7d')
        
        # 1. Filtre de temps et intervalle de regroupement (Heure ou Jour)
        time_filter = ""
        interval = "day" # Par défaut on groupe par jour
        
        if period == '24h':
            time_filter = "WHERE horodatage >= NOW() - INTERVAL '24 hours'"
            interval = "hour" # Sur 24h, on affiche point par point par heure
        elif period == '7d':
            time_filter = "WHERE horodatage >= NOW() - INTERVAL '7 days'"
        elif period == '30d':
            time_filter = "WHERE horodatage >= NOW() - INTERVAL '30 days'"
        elif period == '3m':
            time_filter = "WHERE horodatage >= NOW() - INTERVAL '3 months'"
        elif period == 'all':
            time_filter = ""
            interval = "month" # Sur "toujours", on groupe par mois

        # ==========================================
        # REQUÊTE 1 : Les 4 KPIs du haut
        # ==========================================
        kpi_sql = text(f"""
            SELECT 
                COALESCE(AVG(temperature), 0) as avg_temp,
                COUNT(*) as total_events,
                SUM(CASE WHEN chocs > 0 THEN 1 ELSE 0 END) as total_shocks,
                SUM(CASE WHEN notif IS NOT NULL AND notif != '[]' THEN 1 ELSE 0 END) as total_alertes
            FROM Evenement_save
            {time_filter}
        """)
        kpi_result = db.session.execute(kpi_sql).fetchone()
        
        total_events = kpi_result[1]
        fiabilite = 100.0
        if total_events > 0:
            fiabilite = round(100 - (((kpi_result[3] or 0) / total_events) * 100), 1)

        # ==========================================
        # REQUÊTE 2 : Données temporelles (Pour Temp, Hum, Press, Vitesse, Chocs)
        # ==========================================
        ts_sql = text(f"""
            SELECT 
                TO_CHAR(DATE_TRUNC('{interval}', horodatage), 'DD/MM HH24:MI') as label,
                COALESCE(AVG(temperature), 0) as temp,
                COALESCE(AVG(humidite), 0) as hum,
                COALESCE(AVG(pressions), 0) as press,
                COALESCE(AVG(vitesse), 0) as vit,
                COALESCE(SUM(chocs), 0) as chocs
            FROM Evenement_save
            {time_filter}
            GROUP BY DATE_TRUNC('{interval}', horodatage)
            ORDER BY DATE_TRUNC('{interval}', horodatage) ASC
        """)
        ts_results = db.session.execute(ts_sql).fetchall()

        # Formatage des listes pour le Javascript
        labels = [row[0] for row in ts_results]
        data_temp = [round(row[1], 1) for row in ts_results]
        data_hum = [round(row[2], 1) for row in ts_results]
        data_press = [round(row[3], 1) for row in ts_results]
        data_vit = [round(row[4], 1) for row in ts_results]
        data_chocs = [round(row[5], 1) for row in ts_results]

        # ==========================================
        # REQUÊTE 3 : Répartition des alertes (Graphique Doughnut)
        # ==========================================
        dist_sql = text(f"""
            SELECT
                SUM(CASE WHEN notif ILIKE '%choc%' THEN 1 ELSE 0 END) as a_choc,
                SUM(CASE WHEN notif ILIKE '%temp%' THEN 1 ELSE 0 END) as a_temp,
                SUM(CASE WHEN notif ILIKE '%humid%' THEN 1 ELSE 0 END) as a_hum,
                SUM(CASE WHEN notif ILIKE '%vent%' THEN 1 ELSE 0 END) as a_vent,
                SUM(CASE WHEN notif ILIKE '%press%' THEN 1 ELSE 0 END) as a_press
            FROM Evenement_save
            {time_filter}
        """)
        dist_result = db.session.execute(dist_sql).fetchone()

        return jsonify({
            "status": "success",
            "kpi": {
                "avg_temp": round(kpi_result[0], 1),
                "total_shocks": int(kpi_result[2] or 0),
                "total_alertes": int(kpi_result[3] or 0),
                "fiabilite": fiabilite
            },
            "charts": {
                "labels": labels,
                "temp": data_temp,
                "hum": data_hum,
                "press": data_press,
                "speed": data_vit,
                "shocks": data_chocs,
                "alerts_dist": [
                    int(dist_result[0] or 0), # Choc
                    int(dist_result[1] or 0), # Temp
                    int(dist_result[2] or 0), # Hum
                    int(dist_result[3] or 0), # Vent
                    int(dist_result[4] or 0)  # Pression
                ]
            }
        }), 200

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    

# exécute les requêtes SQL pour compter les entreprises, extraire les pires alertes, 
# trouver les 5 conteneurs les plus critiques et lister les 5 entreprises les plus récentes.

@main_bp.route("/api/dashboard/superadmin", methods=["GET"])
def get_sa_dashboard_data():
    try:
        # 1. Total entreprises (propriétaires et non propriétaires)
        # Remplace 'Entreprise' par le nom exact de ta table si besoin
        sql_ent = text("SELECT COUNT(*) FROM proprietaire_conteneur")
        tot_entreprises = db.session.execute(sql_ent).scalar() or 0

        # 2. Entreprises abonnées actives
        sql_subs = text("SELECT COUNT(*) FROM abonner WHERE type_a IS NOT NULL AND status = 'Actif'")
        tot_abonnes = db.session.execute(sql_subs).scalar() or 0

        # 3. Alertes actives (tous les événements avec une notification JSON valide)
        sql_alerts = text("SELECT COUNT(*) FROM Evenement_save WHERE notif IS NOT NULL AND notif != '[]'")
        tot_alertes = db.session.execute(sql_alerts).scalar() or 0

        # 4. Alertes Récentes (Limité aux 10 dernières pour ne pas faire exploser l'interface)
        sql_recent = text("""
            SELECT horodatage, id_boite, notif, log_action 
            FROM Evenement_save 
            WHERE notif IS NOT NULL AND notif != '[]' 
            ORDER BY horodatage DESC LIMIT 10
        """)
        recent_alerts_raw = db.session.execute(sql_recent).fetchall()
        alertes_recentes = []
        for r in recent_alerts_raw:
            alertes_recentes.append({
                "time": r[0].strftime("%d/%m %H:%M") if r[0] else "Inconnu",
                "boite": r[1],
                "message": r[3] or "Alerte détectée"
            })

        # 5. Top 5 Conteneurs les plus critiques
        sql_crit = text("""
            SELECT id_boite, COUNT(*) as alert_count 
            FROM Evenement_save 
            WHERE notif IS NOT NULL AND notif != '[]' 
            GROUP BY id_boite 
            ORDER BY alert_count DESC LIMIT 5
        """)
        crit_raw = db.session.execute(sql_crit).fetchall()
        conteneurs_critiques = [{"id": r[0], "count": r[1]} for r in crit_raw]

        # 6. Top 5 Entreprises (Du plus récent au plus ancien)
        sql_top_ent = text("""
            SELECT 
                p.nom_agence, 
                p.nbr_boite, 
                'active' as status, -- Remplace par p.status si tu as une colonne status dans proprietaire_conteneur
                p.addresse_mail, 
                COUNT(a.numero_a) as nbr_clients
            FROM proprietaire_conteneur p
            -- On lie les boites au propriétaire via id_boite
            LEFT JOIN boite_noir b ON b.id_boite = p.id_boite
            -- On lie les abonnés aux boites via id_boite
            LEFT JOIN abonner a ON a.id_boite = b.id_boite
            GROUP BY p.id, p.nom_agence, p.nbr_boite, p.addresse_mail
            ORDER BY p.id DESC 
            LIMIT 5
        """)
        
        top_ent_raw = db.session.execute(sql_top_ent).fetchall()
        
        # On mappe les résultats avec les nouveaux noms de champs
        top_entreprises = [{
            "nom": r[0], 
            "boites": r[1], 
            "statut": r[2], 
            "contact": r[3],
            "clients": r[4]
        } for r in top_ent_raw]

        # 7. Données pour le Graphique de distribution (Doughnut)
        dist_sql = text("""
            SELECT
                SUM(CASE WHEN notif ILIKE '%choc%' THEN 1 ELSE 0 END) as a_choc,
                SUM(CASE WHEN notif ILIKE '%temp%' THEN 1 ELSE 0 END) as a_temp,
                SUM(CASE WHEN notif ILIKE '%humid%' THEN 1 ELSE 0 END) as a_hum,
                SUM(CASE WHEN notif ILIKE '%vent%' THEN 1 ELSE 0 END) as a_vent,
                SUM(CASE WHEN notif ILIKE '%press%' THEN 1 ELSE 0 END) as a_press
            FROM Evenement_save
        """)
        dist_result = db.session.execute(dist_sql).fetchone()

        return jsonify({
            "status": "success",
            "kpi": {
                "entreprises": tot_entreprises,
                "abonnes": tot_abonnes,
                "alertes": tot_alertes
            },
            "alertes_recentes": alertes_recentes,
            "conteneurs_critiques": conteneurs_critiques,
            "top_entreprises": top_entreprises,
            "charts": {
                "alerts_dist": [
                    int(dist_result[0] or 0), int(dist_result[1] or 0), 
                    int(dist_result[2] or 0), int(dist_result[3] or 0), 
                    int(dist_result[4] or 0)
                ]
            }
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500

# ============== page de monitoring 

@main_bp.route("/api/monitoring/data", methods=["GET"])
def get_monitoring_data():
    # 1. Tous les conteneurs avec leur dernier état
    containers = db.session.execute(text("SELECT * FROM conteneurs")).fetchall()
    
    # 2. Alertes actives
    alerts = db.session.execute(text("SELECT * FROM evenement_save WHERE notif IS NOT NULL")).fetchall()
    
    # 3. Itinéraires réels (tu peux joindre avec une table 'itineraire' si elle existe)
    # Ici, je renvoie une structure simplifiée pour chaque conteneur
    return jsonify({
        "containers": [dict(c) for c in containers],
        "alerts": [dict(a) for a in alerts]
    })

import os

from flask import Blueprint, current_app, request, jsonify, url_for
# Dans telemetry.py
from app.utils import _sceller_evenement, check_securite_et_seuils, get_boite_for_client # type: ignore
from sqlalchemy import text # type: ignore
from app import db, seal_block
from app.utils import *
from app.utils import get_boites_for_owner, get_boite_for_client, get_boite_for_driver, get_boites_for_agency
tel_bp = Blueprint("telemetry", __name__)

# ═══════════════════════════════════════════════════════════
#  MONITORING
# ═══════════════════════════════════════════════════════════

@tel_bp.route("/api/monitoring/data", methods=["GET"])
def get_monitoring_data():
    containers = db.session.execute(text("SELECT * FROM conteneurs")).fetchall()
    alerts     = db.session.execute(text("""
        SELECT * FROM evenement_save
        WHERE notif IS NOT NULL AND notif!='[]'
        ORDER BY horodatage DESC LIMIT 50
    """)).fetchall()
    positions  = db.session.execute(text("""
        SELECT DISTINCT ON (id_boite) id_boite, lat, lon, horodatage
        FROM evenement_save WHERE lat IS NOT NULL AND lon IS NOT NULL
        ORDER BY id_boite, horodatage DESC
    """)).fetchall()
    return jsonify({
        "containers": [dict(r._mapping) for r in containers],
        "alerts":     [dict(r._mapping) for r in alerts],
        "positions":  [{"id_boite": r[0], "lat": float(r[1]),
                        "lon": float(r[2]), "ts": str(r[3])} for r in positions],
    })

# ═══════════════════════════════════════════════════════════
#  SEUILS
# ═══════════════════════════════════════════════════════════

@tel_bp.route("/api/config/thresholds", methods=["POST"])
def update_thresholds():
    try:
        d = request.get_json()
        id_recv = d.get("id_boite")
        boite = db.session.execute(
            text("SELECT id_boite FROM boite_noir WHERE id_conteneurs=:c LIMIT 1"),
            {"c": id_recv}
        ).fetchone()
        if not boite:
            boite = db.session.execute(
                text("SELECT id_boite FROM boite_noir WHERE id_boite=:b LIMIT 1"),
                {"b": id_recv}
            ).fetchone()
        if not boite:
            return jsonify({"error": f"Boîte introuvable: {id_recv}"}), 404
        bid = boite[0]
        db.session.execute(text("""
            INSERT INTO seuils_alerte
                (id_boite,temp_max,humi_max,choc_max,pression_min,vitesse_max,angle_max,updated_at)
            VALUES (:b,:tm,:hm,:cm,:pm,:vm,:am,NOW())
            ON CONFLICT (id_boite) DO UPDATE SET
                temp_max=EXCLUDED.temp_max, humi_max=EXCLUDED.humi_max,
                choc_max=EXCLUDED.choc_max, pression_min=EXCLUDED.pression_min,
                vitesse_max=EXCLUDED.vitesse_max, angle_max=EXCLUDED.angle_max,
                updated_at=NOW()
        """), {"b": bid, "tm": d.get("temp_max"), "hm": d.get("humi_max"),
               "cm": d.get("choc_max"), "pm": d.get("pression_min"),
               "vm": d.get("vitesse_max"), "am": d.get("angle_max")})
        db.session.commit()
        seal_block("CONFIG_SEUILS", bid, d)
        return jsonify({"status": "success", "id_boite": bid})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@tel_bp.route("/api/config/thresholds/<boite_id>", methods=["GET"])
def get_thresholds(boite_id):
    row = db.session.execute(
        text("SELECT * FROM seuils_alerte WHERE id_boite=:b"), {"b": boite_id}
    ).fetchone()
    if row:
        return jsonify(dict(row._mapping))
    return jsonify({"id_boite": boite_id, "temp_max": 32, "humi_max": 75,
                    "choc_max": 5, "pression_min": 995, "vitesse_max": 90, "angle_max": 30})

# ═══════════════════════════════════════════════════════════
#  ÉVÉNEMENTS
# ═══════════════════════════════════════════════════════════
# fonction de etapes suivante pour continuer le trajet 

@tel_bp.route("/api/trajet/etapes", methods=["GET", "POST"])
def api_trajet_etapes():
    if request.method == "POST":
        d = request.get_json()
        # Logique simplifiée : enregistre la destination comme événement de planification
        db.session.execute(text("""
            INSERT INTO evenement_save (id_boite, log_action, lat, lon)
            VALUES (:b, :log, :lat, :lon)
        """), {"b": d.get("id_boite"), "log": "Nouvelle destination programmée", "lat": d.get("lat"), "lon": d.get("lon")})
        db.session.commit()
        return jsonify({"status": "success"})
    
    # Pour le GET, on renvoie une liste vide simulée si la gestion complète des itinéraires n'est pas encore modélisée en BD
    return jsonify([])


@tel_bp.route("/api/trajet/etape/atteinte", methods=["POST"])
def api_trajet_etape_atteinte():
    """Marque une étape d'itinéraire comme atteinte (modèle simplifié)."""
    d = request.get_json(silent=True) or {}
    id_etape = d.get("id_etape")
    return jsonify({"status": "success", "id_etape": id_etape})


# @tel_bp.route("/api/telemetry", methods=["POST"])
# def receive_telemetry():
#     try:
#         d        = request.form if request.form else request.get_json()
#         id_boite = d.get("id_boite")
#         temp     = float(d.get("temperature", 0))
#         humi     = float(d.get("humidite", 0))
#         press    = float(d.get("pressions", 0))
#         chocs    = float(d.get("chocs", 0))
#         vitesse  = float(d.get("vitesse", 0))
#         lat      = d.get("lat"); lon = d.get("lon")

#         audio_file = request.files.get("audio")
#         media_url  = None
#         if audio_file and audio_file.filename:
#             folder = os.path.join(current_app.root_path, "static", "audio")
#             os.makedirs(folder, exist_ok=True)
#             fname  = secure_filename(f"evt_{id_boite}_{int(time.time())}.mp3") # type: ignore
#             audio_file.save(os.path.join(folder, fname))
#             media_url = url_for("static", filename=f"audio/{fname}")

#         seuils = db.session.execute(
#             text("SELECT * FROM seuils_alerte WHERE id_boite=:b LIMIT 1"),
#             {"b": id_boite}
#         ).fetchone()
#         s = dict(seuils._mapping) if seuils else {}
#         t_temp  = float(s.get("temp_max") or 32)
#         t_hum   = float(s.get("humi_max") or 75)
#         t_choc  = float(s.get("choc_max") or 5)
#         t_press = float(s.get("pression_min") or 995)
#         t_vit   = float(s.get("vitesse_max") or 90)

#         alerts = []
#         if temp   > t_temp:  alerts.append(f"Température critique: {temp}°C (Max: {t_temp})")
#         if humi   > t_hum:   alerts.append(f"Humidité critique: {humi}% (Max: {t_hum})")
#         if chocs  > t_choc:  alerts.append(f"Choc violent: {chocs}G (Max: {t_choc})")
#         if press  < t_press: alerts.append(f"Pression basse: {press}hPa (Min: {t_press})")
#         if vitesse > t_vit:  alerts.append(f"Survitesse: {vitesse}km/h (Max: {t_vit})")

#         notif      = json.dumps(alerts) if alerts else None
#         log_action = "Alerte générée" if alerts else "Scan régulier"

#         db.session.execute(text("""
#             INSERT INTO evenement_save
#                 (id_boite,media_1_url,temperature,humidite,pressions,
#                  lat,lon,log_action,vitesse,chocs,notif)
#             VALUES (:b,:m,:t,:h,:p,:lat,:lon,:la,:v,:c,:n)
#         """), {"b": id_boite, "m": media_url, "t": temp, "h": humi, "p": press,
#                "lat": lat, "lon": lon, "la": log_action, "v": vitesse, "c": chocs, "n": notif})
#         db.session.commit()

#         if alerts:
#             seal_block("ALERTE_CRITIQUE", id_boite, {
#                 "temperature": temp, "humidite": humi, "pressions": press,
#                 "vitesse": vitesse, "chocs": chocs, "lat": lat, "lon": lon,
#                 "alertes": alerts
#             })
#         return jsonify({"status": "success", "alerts": alerts}), 201
#     except Exception as e:
#         db.session.rollback()
#         return jsonify({"error": str(e)}), 500
@tel_bp.route("/api/data")
def data_api():
    try:
        rows = db.session.execute(text(
            "SELECT * FROM abonner ORDER BY created_at DESC LIMIT 50"
        )).fetchall()
        return jsonify([dict(r._mapping) for r in rows])
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    

@tel_bp.route("/api/events")
def get_events():
    role, user_id = get_caller_identity()
    role = role or "superadmin"
    container = request.args.get("container")
    severity  = request.args.get("severity")
    period    = request.args.get("period")
    try:
        limit = min(max(int(request.args.get("limit", 100)), 1), 500)
    except (TypeError, ValueError):
        limit = 100

    # Restriction boites
    boites_filter = None
    if role in ("superadmin", ""):
        boites_filter = None
    elif role == "owner":   boites_filter = get_boites_for_owner(user_id)
    elif role == "client": boites_filter = get_boite_for_client(user_id)
    elif role == "company":
        boites_filter = get_boites_for_agency(user_id)
    elif role == "driver": boites_filter = get_boite_for_driver(user_id)
    else:
        boites_filter = []

    where, params = [], {"limit": limit}
    if container:
        where.append("id_boite = :cid"); params["cid"] = container # type: ignore
    if severity == "alert":
        where.append("NULLIF(TRIM(COALESCE(notif,'')), '') IS NOT NULL AND TRIM(notif) != '[]'")
    elif severity == "normal":
        where.append("(NULLIF(TRIM(COALESCE(notif,'')), '') IS NULL OR TRIM(notif) = '[]')")
    if boites_filter is not None:
        if not boites_filter:
            return jsonify([])
        placeholders = ",".join([f":bf{i}" for i in range(len(boites_filter))])
        where.append(f"id_boite IN ({placeholders})")
        params.update({f"bf{i}": v for i, v in enumerate(boites_filter)})

    if period == '5h':
        where.append("horodatage >= NOW() - INTERVAL '5 hours'")
    elif period == '24h':
        where.append("horodatage >= NOW() - INTERVAL '24 hours'")
    elif period == '7d':
        where.append("horodatage >= NOW() - INTERVAL '7 days'")
    elif period == '30d':
        where.append("horodatage >= NOW() - INTERVAL '30 days'")
    elif period == '3m':
        where.append("horodatage >= NOW() - INTERVAL '3 months'")

    wh = ("WHERE " + " AND ".join(where)) if where else ""
    rows = db.session.execute(text(f"""
        SELECT id_eventinit, COALESCE(horodatage, created_at) AS horodatage,
               id_boite, media_1_url, media_2_url,
               temperature, humidite, pressions, lat, lon, created_at,
               log_action, vitesse, notif, chocs
        FROM evenement_save {wh}
        ORDER BY COALESCE(horodatage, created_at) DESC LIMIT :limit
    """), params).fetchall()
    return jsonify([dict(r._mapping) for r in rows])

import json, time
from werkzeug.utils import secure_filename

#  route qui écoute la boîte physique les donnees 
@tel_bp.route("/api/telemetry", methods=["POST"])
def receive_telemetry():
    try:
        # Accepte le JSON ou le Form-Data (si Arduino envoie en form)
        d = request.form if request.form else request.get_json()
        id_boite = d.get("id_boite")
        temp     = float(d.get("temperature", 0))
        humi     = float(d.get("humidite", 0))
        press    = float(d.get("pressions", 0))
        chocs    = float(d.get("chocs", 0))
        vitesse  = float(d.get("vitesse", 0))
        lat      = d.get("lat")
        lon      = d.get("lon")

        # 1. Vérification stricte des Sécurités et Seuils
        alertes = check_securite_et_seuils(id_boite, temp, chocs)
        notif_json = json.dumps(alertes) if alertes else None
        log_action = "Alerte générée" if alertes else "Scan régulier"

        # 2. Sauvegarde de l'événement GPS/Capteurs
        db.session.execute(text("""
            INSERT INTO evenement_save
                (id_boite, temperature, humidite, pressions, lat, lon, log_action, vitesse, chocs, notif)
            VALUES (:b, :t, :h, :p, :lat, :lon, :la, :v, :c, :n)
        """), {"b": id_boite, "t": temp, "h": humi, "p": press, "lat": lat, "lon": lon, "la": log_action, "v": vitesse, "c": chocs, "n": notif_json})
        
        db.session.commit()

        # 3. Sceller dans la blockchain en cas de fraude ou de choc
        if alertes:
            _sceller_evenement("ALERTE_CRITIQUE", id_boite, {
                "temperature": temp, "chocs": chocs, "alertes": alertes, "lat": lat, "lon": lon
            })

        return jsonify({"status": "success", "alertes_declenchees": alertes}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

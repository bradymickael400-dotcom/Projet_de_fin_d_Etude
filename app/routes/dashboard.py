
import json
import os
from flask import Blueprint, render_template, request, jsonify, current_app
from sqlalchemy import text
from app import db
from app.utils import *
from app.utils import get_boite_for_client
from google.api_core.client_options import ClientOptions
from google.ai.generativelanguage import GenerativeServiceClient, GenerateContentRequest, Content, Part

dash_bp = Blueprint("dashboard", __name__)

MONTH_NAMES = {
    '01': 'Jan', '02': 'Fév', '03': 'Mar', '04': 'Avr',
    '05': 'Mai', '06': 'Juin', '07': 'Juil', '08': 'Août',
    '09': 'Sep', '10': 'Oct', '11': 'Nov', '12': 'Déc'
}


def _visible_boites_for(role, user_id):
    """None = accès global superadmin, [] = aucun accès, liste = boîtes autorisées."""
    if role in (None, "", "superadmin"):
        return None
    if not user_id:
        return []
    if role == "owner":
        return get_boites_for_owner(user_id)
    if role == "company":
        return get_boites_for_agency(user_id)
    if role == "client":
        return get_boite_for_client(user_id)
    if role == "driver":
        return get_boite_for_driver(user_id)
    return []


def _append_boites_filter(parts, params, boites, column="id_boite", prefix="bf"):
    if boites is None:
        return True
    if not boites:
        return False
    placeholders = ",".join([f":{prefix}{i}" for i in range(len(boites))])
    parts.append(f"{column} IN ({placeholders})")
    params.update({f"{prefix}{i}": v for i, v in enumerate(boites)})
    return True


def _monthly_subscriptions_chart(boites=None):
    parts = ["LOWER(COALESCE(status,'')) = 'actif'"]
    params = {}
    if not _append_boites_filter(parts, params, boites, "id_boite", "ab"):
        return {"labels": [], "data": []}

    rows = db.session.execute(text(f"""
        WITH monthly AS (
            SELECT TO_CHAR(DATE_TRUNC('month', created_at), 'YYYY-MM') AS mois_annee,
                   COUNT(*) AS total
            FROM abonner
            WHERE {" AND ".join(parts)}
            GROUP BY DATE_TRUNC('month', created_at)
        )
        SELECT mois_annee, total
        FROM monthly
        ORDER BY mois_annee
    """), params).fetchall()

    return {
        "labels": [f"{MONTH_NAMES.get(r[0].split('-')[1], r[0].split('-')[1])} {r[0].split('-')[0]}" for r in rows],
        "data": [int(r[1] or 0) for r in rows],
    }


def _active_subscriptions_count(boites=None):
    parts = ["LOWER(COALESCE(status,'')) = 'actif'"]
    params = {}
    if not _append_boites_filter(parts, params, boites, "id_boite", "asb"):
        return 0
    return db.session.execute(text(f"""
        SELECT COUNT(*) FROM abonner
        WHERE {" AND ".join(parts)}
    """), params).scalar() or 0



# ═══════════════════════════════════════════════════════════
#  HOME
# ═══════════════════════════════════════════════════════════

@dash_bp.route("/")
def home():
    try:
        init_blockchain()
    except Exception:
        pass
    return render_template("index.html")
# ═══════════════════════════════════════════════════════════
#  STATISTIQUES — avec restriction rôle
# ═══════════════════════════════════════════════════════════

@dash_bp.route("/api/stats", methods=["GET"])
def get_dashboard_stats():
    try:
        period  = request.args.get("period", "7d")
        boite   = request.args.get("boite")
        role, user_id = get_caller_identity()

        # Restriction boites
        if role in ["driver", "client"]:
            return jsonify({"status": "error", "message": "Accès refusé"}), 403
        
        boites_filter = _visible_boites_for(role, user_id)

        interval = "day"
        t_filter = ""
        if period == "24h":  t_filter = "horodatage >= NOW() - INTERVAL '24 hours'"; interval = "hour"
        elif period == "7d": t_filter = "horodatage >= NOW() - INTERVAL '7 days'"
        elif period == "30d": t_filter = "horodatage >= NOW() - INTERVAL '30 days'"
        elif period == "3m":  t_filter = "horodatage >= NOW() - INTERVAL '3 months'"
        else: interval = "month"

        parts, params = [], {}
        if t_filter: parts.append(t_filter)
        if boite:    parts.append("id_boite=:boite"); params["boite"] = boite
        if not _append_boites_filter(parts, params, boites_filter, "id_boite", "bff"):
            return jsonify({"status": "success",
                "kpi": {"avg_temp":0,"avg_hum":0,"avg_press":0,"avg_speed":0,
                        "total_events":0,"total_shocks":0,"total_alertes":0,"fiabilite":100,
                        "total_abonnes": 0},
                "charts": {"labels":[],"temp":[],"hum":[],"press":[],"speed":[],"shocks":[],
                           "alerts_dist":[0,0,0,0,0], "abonnements": {"labels": [], "data": []}}
            })

        wh = ("WHERE " + " AND ".join(parts)) if parts else ""

        kpi = db.session.execute(text(f"""
            SELECT COALESCE(AVG(temperature),0), COALESCE(AVG(humidite),0),
                   COALESCE(AVG(pressions),0),  COALESCE(AVG(vitesse),0),
                   COUNT(*),
                   SUM(CASE WHEN chocs > 0 THEN 1 ELSE 0 END),
                   SUM(CASE WHEN NULLIF(TRIM(COALESCE(notif,'')), '') IS NOT NULL
                             AND TRIM(notif) != '[]' THEN 1 ELSE 0 END)
            FROM evenement_save {wh}
        """), params).fetchone()

        fiabilite = 100.0
        if kpi[4] > 0: # type: ignore
            fiabilite = round(100 - ((kpi[6] or 0) / kpi[4] * 100), 1) # type: ignore

        ts = db.session.execute(text(f"""
            SELECT TO_CHAR(DATE_TRUNC('{interval}',horodatage),'DD/MM HH24:MI'),
                   COALESCE(AVG(temperature),0), COALESCE(AVG(humidite),0),
                   COALESCE(AVG(pressions),0),   COALESCE(AVG(vitesse),0),
                   COALESCE(SUM(chocs),0)
            FROM evenement_save {wh}
            GROUP BY DATE_TRUNC('{interval}',horodatage)
            ORDER BY DATE_TRUNC('{interval}',horodatage)
        """), params).fetchall()

        dist = db.session.execute(text(f"""
            SELECT SUM(CASE WHEN COALESCE(notif,'') ILIKE '%choc%'    THEN 1 ELSE 0 END),
                   SUM(CASE WHEN COALESCE(notif,'') ILIKE '%temp%'    THEN 1 ELSE 0 END),
                   SUM(CASE WHEN COALESCE(notif,'') ILIKE '%humid%'   THEN 1 ELSE 0 END),
                   SUM(CASE WHEN COALESCE(notif,'') ILIKE '%vitesse%' THEN 1 ELSE 0 END),
                   SUM(CASE WHEN COALESCE(notif,'') ILIKE '%press%'   THEN 1 ELSE 0 END)
            FROM evenement_save {wh}
        """), params).fetchone()

        return jsonify({
            "status": "success",
            "kpi": {
                "avg_temp":      round(float(kpi[0]), 1), # type: ignore
                "avg_hum":       round(float(kpi[1]), 1), # type: ignore
                "avg_press":     round(float(kpi[2]), 1), # type: ignore
                "avg_speed":     round(float(kpi[3]), 1), # type: ignore
                "total_events":  int(kpi[4]), # type: ignore
                "total_shocks":  int(kpi[5] or 0), # type: ignore
                "total_alertes": int(kpi[6] or 0), # type: ignore
                "fiabilite":     fiabilite,
                "total_abonnes": _active_subscriptions_count(boites_filter),
            },
            "charts": {
                "labels":      [r[0] for r in ts],
                "temp":        [round(float(r[1]), 1) for r in ts],
                "hum":         [round(float(r[2]), 1) for r in ts],
                "press":       [round(float(r[3]), 1) for r in ts],
                "speed":       [round(float(r[4]), 1) for r in ts],
                "shocks":      [round(float(r[5]), 1) for r in ts],
                "alerts_dist": [int(dist[i] or 0) for i in range(5)], # type: ignore
                "abonnements":  _monthly_subscriptions_chart(boites_filter),
            }
        }), 200
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# ═══════════════════════════════════════════════════════════
#  DASHBOARDS
# ═══════════════════════════════════════════════════════════
@dash_bp.route("/api/dashboard/superadmin", methods=["GET"])
def get_sa_dashboard():
    try:
        tot_ent    = db.session.execute(text("SELECT COUNT(*) FROM proprietaire_conteneur")).scalar() or 0
        tot_abs    = _active_subscriptions_count()
        tot_alerts = db.session.execute(text(
            "SELECT COUNT(*) FROM evenement_save WHERE NULLIF(TRIM(COALESCE(notif,'')), '') IS NOT NULL AND TRIM(notif) != '[]'"
        )).scalar() or 0
        tot_clients= db.session.execute(text("SELECT COUNT(*) FROM client")).scalar() or 0
        tot_boites = db.session.execute(text("SELECT COUNT(*) FROM boite_noir")).scalar() or 0

        recent = db.session.execute(text("""
            SELECT horodatage, id_boite, notif, log_action, temperature, chocs
            FROM evenement_save
            WHERE NULLIF(TRIM(COALESCE(notif,'')), '') IS NOT NULL AND TRIM(notif) != '[]'
            ORDER BY horodatage DESC LIMIT 10
        """)).fetchall()
        alertes_recentes = []
        for r in recent:
            try: msgs = json.loads(r[2]) if r[2] else []
            except: msgs = []
            alertes_recentes.append({
                "time": r[0].strftime("%d/%m %H:%M") if r[0] else "?",
                "boite": r[1], "message": r[3] or "Alerte",
                "details": msgs[:2],
                "temp": float(r[4]) if r[4] else None,
                "chocs": float(r[5]) if r[5] else None,
            })

        crit = db.session.execute(text("""
            SELECT id_boite, COUNT(*) c FROM evenement_save
            WHERE NULLIF(TRIM(COALESCE(notif,'')), '') IS NOT NULL AND TRIM(notif) != '[]'
            GROUP BY id_boite ORDER BY c DESC LIMIT 5
        """)).fetchall()

        top_ent = db.session.execute(text("""
            SELECT p.nom_agence, p.nbr_boite, p.addresse_mail,
                   p.lieu_residence, p.lat, p.lon,
                   COUNT(DISTINCT a.numero_a) AS nbcl
            FROM proprietaire_conteneur p
            LEFT JOIN boite_noir b ON b.id_proprietaire = p.id
            LEFT JOIN abonner a ON a.id_boite = b.id_boite AND LOWER(COALESCE(a.status,'')) = 'actif'
            GROUP BY p.id,p.nom_agence,p.nbr_boite,p.addresse_mail,
                     p.lieu_residence,p.lat,p.lon
            ORDER BY p.id DESC LIMIT 5
        """)).fetchall()

        dist = db.session.execute(text("""
            SELECT SUM(CASE WHEN COALESCE(notif,'') ILIKE '%choc%'    THEN 1 ELSE 0 END),
                   SUM(CASE WHEN COALESCE(notif,'') ILIKE '%temp%'    THEN 1 ELSE 0 END),
                   SUM(CASE WHEN COALESCE(notif,'') ILIKE '%humid%'   THEN 1 ELSE 0 END),
                   SUM(CASE WHEN COALESCE(notif,'') ILIKE '%vitesse%' THEN 1 ELSE 0 END),
                   SUM(CASE WHEN COALESCE(notif,'') ILIKE '%press%'   THEN 1 ELSE 0 END)
            FROM evenement_save
        """)).fetchone()

        abonnements_chart = _monthly_subscriptions_chart()

        # Modifiez la clé "charts" dans votre return jsonify final :
        return jsonify({
            "status": "success",
            "kpi": {"entreprises": tot_ent, "abonnes": tot_abs, "alertes": tot_alerts,
                    "clients": tot_clients, "boites": tot_boites},
            "alertes_recentes": alertes_recentes,
            "conteneurs_critiques": [{"id": r[0], "count": r[1]} for r in crit],
            "top_entreprises": [{
                "nom": r[0], "boites": r[1], "contact": r[2],
                "location": r[3], "lat": float(r[4]) if r[4] else None,
                "lon": float(r[5]) if r[5] else None, "clients": r[6], "statut": "active"
            } for r in top_ent],
            "charts": {
                "alerts_dist": [int(dist[i] or 0) for i in range(5)], # type: ignore
                "abonnements": abonnements_chart
            },
        })
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500

@dash_bp.route("/api/dashboard/owner", methods=["GET"])
def get_owner_dashboard():
    try:
        owner_id = request.args.get("owner_id")
        boites_ids = get_boites_for_owner(owner_id)

        boites = db.session.execute(text("""
            SELECT b.id_boite, b.type_boite, c.id_conteneurs, c.type_conteneurs, c.status
            FROM proprietaire_conteneur p
            JOIN boite_noir b ON b.id_proprietaire = p.id
            JOIN conteneurs c ON c.id_conteneurs = b.id_conteneurs
            WHERE p.id = :oid
        """), {"oid": owner_id}).fetchall()

        boites_data = []
        for b in boites:
            last = db.session.execute(text("""
                SELECT temperature,humidite,pressions,lat,lon,vitesse,chocs,notif
                FROM evenement_save WHERE id_boite=:bid ORDER BY horodatage DESC LIMIT 1
            """), {"bid": b[0]}).fetchone()
            alerts = []
            if last and last[7]:
                try: alerts = json.loads(last[7])
                except: pass
            status = b[4] or "off"
            if last:
                status = "danger" if len(alerts) >= 2 else ("warning" if alerts else "ok")
            boites_data.append({
                "id_boite": b[0], "type_boite": b[1], "id_conteneur": b[2],
                "type_conteneur": b[3], "status": status,
                "temp": float(last[0]) if last and last[0] else None,
                "humidity": float(last[1]) if last and last[1] else None,
                "lat": float(last[3]) if last and last[3] else None,
                "lon": float(last[4]) if last and last[4] else None,
                "speed": float(last[5]) if last and last[5] else 0,
                "shock": float(last[6]) if last and last[6] else 0,
                "alerts": alerts,
            })

        kpi_row = db.session.execute(text("""
            SELECT COALESCE(AVG(temperature),0), COUNT(*),
                SUM(CASE WHEN NULLIF(TRIM(COALESCE(notif,'')), '') IS NOT NULL
                          AND TRIM(notif) != '[]' THEN 1 ELSE 0 END)
            FROM evenement_save e
            JOIN boite_noir b ON b.id_boite = e.id_boite
            JOIN proprietaire_conteneur p ON p.id = b.id_proprietaire -- CORRECTION ICI
            WHERE p.id = :oid
        """), {"oid": owner_id}).fetchone()

        return jsonify({
            "status": "success",
            "boites": boites_data,
            "kpi": {
                "avg_temp": round(float(kpi_row[0]), 1) if kpi_row else 0,
                "total_events": int(kpi_row[1]) if kpi_row else 0,
                "total_alertes": int(kpi_row[2] or 0) if kpi_row else 0,
            }
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    
@dash_bp.route('/api/ai/chat', methods=['POST'])
def ai_chat():
    try:
        data = request.get_json() or {}
        message = (data.get('message') or '').strip()
        system_prompt = data.get('systemPrompt') or 'You are a helpful assistant.'
        context_data = data.get('contextData') or ''

        if not message:
            return jsonify({"error": "Le message est requis."}), 400

        # Récupérer la clé API depuis la config Flask ou l'environnement
        api_key = current_app.config.get('API_KEY') or os.environ.get('API_KEY')
        if not api_key:
            return jsonify({"error": "Assistant IA non configuré côté serveur. Veuillez définir API_KEY dans .env"}), 500

        client = GenerativeServiceClient(client_options=ClientOptions(api_key=api_key))
        final_prompt = f"DONNÉES ACTUELLES DES CONTENEURS :\n{context_data}\n\nDEMANDE DE L'UTILISATEUR :\n{message}"

        gemini_model = current_app.config.get('GEMINI_MODEL') or os.environ.get('GEMINI_MODEL') or 'models/gemini-2.5-flash'
        request_payload = GenerateContentRequest(
            model=gemini_model,
            system_instruction=Content(
                role='system',
                parts=[Part(text=system_prompt)]
            ),
            contents=[
                Content(
                    role='user',
                    parts=[Part(text=final_prompt)]
                )
            ]
        )

        response = client.generate_content(request=request_payload, timeout=30)
        reply = ''
        if response.candidates:
            candidate = response.candidates[0]
            if candidate.content and candidate.content.parts:
                reply = ''.join([part.text or '' for part in candidate.content.parts])

        return jsonify({"reply": reply})

    except Exception as e:
        current_app.logger.exception("Erreur Gemini")
        return jsonify({"error": f"Erreur de communication avec l'IA: {e}"}), 500

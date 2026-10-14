"""Endpoints de publication et d’envoi de messages multi-canaux."""

import threading
from flask import Blueprint, request, jsonify
from sqlalchemy import text # type: ignore
from app import db
from app.utils import *
from app.security import current_identity

pub_bp = Blueprint("publication", __name__)

@pub_bp.route("/api/publications", methods=["GET", "POST"])
def api_publications():
    if request.method == "POST":
        if current_identity().get("role") != "superadmin":
            return jsonify({"error": "Publication reservee au superadmin"}), 403
        try:
            d = request.get_json()
            titre = d.get("titre")
            niveau = d.get("niveau")
            contenu = d.get("contenu")
            cible = d.get("cible") # "Tous les utilisateurs", "Propriétaires BB seulement", "Chauffeurs seulement"

            # 1. Sauvegarder en Base de Données
            db.session.execute(text("""
                INSERT INTO publications (titre, niveau, contenu, cible)
                VALUES (:t, :n, :c, :cb)
            """), {"t": titre, "n": niveau, "c": contenu, "cb": cible})
            db.session.commit()

           # 2. Récupérer les contacts depuis la Base de données
            emails = []
            numeros = []

            if cible in ["Tous les utilisateurs", "Propriétaires BB seulement"]:
                proprios = db.session.execute(text("SELECT addresse_mail FROM proprietaire_conteneur WHERE addresse_mail IS NOT NULL")).fetchall()
                clients = db.session.execute(text("SELECT address_mail FROM client WHERE address_mail IS NOT NULL")).fetchall()
                emails.extend([p[0] for p in proprios])
                emails.extend([c[0] for c in clients])
            
            if cible in ["Tous les utilisateurs", "Chauffeurs seulement"]:
                # Adapter selon la table transporteur
                chauffeurs = db.session.execute(text("SELECT login FROM transporteur")).fetchall()
                # emails.extend([ch[0] for ch in chauffeurs]) # Dé-commenter si transporteur a des emails

            # Dédoublonner
            emails = list(set(emails))

            # 3. Lancer les envois multicanaux en arrière-plan
            if emails:
                normalized_level = str(niveau or "").strip().lower()
                severity = (
                    "critical" if normalized_level in {"critique", "critical", "danger", "urgent"}
                    else "warning" if normalized_level in {"attention", "warning", "avertissement"}
                    else "info"
                )
                threading.Thread(
                    target=send_email_background,
                    args=(emails, titre, contenu),
                    kwargs={
                        "severity": severity,
                        "action_url": get_public_base_url(),
                        "action_label": "Ouvrir ARGOS",
                    },
                    daemon=True,
                ).start()
            
            return jsonify({"status": "success", "cibles_atteintes": len(emails)}), 201
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 500

    else: # GET: Récupérer les publications pour le frontend
        try:
            rows = db.session.execute(text("SELECT * FROM publications ORDER BY date_pub DESC LIMIT 20")).fetchall()
            return jsonify([dict(r._mapping) for r in rows])
        except Exception as e:
            return jsonify({"error": str(e)}), 500

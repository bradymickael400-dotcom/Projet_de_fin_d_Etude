"""Endpoints JSON utilisés par la carte Leaflet et les widgets dynamiques du front."""
import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from flask import jsonify, request
from flask_login import login_required, current_user

from app.api import api_bp
from app.services.geo import schools_near
from app.services.ranking import national_ranking


@api_bp.route("/schools/nearby")
@login_required
def schools_nearby():
    if current_user.lat is None or current_user.lng is None:
        return jsonify({"error": "Position du compte non renseignée."}), 400
    try:
        radius = float(request.args.get("radius", 8))
    except (TypeError, ValueError):
        return jsonify({"error": "Le rayon doit être un nombre."}), 400
    if not 0 < radius <= 100:
        return jsonify({"error": "Le rayon doit être compris entre 0 et 100 km."}), 400
    niveau = request.args.get("niveau", "all")
    statut = request.args.get("statut", "all")
    results = schools_near(current_user.lat, current_user.lng, radius, niveau, statut)
    return jsonify([
        {
            "id": s.id, "nom": s.nom, "lat": s.lat, "lng": s.lng,
            "type": s.type, "statut": s.statut, "distance_km": round(dist, 1),
            "note_parents": s.note_parents, "taux_reussite": s.taux_reussite,
        }
        for s, dist in results
    ])


@api_bp.route("/ranking")
def ranking():
    return jsonify([
        {"rank": e["rank"], "score": e["score"], "id": e["school"].id, "nom": e["school"].nom,
         "ville": e["school"].ville}
        for e in national_ranking()
    ])


@api_bp.route("/geocode")
def geocode():
    """Recherche limitée au Cameroun, utilisée par la carte d'ajout d'école."""
    query = (request.args.get("q") or "").strip()
    if len(query) < 3 or len(query) > 160:
        return jsonify({"error": "Saisissez au moins trois caractères."}), 400
    params = urlencode({
        "q": f"{query}, Cameroun",
        "format": "jsonv2",
        "countrycodes": "cm",
        "limit": 5,
        "addressdetails": 1,
    })
    req = Request(
        f"https://nominatim.openstreetmap.org/search?{params}",
        headers={"User-Agent": "ArthenaSchoolRegistration/1.0 (education platform)"},
    )
    try:
        with urlopen(req, timeout=8) as response:
            results = json.loads(response.read())
    except Exception:
        return jsonify({"error": "Le service de localisation est temporairement indisponible."}), 503
    return jsonify([{
        "label": item.get("display_name", ""),
        "lat": float(item["lat"]),
        "lng": float(item["lon"]),
    } for item in results])

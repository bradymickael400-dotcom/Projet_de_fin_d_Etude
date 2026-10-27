"""Distance et filtrage géographique (carte de proximité parent)."""
from math import radians, sin, cos, sqrt, atan2
from app.models.school import School


def haversine_km(lat1, lng1, lat2, lng2):
    R = 6371
    d_lat = radians(lat2 - lat1)
    d_lng = radians(lng2 - lng1)
    a = sin(d_lat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(d_lng / 2) ** 2
    return R * 2 * atan2(sqrt(a), sqrt(1 - a))


def schools_near(lat, lng, radius_km=8, niveau=None, statut=None):
    """Écoles validées dans un rayon donné autour d'un point, avec leur distance."""
    schools = School.query.filter_by(validated=True).all()
    result = []
    for s in schools:
        dist = haversine_km(lat, lng, s.lat, s.lng)
        if dist > radius_km:
            continue
        if niveau and niveau != "all" and s.type != niveau:
            continue
        if statut and statut != "all" and s.statut != statut:
            continue
        result.append((s, dist))
    result.sort(key=lambda x: x[1])
    return result

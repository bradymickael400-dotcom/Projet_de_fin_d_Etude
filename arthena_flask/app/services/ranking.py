"""Calcul du classement national des établissements.

Score = 55% taux de réussite + 30% (note parents/5 -> sur 100) + 15% effectif plafonné.
Les pondérations sont configurables dans app/config.py.
"""
from flask import current_app
from app.models.school import School


def school_score(school):
    if not school.validated:
        return 0.0
    cfg = current_app.config
    taux = school.taux_reussite or 0
    note_parents_sur_100 = (school.note_parents or 0) * 20
    plafond = cfg["RANKING_EFFECTIF_PLAFOND"]
    effectif_norm = min((school.effectif or 0) / plafond, 1) * 100
    score = (
        taux * cfg["RANKING_WEIGHT_TAUX_REUSSITE"]
        + note_parents_sur_100 * cfg["RANKING_WEIGHT_NOTE_PARENTS"]
        + effectif_norm * cfg["RANKING_WEIGHT_EFFECTIF"]
    )
    return round(score, 1)


def national_ranking(region=None, ville=None):
    """Retourne la liste des écoles validées, triée par score, avec le rang attribué."""
    query = School.query.filter_by(validated=True)
    if region:
        query = query.filter_by(region=region)
    if ville:
        query = query.filter_by(ville=ville)
    schools = query.all()
    scored = sorted(schools, key=school_score, reverse=True)
    ranked = []
    for i, s in enumerate(scored, start=1):
        ranked.append({"school": s, "score": school_score(s), "rank": i})
    return ranked


def school_rank(school):
    """Rang national d'une école précise (utile pour son propre tableau de bord)."""
    ranking = national_ranking()
    for entry in ranking:
        if entry["school"].id == school.id:
            return entry["rank"], entry["score"]
    return None, 0.0

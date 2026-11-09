"""ARGOS shock triage for standard dry containers.

CSC/ISO structural test loads are not impact-accelerometer damage thresholds.
The configured threshold below is an ARGOS operational fallback only.
"""

import math


ARGOS_DEFAULT_SHOCK_THRESHOLD_G = 5.0


def resolve_shock_threshold(value):
    """Return a usable positive per-box threshold; zero/missing uses ARGOS default."""
    try:
        threshold = float(value)
    except (TypeError, ValueError):
        threshold = ARGOS_DEFAULT_SHOCK_THRESHOLD_G
    if not math.isfinite(threshold) or threshold <= 0:
        threshold = ARGOS_DEFAULT_SHOCK_THRESHOLD_G
    return threshold


def assess_shock_level(peak_g, threshold_g, exceedance_count=0):
    """Classify inspection urgency without claiming structural damage probability."""
    threshold = resolve_shock_threshold(threshold_g)
    try:
        peak = float(peak_g)
    except (TypeError, ValueError):
        peak = None
    if peak is None or not math.isfinite(peak):
        return {
            "level": "unknown", "peak_g": None, "threshold_g": threshold,
            "damage_probability": None,
            "damage_assessment": "not_assessable_without_validated_sensor_data",
        }
    count = max(0, int(exceedance_count or 0))
    if peak <= threshold and count == 0:
        level = "within_operational_threshold"
        action = "Poursuivre la surveillance normale."
    elif peak >= 2 * threshold:
        level = "urgent_inspection_recommended"
        action = "Suspendre les manutentions si nécessaire et faire inspecter le conteneur et l’arrimage rapidement."
    else:
        level = "inspection_recommended"
        action = "Contrôler visuellement le conteneur, la cargaison et l’arrimage au prochain arrêt sûr."
    return {
        "level": level,
        "peak_g": round(peak, 3),
        "threshold_g": round(threshold, 3),
        "threshold_source": "per_box_ARGOS_setting_or_5G_operational_fallback",
        "exceedance_count": count,
        "recommended_action": action,
        "damage_probability": None,
        "damage_assessment": "sensor_signal_is_not_a_structural_damage_diagnosis",
    }


def get_box_shock_threshold(black_box_id):
    """Read the box setting, falling back safely when the row/value is absent."""
    try:
        from sqlalchemy import text
        from app.extensions import db

        value = db.session.execute(text(
            "SELECT choc_max FROM seuils_alerte WHERE id_boite=:box"
        ), {"box": int(black_box_id)}).scalar()
        return resolve_shock_threshold(value)
    except Exception:
        return ARGOS_DEFAULT_SHOCK_THRESHOLD_G

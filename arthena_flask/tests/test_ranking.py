from app.extensions import db
from app.models.school import School
from app.services.ranking import school_score, national_ranking


def test_school_score_zero_if_not_validated(app):
    with app.app_context():
        s = School(nom="X", lat=0, lng=0, validated=False, taux_reussite=90)
        assert school_score(s) == 0.0


def test_national_ranking_order(app):
    with app.app_context():
        a = School(nom="A", lat=0, lng=0, validated=True, taux_reussite=95, note_parents=4.5, effectif=500)
        b = School(nom="B", lat=0, lng=0, validated=True, taux_reussite=60, note_parents=3.0, effectif=100)
        db.session.add_all([a, b])
        db.session.commit()
        ranking = national_ranking()
        assert ranking[0]["school"].nom == "A"

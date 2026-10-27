from app.extensions import db
from app.models.user import User
from app.models.teacher import Teacher


def test_login_success(app, client):
    with app.app_context():
        u = User(email="test@demo.cm", role="parent", nom="N", prenom="P")
        u.set_password("secret123")
        db.session.add(u)
        db.session.commit()

    resp = client.post("/login", data={"email": "test@demo.cm", "password": "secret123"},
                        follow_redirects=True)
    assert resp.status_code == 200


def test_teacher_registration_creates_profile(app, client):
    resp = client.post("/inscription", data={
        "prenom": "Ada", "nom": "Test", "email": "ada@demo.cm",
        "password": "secret123", "role": "enseignant",
    })
    assert resp.status_code == 302
    with app.app_context():
        user = User.query.filter_by(email="ada@demo.cm").one()
        assert Teacher.query.filter_by(user_id=user.id).one()

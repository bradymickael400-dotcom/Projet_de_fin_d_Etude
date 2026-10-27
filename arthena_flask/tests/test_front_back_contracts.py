from app.extensions import db
from app.models.school import School
from app.models.student import Student
from app.models.user import User


def _login(client, email, password="secret123"):
    return client.post("/login", data={"email": email, "password": password})


def test_parent_cannot_access_another_parents_student(app, client):
    with app.app_context():
        school = School(nom="Test", lat=0, lng=0, validated=True)
        owner = User(email="owner@test.cm", role="parent", nom="O", prenom="O")
        visitor = User(email="visitor@test.cm", role="parent", nom="V", prenom="V")
        owner.set_password("secret123")
        visitor.set_password("secret123")
        db.session.add_all([school, owner, visitor])
        db.session.flush()
        student = Student(parent_id=owner.id, ecole_id=school.id, nom="E", prenom="E", classe="6e")
        db.session.add(student)
        db.session.commit()
        student_id = student.id

    _login(client, "visitor@test.cm")
    assert client.get(f"/parent/eleve/{student_id}").status_code == 404


def test_payment_accepts_frontend_json_and_validates_amount(app, client):
    with app.app_context():
        school = School(nom="Test", lat=0, lng=0, validated=True)
        parent = User(email="parent@test.cm", role="parent", nom="P", prenom="P")
        parent.set_password("secret123")
        db.session.add_all([school, parent])
        db.session.flush()
        student = Student(parent_id=parent.id, ecole_id=school.id, nom="E", prenom="E",
                          classe="6e", pension_totale=50000)
        db.session.add(student)
        db.session.commit()
        student_id = student.id

    _login(client, "parent@test.cm")
    ok = client.post(f"/parent/eleve/{student_id}/payer",
                     json={"montant": 10000, "methode": "MTN MoMo"})
    assert ok.status_code == 200
    assert ok.get_json()["reste_a_payer"] == 40000
    invalid = client.post(f"/parent/eleve/{student_id}/payer",
                          json={"montant": 999999, "methode": "MTN MoMo"})
    assert invalid.status_code == 400

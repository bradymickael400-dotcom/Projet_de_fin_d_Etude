from datetime import date
from io import BytesIO

from app.extensions import db
from app.models.academic import Note, Presence
from app.models.school import School
from app.models.student import Student
from app.models.teacher import Schedule, Teacher
from app.models.user import User
from app.models.requests import EnrollmentRequest


def _user(email, role, active=True):
    user = User(
        email=email, role=role, nom="Test", prenom="Compte",
        is_active_account=active,
    )
    user.set_password("secret123")
    db.session.add(user)
    db.session.flush()
    return user


def _login(client, email):
    return client.post("/login", data={"email": email, "password": "secret123"})


def test_public_landing_page(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Arthena" in response.data


def test_public_education_news_page(client):
    response = client.get("/actualites")
    assert response.status_code == 200
    assert b"Actualit" in response.data


def test_inactive_account_cannot_login(app, client):
    with app.app_context():
        _user("inactive@test.cm", "parent", active=False)
        db.session.commit()
    response = _login(client, "inactive@test.cm")
    assert response.status_code == 200
    assert b"incorrect" in response.data


def test_teacher_cannot_grade_unassigned_subject(app, client):
    with app.app_context():
        school = School(nom="École", lat=0, lng=0, validated=True)
        db.session.add(school)
        teacher_user = _user("teacher@test.cm", "enseignant")
        parent = _user("parent2@test.cm", "parent")
        teacher = Teacher(user_id=teacher_user.id)
        db.session.add(teacher)
        db.session.flush()
        teacher.schools.append(school)
        db.session.add(Schedule(
            teacher_id=teacher.id, school_id=school.id, jour="Lun",
            heure="08h-10h", matiere="Maths", classe="CM2",
        ))
        student = Student(
            parent_id=parent.id, ecole_id=school.id, nom="Élève",
            prenom="Ada", classe="CM2",
        )
        db.session.add(student)
        db.session.commit()
        student_id = student.id

    _login(client, "teacher@test.cm")
    response = client.post("/enseignant/notes", json={
        "student_id": student_id, "matiere": "Français",
        "trimestre": "T1", "note": 15,
    })
    assert response.status_code == 403
    with app.app_context():
        assert Note.query.count() == 0


def test_attendance_is_updated_not_duplicated(app, client):
    with app.app_context():
        school = School(nom="École", lat=0, lng=0, validated=True)
        db.session.add(school)
        teacher_user = _user("attendance@test.cm", "enseignant")
        parent = _user("parent3@test.cm", "parent")
        teacher = Teacher(user_id=teacher_user.id)
        db.session.add(teacher)
        db.session.flush()
        teacher.schools.append(school)
        db.session.add(Schedule(
            teacher_id=teacher.id, school_id=school.id, jour="Mar",
            heure="08h-10h", matiere="Maths", classe="CM2",
        ))
        student = Student(
            parent_id=parent.id, ecole_id=school.id, nom="Élève",
            prenom="Grace", classe="CM2",
        )
        db.session.add(student)
        db.session.commit()
        school_id, student_id = school.id, student.id

    _login(client, "attendance@test.cm")
    payload = {"school_id": school_id, "presences": [{"student_id": student_id, "statut": "absent"}]}
    assert client.post("/enseignant/appel", json=payload).status_code == 200
    payload["presences"][0]["statut"] = "present"
    assert client.post("/enseignant/appel", json=payload).status_code == 200

    with app.app_context():
        records = Presence.query.filter_by(student_id=student_id, date=date.today()).all()
        assert len(records) == 1
        assert records[0].statut == "present"


def test_enrolment_requires_and_saves_both_documents(app, client, tmp_path):
    app.config["UPLOAD_FOLDER"] = str(tmp_path)
    with app.app_context():
        school = School(
            nom="École active", lat=3.86, lng=11.51,
            validated=True, status="actif",
        )
        db.session.add(school)
        parent = _user("documents@test.cm", "parent")
        db.session.commit()
        school_id = school.id

    _login(client, "documents@test.cm")
    base = {
        "ecole_id": str(school_id), "prenom": "Amina", "nom": "Test",
        "classe": "6e", "age": "11", "motif_nouvelle_ecole": "Entrée au collège",
        "acte_naissance": (BytesIO(b"birth"), "acte.pdf"),
    }
    assert client.post("/parent/inscription", data=base).status_code == 400

    complete = {
        "ecole_id": str(school_id), "prenom": "Amina", "nom": "Test",
        "classe": "6e", "age": "11", "motif_nouvelle_ecole": "Entrée au collège",
        "acte_naissance": (BytesIO(b"birth"), "acte.pdf"),
        "ancien_bulletin": (BytesIO(b"report"), "bulletin.pdf"),
    }
    response = client.post("/parent/inscription", data=complete)
    assert response.status_code == 200
    with app.app_context():
        request_ = EnrollmentRequest.query.one()
        assert request_.acte_naissance
        assert request_.ancien_bulletin

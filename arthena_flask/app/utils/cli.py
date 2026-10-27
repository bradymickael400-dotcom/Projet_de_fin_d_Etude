"""Commandes CLI personnalisées : `flask seed-db` pour peupler la base de démo."""
import click
from flask import current_app
from app.extensions import db
from app.services.email import send_email


def register_cli(app):
    @app.cli.command("seed-db")
    def seed_db():
        """Crée les tables et insère les comptes de démonstration."""
        from app.models.user import User
        from app.models.school import School, SchoolClass
        from app.models.student import Student
        from app.models.teacher import Teacher, Schedule

        db.create_all()

        school = School.query.filter_by(nom="EPP Bastos").first()
        if not school:
            school = School(nom="EPP Bastos", short="EPP Bastos", type="primaire",
                             statut="public", ville="Yaoundé", region="Centre",
                             lat=3.865, lng=11.513, frais_place=0,
                             effectif=342, taux_reussite=87, note_parents=4.2,
                             validated=True, status="actif")
            db.session.add(school)
            db.session.flush()

        demo_users = [
            dict(email="parent@demo.cm", pwd="demo123", role="parent",
                 nom="Nkemdirim", prenom="Christine", lat=3.86, lng=11.51, ville="Yaoundé"),
            dict(email="admin@demo.cm", pwd="demo123", role="admin",
                 nom="Mbida", prenom="Paul", ecole_id=school.id),
            dict(email="prof@demo.cm", pwd="demo123", role="enseignant",
                 nom="Fouda", prenom="Martin"),
            dict(email="super@demo.cm", pwd="demo123", role="superadmin",
                 nom="Admin", prenom="Arthena"),
        ]
        users = {}
        for source in demo_users:
            data = source.copy()
            pwd = data.pop("pwd")
            u = User.query.filter_by(email=data["email"]).first()
            if not u:
                u = User(**data)
                u.set_password(pwd)
                db.session.add(u)
                db.session.flush()
            users[u.role] = u

        teacher = Teacher.query.filter_by(user_id=users["enseignant"].id).first()
        if not teacher:
            teacher = Teacher(user_id=users["enseignant"].id, matieres="Maths, Sciences")
            db.session.add(teacher)
            db.session.flush()
        if school not in teacher.schools:
            teacher.schools.append(school)

        if not SchoolClass.query.filter_by(school_id=school.id, nom="CM2").first():
            db.session.add(SchoolClass(school_id=school.id, nom="CM2"))
        student = Student.query.filter_by(parent_id=users["parent"].id, prenom="Junior").first()
        if not student:
            student = Student(parent_id=users["parent"].id, ecole_id=school.id, nom="Nkemdirim",
                              prenom="Junior", classe="CM2", photo_initiale="JN",
                              pension_totale=120000, pension_payee=40000)
            db.session.add(student)
        if not Schedule.query.filter_by(teacher_id=teacher.id, school_id=school.id).first():
            db.session.add_all([
                Schedule(teacher_id=teacher.id, school_id=school.id, jour="Lun", heure="08h-10h", matiere="Maths", classe="CM2"),
                Schedule(teacher_id=teacher.id, school_id=school.id, jour="Mer", heure="10h-12h", matiere="Sciences", classe="CM2"),
            ])

        db.session.commit()

        click.echo("Base de données initialisée avec les comptes de démonstration.")

    @app.cli.command("test-email")
    @click.argument("recipient")
    def test_email(recipient):
        """Vérifie la connexion SMTP en envoyant un message de test."""
        if not current_app.config["MAIL_USERNAME"] or not current_app.config["MAIL_PASSWORD"]:
            raise click.ClickException("MAIL_USERNAME et MAIL_PASSWORD sont obligatoires.")
        send_email(
            recipient,
            "Test de messagerie Arthena",
            "La messagerie Arthena est correctement configurée.",
        )
        click.echo(f"Email de test envoyé à {recipient}.")

    @app.cli.command("refresh-news")
    def refresh_news():
        """Collecte et classe les actualités éducatives camerounaises."""
        from app.services.news import refresh_education_news

        added, errors = refresh_education_news()
        click.echo(f"Veille actualisée : {added} nouvel(le)s article(s).")
        if errors:
            click.echo("Sources temporairement indisponibles : " + ", ".join(errors), err=True)

"""Profil enseignant : peut être rattaché à PLUSIEURS écoles (table d'association)."""
from app.extensions import db

teacher_school = db.Table(
    "teacher_school",
    db.Column("teacher_id", db.Integer, db.ForeignKey("teachers.id"), primary_key=True),
    db.Column("school_id", db.Integer, db.ForeignKey("schools.id"), primary_key=True),
)


class Teacher(db.Model):
    __tablename__ = "teachers"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)
    matieres = db.Column(db.String(255))  # liste séparée par des virgules (ou table dédiée si besoin)
    score = db.Column(db.Integer, default=3)  # note admin 1-5, sert au calcul de la prime

    schools = db.relationship("School", secondary=teacher_school, back_populates="teachers")
    horaires = db.relationship("Schedule", backref="teacher", cascade="all, delete-orphan")

    def matieres_list(self):
        return [m.strip() for m in (self.matieres or "").split(",") if m.strip()]

    def prime_mensuelle(self):
        return self.score * 15000

    def __repr__(self):
        return f"<Teacher user_id={self.user_id}>"


class Schedule(db.Model):
    """Créneau d'enseignement d'un professeur dans UNE école donnée."""
    __tablename__ = "schedules"
    __table_args__ = (
        db.UniqueConstraint(
            "teacher_id", "school_id", "jour", "heure", "classe",
            name="uq_teacher_schedule_slot",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey("teachers.id"), nullable=False)
    school_id = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=False)
    jour = db.Column(db.String(10))     # Lun, Mar, Mer, Jeu, Ven
    heure = db.Column(db.String(20))    # "08h-10h"
    matiere = db.Column(db.String(60))
    classe = db.Column(db.String(30))

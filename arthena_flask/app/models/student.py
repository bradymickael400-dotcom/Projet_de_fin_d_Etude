"""Élève, rattaché à un parent et à un établissement."""
from app.extensions import db


class Student(db.Model):
    __tablename__ = "students"
    __table_args__ = (
        db.CheckConstraint("pension_totale >= 0", name="ck_student_pension_total"),
        db.CheckConstraint("pension_payee >= 0", name="ck_student_pension_paid"),
        db.CheckConstraint("pension_payee <= pension_totale", name="ck_student_pension_balance"),
    )

    id = db.Column(db.Integer, primary_key=True)
    parent_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    ecole_id = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=False)
    nom = db.Column(db.String(80), nullable=False)
    prenom = db.Column(db.String(80), nullable=False)
    classe = db.Column(db.String(30), nullable=False)
    photo_initiale = db.Column(db.String(2))

    pension_totale = db.Column(db.Integer, default=0)
    pension_payee = db.Column(db.Integer, default=0)

    notes = db.relationship("Note", backref="student", cascade="all, delete-orphan")
    presences = db.relationship("Presence", backref="student", cascade="all, delete-orphan")
    remarques = db.relationship("Remark", backref="student", cascade="all, delete-orphan")
    paiements = db.relationship("Payment", backref="student", cascade="all, delete-orphan")

    def moyenne(self, trimestre=None):
        notes = [n.note for n in self.notes if (trimestre is None or n.trimestre == trimestre)]
        return round(sum(notes) / len(notes), 1) if notes else 0

    def reste_a_payer(self):
        return max(self.pension_totale - self.pension_payee, 0)

    def __repr__(self):
        return f"<Student {self.prenom} {self.nom} ({self.classe})>"

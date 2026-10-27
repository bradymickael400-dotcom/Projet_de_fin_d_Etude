"""Notes, présences et remarques/signalements des enseignants."""
from datetime import date
from app.extensions import db


class Note(db.Model):
    __tablename__ = "notes"
    __table_args__ = (
        db.CheckConstraint("note BETWEEN 0 AND 20", name="ck_note_value"),
        db.CheckConstraint("trimestre IN ('T1','T2','T3')", name="ck_note_term"),
    )
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey("teachers.id"))
    matiere = db.Column(db.String(60), nullable=False)
    trimestre = db.Column(db.String(4), nullable=False)  # T1, T2, T3
    note = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.Date, default=date.today)


class Presence(db.Model):
    __tablename__ = "presences"
    __table_args__ = (
        db.UniqueConstraint("student_id", "school_id", "date", name="uq_daily_presence"),
        db.CheckConstraint(
            "statut IN ('present','absent','retard')", name="ck_presence_status"
        ),
    )
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    school_id = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=False)
    date = db.Column(db.Date, default=date.today, nullable=False)
    statut = db.Column(db.String(10), default="present")  # present | absent | retard


class Remark(db.Model):
    """Remarque positive ou signalement, envoyé directement au parent."""
    __tablename__ = "remarks"
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey("teachers.id"))
    type = db.Column(db.String(20), default="remarque")  # remarque | signalement
    texte = db.Column(db.Text, nullable=False)
    prive = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.Date, default=date.today)

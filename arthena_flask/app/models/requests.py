"""Demandes d'inscription (élèves) et de candidature (enseignants)."""
from datetime import date
from app.extensions import db


class EnrollmentRequest(db.Model):
    """Demande d'inscription d'un élève, soumise par un parent, à valider par l'école."""
    __tablename__ = "enrollment_requests"
    id = db.Column(db.Integer, primary_key=True)
    ecole_id = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    nom = db.Column(db.String(80), nullable=False)
    prenom = db.Column(db.String(80), nullable=False)
    classe = db.Column(db.String(30), nullable=False)
    ancien_eleve = db.Column(db.Boolean, default=False)
    age = db.Column(db.Integer, nullable=False)
    motif_nouvelle_ecole = db.Column(db.Text)
    acte_naissance = db.Column(db.String(255), nullable=False)
    ancien_bulletin = db.Column(db.String(255), nullable=False)
    documents = db.Column(db.String(255))  # chemins séparés par des virgules
    documents_statut = db.Column(db.String(20), default="pending")
    documents_note = db.Column(db.Text)
    documents_checked_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    statut = db.Column(db.String(20), default="pending")  # pending | accepted | rejected
    created_at = db.Column(db.Date, default=date.today)


class SchoolTask(db.Model):
    """Tâche attribuée à un membre du personnel d'un établissement."""
    __tablename__ = "school_tasks"
    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=False, index=True)
    assigned_to_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    titre = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text)
    statut = db.Column(db.String(20), nullable=False, default="a_faire")
    created_at = db.Column(db.Date, default=date.today)

    assigned_to = db.relationship("User", foreign_keys=[assigned_to_id])


class TeacherApplication(db.Model):
    """Candidature d'un enseignant pour rejoindre un établissement supplémentaire."""
    __tablename__ = "teacher_applications"
    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey("teachers.id"), nullable=False)
    ecole_id = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=False)
    matieres = db.Column(db.String(255))
    motivation = db.Column(db.Text)
    cv_path = db.Column(db.String(255))
    statut = db.Column(db.String(20), default="pending")  # pending | accepted | rejected
    created_at = db.Column(db.Date, default=date.today)


class Message(db.Model):
    """Messagerie interne enseignant <-> administration d'école."""
    __tablename__ = "messages"
    id = db.Column(db.Integer, primary_key=True)
    from_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    to_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    sujet = db.Column(db.String(150))
    texte = db.Column(db.Text)
    reponse = db.Column(db.Text)
    statut = db.Column(db.String(10), default="unread")  # unread | read
    created_at = db.Column(db.Date, default=date.today)

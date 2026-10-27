"""Établissement scolaire + entités associées (classe, événement, document)."""
from datetime import datetime, timezone
from app.extensions import db


class School(db.Model):
    __tablename__ = "schools"
    __table_args__ = (
        db.CheckConstraint("taux_reussite BETWEEN 0 AND 100", name="ck_school_success"),
        db.CheckConstraint("note_parents BETWEEN 0 AND 5", name="ck_school_rating"),
        db.CheckConstraint("effectif >= 0", name="ck_school_effectif"),
    )

    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(150), nullable=False)
    short = db.Column(db.String(40))
    type = db.Column(db.String(20))       # primaire | secondaire
    statut = db.Column(db.String(20))     # public | prive
    sous_type = db.Column(db.String(40))  # college_bilingue, lycee_scientifique, ...
    ville = db.Column(db.String(80), index=True)
    region = db.Column(db.String(80), index=True)
    lat = db.Column(db.Float, nullable=False)
    lng = db.Column(db.Float, nullable=False)
    frais_place = db.Column(db.Integer, default=0)
    contact = db.Column(db.String(30))
    description = db.Column(db.Text)

    # Indicateurs utilisés pour le classement national (voir services/ranking.py)
    effectif = db.Column(db.Integer, default=0)
    taux_reussite = db.Column(db.Float, default=0)   # en %
    note_parents = db.Column(db.Float, default=0)    # moyenne des avis, sur 5

    validated = db.Column(db.Boolean, default=False)
    status = db.Column(db.String(20), default="en_attente")  # actif | en_attente
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    admins = db.relationship("User", backref="ecole", foreign_keys="User.ecole_id")
    classes = db.relationship("SchoolClass", backref="school", cascade="all, delete-orphan")
    students = db.relationship("Student", backref="school", foreign_keys="Student.ecole_id")
    events = db.relationship("SchoolEvent", backref="school", cascade="all, delete-orphan")
    documents = db.relationship("SchoolDocument", backref="school", cascade="all, delete-orphan")
    teachers = db.relationship("Teacher", secondary="teacher_school", back_populates="schools")

    def __repr__(self):
        return f"<School {self.nom}>"


class SchoolClass(db.Model):
    __tablename__ = "school_classes"
    __table_args__ = (
        db.UniqueConstraint("school_id", "nom", name="uq_school_class_name"),
    )
    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=False)
    nom = db.Column(db.String(30), nullable=False)  # ex: "CM2", "6ème"


class SchoolEvent(db.Model):
    __tablename__ = "school_events"
    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=False)
    titre = db.Column(db.String(150), nullable=False)
    date = db.Column(db.Date, nullable=False)
    texte = db.Column(db.Text)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class SchoolPost(db.Model):
    """Publication d'un établissement, publique ou réservée à sa communauté."""
    __tablename__ = "school_posts"
    __table_args__ = (
        db.CheckConstraint(
            "category IN ('calendrier','evenement','communique','information')",
            name="ck_school_post_category",
        ),
        db.CheckConstraint(
            "visibility IN ('public','communaute')",
            name="ck_school_post_visibility",
        ),
    )
    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=False, index=True)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    title = db.Column(db.String(180), nullable=False)
    content = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(30), nullable=False, default="information")
    visibility = db.Column(db.String(20), nullable=False, default="communaute")
    starts_at = db.Column(db.DateTime(timezone=True))
    ends_at = db.Column(db.DateTime(timezone=True))
    published_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    school = db.relationship("School", backref=db.backref("posts", cascade="all, delete-orphan"))
    author = db.relationship("User")


class SchoolDocument(db.Model):
    """Documents MINESEC déposés par l'école, à valider par le Super Admin."""
    __tablename__ = "school_documents"
    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=False)
    nom_fichier = db.Column(db.String(150))
    chemin = db.Column(db.String(255))
    type_doc = db.Column(db.String(60))  # certificat_creation | arrete_ouverture | statut | ...
    valide = db.Column(db.Boolean, default=False)
    uploaded_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class PendingSchoolRequest(db.Model):
    """Demande d'inscription d'un nouvel établissement sur la plateforme."""
    __tablename__ = "pending_school_requests"
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(150), nullable=False)
    ville = db.Column(db.String(80))
    region = db.Column(db.String(80))
    contact = db.Column(db.String(30))
    email = db.Column(db.String(120))
    type = db.Column(db.String(30))
    cycle = db.Column(db.String(30))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    manager_nom = db.Column(db.String(80))
    manager_prenom = db.Column(db.String(80))
    manager_phone = db.Column(db.String(30))
    manager_password_hash = db.Column(db.String(255))
    document_creation = db.Column(db.String(255))
    document_autorisation = db.Column(db.String(255))
    statut = db.Column(db.String(20), default="pending")  # pending | approved | rejected
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

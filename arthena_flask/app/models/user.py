"""Compte utilisateur générique : sert de base pour les 4 rôles Arthena."""
from datetime import datetime, timezone
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from app.extensions import db


class User(db.Model, UserMixin):
    __tablename__ = "users"
    __table_args__ = (
        db.CheckConstraint(
            "role IN ('parent','enseignant','admin','superadmin','intendante','censeur')",
            name="ck_users_role",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    nom = db.Column(db.String(80), nullable=False)
    prenom = db.Column(db.String(80), nullable=False)
    phone = db.Column(db.String(30))
    adresse = db.Column(db.String(200))
    ville = db.Column(db.String(80))
    lat = db.Column(db.Float)   # position du parent, utilisée pour la carte de proximité
    lng = db.Column(db.Float)
    is_active_account = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Un admin gère un seul établissement
    ecole_id = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=True)

    students = db.relationship("Student", backref="parent", foreign_keys="Student.parent_id")
    teacher_profile = db.relationship("Teacher", backref="user", uselist=False)
    notifications = db.relationship("Notification", backref="user", lazy="dynamic")

    def set_password(self, raw_password):
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        return check_password_hash(self.password_hash, raw_password)

    @property
    def is_active(self):
        return bool(self.is_active_account)

    def full_name(self):
        return f"{self.prenom} {self.nom}"

    def __repr__(self):
        return f"<User {self.email} ({self.role})>"

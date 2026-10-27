"""Notifications poussées aux parents (notes, absences, signalements, paiements)."""
from datetime import date
from app.extensions import db


class Notification(db.Model):
    __tablename__ = "notifications"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    texte = db.Column(db.String(255), nullable=False)
    lu = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.Date, default=date.today)

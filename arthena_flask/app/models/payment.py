"""Paiements de pension et de frais de dossier (Mobile Money / Banque)."""
from datetime import date
from app.extensions import db


class Payment(db.Model):
    __tablename__ = "payments"
    __table_args__ = (
        db.CheckConstraint("montant > 0", name="ck_payment_amount"),
        db.CheckConstraint(
            "status IN ('pending','confirmed','failed')", name="ck_payment_status"
        ),
    )
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    montant = db.Column(db.Integer, nullable=False)
    type = db.Column(db.String(30), default="pension")  # pension | inscription
    methode = db.Column(db.String(30))  # MTN MoMo | Orange Money | Banque
    reference = db.Column(db.String(100), unique=True, nullable=False)
    status = db.Column(db.String(20), default="pending", nullable=False)
    created_at = db.Column(db.Date, default=date.today)

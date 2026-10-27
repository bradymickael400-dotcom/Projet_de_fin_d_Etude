"""Création centralisée de notifications (notes, absences, signalements, paiements)."""
from app.extensions import db
from app.models.notification import Notification
from app.models.user import User
from app.services.email import send_email_safely


def notify(user_id, texte, *, commit=False):
    if not user_id:
        return None
    notif = Notification(user_id=user_id, texte=texte)
    db.session.add(notif)
    db.session.flush()
    user = db.session.get(User, user_id)
    if user:
        send_email_safely(user.email, "Nouvelle notification Arthena", texte)
    if commit:
        db.session.commit()
    return notif

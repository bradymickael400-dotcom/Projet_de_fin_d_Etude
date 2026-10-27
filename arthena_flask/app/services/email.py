"""Envoi SMTP centralisé, sans exposer les secrets ni bloquer les tests."""
import smtplib
from email.message import EmailMessage

from flask import current_app


def send_email(recipient, subject, text):
    if not recipient:
        return False
    cfg = current_app.config
    if cfg["MAIL_SUPPRESS_SEND"]:
        current_app.logger.info("Email supprimé en test: %s -> %s", subject, recipient)
        return True
    sender = cfg["MAIL_DEFAULT_SENDER"]
    username = cfg["MAIL_USERNAME"]
    password = cfg["MAIL_PASSWORD"]
    if not sender or not username or not password:
        current_app.logger.warning("SMTP non configuré; email non envoyé à %s", recipient)
        return False

    message = EmailMessage()
    message["From"] = sender
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(text)

    smtp_class = smtplib.SMTP_SSL if cfg["MAIL_USE_SSL"] else smtplib.SMTP
    with smtp_class(cfg["MAIL_SERVER"], cfg["MAIL_PORT"], timeout=cfg["MAIL_TIMEOUT"]) as smtp:
        if cfg["MAIL_USE_TLS"] and not cfg["MAIL_USE_SSL"]:
            smtp.starttls()
        smtp.login(username, password)
        smtp.send_message(message)
    return True


def send_email_safely(recipient, subject, text):
    try:
        return send_email(recipient, subject, text)
    except (OSError, smtplib.SMTPException):
        current_app.logger.exception("Échec d'envoi SMTP vers %s", recipient)
        return False

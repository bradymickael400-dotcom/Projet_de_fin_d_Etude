"""Initialisation minimale d'une instance ARGOS neuve."""

import os
import time

from sqlalchemy import text
from werkzeug.security import generate_password_hash

from app import create_app
from app.extensions import db
from app.migrate import run_migrations


def main():
    login = os.getenv("INITIAL_ADMIN_LOGIN", "superadmin").strip()
    password = os.getenv("INITIAL_ADMIN_PASSWORD", "")
    if not password:
        raise RuntimeError("INITIAL_ADMIN_PASSWORD obligatoire pour initialiser ARGOS")
    run_migrations()
    app = create_app()
    last_error = None
    for _ in range(30):
        try:
            with app.app_context():
                exists = db.session.execute(text(
                    "SELECT 1 FROM superadmin WHERE LOWER(login)=LOWER(:login)"
                ), {"login": login}).scalar()
                if not exists:
                    db.session.execute(text("""
                        INSERT INTO superadmin(login,password) VALUES (:login,:password)
                    """), {"login": login, "password": generate_password_hash(password)})
                    db.session.commit()
                    print("Compte administrateur initial ARGOS cree.")
                return
        except Exception as exc:
            last_error = exc
            time.sleep(2)
    raise RuntimeError("Base ARGOS indisponible pendant le bootstrap") from last_error


if __name__ == "__main__":
    main()

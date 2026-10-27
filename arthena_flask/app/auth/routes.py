"""Connexion, inscription, déconnexion, redirection par rôle."""
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from threading import Lock
from pathlib import Path
from uuid import uuid4

from flask import current_app, render_template, redirect, url_for, flash, request, abort, session
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename

from app.auth import auth_bp
from app.auth.forms import LoginForm, RegisterForm
from app.extensions import db
from app.models.user import User
from app.models.teacher import Teacher
from app.models.school import PendingSchoolRequest

_login_attempts = defaultdict(deque)
_attempt_lock = Lock()
_LOGIN_LIMIT = 8
_LOGIN_WINDOW = timedelta(minutes=15)


def _client_key():
    return request.remote_addr or "unknown"


def _check_login_rate():
    now = datetime.now(timezone.utc)
    with _attempt_lock:
        attempts = _login_attempts[_client_key()]
        while attempts and now - attempts[0] > _LOGIN_WINDOW:
            attempts.popleft()
        if len(attempts) >= _LOGIN_LIMIT:
            abort(429)
        attempts.append(now)


def _clear_login_rate():
    with _attempt_lock:
        _login_attempts.pop(_client_key(), None)


@auth_bp.route("/", methods=["GET"])
def index():
    dashboard_url = role_dashboard(current_user.role) if current_user.is_authenticated else None
    return render_template("landing.html", role_dashboard_url=dashboard_url)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(role_dashboard(current_user.role))
    form = LoginForm()
    if form.validate_on_submit():
        _check_login_rate()
        user = User.query.filter_by(email=form.email.data.lower()).first()
        if user and user.is_active and user.check_password(form.password.data):
            session.clear()
            login_user(user)
            _clear_login_rate()
            return redirect(role_dashboard(user.role))
        flash("Email ou mot de passe incorrect.", "error")
    return render_template("auth/login.html", form=form)


@auth_bp.route("/inscription", methods=["GET", "POST"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        if User.query.filter_by(email=form.email.data.lower()).first():
            flash("Cet email est déjà utilisé.", "error")
        else:
            user = User(email=form.email.data.lower(), nom=form.nom.data,
                        prenom=form.prenom.data, role=form.role.data)
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.flush()
            if user.role == "enseignant":
                db.session.add(Teacher(user_id=user.id))
            db.session.commit()
            flash("Compte créé ! Connectez-vous.", "success")
            return redirect(url_for("auth.login"))
    return render_template("auth/register.html", form=form)


@auth_bp.route("/ajouter-etablissement", methods=["GET", "POST"])
def request_school():
    if request.method == "POST":
        fields = {key: (request.form.get(key) or "").strip() for key in (
            "nom", "ville", "region", "contact", "email", "type", "cycle",
            "manager_nom", "manager_prenom", "manager_phone",
        )}
        password = request.form.get("password") or ""
        try:
            latitude = float(request.form.get("latitude"))
            longitude = float(request.form.get("longitude"))
        except (TypeError, ValueError):
            latitude = longitude = None
        if not all(fields.values()) or latitude is None or longitude is None:
            flash("Tous les champs sont obligatoires.", "error")
        elif not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
            flash("La position géographique sélectionnée est invalide.", "error")
        elif len(password) < 10:
            flash("Le mot de passe doit contenir au moins 10 caractères.", "error")
        elif User.query.filter_by(email=fields["email"].lower()).first():
            flash("Cette adresse e-mail possède déjà un compte.", "error")
        elif PendingSchoolRequest.query.filter_by(
                email=fields["email"].lower(), nom=fields["nom"], statut="pending").first():
            flash("Une demande identique est déjà en cours d'étude.", "error")
        else:
            saved_documents = {}
            for field_name in ("document_creation", "document_autorisation"):
                uploaded = request.files.get(field_name)
                if not uploaded or not uploaded.filename:
                    flash("Les deux documents légaux sont obligatoires.", "error")
                    break
                extension = Path(secure_filename(uploaded.filename)).suffix.lower()
                if extension not in {".pdf", ".jpg", ".jpeg", ".png"}:
                    flash("Les documents doivent être au format PDF, JPG ou PNG.", "error")
                    break
                directory = Path(current_app.config["UPLOAD_FOLDER"]) / "school-requests"
                directory.mkdir(parents=True, exist_ok=True)
                filename = f"{uuid4().hex}{extension}"
                uploaded.save(directory / filename)
                saved_documents[field_name] = f"school-requests/{filename}"
            if len(saved_documents) == 2:
                fields["email"] = fields["email"].lower()
                db.session.add(PendingSchoolRequest(
                    **fields, latitude=latitude, longitude=longitude,
                    manager_password_hash=generate_password_hash(password),
                    **saved_documents,
                ))
                db.session.commit()
                flash("Votre dossier a été transmis. Votre compte sera activé après validation.", "success")
                return redirect(url_for("auth.request_school"))
    return render_template("auth/request_school.html")


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))


def role_dashboard(role):
    return {
        "parent": url_for("parent.dashboard"),
        "enseignant": url_for("teacher.dashboard"),
        "admin": url_for("school_admin.dashboard"),
        "superadmin": url_for("superadmin.dashboard"),
        "intendante": url_for("school_admin.enrolments"),
        "censeur": url_for("school_admin.staff_workspace"),
    }.get(role, url_for("auth.login"))

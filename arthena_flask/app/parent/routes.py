"""Espace parent : accueil/carte, mes élèves, classement national, notifications."""
from flask import current_app, render_template, request, jsonify
from pathlib import Path
from uuid import uuid4
from werkzeug.utils import secure_filename
from flask_login import login_required, current_user

from app.parent import parent_bp
from app.utils.decorators import role_required
from app.services.geo import schools_near
from app.services.ranking import national_ranking
from app.services.payments import initiate_payment
from app.extensions import db
from app.models.student import Student
from app.models.school import School
from app.models.requests import EnrollmentRequest
from app.models.notification import Notification
from app.models.user import User
from app.services.notifications import notify


@parent_bp.route("/")
@login_required
@role_required("parent")
def dashboard():
    try:
        radius = max(1, min(int(request.args.get("radius", 8)), 100))
    except (TypeError, ValueError):
        radius = 8
    nearby = schools_near(current_user.lat, current_user.lng, radius) if current_user.lat is not None and current_user.lng is not None else []
    students = Student.query.filter_by(parent_id=current_user.id).all()
    notifications = Notification.query.filter_by(user_id=current_user.id).order_by(
        Notification.created_at.desc()).limit(5).all()
    return render_template("parent/dashboard.html", nearby=nearby, students=students,
                            notifications=notifications, radius=radius)


@parent_bp.route("/mes-eleves")
@login_required
@role_required("parent")
def students():
    students = Student.query.filter_by(parent_id=current_user.id).all()
    return render_template("parent/students.html", students=students)


@parent_bp.route("/inscription", methods=["GET", "POST"])
@login_required
@role_required("parent")
def enrol():
    if request.method == "POST":
        data = request.form if request.files else (request.get_json(silent=True) or request.form)
        try:
            school_id = int(data.get("ecole_id"))
        except (TypeError, ValueError):
            return jsonify({"error": "Sélectionnez un établissement valide."}), 400
        school = School.query.filter_by(id=school_id, validated=True, status="actif").first_or_404()
        required = {name: (data.get(name) or "").strip() for name in ("nom", "prenom", "classe")}
        if not all(required.values()):
            return jsonify({"error": "Le nom, le prénom et la classe sont obligatoires."}), 400
        try:
            age = int(data.get("age", 0))
        except (TypeError, ValueError):
            return jsonify({"error": "L'âge doit être un nombre entier."}), 400
        if not 2 <= age <= 25:
            return jsonify({"error": "L'âge doit être compris entre 2 et 25 ans."}), 400
        ancien_eleve = str(data.get("ancien_eleve", "")).lower() in {"1", "true", "on"}
        motif = (data.get("motif_nouvelle_ecole") or "").strip()
        if not ancien_eleve and len(motif) < 10:
            return jsonify({"error": "Précisez le motif du choix de ce nouvel établissement."}), 400
        duplicate = EnrollmentRequest.query.filter_by(
            parent_id=current_user.id, ecole_id=school.id, nom=required["nom"],
            prenom=required["prenom"], statut="pending").first()
        if duplicate:
            return jsonify({"error": "Une demande identique est déjà en attente."}), 409
        uploads = {
            "acte_naissance": request.files.get("acte_naissance"),
            "ancien_bulletin": request.files.get("ancien_bulletin"),
        }
        for label, uploaded in uploads.items():
            if not uploaded or not uploaded.filename:
                readable = "L'acte de naissance" if label == "acte_naissance" else "L'ancien bulletin"
                return jsonify({"error": f"{readable} est obligatoire."}), 400
            extension = Path(secure_filename(uploaded.filename)).suffix.lower()
            if extension not in {".pdf", ".jpg", ".jpeg", ".png"}:
                return jsonify({"error": "Les documents doivent être au format PDF, JPG ou PNG."}), 400
        directory = Path(current_app.config["UPLOAD_FOLDER"]) / "enrollment-documents"
        directory.mkdir(parents=True, exist_ok=True)
        saved = {}
        for label, uploaded in uploads.items():
            extension = Path(secure_filename(uploaded.filename)).suffix.lower()
            stored_name = f"{uuid4().hex}{extension}"
            uploaded.save(directory / stored_name)
            saved[label] = f"enrollment-documents/{stored_name}"
        enrolment = EnrollmentRequest(ecole_id=school.id, parent_id=current_user.id,
                                      ancien_eleve=ancien_eleve, age=age,
                                      motif_nouvelle_ecole=motif if not ancien_eleve else None,
                                      acte_naissance=saved["acte_naissance"],
                                      ancien_bulletin=saved["ancien_bulletin"],
                                      **required)
        db.session.add(enrolment)
        for admin in User.query.filter(
                User.ecole_id == school.id,
                User.role.in_(("admin", "intendante")),
                User.is_active_account.is_(True)):
            notify(admin.id, f"Nouvelle demande d'inscription : {required['prenom']} {required['nom']}.")
        db.session.commit()
        return jsonify({"ok": True, "request_id": enrolment.id})
    schools = School.query.filter_by(validated=True, status="actif").order_by(School.nom).all()
    requests_ = EnrollmentRequest.query.filter_by(parent_id=current_user.id).order_by(
        EnrollmentRequest.created_at.desc()).all()
    return render_template("parent/enrol.html", schools=schools, requests=requests_)


@parent_bp.route("/eleve/<int:student_id>")
@login_required
@role_required("parent")
def student_detail(student_id):
    student = Student.query.filter_by(id=student_id, parent_id=current_user.id).first_or_404()
    return render_template("parent/student_detail.html", student=student)


@parent_bp.route("/classement")
@login_required
@role_required("parent")
def ranking():
    return render_template("parent/ranking.html", ranking=national_ranking())


@parent_bp.route("/eleve/<int:student_id>/payer", methods=["POST"])
@login_required
@role_required("parent")
def pay_pension(student_id):
    student = Student.query.filter_by(id=student_id, parent_id=current_user.id).first_or_404()
    data = request.get_json(silent=True) or request.form
    try:
        montant = int(data.get("montant", 0))
    except (TypeError, ValueError):
        return jsonify({"error": "Le montant doit être un nombre entier."}), 400
    methode = (data.get("methode") or "").strip()
    if montant <= 0 or not methode:
        return jsonify({"error": "Le montant et la méthode de paiement sont obligatoires."}), 400
    if montant > student.reste_a_payer():
        return jsonify({"error": "Le montant dépasse le reste à payer."}), 400
    payment = initiate_payment(student_id, montant, methode, type_="pension")
    return jsonify({
        "ok": True,
        "status": payment.status,
        "reference": payment.reference,
        "reste_a_payer": student.reste_a_payer(),
    })

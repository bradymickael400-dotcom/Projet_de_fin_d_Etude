"""Espace super admin : supervision nationale, classement, validation des écoles."""
from flask import current_app, render_template, request, jsonify, send_from_directory

from flask_login import login_required
from app.superadmin import superadmin_bp
from app.utils.decorators import role_required
from app.extensions import db
from app.models.school import School, PendingSchoolRequest
from app.services.ranking import national_ranking
from app.services.email import send_email_safely
from app.models.user import User


@superadmin_bp.route("/")
@login_required
@role_required("superadmin")
def dashboard():
    schools = School.query.filter_by(validated=True).all()
    pending = PendingSchoolRequest.query.filter_by(statut="pending").all()
    return render_template("superadmin/dashboard.html", schools=schools, pending=pending)


@superadmin_bp.route("/classement")
@login_required
@role_required("superadmin")
def ranking():
    return render_template("superadmin/ranking.html", ranking=national_ranking())


@superadmin_bp.route("/demandes-ecoles")
@login_required
@role_required("superadmin")
def pending_schools():
    pending = PendingSchoolRequest.query.filter_by(statut="pending").all()
    return render_template("superadmin/pending_schools.html", pending=pending)


@superadmin_bp.route("/demandes-ecoles/<int:req_id>/approuver", methods=["POST"])
@login_required
@role_required("superadmin")
def approve_school(req_id):
    req = PendingSchoolRequest.query.filter_by(id=req_id, statut="pending").first_or_404()
    if User.query.filter_by(email=req.email).first():
        return jsonify({"error": "L'adresse du gestionnaire est déjà associée à un compte."}), 409
    req.statut = "approved"
    school_type = "primaire" if req.cycle == "primaire" else "secondaire"
    school = School(nom=req.nom, ville=req.ville, region=req.region, statut=req.type,
                     type=school_type, sous_type=req.cycle, contact=req.contact,
                     lat=req.latitude, lng=req.longitude, validated=True, status="actif")
    db.session.add(school)
    db.session.flush()
    manager = User(
        email=req.email, password_hash=req.manager_password_hash,
        nom=req.manager_nom, prenom=req.manager_prenom,
        phone=req.manager_phone, role="admin", ecole_id=school.id,
    )
    db.session.add(manager)
    db.session.commit()
    send_email_safely(req.email, "Établissement approuvé sur Arthena",
                      f"La demande de l'établissement {req.nom} a été approuvée.")
    return jsonify({"ok": True})


@superadmin_bp.route("/demandes-ecoles/<int:req_id>/document/<kind>")
@login_required
@role_required("superadmin")
def school_request_document(req_id, kind):
    req = db.get_or_404(PendingSchoolRequest, req_id)
    path = {
        "creation": req.document_creation,
        "autorisation": req.document_autorisation,
    }.get(kind)
    if not path or "/" not in path:
        return jsonify({"error": "Document indisponible."}), 404
    directory, filename = path.rsplit("/", 1)
    return send_from_directory(
        f"{current_app.config['UPLOAD_FOLDER']}/{directory}",
        filename,
        as_attachment=True,
        download_name=f"{kind}-{req.nom}{filename[filename.rfind('.'):]}",
    )


@superadmin_bp.route("/demandes-ecoles/<int:req_id>/rejeter", methods=["POST"])
@login_required
@role_required("superadmin")
def reject_school(req_id):
    req = db.get_or_404(PendingSchoolRequest, req_id)
    req.statut = "rejected"
    db.session.commit()
    send_email_safely(req.email, "Demande d'établissement Arthena",
                      f"La demande de l'établissement {req.nom} a été rejetée.")
    return jsonify({"ok": True})

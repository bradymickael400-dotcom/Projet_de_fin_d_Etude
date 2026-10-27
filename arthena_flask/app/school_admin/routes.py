"""Espace admin d'établissement : classes, enseignants, candidatures, inscriptions, bilans."""
from flask import current_app, render_template, request, jsonify, send_from_directory, redirect, url_for
from flask_login import login_required, current_user

from app.school_admin import school_admin_bp
from app.utils.decorators import role_required
from app.extensions import db
from app.models.school import School, SchoolPost
from app.models.student import Student
from app.models.teacher import Teacher
from app.models.requests import TeacherApplication, EnrollmentRequest, SchoolTask
from app.models.user import User
from app.models.academic import Presence
from app.services.ranking import school_rank
from app.services.notifications import notify
from datetime import datetime


def _accessible_school(school_id):
    school = db.get_or_404(School, school_id)
    if current_user.role in {"admin", "intendante", "censeur"}:
        allowed = current_user.ecole_id == school.id
    elif current_user.role == "enseignant":
        allowed = current_user.teacher_profile and school in current_user.teacher_profile.schools
    elif current_user.role == "parent":
        allowed = Student.query.filter_by(parent_id=current_user.id, ecole_id=school.id).first() is not None
    else:
        allowed = False
    if not allowed:
        from flask import abort
        abort(403)
    return school


@school_admin_bp.route("/")
@login_required
@role_required("admin")
def dashboard():
    school = db.get_or_404(School, current_user.ecole_id)
    rank, score = school_rank(school)
    pending_affil = TeacherApplication.query.filter_by(ecole_id=school.id, statut="pending").count()
    pending_enrol = EnrollmentRequest.query.filter_by(ecole_id=school.id, statut="pending").count()
    return render_template("admin/dashboard.html", school=school, rank=rank, score=score,
                            pending_affil=pending_affil, pending_enrol=pending_enrol)


@school_admin_bp.route("/candidatures")
@login_required
@role_required("admin")
def affiliations():
    apps = TeacherApplication.query.filter_by(ecole_id=current_user.ecole_id, statut="pending").all()
    return render_template("admin/affiliations.html", applications=apps)


@school_admin_bp.route("/candidatures/<int:app_id>/accepter", methods=["POST"])
@login_required
@role_required("admin")
def accept_affiliation(app_id):
    application = TeacherApplication.query.filter_by(
        id=app_id, ecole_id=current_user.ecole_id, statut="pending").first_or_404()
    application.statut = "accepted"
    teacher = db.session.get(Teacher, application.teacher_id)
    school = db.session.get(School, current_user.ecole_id)
    if school not in teacher.schools:
        teacher.schools.append(school)
    notify(teacher.user_id, f"Votre candidature auprès de {school.nom} a été acceptée.")
    db.session.commit()
    return jsonify({"ok": True})


@school_admin_bp.route("/candidatures/<int:app_id>/rejeter", methods=["POST"])
@login_required
@role_required("admin")
def reject_affiliation(app_id):
    application = TeacherApplication.query.filter_by(
        id=app_id, ecole_id=current_user.ecole_id, statut="pending").first_or_404()
    application.statut = "rejected"
    teacher = db.session.get(Teacher, application.teacher_id)
    if teacher:
        notify(teacher.user_id, "Votre candidature auprès de l'établissement a été rejetée.")
    db.session.commit()
    return jsonify({"ok": True})


@school_admin_bp.route("/inscriptions")
@login_required
@role_required("admin", "intendante")
def enrolments():
    reqs = EnrollmentRequest.query.filter_by(ecole_id=current_user.ecole_id, statut="pending").all()
    return render_template("admin/enrolments.html", requests=reqs)


@school_admin_bp.route("/inscriptions/<int:req_id>/accepter", methods=["POST"])
@login_required
@role_required("admin", "intendante")
def accept_enrolment(req_id):
    req = EnrollmentRequest.query.filter_by(
        id=req_id, ecole_id=current_user.ecole_id, statut="pending").first_or_404()
    if req.documents_statut != "conforme":
        return jsonify({"error": "Les documents doivent d'abord être déclarés conformes."}), 409
    req.statut = "accepted"
    student = Student(parent_id=req.parent_id, ecole_id=req.ecole_id, nom=req.nom,
                       prenom=req.prenom, classe=req.classe, photo_initiale=req.prenom[0])
    db.session.add(student)
    notify(req.parent_id, f"L'inscription de {req.prenom} {req.nom} a été acceptée.")
    db.session.commit()
    return jsonify({"ok": True})


@school_admin_bp.route("/inscriptions/<int:req_id>/rejeter", methods=["POST"])
@login_required
@role_required("admin", "intendante")
def reject_enrolment(req_id):
    req = EnrollmentRequest.query.filter_by(
        id=req_id, ecole_id=current_user.ecole_id, statut="pending").first_or_404()
    req.statut = "rejected"
    notify(req.parent_id, f"L'inscription de {req.prenom} {req.nom} a été rejetée.")
    db.session.commit()
    return jsonify({"ok": True})


@school_admin_bp.route("/inscriptions/<int:req_id>/documents/<decision>", methods=["POST"])
@login_required
@role_required("admin", "intendante")
def review_documents(req_id, decision):
    if decision not in {"conforme", "non_conforme"}:
        return jsonify({"error": "Décision invalide."}), 400
    req = EnrollmentRequest.query.filter_by(id=req_id, ecole_id=current_user.ecole_id).first_or_404()
    data = request.get_json(silent=True) or request.form
    req.documents_statut = decision
    req.documents_note = (data.get("note") or "").strip()[:1000]
    req.documents_checked_by = current_user.id
    notify(req.parent_id, f"Les documents de {req.prenom} {req.nom} ont été déclarés "
           f"{'conformes' if decision == 'conforme' else 'non conformes'}.")
    db.session.commit()
    return jsonify({"ok": True})


@school_admin_bp.route("/inscriptions/<int:req_id>/document/<kind>")
@login_required
@role_required("admin", "intendante")
def enrolment_document(req_id, kind):
    req = EnrollmentRequest.query.filter_by(id=req_id, ecole_id=current_user.ecole_id).first_or_404()
    path = {"acte-naissance": req.acte_naissance, "ancien-bulletin": req.ancien_bulletin}.get(kind)
    if not path or "/" not in path:
        return jsonify({"error": "Document indisponible."}), 404
    directory, filename = path.rsplit("/", 1)
    return send_from_directory(
        f"{current_app.config['UPLOAD_FOLDER']}/{directory}",
        filename,
        as_attachment=True,
        download_name=f"{kind}-{req.prenom}-{req.nom}{filename[filename.rfind('.'):]}",
    )


@school_admin_bp.route("/personnel", methods=["GET", "POST"])
@login_required
@role_required("admin")
def staff():
    if request.method == "POST":
        data = request.get_json(silent=True) or request.form
        fields = {key: (data.get(key) or "").strip() for key in ("prenom", "nom", "email", "password", "role")}
        fields["email"] = fields["email"].lower()
        if not all(fields.values()) or fields["role"] not in {"intendante", "censeur"}:
            return jsonify({"error": "Informations incomplètes ou rôle non autorisé."}), 400
        if len(fields["password"]) < 10:
            return jsonify({"error": "Le mot de passe doit contenir au moins 10 caractères."}), 400
        if User.query.filter_by(email=fields["email"]).first():
            return jsonify({"error": "Cette adresse e-mail est déjà utilisée."}), 409
        user = User(email=fields["email"], prenom=fields["prenom"], nom=fields["nom"],
                    role=fields["role"], ecole_id=current_user.ecole_id)
        user.set_password(fields["password"])
        db.session.add(user)
        db.session.flush()
        notify(user.id, f"Votre compte {fields['role']} a été créé pour {current_user.ecole.nom}.")
        db.session.commit()
        return jsonify({"ok": True})
    personnel = User.query.filter(
        User.ecole_id == current_user.ecole_id,
        User.role.in_(("intendante", "censeur")),
    ).order_by(User.role, User.nom).all()
    return render_template("admin/staff.html", personnel=personnel)


@school_admin_bp.route("/personnel/taches", methods=["POST"])
@login_required
@role_required("admin")
def assign_task():
    data = request.get_json(silent=True) or request.form
    try:
        assigned_to_id = int(data.get("assigned_to_id"))
    except (TypeError, ValueError):
        return jsonify({"error": "Sélectionnez un membre du personnel."}), 400
    member = User.query.filter(
        User.id == assigned_to_id, User.ecole_id == current_user.ecole_id,
        User.role.in_(("intendante", "censeur"))).first_or_404()
    title = (data.get("titre") or "").strip()
    if len(title) < 3:
        return jsonify({"error": "Le titre de la tâche est obligatoire."}), 400
    task = SchoolTask(school_id=current_user.ecole_id, assigned_to_id=member.id,
                      created_by_id=current_user.id, titre=title[:150],
                      description=(data.get("description") or "").strip()[:2000])
    db.session.add(task)
    notify(member.id, f"Nouvelle tâche : {task.titre}")
    db.session.commit()
    return jsonify({"ok": True})


@school_admin_bp.route("/espace-personnel")
@login_required
@role_required("admin", "intendante", "censeur")
def staff_workspace():
    tasks = SchoolTask.query.filter_by(
        school_id=current_user.ecole_id,
        assigned_to_id=current_user.id,
    ).order_by(SchoolTask.created_at.desc()).all()
    return render_template("admin/staff_workspace.html", tasks=tasks)


@school_admin_bp.route("/espace-personnel/taches/<int:task_id>", methods=["POST"])
@login_required
@role_required("intendante", "censeur")
def complete_task(task_id):
    task = SchoolTask.query.filter_by(
        id=task_id, school_id=current_user.ecole_id, assigned_to_id=current_user.id).first_or_404()
    task.statut = "terminee"
    db.session.commit()
    return jsonify({"ok": True})


@school_admin_bp.route("/bilan", methods=["POST"])
@login_required
@role_required("admin")
def submit_bilan():
    """Mise à jour du taux de réussite : impacte directement le classement national."""
    school = db.get_or_404(School, current_user.ecole_id)
    data = request.get_json(silent=True) or request.form
    try:
        taux = float(data.get("taux_reussite"))
    except (TypeError, ValueError):
        return jsonify({"error": "Le taux de réussite doit être un nombre."}), 400
    if not 0 <= taux <= 100:
        return jsonify({"error": "Le taux doit être compris entre 0 et 100."}), 400
    school.taux_reussite = taux
    db.session.commit()
    return jsonify({"ok": True})


@school_admin_bp.route("/communaute")
@login_required
@role_required("admin", "intendante", "censeur")
def community():
    return redirect(url_for("school_admin.school_community", school_id=current_user.ecole_id))


@school_admin_bp.route("/communaute/<int:school_id>")
@login_required
@role_required("admin", "intendante", "censeur", "enseignant", "parent")
def school_community(school_id):
    school = _accessible_school(school_id)
    posts = SchoolPost.query.filter_by(school_id=school.id).order_by(SchoolPost.published_at.desc()).all()
    can_manage = current_user.role in {"admin", "intendante", "censeur", "enseignant"}
    students = []
    fully_paid = []
    recent_presences = []
    if current_user.role in {"admin", "intendante", "censeur"}:
        students = Student.query.filter_by(ecole_id=school.id).order_by(Student.classe, Student.nom).all()
        fully_paid = [student for student in students if student.reste_a_payer() == 0]
        recent_presences = (
            Presence.query.filter_by(school_id=school.id)
            .order_by(Presence.date.desc()).limit(100).all()
        )
    return render_template("admin/community.html", school=school, posts=posts,
                           can_manage=can_manage, students=students, fully_paid=fully_paid,
                           recent_presences=recent_presences)


@school_admin_bp.route("/communaute/<int:school_id>/publier", methods=["POST"])
@login_required
@role_required("admin", "intendante", "censeur", "enseignant")
def publish_school_post(school_id):
    school = _accessible_school(school_id)
    data = request.get_json(silent=True) or request.form
    title = (data.get("title") or "").strip()
    content = (data.get("content") or "").strip()
    category = data.get("category")
    visibility = data.get("visibility")
    if len(title) < 3 or len(content) < 10:
        return jsonify({"error": "Le titre et un contenu détaillé sont obligatoires."}), 400
    if category not in {"calendrier", "evenement", "communique", "information"}:
        return jsonify({"error": "Catégorie invalide."}), 400
    if visibility not in {"public", "communaute"}:
        return jsonify({"error": "Visibilité invalide."}), 400
    def parse_date(value):
        return datetime.fromisoformat(value) if value else None
    try:
        starts_at = parse_date(data.get("starts_at"))
        ends_at = parse_date(data.get("ends_at"))
    except ValueError:
        return jsonify({"error": "Date ou heure invalide."}), 400
    post = SchoolPost(
        school_id=school.id, author_id=current_user.id, title=title[:180],
        content=content[:5000], category=category, visibility=visibility,
        starts_at=starts_at, ends_at=ends_at,
    )
    db.session.add(post)
    db.session.commit()
    return jsonify({"ok": True})

"""Espace enseignant : établissements, appel, notes, signalements, candidatures."""
from datetime import date
from flask import render_template, request, jsonify
from flask_login import login_required, current_user

from app.teacher import teacher_bp
from app.utils.decorators import role_required
from app.extensions import db
from app.models.teacher import Teacher, Schedule
from app.models.student import Student
from app.models.academic import Note, Presence, Remark
from app.models.requests import TeacherApplication
from app.models.school import School
from app.services.notifications import notify
from app.models.user import User


def current_teacher():
    return Teacher.query.filter_by(user_id=current_user.id).first_or_404()

def assigned_schedules(teacher, school_id, classe=None):
    query = Schedule.query.filter_by(teacher_id=teacher.id, school_id=school_id)
    if classe is not None:
        query = query.filter_by(classe=classe)
    return query.all()


def can_teach(teacher, student, matiere=None):
    schedules = assigned_schedules(teacher, student.ecole_id, student.classe)
    if not schedules:
        return False
    if matiere is None:
        return True
    wanted = matiere.strip().casefold()
    return any((schedule.matiere or "").strip().casefold() == wanted for schedule in schedules)


@teacher_bp.route("/")
@login_required
@role_required("enseignant")
def dashboard():
    teacher = current_teacher()
    classes = sorted({(h.school_id, h.classe) for h in teacher.horaires if h.classe})
    return render_template("teacher/dashboard.html", teacher=teacher, schools=teacher.schools,
                           classes=classes)


@teacher_bp.route("/ecole/<int:school_id>/classe/<classe>")
@login_required
@role_required("enseignant")
def class_view(school_id, classe):
    teacher = current_teacher()
    if not assigned_schedules(teacher, school_id, classe):
        return jsonify({"error": "Cette classe ne vous est pas attribuée."}), 403
    students = Student.query.filter_by(ecole_id=school_id, classe=classe).all()
    return render_template("teacher/class_view.html", students=students,
                            school_id=school_id, classe=classe)


@teacher_bp.route("/appel", methods=["POST"])
@login_required
@role_required("enseignant")
def take_attendance():
    """Enregistre l'appel du jour ; notifie le parent en cas d'absence."""
    data = request.get_json(silent=True) or {}
    teacher = current_teacher()
    try:
        school_id = int(data.get("school_id"))
    except (TypeError, ValueError):
        return jsonify({"error": "Établissement invalide."}), 400
    allowed_classes = {
        schedule.classe for schedule in assigned_schedules(teacher, school_id) if schedule.classe
    }
    if not allowed_classes:
        return jsonify({"error": "Établissement non autorisé."}), 403
    presences = data.get("presences")
    if not isinstance(presences, list) or not presences:
        return jsonify({"error": "Aucune présence à enregistrer."}), 400
    validated = []
    for entry in presences:
        if not isinstance(entry, dict):
            return jsonify({"error": "Données de présence invalides."}), 400
        try:
            student_id = int(entry.get("student_id"))
        except (TypeError, ValueError):
            return jsonify({"error": "Identifiant élève invalide."}), 400
        statut = entry.get("statut")
        student = Student.query.filter_by(id=student_id, ecole_id=school_id).first()
        if not student or student.classe not in allowed_classes or statut not in {"present", "absent", "retard"}:
            return jsonify({"error": "Données de présence invalides."}), 400
        validated.append((student, statut))

    for student, statut in validated:
        presence = Presence.query.filter_by(
            student_id=student.id, school_id=school_id, date=date.today()
        ).first()
        if presence:
            presence.statut = statut
        else:
            db.session.add(Presence(
                student_id=student.id, school_id=school_id, date=date.today(), statut=statut
            ))
        if statut == "absent":
            notify(student.parent_id, f"Absence de {student.prenom} enregistrée aujourd'hui.")
    db.session.commit()
    return jsonify({"ok": True})


@teacher_bp.route("/notes", methods=["POST"])
@login_required
@role_required("enseignant")
def save_note():
    """Enregistre une note ; la moyenne de l'élève est recalculée à la volée (Student.moyenne)."""
    data = request.get_json(silent=True) or {}
    teacher = current_teacher()
    try:
        student_id = int(data.get("student_id"))
    except (TypeError, ValueError):
        return jsonify({"error": "Identifiant élève invalide."}), 400
    student = db.get_or_404(Student, student_id)
    try:
        value = float(data.get("note"))
    except (TypeError, ValueError):
        return jsonify({"error": "La note doit être un nombre."}), 400
    matiere = (data.get("matiere") or "").strip()
    if not can_teach(teacher, student, matiere):
        return jsonify({"error": "Cette classe ou cette matière ne vous est pas attribuée."}), 403
    if not 0 <= value <= 20 or not matiere or data.get("trimestre") not in {"T1", "T2", "T3"}:
        return jsonify({"error": "La note, la matière ou le trimestre est invalide."}), 400
    note = Note(student_id=student.id, teacher_id=teacher.id,
                matiere=matiere, trimestre=data["trimestre"], note=value)
    db.session.add(note)
    notify(student.parent_id, f"Nouvelle note en {matiere} ({data['trimestre']}) : {value}/20.")
    db.session.commit()
    return jsonify({"ok": True, "moyenne": student.moyenne(data["trimestre"])})


@teacher_bp.route("/signalement", methods=["POST"])
@login_required
@role_required("enseignant")
def send_remark():
    """Signalement ou remarque envoyée directement au parent (utilisée depuis l'onglet classe)."""
    data = request.get_json(silent=True) or {}
    teacher = current_teacher()
    try:
        student_id = int(data.get("student_id"))
    except (TypeError, ValueError):
        return jsonify({"error": "Identifiant élève invalide."}), 400
    student = db.get_or_404(Student, student_id)
    if not can_teach(teacher, student):
        return jsonify({"error": "Cette classe ne vous est pas attribuée."}), 403
    if data.get("type") not in {"remarque", "signalement"} or not (data.get("texte") or "").strip():
        return jsonify({"error": "Le type et le texte sont obligatoires."}), 400
    remark = Remark(student_id=student.id, teacher_id=teacher.id,
                     type=data["type"], texte=data["texte"], prive=data.get("prive", False))
    db.session.add(remark)
    prefix = "Signalement" if data["type"] == "signalement" else "Remarque"
    notify(student.parent_id, f"{prefix} de {current_user.full_name()} : {data['texte'][:80]}")
    db.session.commit()
    return jsonify({"ok": True})


@teacher_bp.route("/postuler", methods=["GET", "POST"])
@login_required
@role_required("enseignant")
def apply():
    if request.method == "POST":
        teacher = current_teacher()
        data = request.get_json(silent=True) or request.form
        try:
            school_id = int(data.get("ecole_id"))
        except (TypeError, ValueError):
            return jsonify({"error": "Sélectionnez un établissement valide."}), 400
        school = School.query.filter_by(
            id=school_id, validated=True, status="actif"
        ).first_or_404()
        if school in teacher.schools:
            return jsonify({"error": "Vous enseignez déjà dans cette école."}), 400
        if not (data.get("matieres") or "").strip():
            return jsonify({"error": "Veuillez renseigner au moins une matière."}), 400
        existing = TeacherApplication.query.filter_by(
            teacher_id=teacher.id, ecole_id=school.id, statut="pending").first()
        if existing:
            return jsonify({"error": "Une candidature est déjà en attente."}), 409
        app_ = TeacherApplication(teacher_id=teacher.id, ecole_id=school.id,
                                   matieres=data["matieres"], motivation=data.get("motivation", ""))
        db.session.add(app_)
        for admin in User.query.filter_by(ecole_id=school.id, role="admin", is_active_account=True):
            notify(admin.id, f"Nouvelle candidature de {current_user.full_name()} pour {school.nom}.")
        db.session.commit()
        return jsonify({"ok": True})
    schools = School.query.filter_by(validated=True).all()
    return render_template("teacher/apply.html", schools=schools)

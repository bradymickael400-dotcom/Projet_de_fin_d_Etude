from flask import Blueprint

school_admin_bp = Blueprint("school_admin", __name__, template_folder="../templates/admin")

from app.school_admin import routes  # noqa

from flask import Blueprint

superadmin_bp = Blueprint("superadmin", __name__, template_folder="../templates/superadmin")

from app.superadmin import routes  # noqa

from flask import Blueprint

news_bp = Blueprint("news", __name__, template_folder="../templates")

from app.news import routes  # noqa: E402,F401

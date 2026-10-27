from flask import render_template

from app.news import news_bp
from app.services.news import latest_news
from app.extensions import db
from app.models.school import School, SchoolPost


@news_bp.route("/actualites")
def index():
    return render_template("news/index.html", articles=latest_news(30))


@news_bp.route("/etablissements/<int:school_id>")
def school_publications(school_id):
    school = db.get_or_404(School, school_id)
    posts = SchoolPost.query.filter_by(
        school_id=school.id, visibility="public"
    ).order_by(SchoolPost.published_at.desc()).all()
    return render_template("news/school.html", school=school, posts=posts)

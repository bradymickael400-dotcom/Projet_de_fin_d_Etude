"""Actualités éducatives camerounaises collectées depuis des sources externes."""
from datetime import datetime, timezone

from app.extensions import db


class EducationNews(db.Model):
    __tablename__ = "education_news"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(300), nullable=False)
    summary = db.Column(db.Text, nullable=False, default="")
    url = db.Column(db.String(1000), nullable=False, unique=True, index=True)
    source = db.Column(db.String(120), nullable=False)
    category = db.Column(db.String(40), nullable=False, default="education")
    language = db.Column(db.String(5), nullable=False, default="fr")
    published_at = db.Column(db.DateTime(timezone=True), nullable=False, index=True)
    collected_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    relevance_score = db.Column(db.Integer, nullable=False, default=0)
    is_verified_source = db.Column(db.Boolean, nullable=False, default=False)

    __table_args__ = (
        db.CheckConstraint("language IN ('fr', 'en')", name="ck_news_language"),
        db.CheckConstraint(
            "category IN ('decision', 'etablissement', 'examen', 'enseignant', 'innovation', 'education')",
            name="ck_news_category",
        ),
        db.CheckConstraint("relevance_score >= 0", name="ck_news_score_positive"),
    )

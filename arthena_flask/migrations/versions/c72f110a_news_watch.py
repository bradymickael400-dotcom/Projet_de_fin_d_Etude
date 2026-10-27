"""education news watch

Revision ID: c72f110a
Revises: b41c9a77
"""
from alembic import op
import sqlalchemy as sa

revision = "c72f110a"
down_revision = "b41c9a77"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "education_news",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("url", sa.String(length=1000), nullable=False),
        sa.Column("source", sa.String(length=120), nullable=False),
        sa.Column("category", sa.String(length=40), nullable=False),
        sa.Column("language", sa.String(length=5), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("relevance_score", sa.Integer(), nullable=False),
        sa.Column("is_verified_source", sa.Boolean(), nullable=False),
        sa.CheckConstraint("language IN ('fr', 'en')", name="ck_news_language"),
        sa.CheckConstraint(
            "category IN ('decision', 'etablissement', 'examen', 'enseignant', 'innovation', 'education')",
            name="ck_news_category",
        ),
        sa.CheckConstraint("relevance_score >= 0", name="ck_news_score_positive"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("url"),
    )
    op.create_index("ix_education_news_url", "education_news", ["url"], unique=False)
    op.create_index("ix_education_news_published_at", "education_news", ["published_at"], unique=False)


def downgrade():
    op.drop_index("ix_education_news_published_at", table_name="education_news")
    op.drop_index("ix_education_news_url", table_name="education_news")
    op.drop_table("education_news")

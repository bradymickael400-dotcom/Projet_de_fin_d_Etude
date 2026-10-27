"""school community and public publications

Revision ID: f05c421d
Revises: e94b310c
"""
from alembic import op
import sqlalchemy as sa

revision = "f05c421d"
down_revision = "e94b310c"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "school_posts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("school_id", sa.Integer(), nullable=False),
        sa.Column("author_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=30), nullable=False),
        sa.Column("visibility", sa.String(length=20), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "category IN ('calendrier','evenement','communique','information')",
            name="ck_school_post_category",
        ),
        sa.CheckConstraint(
            "visibility IN ('public','communaute')",
            name="ck_school_post_visibility",
        ),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_school_posts_school_id", "school_posts", ["school_id"])


def downgrade():
    op.drop_index("ix_school_posts_school_id", table_name="school_posts")
    op.drop_table("school_posts")

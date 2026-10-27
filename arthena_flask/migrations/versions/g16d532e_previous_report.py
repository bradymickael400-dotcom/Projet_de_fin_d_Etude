"""previous school report for enrolments

Revision ID: g16d532e
Revises: f05c421d
"""
from alembic import op
import sqlalchemy as sa

revision = "g16d532e"
down_revision = "f05c421d"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("enrollment_requests") as batch:
        batch.add_column(sa.Column("ancien_bulletin", sa.String(length=255), nullable=True))
    op.execute(
        "UPDATE enrollment_requests SET ancien_bulletin='document-historique' "
        "WHERE ancien_bulletin IS NULL"
    )
    with op.batch_alter_table("enrollment_requests") as batch:
        batch.alter_column(
            "ancien_bulletin", existing_type=sa.String(length=255), nullable=False
        )


def downgrade():
    with op.batch_alter_table("enrollment_requests") as batch:
        batch.drop_column("ancien_bulletin")

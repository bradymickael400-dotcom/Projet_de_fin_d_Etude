"""complete school request and manager identity

Revision ID: e94b310c
Revises: d83a201b
"""
from alembic import op
import sqlalchemy as sa

revision = "e94b310c"
down_revision = "d83a201b"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("pending_school_requests") as batch:
        batch.add_column(sa.Column("latitude", sa.Float(), nullable=True))
        batch.add_column(sa.Column("longitude", sa.Float(), nullable=True))
        batch.add_column(sa.Column("manager_nom", sa.String(length=80), nullable=True))
        batch.add_column(sa.Column("manager_prenom", sa.String(length=80), nullable=True))
        batch.add_column(sa.Column("manager_phone", sa.String(length=30), nullable=True))
        batch.add_column(sa.Column("manager_password_hash", sa.String(length=255), nullable=True))
        batch.add_column(sa.Column("document_creation", sa.String(length=255), nullable=True))
        batch.add_column(sa.Column("document_autorisation", sa.String(length=255), nullable=True))


def downgrade():
    with op.batch_alter_table("pending_school_requests") as batch:
        batch.drop_column("document_autorisation")
        batch.drop_column("document_creation")
        batch.drop_column("manager_password_hash")
        batch.drop_column("manager_phone")
        batch.drop_column("manager_prenom")
        batch.drop_column("manager_nom")
        batch.drop_column("longitude")
        batch.drop_column("latitude")

"""school staff, tasks and complete enrolment files

Revision ID: d83a201b
Revises: c72f110a
"""
from alembic import op
import sqlalchemy as sa

revision = "d83a201b"
down_revision = "c72f110a"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint("ck_users_role", "users", type_="check")
    op.create_check_constraint(
        "ck_users_role", "users",
        "role IN ('parent','enseignant','admin','superadmin','intendante','censeur')",
    )
    with op.batch_alter_table("enrollment_requests") as batch:
        batch.add_column(sa.Column("age", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("motif_nouvelle_ecole", sa.Text(), nullable=True))
        batch.add_column(sa.Column("acte_naissance", sa.String(length=255), nullable=True))
        batch.add_column(sa.Column("documents_statut", sa.String(length=20), nullable=True))
        batch.add_column(sa.Column("documents_note", sa.Text(), nullable=True))
        batch.add_column(sa.Column("documents_checked_by", sa.Integer(), nullable=True))
        batch.create_foreign_key(
            "fk_enrolment_document_checker", "users", ["documents_checked_by"], ["id"]
        )
    op.execute("UPDATE enrollment_requests SET age=6 WHERE age IS NULL")
    op.execute("UPDATE enrollment_requests SET acte_naissance='document-historique' WHERE acte_naissance IS NULL")
    op.execute("UPDATE enrollment_requests SET documents_statut='pending' WHERE documents_statut IS NULL")
    with op.batch_alter_table("enrollment_requests") as batch:
        batch.alter_column("age", existing_type=sa.Integer(), nullable=False)
        batch.alter_column("acte_naissance", existing_type=sa.String(length=255), nullable=False)

    op.create_table(
        "school_tasks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("school_id", sa.Integer(), nullable=False),
        sa.Column("assigned_to_id", sa.Integer(), nullable=False),
        sa.Column("created_by_id", sa.Integer(), nullable=False),
        sa.Column("titre", sa.String(length=150), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("statut", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.Date(), nullable=True),
        sa.ForeignKeyConstraint(["assigned_to_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_school_tasks_school_id", "school_tasks", ["school_id"])
    op.create_index("ix_school_tasks_assigned_to_id", "school_tasks", ["assigned_to_id"])


def downgrade():
    op.drop_index("ix_school_tasks_assigned_to_id", table_name="school_tasks")
    op.drop_index("ix_school_tasks_school_id", table_name="school_tasks")
    op.drop_table("school_tasks")
    with op.batch_alter_table("enrollment_requests") as batch:
        batch.drop_constraint("fk_enrolment_document_checker", type_="foreignkey")
        batch.drop_column("documents_checked_by")
        batch.drop_column("documents_note")
        batch.drop_column("documents_statut")
        batch.drop_column("acte_naissance")
        batch.drop_column("motif_nouvelle_ecole")
        batch.drop_column("age")
    op.drop_constraint("ck_users_role", "users", type_="check")
    op.create_check_constraint(
        "ck_users_role", "users",
        "role IN ('parent','enseignant','admin','superadmin')",
    )

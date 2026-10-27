"""security and integrity constraints

Revision ID: b41c9a77
Revises: a83d7f0569e2
"""
from alembic import op
import sqlalchemy as sa

revision = "b41c9a77"
down_revision = "a83d7f0569e2"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("UPDATE payments SET reference = 'LEGACY-' || id WHERE reference IS NULL OR reference = ''")
    with op.batch_alter_table("users") as b:
        b.create_check_constraint("ck_users_role", "role IN ('parent','enseignant','admin','superadmin')")
    with op.batch_alter_table("schools") as b:
        b.create_check_constraint("ck_school_success", "taux_reussite BETWEEN 0 AND 100")
        b.create_check_constraint("ck_school_rating", "note_parents BETWEEN 0 AND 5")
        b.create_check_constraint("ck_school_effectif", "effectif >= 0")
    with op.batch_alter_table("school_classes") as b:
        b.create_unique_constraint("uq_school_class_name", ["school_id", "nom"])
    with op.batch_alter_table("students") as b:
        b.create_check_constraint("ck_student_pension_total", "pension_totale >= 0")
        b.create_check_constraint("ck_student_pension_paid", "pension_payee >= 0")
        b.create_check_constraint("ck_student_pension_balance", "pension_payee <= pension_totale")
    with op.batch_alter_table("notes") as b:
        b.create_check_constraint("ck_note_value", "note BETWEEN 0 AND 20")
        b.create_check_constraint("ck_note_term", "trimestre IN ('T1','T2','T3')")
    with op.batch_alter_table("presences") as b:
        b.create_unique_constraint("uq_daily_presence", ["student_id", "school_id", "date"])
        b.create_check_constraint("ck_presence_status", "statut IN ('present','absent','retard')")
    with op.batch_alter_table("payments") as b:
        b.alter_column("reference", existing_type=sa.String(60), type_=sa.String(100), nullable=False)
        b.add_column(sa.Column("status", sa.String(20), nullable=False, server_default="pending"))
        b.create_unique_constraint("uq_payments_reference", ["reference"])
        b.create_check_constraint("ck_payment_amount", "montant > 0")
        b.create_check_constraint("ck_payment_status", "status IN ('pending','confirmed','failed')")
    with op.batch_alter_table("schedules") as b:
        b.create_unique_constraint(
            "uq_teacher_schedule_slot", ["teacher_id", "school_id", "jour", "heure", "classe"]
        )


def downgrade():
    with op.batch_alter_table("schedules") as b:
        b.drop_constraint("uq_teacher_schedule_slot", type_="unique")
    with op.batch_alter_table("payments") as b:
        b.drop_constraint("ck_payment_status", type_="check")
        b.drop_constraint("ck_payment_amount", type_="check")
        b.drop_constraint("uq_payments_reference", type_="unique")
        b.drop_column("status")
        b.alter_column("reference", existing_type=sa.String(100), type_=sa.String(60), nullable=True)
    with op.batch_alter_table("presences") as b:
        b.drop_constraint("ck_presence_status", type_="check")
        b.drop_constraint("uq_daily_presence", type_="unique")
    with op.batch_alter_table("notes") as b:
        b.drop_constraint("ck_note_term", type_="check")
        b.drop_constraint("ck_note_value", type_="check")
    with op.batch_alter_table("students") as b:
        b.drop_constraint("ck_student_pension_balance", type_="check")
        b.drop_constraint("ck_student_pension_paid", type_="check")
        b.drop_constraint("ck_student_pension_total", type_="check")
    with op.batch_alter_table("school_classes") as b:
        b.drop_constraint("uq_school_class_name", type_="unique")
    with op.batch_alter_table("schools") as b:
        b.drop_constraint("ck_school_effectif", type_="check")
        b.drop_constraint("ck_school_rating", type_="check")
        b.drop_constraint("ck_school_success", type_="check")
    with op.batch_alter_table("users") as b:
        b.drop_constraint("ck_users_role", type_="check")

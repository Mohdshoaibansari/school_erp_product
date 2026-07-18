"""Homework module — tables, RLS, C-04 permission extension

Revision ID: 006_homework_module
Revises: 005_fees_module
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "006_homework_module"
down_revision = "005_fees_module"
branch_labels = None
depends_on = None

def upgrade():
    # Tables
    for tbl, cols in [
        ("homework", [sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
            sa.Column("client_id", UUID, sa.ForeignKey("client.id"), nullable=False),
            sa.Column("institution_id", UUID, sa.ForeignKey("institution.id"), nullable=False),
            sa.Column("title", sa.Text, nullable=False), sa.Column("description", sa.Text),
            sa.Column("subject", sa.Text), sa.Column("grade_level", sa.Text), sa.Column("section", sa.Text),
            sa.Column("due_date", sa.Date, nullable=False), sa.Column("max_score", sa.Integer),
            sa.Column("status", sa.String(20), nullable=False, server_default="active"),
            sa.Column("assigned_by", UUID, sa.ForeignKey("app_user.id")),
            sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"))]),
        ("submission", [sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
            sa.Column("client_id", UUID, sa.ForeignKey("client.id"), nullable=False),
            sa.Column("institution_id", UUID, sa.ForeignKey("institution.id"), nullable=False),
            sa.Column("homework_id", UUID, sa.ForeignKey("homework.id"), nullable=False),
            sa.Column("student_id", UUID, sa.ForeignKey("app_user.id"), nullable=False),
            sa.Column("content", sa.Text), sa.Column("status", sa.String(20), nullable=False, server_default="submitted"),
            sa.Column("submitted_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
            sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"))]),
        ("grade", [sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
            sa.Column("client_id", UUID, sa.ForeignKey("client.id"), nullable=False),
            sa.Column("institution_id", UUID, sa.ForeignKey("institution.id"), nullable=False),
            sa.Column("submission_id", UUID, sa.ForeignKey("submission.id"), nullable=False),
            sa.Column("score", sa.Integer, nullable=False), sa.Column("max_score", sa.Integer),
            sa.Column("feedback", sa.Text), sa.Column("graded_by", UUID, sa.ForeignKey("app_user.id")),
            sa.Column("graded_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
            sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"))]),
    ]:
        op.create_table(tbl, *cols)

    # RLS
    for tbl in ["homework", "submission", "grade"]:
        op.execute(f"ALTER TABLE {tbl} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {tbl} FORCE ROW LEVEL SECURITY")
        for op_type, policy in [("SELECT", f"CREATE POLICY {tbl}_sel ON {tbl} FOR SELECT USING (is_platform_owner() OR client_id = current_client_id())"),
            ("INSERT", f"CREATE POLICY {tbl}_ins ON {tbl} FOR INSERT WITH CHECK (is_platform_owner() OR client_id = current_client_id())"),
            ("UPDATE", f"CREATE POLICY {tbl}_upd ON {tbl} FOR UPDATE USING (is_platform_owner() OR client_id = current_client_id()) WITH CHECK (is_platform_owner() OR client_id = current_client_id())"),
            ("DELETE", f"CREATE POLICY {tbl}_del ON {tbl} FOR DELETE USING (is_platform_owner())")]:
            op.execute(policy)

    # C-04 permissions
    for name, desc, resource, action in [
        ("homework.read", "View homework", "homework", "read"),
        ("homework.create", "Create homework", "homework", "create"),
        ("homework.update", "Update homework", "homework", "update"),
        ("homework.delete", "Delete homework", "homework", "delete"),
        ("homework.close", "Close homework", "homework", "close"),
        ("submission.read", "View submissions", "submission", "read"),
        ("submission.create", "Submit homework", "submission", "create"),
        ("grade.read", "View grades", "grade", "read"),
        ("grade.create", "Grade a submission", "grade", "create"),
        ("grade.update", "Update a grade", "grade", "update"),
    ]:
        op.execute(sa.text(f"INSERT INTO permission (id, name, description, resource, action) VALUES (gen_random_uuid(), '{name}', '{desc}', '{resource}', '{action}') ON CONFLICT (name) DO NOTHING"))

    rp = "INSERT INTO role_permission (id, role_id, permission_id) SELECT gen_random_uuid(), r.id, p.id FROM role r, permission p WHERE r.name = '{role}' AND p.name = '{perm}' ON CONFLICT (role_id, permission_id) DO NOTHING"
    for perm in ["homework.read", "homework.create", "homework.update", "homework.delete", "homework.close", "submission.read", "grade.read", "grade.create", "grade.update"]:
        op.execute(sa.text(rp.format(role="Teacher", perm=perm)))
    for perm in ["homework.read", "submission.read", "grade.read"]:
        for role in ["Admin", "Principal", "HOD"]:
            op.execute(sa.text(rp.format(role=role, perm=perm)))
    for perm in ["homework.read", "submission.read", "submission.create", "grade.read"]:
        op.execute(sa.text(rp.format(role="Student", perm=perm)))

def downgrade():
    op.drop_table("grade"); op.drop_table("submission"); op.drop_table("homework")

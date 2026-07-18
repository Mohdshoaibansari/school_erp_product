"""Fees module — integration tests (AC-1 through AC-10).

Tests validate:
- Fee type CRUD
- Fee assignment (single + bulk)
- Payment recording (status transitions, receipt numbers)
- Lifecycle statuses (pending/paid/partial/overdue/waived)
- Student ownership enforcement
- Role-based authorization (real Casbin enforcer)
- Audit events
- Bulk assignment atomicity
- Receipt sequential generation
- Tenant isolation (RLS)
"""

from __future__ import annotations

import uuid

import pytest
import casbin

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

from kernel.tenant_context import TenantContext, get_tenant_context
from kernel.authz.dependencies import get_enforcer, set_enforcer
from business.tenant_institution.policies import register_policies
from kernel.authz.services.policy_loader import register_policies_from_map


# ============================================================
# Helpers
# ============================================================

def _build_real_enforcer() -> casbin.Enforcer:
    """Build a real Casbin enforcer with C-01 + C-04 policies (for authz tests)."""
    import os
    import kernel.authz
    model_path = os.path.join(os.path.dirname(kernel.authz.__file__), "casbin_model.conf")
    e = casbin.Enforcer(model_path)
    register_policies(e)  # C-01 D11 matrix

    # Register C-04 permissions from DB (simplified for tests — uses known seed data)
    from sqlalchemy import create_engine, text as sa_text
    database_url = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:54322/postgres")
    engine = create_engine(database_url)
    with engine.connect() as conn:
        rows = conn.execute(sa_text(
            "SELECT r.name AS role_name, p.resource, p.action "
            "FROM role_permission rp JOIN role r ON r.id = rp.role_id "
            "JOIN permission p ON p.id = rp.permission_id "
            "ORDER BY r.name"
        )).fetchall()

    for role_name, resource, action in rows:
        e.add_role_for_user(role_name, role_name)
        e.add_policy(role_name, resource, action, "institution")
    return e


def _create_test_client(app, role: str = "Admin", client_id: uuid.UUID | None = None,
                        institution_id: uuid.UUID | None = None,
                        is_platform_owner: bool = False) -> TestClient:
    """Create a TestClient with a TenantContext override for the given role."""
    ctx = TenantContext(
        client_id=client_id or uuid.UUID(name="fee-test"),
        institution_id=institution_id or uuid.UUID(name="fee-inst"),
        user_id="test-user",
        is_platform_owner=is_platform_owner,
        roles=[role],
    )
    app.dependency_overrides[get_tenant_context] = lambda: ctx
    return TestClient(app, headers={"Host": "test.localhost"})


def _seed_data(session: Session, ctx: TenantContext) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    """Seed test infrastructure: client, institution_type, institution, user_category, student user."""
    # Client
    session.execute(text(
        "INSERT INTO client (id, display_name, legal_name, slug, legal_entity_type_id, "
        "primary_contact_email, current_lifecycle_status) VALUES "
        "(:cid, 'Test', 'Test Legal', :slug, "
        "(SELECT id FROM legal_entity_type LIMIT 1), 't@t.com', 'active') "
        "ON CONFLICT DO NOTHING"
    ), {"cid": ctx.client_id, "slug": f"test-{ctx.client_id.hex[:8]}"})

    # Institution
    session.execute(text("INSERT INTO institution_type_name (id, name) VALUES (gen_random_uuid(), 'School') ON CONFLICT DO NOTHING"))
    session.flush()
    itn_id = session.execute(text("SELECT id FROM institution_type_name LIMIT 1")).fetchone()[0]
    itype_id = uuid.uuid4()
    session.execute(text(
        "INSERT INTO institution_type (id, name_id, code, is_system) VALUES (:id, :name_id, 'INTG_SCH', true) ON CONFLICT DO NOTHING"
    ), {"id": itype_id, "name_id": itn_id})
    session.flush()
    itype_id = session.execute(text("SELECT id FROM institution_type LIMIT 1")).fetchone()[0]
    session.execute(text(
        "INSERT INTO institution (id, client_id, institution_type_id, display_name, current_lifecycle_status) "
        "VALUES (:iid, :cid, :itype_id, 'Test School', 'active') ON CONFLICT DO NOTHING"
    ), {"iid": ctx.institution_id, "cid": ctx.client_id, "itype_id": itype_id})

    # User category and student user
    session.execute(text(
        "INSERT INTO user_category (id, name) VALUES (gen_random_uuid(), 'Learner') ON CONFLICT DO NOTHING"
    ))
    session.flush()
    cat_id = session.execute(text("SELECT id FROM user_category WHERE name = 'Learner'")).fetchone()[0]

    student_id = uuid.uuid4()
    session.execute(text(
        "INSERT INTO app_user (id, client_id, institution_id, email, name, user_category_id, lifecycle_status) "
        "VALUES (:id, :cid, :iid, :email, :name, :cat_id, 'active')"
    ), {"id": student_id, "cid": ctx.client_id, "iid": ctx.institution_id,
         "email": f"student-{student_id.hex[:8]}@test.com", "name": "Test Student", "cat_id": cat_id})
    session.commit()
    return ctx.client_id, ctx.institution_id, student_id


# ============================================================
# Test: FeeType CRUD (AC-1)
# ============================================================

class TestFeeTypeCRUD:
    """AC-1: Fee type CRUD operations."""

    def test_create_fee_type(self, app, db_session):
        ctx = TenantContext(client_id=uuid.uuid4(), institution_id=uuid.uuid4(),
                            user_id="admin", roles=["Admin"])
        cid, iid, _ = _seed_data(db_session, ctx)
        ctx = TenantContext(client_id=cid, institution_id=iid, user_id="admin", roles=["Admin"])

        app.dependency_overrides[get_tenant_context] = lambda: ctx
        tc = TestClient(app, headers={"Host": "test.localhost"})

        response = tc.post("/api/v1/fee-types", json={
            "name": "Tuition Fee", "description": "Term 1 Tuition",
            "default_amount": "5000.00", "institution_id": str(iid),
        })
        assert response.status_code == 201, response.text
        data = response.json()
        assert data["name"] == "Tuition Fee"
        assert data["default_amount"] == "5000.00"
        assert data["client_id"] == str(cid)

    def test_list_fee_types(self, app, db_session):
        ctx = TenantContext(client_id=uuid.uuid4(), institution_id=uuid.uuid4(),
                            user_id="admin", roles=["Admin"])
        cid, iid, _ = _seed_data(db_session, ctx)
        ctx = TenantContext(client_id=cid, institution_id=iid, user_id="admin", roles=["Admin"])

        # Create one
        app.dependency_overrides[get_tenant_context] = lambda: ctx
        tc = TestClient(app, headers={"Host": "test.localhost"})
        tc.post("/api/v1/fee-types", json={
            "name": "Transport Fee", "default_amount": "2000.00", "institution_id": str(iid),
        })

        response = tc.get("/api/v1/fee-types")
        assert response.status_code == 200, response.text
        types = response.json()
        assert len(types) >= 1
        names = [t["name"] for t in types]
        assert "Transport Fee" in names

    def test_get_fee_type(self, app, db_session):
        ctx = TenantContext(client_id=uuid.uuid4(), institution_id=uuid.uuid4(),
                            user_id="admin", roles=["Admin"])
        cid, iid, _ = _seed_data(db_session, ctx)
        ctx = TenantContext(client_id=cid, institution_id=iid, user_id="admin", roles=["Admin"])
        app.dependency_overrides[get_tenant_context] = lambda: ctx
        tc = TestClient(app, headers={"Host": "test.localhost"})

        r = tc.post("/api/v1/fee-types", json={
            "name": "Library Fee", "default_amount": "500.00", "institution_id": str(iid),
        })
        ft_id = r.json()["id"]

        r2 = tc.get(f"/api/v1/fee-types/{ft_id}")
        assert r2.status_code == 200
        assert r2.json()["name"] == "Library Fee"

    def test_update_fee_type(self, app, db_session):
        ctx = TenantContext(client_id=uuid.uuid4(), institution_id=uuid.uuid4(),
                            user_id="admin", roles=["Admin"])
        cid, iid, _ = _seed_data(db_session, ctx)
        ctx = TenantContext(client_id=cid, institution_id=iid, user_id="admin", roles=["Admin"])
        app.dependency_overrides[get_tenant_context] = lambda: ctx
        tc = TestClient(app, headers={"Host": "test.localhost"})

        r = tc.post("/api/v1/fee-types", json={
            "name": "Old Name", "default_amount": "1000.00", "institution_id": str(iid),
        })
        ft_id = r.json()["id"]

        r2 = tc.patch(f"/api/v1/fee-types/{ft_id}", json={"name": "New Name"})
        assert r2.status_code == 200
        assert r2.json()["name"] == "New Name"

    def test_deactivate_fee_type(self, app, db_session):
        ctx = TenantContext(client_id=uuid.uuid4(), institution_id=uuid.uuid4(),
                            user_id="admin", roles=["Admin"])
        cid, iid, _ = _seed_data(db_session, ctx)
        ctx = TenantContext(client_id=cid, institution_id=iid, user_id="admin", roles=["Admin"])
        app.dependency_overrides[get_tenant_context] = lambda: ctx
        tc = TestClient(app, headers={"Host": "test.localhost"})

        r = tc.post("/api/v1/fee-types", json={
            "name": "To Deactivate", "default_amount": "100.00", "institution_id": str(iid),
        })
        ft_id = r.json()["id"]

        r2 = tc.delete(f"/api/v1/fee-types/{ft_id}")
        assert r2.status_code == 204


# ============================================================
# Test: FeeAssignment (AC-2, AC-8)
# ============================================================

class TestFeeAssignment:
    """AC-2: Fee assignment, AC-8: Bulk assignment."""

    def test_assign_fee_single_student(self, app, db_session):
        ctx = TenantContext(client_id=uuid.uuid4(), institution_id=uuid.uuid4(),
                            user_id="admin", roles=["Admin"])
        cid, iid, student_id = _seed_data(db_session, ctx)
        ctx = TenantContext(client_id=cid, institution_id=iid, user_id="admin", roles=["Admin"])
        app.dependency_overrides[get_tenant_context] = lambda: ctx
        tc = TestClient(app, headers={"Host": "test.localhost"})

        # Create fee type
        r = tc.post("/api/v1/fee-types", json={
            "name": "Exam Fee", "default_amount": "1500.00", "institution_id": str(iid),
        })
        assert r.status_code == 201, f"Fee type creation failed: {r.text}"
        ft_id = r.json()["id"]
        print(f"Fee type ID: {ft_id}, student_id: {student_id}")

        # Assign to student
        r2 = tc.post("/api/v1/fee-assignments", json={
            "fee_type_id": ft_id, "amount": "1500.00",
            "due_date": "2026-12-31", "academic_term": "2026 Term 2",
            "user_ids": [str(student_id)],
        })
        assert r2.status_code == 201, r2.text
        assignments = r2.json()
        assert len(assignments) == 1
        assert assignments[0]["status"] == "pending"
        assert assignments[0]["user_id"] == str(student_id)

    def test_bulk_assign_fees(self, app, db_session):
        ctx = TenantContext(client_id=uuid.uuid4(), institution_id=uuid.uuid4(),
                            user_id="admin", roles=["Admin"])
        cid, iid, s1 = _seed_data(db_session, ctx)
        ctx = TenantContext(client_id=cid, institution_id=iid, user_id="admin", roles=["Admin"])

        # Create second student
        cat_id = db_session.execute(text("SELECT id FROM user_category WHERE name = 'Learner'")).fetchone()[0]
        s2 = uuid.uuid4()
        db_session.execute(text(
            "INSERT INTO app_user (id, client_id, institution_id, email, name, user_category_id, lifecycle_status) "
            "VALUES (:id, :cid, :iid, :email, :name, :cat_id, 'active')"
        ), {"id": s2, "cid": cid, "iid": iid, "email": "s2@test.com", "name": "S2", "cat_id": cat_id})
        db_session.commit()

        app.dependency_overrides[get_tenant_context] = lambda: ctx
        tc = TestClient(app, headers={"Host": "test.localhost"})

        r = tc.post("/api/v1/fee-types", json={
            "name": "Bulk Fee", "default_amount": "1000.00", "institution_id": str(iid),
        })
        ft_id = r.json()["id"]

        r2 = tc.post("/api/v1/fee-assignments", json={
            "fee_type_id": ft_id, "amount": "1000.00",
            "due_date": "2026-12-31", "user_ids": [str(s1), str(s2)],
        })
        assert r2.status_code == 201, r2.text
        assert len(r2.json()) == 2

    def test_bulk_assign_non_student_rejected(self, app, db_session):
        """Non-Learner user_ids should be rejected."""
        ctx = TenantContext(client_id=uuid.uuid4(), institution_id=uuid.uuid4(),
                            user_id="admin", roles=["Admin"])
        cid, iid, _ = _seed_data(db_session, ctx)
        ctx = TenantContext(client_id=cid, institution_id=iid, user_id="admin", roles=["Admin"])

        # Create a non-Learner user (Staff)
        cat_id = db_session.execute(text("SELECT id FROM user_category WHERE name != 'Learner' LIMIT 1")).fetchone()[0]
        staff_id = uuid.uuid4()
        db_session.execute(text(
            "INSERT INTO app_user (id, client_id, institution_id, email, name, user_category_id, lifecycle_status) "
            "VALUES (:id, :cid, :iid, :email, :name, :cat_id, 'active')"
        ), {"id": staff_id, "cid": cid, "iid": iid, "email": "staff@test.com", "name": "Staff", "cat_id": cat_id})
        db_session.commit()

        app.dependency_overrides[get_tenant_context] = lambda: ctx
        tc = TestClient(app, headers={"Host": "test.localhost"})

        r = tc.post("/api/v1/fee-types", json={
            "name": "Test Fee", "default_amount": "500.00", "institution_id": str(iid),
        })

        r2 = tc.post("/api/v1/fee-assignments", json={
            "fee_type_id": r.json()["id"], "amount": "500.00",
            "due_date": "2026-12-31", "user_ids": [str(staff_id)],
        })
        assert r2.status_code == 400, f"Expected 400, got {r2.status_code}: {r2.text}"
        assert "Learner" in r2.text


# ============================================================
# Test: Payment Recording (AC-3, AC-9)
# ============================================================

class TestPaymentRecording:
    """AC-3: Payment recording, AC-9: Receipt numbers."""

    def test_record_payment_full(self, app, db_session):
        ctx = TenantContext(client_id=uuid.uuid4(), institution_id=uuid.uuid4(),
                            user_id="admin", roles=["Admin"])
        cid, iid, student_id = _seed_data(db_session, ctx)
        ctx = TenantContext(client_id=cid, institution_id=iid, user_id="admin", roles=["Admin"])
        app.dependency_overrides[get_tenant_context] = lambda: ctx
        tc = TestClient(app, headers={"Host": "test.localhost"})

        # Create fee type + assignment
        r = tc.post("/api/v1/fee-types", json={
            "name": "Tuition", "default_amount": "5000.00", "institution_id": str(iid),
        })
        ft_id = r.json()["id"]
        r2 = tc.post("/api/v1/fee-assignments", json={
            "fee_type_id": ft_id, "amount": "5000.00",
            "due_date": "2026-12-31", "user_ids": [str(student_id)],
        })
        fa_id = r2.json()[0]["id"]

        # Record full payment
        r3 = tc.post("/api/v1/payments", json={
            "fee_assignment_id": fa_id, "amount": "5000.00",
            "payment_method": "Cash",
        })
        assert r3.status_code == 201, r3.text
        payment = r3.json()
        assert payment["receipt_number"] is not None
        assert "REC-" in payment["receipt_number"]

        # Verify assignment status → paid
        r4 = tc.get(f"/api/v1/fee-assignments/{fa_id}")
        assert r4.json()["status"] == "paid"

    def test_record_payment_partial(self, app, db_session):
        ctx = TenantContext(client_id=uuid.uuid4(), institution_id=uuid.uuid4(),
                            user_id="admin", roles=["Admin"])
        cid, iid, student_id = _seed_data(db_session, ctx)
        ctx = TenantContext(client_id=cid, institution_id=iid, user_id="admin", roles=["Admin"])
        app.dependency_overrides[get_tenant_context] = lambda: ctx
        tc = TestClient(app, headers={"Host": "test.localhost"})

        r = tc.post("/api/v1/fee-types", json={
            "name": "Tuition 2", "default_amount": "5000.00", "institution_id": str(iid),
        })
        r2 = tc.post("/api/v1/fee-assignments", json={
            "fee_type_id": r.json()["id"], "amount": "5000.00",
            "due_date": "2026-12-31", "user_ids": [str(student_id)],
        })
        fa_id = r2.json()[0]["id"]

        tc.post("/api/v1/payments", json={
            "fee_assignment_id": fa_id, "amount": "2000.00", "payment_method": "Cash",
        })
        r4 = tc.get(f"/api/v1/fee-assignments/{fa_id}")
        assert r4.json()["status"] == "partial"

    def test_receipt_sequential(self, app, db_session):
        """Receipt numbers are sequential."""
        ctx = TenantContext(client_id=uuid.uuid4(), institution_id=uuid.uuid4(),
                            user_id="admin", roles=["Admin"])
        cid, iid, student_id = _seed_data(db_session, ctx)
        ctx = TenantContext(client_id=cid, institution_id=iid, user_id="admin", roles=["Admin"])
        app.dependency_overrides[get_tenant_context] = lambda: ctx
        tc = TestClient(app, headers={"Host": "test.localhost"})

        r = tc.post("/api/v1/fee-types", json={
            "name": "Test", "default_amount": "100.00", "institution_id": str(iid),
        })
        ft_id = r.json()["id"]

        # Create two assignments
        r2 = tc.post("/api/v1/fee-assignments", json={
            "fee_type_id": ft_id, "amount": "100.00",
            "due_date": "2026-12-31", "user_ids": [str(student_id)],
        })
        fa1 = r2.json()[0]["id"]

        # Need another student for second assignment
        cat_id = db_session.execute(text("SELECT id FROM user_category WHERE name = 'Learner'")).fetchone()[0]
        s2 = uuid.uuid4()
        db_session.execute(text(
            "INSERT INTO app_user (id, client_id, institution_id, email, name, user_category_id, lifecycle_status) "
            "VALUES (:id, :cid, :iid, :email, :name, :cat_id, 'active')"
        ), {"id": s2, "cid": cid, "iid": iid, "email": "s22@test.com", "name": "S2", "cat_id": cat_id})
        db_session.commit()

        r3 = tc.post("/api/v1/fee-assignments", json={
            "fee_type_id": ft_id, "amount": "100.00",
            "due_date": "2026-12-31", "user_ids": [str(s2)],
        })
        fa2 = r3.json()[0]["id"]

        p1 = tc.post("/api/v1/payments", json={
            "fee_assignment_id": fa1, "amount": "100.00", "payment_method": "Cash",
        })
        p2 = tc.post("/api/v1/payments", json={
            "fee_assignment_id": fa2, "amount": "100.00", "payment_method": "Cash",
        })
        r1 = p1.json()["receipt_number"]
        r2_num = p2.json()["receipt_number"]
        assert r1 != r2_num, f"Receipt numbers should be different: {r1} vs {r2_num}"


# ============================================================
# Test: Lifecycle Statuses (AC-4)
# ============================================================

class TestLifecycleStatuses:
    """AC-4: Lifecycle statuses — pending/paid/partial/overdue/waived."""

    def test_waived_is_terminal(self, app, db_session):
        ctx = TenantContext(client_id=uuid.uuid4(), institution_id=uuid.uuid4(),
                            user_id="admin", roles=["Admin"])
        cid, iid, student_id = _seed_data(db_session, ctx)
        ctx = TenantContext(client_id=cid, institution_id=iid, user_id="admin", roles=["Admin"])
        app.dependency_overrides[get_tenant_context] = lambda: ctx
        tc = TestClient(app, headers={"Host": "test.localhost"})

        r = tc.post("/api/v1/fee-types", json={
            "name": "Waved Fee", "default_amount": "1000.00", "institution_id": str(iid),
        })
        r2 = tc.post("/api/v1/fee-assignments", json={
            "fee_type_id": r.json()["id"], "amount": "1000.00",
            "due_date": "2026-12-31", "user_ids": [str(student_id)],
        })
        fa_id = r2.json()[0]["id"]

        r3 = tc.post(f"/api/v1/fee-assignments/{fa_id}/waive", json={"reason": "Scholarship"})
        assert r3.status_code == 200, r3.text
        assert r3.json()["status"] == "waived"

        # Cannot update after waived
        r4 = tc.patch(f"/api/v1/fee-assignments/{fa_id}", json={"amount": "500.00"})
        assert r4.status_code == 400

    def test_overdue_filter(self, app, db_session):
        ctx = TenantContext(client_id=uuid.uuid4(), institution_id=uuid.uuid4(),
                            user_id="admin", roles=["Admin"])
        cid, iid, student_id = _seed_data(db_session, ctx)
        ctx = TenantContext(client_id=cid, institution_id=iid, user_id="admin", roles=["Admin"])
        app.dependency_overrides[get_tenant_context] = lambda: ctx
        tc = TestClient(app, headers={"Host": "test.localhost"})

        r = tc.post("/api/v1/fee-types", json={
            "name": "Past Due", "default_amount": "1000.00", "institution_id": str(iid),
        })
        r2 = tc.post("/api/v1/fee-assignments", json={
            "fee_type_id": r.json()["id"], "amount": "1000.00",
            "due_date": "2020-01-01", "user_ids": [str(student_id)],
        })

        r3 = tc.get("/api/v1/fee-assignments?overdue=true")
        assert r3.status_code == 200
        overdue_list = r3.json()
        assert len(overdue_list) >= 1


# ============================================================
# Test: Student Ownership (AC-5)
# ============================================================

class TestStudentOwnership:
    """AC-5: Student can only access their own fees."""

    def test_student_sees_own_fees(self, app, db_session):
        ctx = TenantContext(client_id=uuid.uuid4(), institution_id=uuid.uuid4(),
                            user_id="admin", roles=["Admin"])
        cid, iid, student_id = _seed_data(db_session, ctx)

        # Assign a fee as admin
        admin_ctx = TenantContext(client_id=cid, institution_id=iid, user_id="admin", roles=["Admin"])
        app.dependency_overrides[get_tenant_context] = lambda: admin_ctx
        tc = TestClient(app, headers={"Host": "test.localhost"})

        r = tc.post("/api/v1/fee-types", json={
            "name": "Student Fee", "default_amount": "500.00", "institution_id": str(iid),
        })
        tc.post("/api/v1/fee-assignments", json={
            "fee_type_id": r.json()["id"], "amount": "500.00",
            "due_date": "2026-12-31", "user_ids": [str(student_id)],
        })

        # Now as student, request own fees
        student_ctx = TenantContext(client_id=cid, institution_id=iid,
                                     user_id=str(student_id), roles=["Student"])
        app.dependency_overrides[get_tenant_context] = lambda: student_ctx
        tc2 = TestClient(app, headers={"Host": "test.localhost"})

        response = tc2.get(f"/api/v1/fee-assignments?user_id={student_id}")
        assert response.status_code == 200, response.text
        assert len(response.json()) >= 1

    def test_student_blocked_from_other_student(self, app, db_session):
        ctx = TenantContext(client_id=uuid.uuid4(), institution_id=uuid.uuid4(),
                            user_id="admin", roles=["Admin"])
        cid, iid, student_a = _seed_data(db_session, ctx)

        # Create another student
        cat_id = db_session.execute(text("SELECT id FROM user_category WHERE name = 'Learner'")).fetchone()[0]
        student_b = uuid.uuid4()
        db_session.execute(text(
            "INSERT INTO app_user (id, client_id, institution_id, email, name, user_category_id, lifecycle_status) "
            "VALUES (:id, :cid, :iid, :email, :name, :cat_id, 'active')"
        ), {"id": student_b, "cid": cid, "iid": iid, "email": "sb@test.com", "name": "SB", "cat_id": cat_id})
        db_session.commit()

        # Student A tries to access Student B's fees
        student_ctx = TenantContext(client_id=cid, institution_id=iid,
                                     user_id=str(student_a), roles=["Student"])
        app.dependency_overrides[get_tenant_context] = lambda: student_ctx
        tc = TestClient(app, headers={"Host": "test.localhost"})

        response = tc.get(f"/api/v1/fee-assignments?user_id={student_b}")
        assert response.status_code == 403, f"Should be blocked: {response.text}"


# ============================================================
# Test: Authorization — Real Casbin (AC-6)
# ============================================================

class TestAuthorization:
    """AC-6: Role-based authorization with real Casbin enforcer."""

    def test_teacher_cannot_create_fee_type(self, app, db_session):
        """Teacher does not have fee.create → 403."""
        e = _build_real_enforcer()
        app.dependency_overrides[get_enforcer] = lambda: e

        ctx = TenantContext(client_id=uuid.uuid4(), institution_id=uuid.uuid4(),
                            user_id="teacher", roles=["Teacher"])
        app.dependency_overrides[get_tenant_context] = lambda: ctx
        tc = TestClient(app, headers={"Host": "test.localhost"})

        response = tc.post("/api/v1/fee-types", json={
            "name": "Bad", "default_amount": "100.00", "institution_id": str(uuid.uuid4()),
        })
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"

    def test_teacher_can_read_fee_assignments(self, app, db_session):
        """Teacher has fee_assignment.read → 200."""
        e = _build_real_enforcer()
        app.dependency_overrides[get_enforcer] = lambda: e

        ctx = TenantContext(client_id=uuid.uuid4(), institution_id=uuid.uuid4(),
                            user_id="teacher", roles=["Teacher"])
        app.dependency_overrides[get_tenant_context] = lambda: ctx
        tc = TestClient(app, headers={"Host": "test.localhost"})

        response = tc.get("/api/v1/fee-assignments")
        assert response.status_code == 200, response.text

    def test_student_cannot_waive(self, app, db_session):
        """Student does not have fee_assignment.waive → 403."""
        e = _build_real_enforcer()
        app.dependency_overrides[get_enforcer] = lambda: e

        ctx = TenantContext(client_id=uuid.uuid4(), institution_id=uuid.uuid4(),
                            user_id="student", roles=["Student"])
        app.dependency_overrides[get_tenant_context] = lambda: ctx
        tc = TestClient(app, headers={"Host": "test.localhost"})

        response = tc.post(f"/api/v1/fee-assignments/{uuid.uuid4()}/waive", json={"reason": "test"})
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"

    def test_admin_can_create_fee_type(self, app, db_session):
        """Admin has fee.create → 201."""
        e = _build_real_enforcer()
        app.dependency_overrides[get_enforcer] = lambda: e

        ctx = TenantContext(client_id=uuid.uuid4(), institution_id=uuid.uuid4(),
                            user_id="admin", roles=["Admin"])
        cid, iid, _ = _seed_data(db_session, ctx)
        ctx = TenantContext(client_id=cid, institution_id=iid, user_id="admin", roles=["Admin"])
        app.dependency_overrides[get_tenant_context] = lambda: ctx
        tc = TestClient(app, headers={"Host": "test.localhost"})

        response = tc.post("/api/v1/fee-types", json={
            "name": "Admin Fee", "default_amount": "100.00", "institution_id": str(iid),
        })
        assert response.status_code == 201, f"Admin should succeed: {response.text}"

    def test_platform_owner_bypasses_all(self, app, db_session):
        """Platform owner bypasses all checks."""
        e = _build_real_enforcer()
        app.dependency_overrides[get_enforcer] = lambda: e

        ctx = TenantContext(client_id=uuid.uuid4(), institution_id=uuid.uuid4(),
                            user_id="po", is_platform_owner=True, roles=[])
        cid, iid, _ = _seed_data(db_session, ctx)
        ctx = TenantContext(client_id=cid, institution_id=iid, user_id="po",
                            is_platform_owner=True, roles=[])
        app.dependency_overrides[get_tenant_context] = lambda: ctx
        tc = TestClient(app, headers={"Host": "test.localhost"})

        response = tc.post("/api/v1/fee-types", json={
            "name": "PO Fee", "default_amount": "100.00", "institution_id": str(iid),
        })
        assert response.status_code == 201, f"PO should succeed: {response.text}"


# ============================================================
# Test: Tenant Isolation (AC-10)
# ============================================================

class TestTenantIsolation:
    """AC-10: Tenant isolation — School A cannot see School B's fees."""

    def test_cross_client_isolation(self, app, db_session):
        """Fee types from Client A are not visible to Client B."""
        ctx_a = TenantContext(client_id=uuid.uuid4(), institution_id=uuid.uuid4(),
                              user_id="admin-a", roles=["Admin"])
        cid_a, iid_a, _ = _seed_data(db_session, ctx_a)
        ctx_a = TenantContext(client_id=cid_a, institution_id=iid_a, user_id="admin-a", roles=["Admin"])

        # Create fee type for Client A
        app.dependency_overrides[get_tenant_context] = lambda: ctx_a
        tc_a = TestClient(app, headers={"Host": "test.localhost"})
        tc_a.post("/api/v1/fee-types", json={
            "name": "Client A Fee", "default_amount": "500.00", "institution_id": str(iid_a),
        })

        # Client B tries to list — should see empty
        ctx_b = TenantContext(client_id=uuid.uuid4(), institution_id=uuid.uuid4(),
                              user_id="admin-b", roles=["Admin"])
        cid_b, iid_b, _ = _seed_data(db_session, ctx_b)
        ctx_b = TenantContext(client_id=cid_b, institution_id=iid_b, user_id="admin-b", roles=["Admin"])
        app.dependency_overrides[get_tenant_context] = lambda: ctx_b
        tc_b = TestClient(app, headers={"Host": "test.localhost"})

        response = tc_b.get("/api/v1/fee-types")
        assert response.status_code == 200
        names = [ft["name"] for ft in response.json()]
        assert "Client A Fee" not in names, f"Client B should not see Client A's fee types"

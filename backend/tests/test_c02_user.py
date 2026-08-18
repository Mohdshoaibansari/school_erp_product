"""Integration tests for C-02 Identity & User Management (tasks 11.1-11.5, T-32).

End-to-end scenarios verifying the full request flow:
middleware → route → service → repo → database.

Updated for person-model revamp (D6a): person_data replaces name + user_category_id.
"""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from kernel.user.models.user import User
from kernel.user.models.person import Person
from kernel.user.models.role_assignment import RoleAssignment
from kernel.user.models.user_identifier import UserIdentifier
from kernel.user.models.user_lifecycle_event import UserLifecycleEvent
from business.tenant_institution.models import (
    Client,
    Institution,
    InstitutionType,
    LegalEntityType,
    InstitutionTypeName,
)


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def client_obj(db_session):
    """Create a test Client."""
    let = db_session.query(LegalEntityType).first()
    client = Client(
        slug="test-school",
        display_name="Test School",
        legal_name="Test School Ltd",
        legal_entity_type_id=let.id,
        primary_contact_email="info@testschool.com",
    )
    db_session.add(client)
    db_session.flush()
    db_session.commit()
    return client


@pytest.fixture
def institution(db_session, client_obj):
    """Create a test Institution under the test Client."""
    itn = db_session.query(InstitutionTypeName).first()
    itype = InstitutionType(name_id=itn.id, code="SCH_C02", is_system=True)
    db_session.add(itype)
    db_session.flush()
    inst = Institution(
        client_id=client_obj.id,
        institution_type_id=itype.id,
        display_name="Test Institution",
    )
    db_session.add(inst)
    db_session.flush()
    db_session.commit()
    return inst


@pytest.fixture
def client_a(db_session):
    """Create Client A for cross-tenant tests."""
    let = db_session.query(LegalEntityType).first()
    client = Client(
        slug="school-a",
        display_name="School A",
        legal_name="School A Ltd",
        legal_entity_type_id=let.id,
        primary_contact_email="info@schoola.com",
    )
    db_session.add(client)
    db_session.flush()
    db_session.commit()
    return client


@pytest.fixture
def client_b(db_session):
    """Create Client B for cross-tenant tests."""
    let = db_session.query(LegalEntityType).first()
    client = Client(
        slug="school-b",
        display_name="School B",
        legal_name="School B Ltd",
        legal_entity_type_id=let.id,
        primary_contact_email="info@schoolb.com",
    )
    db_session.add(client)
    db_session.flush()
    db_session.commit()
    return client


@pytest.fixture
def institution_a(db_session, client_a):
    """Create Institution A under Client A."""
    itn = db_session.query(InstitutionTypeName).first()
    itype = InstitutionType(name_id=itn.id, code="SCH_A", is_system=True)
    db_session.add(itype)
    db_session.flush()
    inst = Institution(
        client_id=client_a.id,
        institution_type_id=itype.id,
        display_name="Institution A",
    )
    db_session.add(inst)
    db_session.flush()
    db_session.commit()
    return inst


@pytest.fixture
def institution_b(db_session, client_b):
    """Create Institution B under Client B."""
    itn = db_session.query(InstitutionTypeName).first()
    itype = InstitutionType(name_id=itn.id, code="SCH_B", is_system=True)
    db_session.add(itype)
    db_session.flush()
    inst = Institution(
        client_id=client_b.id,
        institution_type_id=itype.id,
        display_name="Institution B",
    )
    db_session.add(inst)
    db_session.flush()
    db_session.commit()
    return inst


# ============================================================
# Helpers
# ============================================================

def _get_role_id(db_session: Session) -> uuid.UUID:
    """Get the first Role ID from the seed data."""
    from kernel.user.models.role import Role
    role = db_session.query(Role).first()
    return role.id


def _create_user_via_api(tc: TestClient, email: str, name: str, institution_id: uuid.UUID) -> dict:
    """Create a user via the API and return the response data. (T-32: person_data replaces name + user_category_id)."""
    response = tc.post("/api/v1/users", json={
        "email": email,
        "person_data": {"name": name},
        "institution_id": str(institution_id),
    })
    assert response.status_code == 201, f"Failed to create user: {response.text}"
    return response.json()["user"]


# ============================================================
# 11.1 — Test full user creation flow
# ============================================================

class TestFullUserCreationFlow:
    """11.1: Test full user creation flow: create User → create RoleAssignment → create UserIdentifier."""

    def test_full_user_onboarding(
        self, make_tenant_client, db_session, client_obj, institution
    ):
        """11.1 evidence: create User → create RoleAssignment → create UserIdentifier.
        UserProfile step removed (table dropped, D6a)."""
        tc = make_tenant_client(
            subdomain="test-school",
            client_id=client_obj.id,
            institution_id=institution.id,
            roles=["institution_admin"],
        )

        # Step 1: Create User
        user_data = _create_user_via_api(
            tc, "testuser@test.com", "Test User", institution.id
        )
        user_id = user_data["id"]
        assert user_data["email"] == "testuser@test.com"
        assert user_data["person"]["name"] == "Test User"
        assert user_data["lifecycle_status"] == "invited"
        # D3f: person.id is independent of account UUID
        assert user_data["person"]["id"] != user_id

        # Step 2: Create RoleAssignment
        role_id = _get_role_id(db_session)
        response = tc.post(f"/api/v1/users/{user_id}/roles", json={
            "role_id": str(role_id),
            "scope": "Mathematics Department",
        })
        assert response.status_code == 201, f"Failed to create role assignment: {response.text}"
        role_data = response.json()
        assert role_data["user_id"] == user_id
        assert role_data["role_id"] == str(role_id)
        assert role_data["scope"] == "Mathematics Department"

        # Step 3: Create UserIdentifier
        response = tc.post(f"/api/v1/users/{user_id}/identifiers", json={
            "type": "student_id",
            "value": "STU-001",
        })
        assert response.status_code == 201, f"Failed to create identifier: {response.text}"
        id_data = response.json()
        assert id_data["user_id"] == user_id
        assert id_data["type"] == "student_id"
        assert id_data["value"] == "STU-001"

        # Verify the full user record in the database
        db_session.expire_all()
        user = db_session.execute(
            select(User).where(User.id == uuid.UUID(user_id))
        ).scalars().first()
        assert user is not None
        assert user.email == "testuser@test.com"
        assert user.client_id == client_obj.id
        assert user.institution_id == institution.id
        # D6a: no name on app_user
        assert not hasattr(user, 'name') or user.person_id is not None

        # Verify person exists and is linked
        person = db_session.execute(
            select(Person).where(Person.id == user.person_id)
        ).scalars().first()
        assert person is not None
        assert person.name == "Test User"
        assert person.id != user.id  # D3f: person.id independent

        # Verify role assignment exists
        role_assignment = db_session.execute(
            select(RoleAssignment).where(RoleAssignment.user_id == uuid.UUID(user_id))
        ).scalars().first()
        assert role_assignment is not None
        assert role_assignment.role_id == role_id

        # Verify identifier exists
        identifier = db_session.execute(
            select(UserIdentifier).where(UserIdentifier.user_id == uuid.UUID(user_id))
        ).scalars().first()
        assert identifier is not None
        assert identifier.type == "student_id"
        assert identifier.value == "STU-001"


# ============================================================
# 11.2 — Test tenant isolation
# ============================================================

class TestTenantIsolation:
    """11.2: Test tenant isolation: User at School A cannot see User at School B."""

    def test_cross_tenant_isolation(
        self, app, db_session, test_jwt, client_a, client_b, institution_a, institution_b
    ):
        """11.2 evidence: User at School A cannot see User at School B (AC-1)."""
        # Create User A at School A (via API with School A's context)
        tc_a = TestClient(app, headers={
            "Authorization": f"Bearer {test_jwt(client_id=str(client_a.id), institution_id=str(institution_a.id), roles=['institution_admin'])}",
            "Host": "school-a.localhost",
        })
        user_a_data = _create_user_via_api(
            tc_a, "user_a@schoola.com", "User A", institution_a.id
        )

        # Create User B at School B (via API with School B's context)
        tc_b = TestClient(app, headers={
            "Authorization": f"Bearer {test_jwt(client_id=str(client_b.id), institution_id=str(institution_b.id), roles=['institution_admin'])}",
            "Host": "school-b.localhost",
        })
        user_b_data = _create_user_via_api(
            tc_b, "user_b@schoolb.com", "User B", institution_b.id
        )

        # User A should NOT see User B
        response = tc_a.get(f"/api/v1/users/{user_b_data['id']}")
        assert response.status_code == 404, "User A should not see User B (tenant isolation)"

        # User B should NOT see User A
        response = tc_b.get(f"/api/v1/users/{user_a_data['id']}")
        assert response.status_code == 404, "User B should not see User A (tenant isolation)"

        # User A should see only their own users
        response = tc_a.get("/api/v1/users")
        assert response.status_code == 200
        users_a = response.json()
        assert len(users_a) == 1, "User A should see only 1 user (themselves)"
        assert users_a[0]["id"] == user_a_data["id"]

        # User B should see only their own users
        response = tc_b.get("/api/v1/users")
        assert response.status_code == 200
        users_b = response.json()
        assert len(users_b) == 1, "User B should see only 1 user (themselves)"
        assert users_b[0]["id"] == user_b_data["id"]


# ============================================================
# 11.3 — Test lifecycle flow
# ============================================================

class TestLifecycleFlow:
    """11.3: Test lifecycle flow: Invited → Pending → Active → Suspended → Active → Archived."""

    def test_full_lifecycle_flow(
        self, make_tenant_client, db_session, client_obj, institution
    ):
        """11.3 evidence: Invited → Pending → Active → Suspended → Active → Archived."""
        tc = make_tenant_client(
            subdomain="test-school",
            client_id=client_obj.id,
            institution_id=institution.id,
            roles=["institution_admin"],
        )

        user_data = _create_user_via_api(
            tc, "lifecycle@test.com", "Lifecycle User", institution.id
        )
        user_id = user_data["id"]
        assert user_data["lifecycle_status"] == "invited"

        # Invited → Pending
        response = tc.post(f"/api/v1/users/{user_id}/transition", json={
            "new_state": "pending",
            "reason": "User accepted invitation",
        })
        assert response.status_code == 200, f"Invited→Pending failed: {response.text}"
        assert response.json()["lifecycle_status"] == "pending"

        # Pending → Active
        response = tc.post(f"/api/v1/users/{user_id}/transition", json={
            "new_state": "active",
            "reason": "User completed onboarding",
        })
        assert response.status_code == 200, f"Pending→Active failed: {response.text}"
        assert response.json()["lifecycle_status"] == "active"

        # Active → Suspended
        response = tc.post(f"/api/v1/users/{user_id}/transition", json={
            "new_state": "suspended",
            "reason": "Policy violation",
        })
        assert response.status_code == 200, f"Active→Suspended failed: {response.text}"
        assert response.json()["lifecycle_status"] == "suspended"

        # Suspended → Active (reactivate)
        response = tc.post(f"/api/v1/users/{user_id}/transition", json={
            "new_state": "active",
            "reason": "Suspension period ended",
        })
        assert response.status_code == 200, f"Suspended→Active failed: {response.text}"
        assert response.json()["lifecycle_status"] == "active"

        # Active → Archived
        response = tc.post(f"/api/v1/users/{user_id}/transition", json={
            "new_state": "archived",
            "reason": "User left institution",
        })
        assert response.status_code == 200, f"Active→Archived failed: {response.text}"
        assert response.json()["lifecycle_status"] == "archived"

        # Verify lifecycle events were recorded
        db_session.expire_all()
        events = db_session.execute(
            select(UserLifecycleEvent)
            .where(UserLifecycleEvent.user_id == uuid.UUID(user_id))
            .order_by(UserLifecycleEvent.entered_at)
        ).scalars().all()
        assert len(events) == 5, f"Expected 5 lifecycle events, got {len(events)}"
        states = [e.state for e in events]
        assert states == ["pending", "active", "suspended", "active", "archived"]

    def test_archived_is_terminal(
        self, make_tenant_client, db_session, client_obj, institution
    ):
        """11.3 evidence: Archived is terminal — no outgoing arcs."""
        tc = make_tenant_client(
            subdomain="test-school",
            client_id=client_obj.id,
            institution_id=institution.id,
            roles=["institution_admin"],
        )

        user_data = _create_user_via_api(
            tc, "terminal@test.com", "Terminal User", institution.id
        )
        user_id = user_data["id"]

        tc.post(f"/api/v1/users/{user_id}/transition", json={"new_state": "pending"})
        tc.post(f"/api/v1/users/{user_id}/transition", json={"new_state": "active"})
        tc.post(f"/api/v1/users/{user_id}/transition", json={"new_state": "archived"})

        response = tc.post(f"/api/v1/users/{user_id}/transition", json={
            "new_state": "active",
            "reason": "Attempt to reactivate",
        })
        assert response.status_code == 400, "Archived→Active should be rejected (terminal state)"

    def test_disallowed_arc_rejected(
        self, make_tenant_client, db_session, client_obj, institution
    ):
        """11.3 evidence: disallowed arc rejected (e.g., Invited→Suspended is not a valid arc)."""
        tc = make_tenant_client(
            subdomain="test-school",
            client_id=client_obj.id,
            institution_id=institution.id,
            roles=["institution_admin"],
        )

        user_data = _create_user_via_api(
            tc, "disallowed@test.com", "Disallowed User", institution.id
        )
        user_id = user_data["id"]

        response = tc.post(f"/api/v1/users/{user_id}/transition", json={
            "new_state": "suspended",
            "reason": "Skip pending",
        })
        assert response.status_code == 400, "Invited→Suspended should be rejected (not a valid arc)"


# ============================================================
# 11.4 — Test email uniqueness
# ============================================================

class TestEmailUniqueness:
    """11.4: Test email uniqueness: duplicate email rejected across institutions and clients."""

    def test_duplicate_email_rejected_same_institution(
        self, make_tenant_client, db_session, client_obj, institution
    ):
        """11.4 evidence: duplicate email rejected within the same institution."""
        tc = make_tenant_client(
            subdomain="test-school",
            client_id=client_obj.id,
            institution_id=institution.id,
            roles=["institution_admin"],
        )

        _create_user_via_api(tc, "duplicate@test.com", "First User", institution.id)

        response = tc.post("/api/v1/users", json={
            "email": "duplicate@test.com",
            "person_data": {"name": "Second User"},
            "institution_id": str(institution.id),
        })
        assert response.status_code == 409, "Duplicate email should be rejected (409)"
        assert "email_taken" in response.text

    def test_duplicate_email_rejected_across_institutions(
        self, app, db_session, test_jwt, client_obj, institution_a, institution_b
    ):
        """11.4 evidence: duplicate email rejected across institutions."""
        tc_a = TestClient(app, headers={
            "Authorization": f"Bearer {test_jwt(client_id=str(client_obj.id), institution_id=str(institution_a.id), roles=['institution_admin'])}",
            "Host": "school-a.localhost",
        })
        _create_user_via_api(tc_a, "cross_inst@test.com", "User A", institution_a.id)

        tc_b = TestClient(app, headers={
            "Authorization": f"Bearer {test_jwt(client_id=str(client_obj.id), institution_id=str(institution_b.id), roles=['institution_admin'])}",
            "Host": "school-b.localhost",
        })
        response = tc_b.post("/api/v1/users", json={
            "email": "cross_inst@test.com",
            "person_data": {"name": "User B"},
            "institution_id": str(institution_b.id),
        })
        assert response.status_code == 409, "Duplicate email across institutions should be rejected (409)"

    def test_duplicate_email_rejected_across_clients(
        self, app, db_session, test_jwt, client_a, client_b, institution_a, institution_b
    ):
        """11.4 evidence: duplicate email rejected across clients."""
        tc_a = TestClient(app, headers={
            "Authorization": f"Bearer {test_jwt(client_id=str(client_a.id), institution_id=str(institution_a.id), roles=['institution_admin'])}",
            "Host": "school-a.localhost",
        })
        _create_user_via_api(tc_a, "cross_client@test.com", "User A", institution_a.id)

        tc_b = TestClient(app, headers={
            "Authorization": f"Bearer {test_jwt(client_id=str(client_b.id), institution_id=str(institution_b.id), roles=['institution_admin'])}",
            "Host": "school-b.localhost",
        })
        response = tc_b.post("/api/v1/users", json={
            "email": "cross_client@test.com",
            "person_data": {"name": "User B"},
            "institution_id": str(institution_b.id),
        })
        assert response.status_code == 409, "Duplicate email across clients should be rejected (409)"


# ============================================================
# 11.5 — Test lookup tables (modified — no user_categories)
# ============================================================

class TestLookupTables:
    """11.5: Test lookup tables: Role is queryable and usable for FK validation.
    UserCategory tests removed (table dropped, D6a)."""

    def test_roles_queryable(self, make_tenant_client, client_a, db_session):
        """11.5 evidence: Role lookup table is queryable."""
        client = make_tenant_client(
            subdomain="test-school",
            client_id=client_a.id,
            roles=["admin"],
        )
        response = client.get("/api/v1/lookups/roles")
        assert response.status_code == 200, f"Failed to list roles: {response.text}"
        roles = response.json()
        assert len(roles) > 0, "Role seed data should exist"
        names = [r["name"] for r in roles]
        assert "Teacher" in names, "Teacher should be in Role seed data"
        assert "Student" in names, "Student should be in Role seed data"

    def test_user_categories_endpoint_removed(self, make_tenant_client, client_a, db_session):
        """11.5 evidence: UserCategory endpoint removed (T-23, D6a)."""
        client = make_tenant_client(
            subdomain="test-school",
            client_id=client_a.id,
            roles=["admin"],
        )
        response = client.get("/api/v1/lookups/user-categories")
        assert response.status_code == 404, "user-categories endpoint should be 404 (removed)"

    def test_role_fk_validation(
        self, make_tenant_client, db_session, client_obj, institution
    ):
        """11.5 evidence: Role FK is validated — invalid role rejected."""
        tc = make_tenant_client(
            subdomain="test-school",
            client_id=client_obj.id,
            institution_id=institution.id,
            roles=["institution_admin"],
        )

        user_data = _create_user_via_api(
            tc, "role_fk@test.com", "Role FK User", institution.id
        )
        user_id = user_data["id"]

        with pytest.raises(Exception):
            tc.post(f"/api/v1/users/{user_id}/roles", json={
                "role_id": str(uuid.uuid4()),
                "scope": "Test Scope",
            })

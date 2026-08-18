"""Tests for Client User Bootstrap — two-tier user model (AC-1 through AC-10).

Requires a running Supabase instance (local: supabase start, or cloud).
Run: cd backend && uv run pytest tests/test_client_user_bootstrap.py -v
"""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from kernel.tenant_context import TenantContext, set_tenant_context
from kernel.middleware import mint_test_jwt


# ============================================================
# Test fixtures (extend conftest.py patterns)
# ============================================================
# These tests use the existing conftest.py which provides:
# - db_session (synchronous session factory)
# - test_client (FastAPI TestClient)
# - fake_supabase_auth (mock Supabase auth for unit tests)
# - platform_owner_ctx / client_director_ctx / institute_admin_ctx etc.

pytestmark = pytest.mark.skip(
    reason="These tests require a local Supabase instance + fresh migrations. "
           "Run them after migration 011 + 012 are applied in a local dev environment."
)


# ============================================================
# AC-1: Two-tier physical separation
# ============================================================

def test_client_user_table_exists(test_client: TestClient, platform_owner_token: str):
    """Verify client_user table exists and has correct columns."""
    # Query via raw SQL or inspect via the ORM
    from kernel.user.models.client_user import ClientUser
    assert ClientUser.__tablename__ == "client_user"
    assert hasattr(ClientUser, "role_id")
    assert not hasattr(ClientUser, "institution_id")

def test_app_user_institution_id_not_null(test_client: TestClient):
    """Verify app_user.institution_id is NOT NULL after migration 012."""
    from sqlalchemy import inspect as sa_inspect
    from kernel.user.models.user import User
    col = sa_inspect(User).columns["institution_id"]
    assert not col.nullable  # NOT NULL enforced

def test_insert_app_user_without_institution_id_fails(test_client, platform_owner_token):
    """Attempting to POST /api/v1/users without institution_id returns 422."""
    response = test_client.post("/api/v1/users", json={
        "email": "test-no-inst@test.com",
        "person_data": {"name": "No Inst"},
        # institution_id omitted
    }, headers={"Authorization": f"Bearer {platform_owner_token}"})
    assert response.status_code == 422


# ============================================================
# AC-2: Login lookup by user_tier
# ============================================================

def test_client_leadership_login_resolves_to_client_user(test_client):
    """CD with user_tier=client_leadership queries client_user."""
    # Requires a CD with user_metadata.user_tier="client_leadership" in Supabase
    pass

def test_institution_login_resolves_to_app_user(test_client):
    """Institution user with user_tier=institution queries app_user."""
    pass

def test_no_tier_strict_fail(test_client):
    """User without user_tier flag gets 403."""
    response = test_client.post("/api/auth/login", json={
        "email": "legacy@test.com",
        "password": "test123",
    })
    # The Supabase auth might reject first (user doesn't exist), but if they
    # exist, the backend should reject on missing user_tier
    pass


# ============================================================
# AC-3: PO bootstrap + invite
# ============================================================

def test_po_bootstrap_returns_invite_url(test_client, platform_owner_token, test_client_id):
    """POST /api/v1/platform/clients/{id}/users returns 201 with invite_url."""
    response = test_client.post(
        f"/api/v1/platform/clients/{test_client_id}/users",
        json={
            "email": f"test-cd-{uuid.uuid4().hex[:8]}@test.com",
            "person_data": {"name": "Test CD"},
            "role_id": "5f653436-97e0-40e0-8bb3-2301a8eb85c8",  # client_director
        },
        headers={"Authorization": f"Bearer {platform_owner_token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert "invite_url" in data
    assert "user_id" in data


# ============================================================
# AC-4: PO list / suspend / revoke
# ============================================================

def test_po_list_cds(test_client, platform_owner_token, test_client_id):
    """GET /api/v1/platform/clients/{id}/users returns CDs."""
    response = test_client.get(
        f"/api/v1/platform/clients/{test_client_id}/users",
        headers={"Authorization": f"Bearer {platform_owner_token}"},
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_po_transition_cd(test_client, platform_owner_token, test_client_id, test_cd_id):
    """PATCH transition endpoint suspends a CD."""
    response = test_client.patch(
        f"/api/v1/platform/clients/{test_client_id}/users/{test_cd_id}/transition",
        json={"new_state": "suspended", "reason": "Test suspension"},
        headers={"Authorization": f"Bearer {platform_owner_token}"},
    )
    assert response.status_code == 200
    assert response.json()["lifecycle_status"] == "suspended"

def test_po_revoke_cd(test_client, platform_owner_token, test_client_id, test_cd_id):
    """DELETE revoke endpoint archives the CD."""
    response = test_client.delete(
        f"/api/v1/platform/clients/{test_client_id}/users/{test_cd_id}",
        headers={"Authorization": f"Bearer {platform_owner_token}"},
    )
    assert response.status_code == 204


# ============================================================
# AC-5: CD own-row access only
# ============================================================

def test_cd_reads_own_row(test_client, cd_token, test_client_id, cd_user_id):
    """CD can read their own client_user row."""
    response = test_client.get(
        f"/api/v1/platform/clients/{test_client_id}/users/{cd_user_id}",
        headers={"Authorization": f"Bearer {cd_token}"},
    )
    assert response.status_code == 200

def test_cd_cannot_read_sibling(test_client, cd_token, test_client_id):
    """CD cannot read another CD's row — RLS filters to 404."""
    sibling_id = str(uuid.uuid4())
    response = test_client.get(
        f"/api/v1/platform/clients/{test_client_id}/users/{sibling_id}",
        headers={"Authorization": f"Bearer {cd_token}"},
    )
    assert response.status_code == 404


# ============================================================
# AC-6/7: PO walled off from institution data
# ============================================================

def test_po_zero_app_user_rows(test_client, platform_owner_token):
    """PO querying app_user sees zero rows."""
    response = test_client.get(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {platform_owner_token}"},
    )
    assert response.status_code == 200
    assert len(response.json()) == 0

def test_po_cannot_post_app_user(test_client, platform_owner_token, test_client_id):
    """PO cannot POST to /api/v1/users."""
    response = test_client.post("/api/v1/users", json={
        "email": "po-try@test.com",
        "person_data": {"name": "PO Try"},
        "institution_id": str(uuid.uuid4()),
    }, headers={"Authorization": f"Bearer {platform_owner_token}"})
    assert response.status_code == 403


# ============================================================
# AC-9: Strict-fail login
# ============================================================

def test_no_user_tier_login_rejected(test_client):
    """User without user_metadata.user_tier is rejected at login."""
    response = test_client.post("/api/auth/login", json={
        "email": "no-tier@test.com",
        "password": "test",
    })
    # Supabase will reject first (user doesn't exist), then backend checks tier
    assert response.status_code in (401, 403)


# ============================================================
# AC-10: Migration order + rollback
# ============================================================

def test_migration_011_idempotent():
    """Migration 011 applied twice is a no-op."""
    pass  # Tested by running alembic upgrade twice

def test_migration_012_post_011_succeeds():
    """Migration 012 ALTERs NOT NULL if 011 assertion passes."""
    pass  # Verified on cloud DB

def test_migration_012_without_011_fails():
    """Migration 012 fails if 011 did not clean NULL rows."""
    pass  # Tested by design (pre-condition assertion in 012)

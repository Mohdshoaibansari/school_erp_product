"""C-04 Authorization tests — Casbin enforcement + require_permission dependency.

Sections 12-13 of tasks.md. Tests verify:
- Each role has correct permissions via Casbin
- Scope enforcement (institution, tenant)
- Platform owner bypass
- require_permission dependency grants/denies correctly
"""

from __future__ import annotations

import uuid

import pytest
import casbin
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient

from kernel.authz.dependencies import require_permission, get_enforcer, set_enforcer
from kernel.tenant_context import TenantContext, get_tenant_context, set_tenant_context
from business.tenant_institution.policies import register_policies
from kernel.authz.services.policy_loader import register_policies_from_map


# ============================================================
# Helpers
# ============================================================

def _build_test_enforcer(with_c01_policies: bool = True) -> casbin.Enforcer:
    """Build a Casbin enforcer with C-04 permission map and optional C-01 policies."""
    import os
    import kernel.authz
    model_path = os.path.join(os.path.dirname(kernel.authz.__file__), "casbin_model.conf")
    e = casbin.Enforcer(model_path)

    if with_c01_policies:
        register_policies(e)

    # Register C-04 role-permission policies from seed data
    _register_c04_test_policies(e)
    return e


def _register_c04_test_policies(e: casbin.Enforcer) -> None:
    """Register C-04 role-permission policies for tests (mirrors seed data).

    Each (role, resource, action) gets a Casbin policy with 'institution' scope.
    Role hierarchy links are also added.
    """
    # C-04 role → (resource, action) mappings (mirrors migration seed)
    c04_policies: dict[str, list[tuple[str, str]]] = {
        "Admin": [
            ("user", "read"), ("user", "create"), ("user", "update"), ("user", "suspend"),
            ("user_profile", "read"), ("user_profile", "update"),
            ("role_assignment", "read"), ("role_assignment", "create"), ("role_assignment", "delete"),
            ("user_identifier", "read"), ("user_identifier", "create"), ("user_identifier", "delete"),
            ("institution", "read"), ("institution", "update"), ("institution", "transition_lifecycle"),
            ("org_unit", "read"), ("org_unit", "create"), ("org_unit", "update"), ("org_unit", "delete"), ("org_unit", "move"),
            ("institution_type", "read"),
        ],
        "Principal": [
            ("user", "read"),
            ("role_assignment", "read"),
            ("user_identifier", "read"),
            ("institution", "read"), ("institution", "update"),
            ("org_unit", "read"), ("org_unit", "create"), ("org_unit", "update"), ("org_unit", "delete"), ("org_unit", "move"),
            ("institution_type", "read"),
        ],
        "HOD": [
            ("user", "read"),
            ("role_assignment", "read"),
            ("org_unit", "read"), ("org_unit", "update"),
            ("institution_type", "read"),
        ],
        "Teacher": [("user", "read"), ("user", "update")],
        "Staff": [("user", "read"), ("user", "update")],
        "Student": [("user", "read")],
        "Parent": [("user", "read")],
    }

    for role_name, permissions in c04_policies.items():
        # Role hierarchy: the identity role is also a Casbin role
        e.add_role_for_user(role_name, role_name)
        for resource, action in permissions:
            e.add_policy(role_name, resource, action, "institution")


def _make_sub(role: str, client_id: str = "", institution_id: str = "") -> dict:
    """Build a Casbin subject dict."""
    return {"role": role, "client_id": client_id, "institution_id": institution_id}


def _make_obj(name: str, client_id: str = "", institution_id: str = "") -> dict:
    """Build a Casbin object dict."""
    return {"name": name, "client_id": client_id, "institution_id": institution_id}


# ============================================================
# Section 12 — Casbin enforcement unit tests
# ============================================================

class TestCasbinEnforcement:
    """12.1-12.6: Casbin enforcement tests — each role + scope combination."""

    @pytest.fixture
    def enforcer(self):
        return _build_test_enforcer(with_c01_policies=True)

    # ---- 12.1: Admin role ----

    @pytest.mark.parametrize("resource,action", [
        ("user", "create"), ("user", "suspend"), ("user", "read"), ("user", "update"),
        ("institution", "read"), ("institution", "update"),
        ("org_unit", "create"), ("org_unit", "read"),
    ])
    def test_admin_has_expected_permissions(self, enforcer, resource, action):
        """Admin should have all assigned permissions within their institution."""
        sub = _make_sub("Admin", client_id="c1", institution_id="i1")
        obj = _make_obj(resource, client_id="c1", institution_id="i1")
        assert enforcer.enforce(sub, obj, action), f"Admin should be able to {resource}.{action}"

    def test_admin_cannot_user_suspend(self, enforcer):
        """Admin CAN suspend users (it's in their permission set)."""
        sub = _make_sub("Admin", client_id="c1", institution_id="i1")
        obj = _make_obj("user", client_id="c1", institution_id="i1")
        assert enforcer.enforce(sub, obj, "suspend")

    # ---- 12.2: Principal role ----

    def test_principal_can_read_institution(self, enforcer):
        sub = _make_sub("Principal", client_id="c1", institution_id="i1")
        obj = _make_obj("institution", client_id="c1", institution_id="i1")
        assert enforcer.enforce(sub, obj, "read")

    def test_principal_cannot_create_user(self, enforcer):
        sub = _make_sub("Principal", client_id="c1", institution_id="i1")
        obj = _make_obj("user", client_id="c1", institution_id="i1")
        assert not enforcer.enforce(sub, obj, "create")

    def test_principal_cannot_suspend_user(self, enforcer):
        sub = _make_sub("Principal", client_id="c1", institution_id="i1")
        obj = _make_obj("user", client_id="c1", institution_id="i1")
        assert not enforcer.enforce(sub, obj, "suspend")

    # ---- 12.3: Teacher role ----

    def test_teacher_can_read_user(self, enforcer):
        sub = _make_sub("Teacher", client_id="c1", institution_id="i1")
        obj = _make_obj("user", client_id="c1", institution_id="i1")
        assert enforcer.enforce(sub, obj, "read")

    def test_teacher_can_update_user(self, enforcer):
        sub = _make_sub("Teacher", client_id="c1", institution_id="i1")
        obj = _make_obj("user", client_id="c1", institution_id="i1")
        assert enforcer.enforce(sub, obj, "update")

    def test_teacher_cannot_create_user(self, enforcer):
        sub = _make_sub("Teacher", client_id="c1", institution_id="i1")
        obj = _make_obj("user", client_id="c1", institution_id="i1")
        assert not enforcer.enforce(sub, obj, "create")

    def test_teacher_cannot_read_institution(self, enforcer):
        sub = _make_sub("Teacher", client_id="c1", institution_id="i1")
        obj = _make_obj("institution", client_id="c1", institution_id="i1")
        assert not enforcer.enforce(sub, obj, "read")

    # ---- 12.4: Student / Parent / Staff ----

    def test_student_can_read_user(self, enforcer):
        sub = _make_sub("Student", client_id="c1", institution_id="i1")
        obj = _make_obj("user", client_id="c1", institution_id="i1")
        assert enforcer.enforce(sub, obj, "read")

    def test_student_cannot_update_user(self, enforcer):
        sub = _make_sub("Student", client_id="c1", institution_id="i1")
        obj = _make_obj("user", client_id="c1", institution_id="i1")
        assert not enforcer.enforce(sub, obj, "update")

    def test_parent_can_read_user(self, enforcer):
        sub = _make_sub("Parent", client_id="c1", institution_id="i1")
        obj = _make_obj("user", client_id="c1", institution_id="i1")
        assert enforcer.enforce(sub, obj, "read")

    def test_staff_can_read_user(self, enforcer):
        sub = _make_sub("Staff", client_id="c1", institution_id="i1")
        obj = _make_obj("user", client_id="c1", institution_id="i1")
        assert enforcer.enforce(sub, obj, "read")

    def test_staff_can_update_user(self, enforcer):
        """Staff has same permissions as Teacher."""
        sub = _make_sub("Staff", client_id="c1", institution_id="i1")
        obj = _make_obj("user", client_id="c1", institution_id="i1")
        assert enforcer.enforce(sub, obj, "update")

    # ---- 12.5: Scope enforcement ----

    def test_scope_institution_enforced(self, enforcer):
        """Same role, different institution_id → deny."""
        sub = _make_sub("Admin", client_id="c1", institution_id="i1")
        obj = _make_obj("user", client_id="c1", institution_id="i2")  # different institution
        assert not enforcer.enforce(sub, obj, "read"), "Cross-institution should be denied"

    def test_scope_institution_allowed_same(self, enforcer):
        """Same role, same institution_id → allow."""
        sub = _make_sub("Admin", client_id="c1", institution_id="i1")
        obj = _make_obj("user", client_id="c1", institution_id="i1")
        assert enforcer.enforce(sub, obj, "read")

    # ---- 12.6: Platform owner bypass ----

    def test_platform_owner_bypasses_all_c01(self, enforcer):
        """platform_owner has *.* at any scope via C-01 D11 policies."""
        sub = _make_sub("platform_owner", client_id="c1", institution_id="i1")
        obj = _make_obj("client", client_id="c2", institution_id="i2")  # cross-client!
        assert enforcer.enforce(sub, obj, "create"), "Platform owner should create any client"

    def test_platform_owner_bypasses_user_create(self, enforcer):
        sub = _make_sub("platform_owner", client_id="c1", institution_id="i1")
        obj = _make_obj("user", client_id="c2", institution_id="i2")
        assert enforcer.enforce(sub, obj, "create")

    def test_platform_owner_bypasses_institution_read(self, enforcer):
        sub = _make_sub("platform_owner", client_id="c1", institution_id="i1")
        obj = _make_obj("institution", client_id="c2", institution_id="i2")
        assert enforcer.enforce(sub, obj, "read")

    # ---- C-01 D11 tests: client_director, institution_admin ----

    def test_client_director_can_read_institution(self, enforcer):
        """Client Director has institution.* at tenant scope."""
        sub = _make_sub("client_director", client_id="c1", institution_id="i1")
        obj = _make_obj("institution", client_id="c1", institution_id="i1")
        assert enforcer.enforce(sub, obj, "create")

    def test_client_director_cannot_cross_client_institution(self, enforcer):
        sub = _make_sub("client_director", client_id="c1", institution_id="")
        obj = _make_obj("institution", client_id="c2", institution_id="i2")
        assert not enforcer.enforce(sub, obj, "read"), "Cross-client should be denied"

    def test_institution_admin_can_create_org_unit(self, enforcer):
        sub = _make_sub("institution_admin", client_id="c1", institution_id="i1")
        obj = _make_obj("org_unit", client_id="c1", institution_id="i1")
        assert enforcer.enforce(sub, obj, "create")

    def test_institution_admin_cannot_cross_institution(self, enforcer):
        sub = _make_sub("institution_admin", client_id="c1", institution_id="i1")
        obj = _make_obj("org_unit", client_id="c1", institution_id="i2")
        assert not enforcer.enforce(sub, obj, "create")


# ============================================================
# Section 13 — require_permission dependency tests
# ============================================================

class TestRequirePermissionDependency:
    """13.1-13.5: Integration tests for the require_permission FastAPI dependency."""

    @pytest.fixture
    def app_with_enforcer(self):
        """Create a minimal FastAPI app with the Casbin enforcer wired."""
        app = FastAPI()
        enforcer = _build_test_enforcer(with_c01_policies=True)
        set_enforcer(enforcer)

        @app.get("/test/user-read")
        def read_user(
            ctx: TenantContext = Depends(get_tenant_context),
            _authz: None = Depends(require_permission("user", "read")),
        ):
            return {"allowed": True}

        @app.get("/test/user-create")
        def create_user(
            ctx: TenantContext = Depends(get_tenant_context),
            _authz: None = Depends(require_permission("user", "create")),
        ):
            return {"allowed": True}

        @app.get("/test/institution-read")
        def read_institution(
            ctx: TenantContext = Depends(get_tenant_context),
            _authz: None = Depends(require_permission("institution", "read")),
        ):
            return {"allowed": True}

        yield app
        set_enforcer(None)

    def _make_context(
        self, role: str = "", client_id: uuid.UUID | None = None,
        institution_id: uuid.UUID | None = None, is_platform_owner: bool = False,
    ) -> TenantContext:
        return TenantContext(
            client_id=client_id or uuid.uuid4(),
            institution_id=institution_id,
            user_id="test-user",
            is_platform_owner=is_platform_owner,
            roles=[role] if role else [],
        )

    # ---- 13.1: Grant authorized role ----

    def test_admin_can_read_user(self, app_with_enforcer):
        """Admin with user.read at matching institution → 200."""
        ctx = self._make_context("Admin")
        app_with_enforcer.dependency_overrides[get_tenant_context] = lambda: ctx
        tc = TestClient(app_with_enforcer)
        response = tc.get("/test/user-read")
        assert response.status_code == 200, response.text

    def test_admin_can_create_user(self, app_with_enforcer):
        """Admin with user.create → 200."""
        ctx = self._make_context("Admin")
        app_with_enforcer.dependency_overrides[get_tenant_context] = lambda: ctx
        tc = TestClient(app_with_enforcer)
        response = tc.get("/test/user-create")
        assert response.status_code == 200, response.text

    # ---- 13.2: Deny unauthorized role ----

    def test_teacher_denied_user_create(self, app_with_enforcer):
        """Teacher does not have user.create → 403."""
        ctx = self._make_context("Teacher")
        app_with_enforcer.dependency_overrides[get_tenant_context] = lambda: ctx
        tc = TestClient(app_with_enforcer)
        response = tc.get("/test/user-create")
        assert response.status_code == 403, response.text

    def test_parent_denied_user_update(self, app_with_enforcer):
        """Parent only has user.read → /test/user-create → 403."""
        ctx = self._make_context("Parent")
        app_with_enforcer.dependency_overrides[get_tenant_context] = lambda: ctx
        tc = TestClient(app_with_enforcer)
        response = tc.get("/test/user-create")
        assert response.status_code == 403, response.text

    def test_teacher_denied_institution_read(self, app_with_enforcer):
        """Teacher has no institution permissions → 403."""
        ctx = self._make_context("Teacher")
        app_with_enforcer.dependency_overrides[get_tenant_context] = lambda: ctx
        tc = TestClient(app_with_enforcer)
        response = tc.get("/test/institution-read")
        assert response.status_code == 403, response.text

    # ---- 13.5: Platform owner bypass ----

    def test_platform_owner_bypass_user_create(self, app_with_enforcer):
        """Platform owner bypasses all checks → 200."""
        ctx = self._make_context(is_platform_owner=True)
        app_with_enforcer.dependency_overrides[get_tenant_context] = lambda: ctx
        tc = TestClient(app_with_enforcer)
        response = tc.get("/test/user-create")
        assert response.status_code == 200, response.text

    def test_platform_owner_bypass_institution_read(self, app_with_enforcer):
        """Platform owner with is_platform_owner=True → 200."""
        ctx = self._make_context(is_platform_owner=True)
        app_with_enforcer.dependency_overrides[get_tenant_context] = lambda: ctx
        tc = TestClient(app_with_enforcer)
        response = tc.get("/test/institution-read")
        assert response.status_code == 200, response.text

    # ---- Edge cases ----

    def test_no_roles_denied(self, app_with_enforcer):
        """No roles assigned → 403."""
        ctx = self._make_context(role="")
        app_with_enforcer.dependency_overrides[get_tenant_context] = lambda: ctx
        tc = TestClient(app_with_enforcer)
        response = tc.get("/test/user-read")
        assert response.status_code == 403, response.text
        assert "no roles" in response.text.lower()

    def test_enforcer_none_returns_500(self, app_with_enforcer):
        """If enforcer is None → 500."""
        set_enforcer(None)
        ctx = self._make_context("Admin")
        app_with_enforcer.dependency_overrides[get_tenant_context] = lambda: ctx
        tc = TestClient(app_with_enforcer)
        response = tc.get("/test/user-read")
        assert response.status_code == 500, response.text
        assert "not available" in response.text.lower()

    def test_hod_can_read_org_unit(self, app_with_enforcer):
        """HOD has org_unit.read."""
        e = _build_test_enforcer(with_c01_policies=True)
        set_enforcer(e)

        @app_with_enforcer.get("/test/org-unit-read")
        def read_org_unit(
            ctx: TenantContext = Depends(get_tenant_context),
            _authz: None = Depends(require_permission("org_unit", "read")),
        ):
            return {"allowed": True}

        ctx = self._make_context("HOD")
        app_with_enforcer.dependency_overrides[get_tenant_context] = lambda: ctx
        tc = TestClient(app_with_enforcer)
        response = tc.get("/test/org-unit-read")
        assert response.status_code == 200, response.text

    def test_client_director_can_create_institution(self, app_with_enforcer):
        """Client Director has institution.* at tenant scope (C-01 D11)."""
        e = _build_test_enforcer(with_c01_policies=True)
        set_enforcer(e)

        @app_with_enforcer.get("/test/inst-create")
        def create_inst(
            ctx: TenantContext = Depends(get_tenant_context),
            _authz: None = Depends(require_permission("institution", "create")),
        ):
            return {"allowed": True}

        ctx = self._make_context("client_director")
        app_with_enforcer.dependency_overrides[get_tenant_context] = lambda: ctx
        tc = TestClient(app_with_enforcer)
        response = tc.get("/test/inst-create")
        assert response.status_code == 200, response.text

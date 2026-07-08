"""Tests for the D11 permission matrix via Casbin (tasks 12.1–12.3, AC-15).

C-04 owns the Casbin framework; C-01 supplies the D11 tiered-delegation
matrix and registers it via the manifest ``register_casbin_policies`` hook
(A5). These tests build the C-01 enforcer and assert each role's allowed +
denied actions per D11.

12.1 — encode the matrix: Platform Owner ALL; Client Director own-client
       (cannot mutate the Client); Institution Admin own-institution (cannot
       mutate the institution); cross-institution roles READ-only.
12.2 — cross-tenant writes (Client create/suspend/terminate, ownership
       transfer) are Platform-gated — a Client Director is rejected.
12.3 — all C-01 writes record actor identity via C-11 (asserted in
       test_audit_emission.py).
"""

from __future__ import annotations

import uuid

import pytest

from business.tenant_institution.manifest import manifest as c01_manifest
from business.tenant_institution.policies import (
    build_enforcer,
    make_subject,
    make_resource,
    register_policies,
    casbin_model_path,
)


@pytest.fixture
def enforcer():
    """A Casbin enforcer with the C-01 D11 matrix registered via the manifest hook."""
    import casbin

    e = casbin.Enforcer(casbin_model_path())
    # Register via the manifest hook (A5) — same path C-04 will invoke at startup.
    c01_manifest.register_casbin_policies(e)
    return e


# ============================================================
# 12.1 — D11 matrix per role
# ============================================================

class TestPlatformOwnerMatrix:
    """Platform Owner: ALL C-01 operations, any scope (D11)."""

    def test_platform_owner_can_create_client_any_tenant(self, enforcer):
        sub = make_subject("platform_owner", client_id=None)
        obj = make_resource("client", client_id=str(uuid.uuid4()))
        assert enforcer.enforce(sub, obj, "create") is True

    def test_platform_owner_can_suspend_terminate_client(self, enforcer):
        sub = make_subject("platform_owner", client_id="B")
        obj = make_resource("client", client_id="A")  # cross-tenant OK for PO
        for act in ("suspend", "terminate", "archive", "transition", "update_identity"):
            assert enforcer.enforce(sub, obj, act) is True, f"PO should be allowed {act}"

    def test_platform_owner_can_manage_institution_types_and_transfers(self, enforcer):
        sub = make_subject("platform_owner", client_id="B")
        assert enforcer.enforce(sub, make_resource("institution_type", client_id="A"), "manage") is True
        assert enforcer.enforce(
            sub, make_resource("ownership_transfer", client_id="A"), "approve"
        ) is True


class TestClientDirectorMatrix:
    """Client Director: own-client scope — manage Institutions/OrgUnits; CANNOT mutate the Client itself (D11)."""

    def test_can_manage_institutions_within_own_client(self, enforcer):
        cid = str(uuid.uuid4())
        sub = make_subject("client_director", client_id=cid)
        obj = make_resource("institution", client_id=cid)
        for act in ("create", "update_identity", "transition", "archive", "read"):
            assert enforcer.enforce(sub, obj, act) is True, f"CD should be allowed institution {act}"

    def test_can_manage_org_units_within_own_client(self, enforcer):
        cid = str(uuid.uuid4())
        sub = make_subject("client_director", client_id=cid)
        obj = make_resource("org_unit", client_id=cid)
        for act in ("create", "move", "archive", "reactivate", "update_identity", "reorder", "read"):
            assert enforcer.enforce(sub, obj, act) is True, f"CD should be allowed org_unit {act}"

    def test_can_update_own_client_identity(self, enforcer):
        cid = str(uuid.uuid4())
        sub = make_subject("client_director", client_id=cid)
        obj = make_resource("client", client_id=cid)
        assert enforcer.enforce(sub, obj, "update_identity") is True
        assert enforcer.enforce(sub, obj, "read") is True

    def test_cannot_create_suspend_terminate_client(self, enforcer):
        """12.2: cross-tenant/boundary Client writes are Platform-gated."""
        cid = str(uuid.uuid4())
        sub = make_subject("client_director", client_id=cid)
        obj = make_resource("client", client_id=cid)
        for act in ("create", "suspend", "terminate"):
            assert enforcer.enforce(sub, obj, act) is False, (
                f"Client Director MUST NOT be able to {act} the Client (Platform-gated, D11, 12.2)"
            )

    def test_cannot_cross_tenant_write(self, enforcer):
        """12.2: a Client Director for Client A cannot act on Client B tenant resources."""
        sub = make_subject("client_director", client_id="A")
        obj = make_resource("institution", client_id="B")
        assert enforcer.enforce(sub, obj, "create") is False
        assert enforcer.enforce(sub, obj, "read") is False

    def test_cannot_approve_ownership_transfer(self, enforcer):
        """12.2: ownership transfer approval is Platform-gated."""
        sub = make_subject("client_director", client_id="A")
        obj = make_resource("ownership_transfer", client_id="A")
        assert enforcer.enforce(sub, obj, "approve") is False


class TestInstitutionAdminMatrix:
    """Institution Admin: own-institution scope — manage OrgUnits; CANNOT mutate the Institution itself (D11)."""

    def test_can_manage_org_units_within_own_institution(self, enforcer):
        cid, iid = str(uuid.uuid4()), str(uuid.uuid4())
        sub = make_subject("institution_admin", client_id=cid, institution_id=iid)
        obj = make_resource("org_unit", client_id=cid, institution_id=iid)
        for act in ("create", "move", "archive", "reactivate", "update_identity", "reorder", "read"):
            assert enforcer.enforce(sub, obj, act) is True, f"IA should be allowed org_unit {act}"

    def test_can_update_own_institution_identity(self, enforcer):
        cid, iid = str(uuid.uuid4()), str(uuid.uuid4())
        sub = make_subject("institution_admin", client_id=cid, institution_id=iid)
        obj = make_resource("institution", client_id=cid, institution_id=iid)
        assert enforcer.enforce(sub, obj, "update_identity") is True
        assert enforcer.enforce(sub, obj, "read") is True

    def test_cannot_create_or_archive_institution(self, enforcer):
        """Institution Admin cannot mutate the institution itself (D11)."""
        cid, iid = str(uuid.uuid4()), str(uuid.uuid4())
        sub = make_subject("institution_admin", client_id=cid, institution_id=iid)
        obj = make_resource("institution", client_id=cid, institution_id=iid)
        for act in ("create", "transition", "archive"):
            assert enforcer.enforce(sub, obj, act) is False, (
                f"Institution Admin MUST NOT be able to {act} the Institution (D11)"
            )

    def test_cannot_cross_institution_write(self, enforcer):
        """Institution Admin of I1 cannot write OrgUnits under I2 (own-institution scope, D11)."""
        sub = make_subject("institution_admin", client_id="A", institution_id="I1")
        obj = make_resource("org_unit", client_id="A", institution_id="I2")
        assert enforcer.enforce(sub, obj, "create") is False
        assert enforcer.enforce(sub, obj, "move") is False


class TestCrossInstitutionRoleMatrix:
    """Cross-institution roles: READ-only oversight on C-01 (D11)."""

    @pytest.mark.parametrize("role", ["regional_manager", "group_academic_head", "finance_controller"])
    def test_read_only_on_c01(self, enforcer, role):
        cid = str(uuid.uuid4())
        sub = make_subject(role, client_id=cid)
        for name in ("institution", "org_unit", "client"):
            assert enforcer.enforce(sub, make_resource(name, client_id=cid), "read") is True, (
                f"{role} should READ {name}"
            )

    def test_all_writes_denied_for_cross_institution_role(self, enforcer):
        cid = str(uuid.uuid4())
        sub = make_subject("regional_manager", client_id=cid)
        obj = make_resource("institution", client_id=cid)
        for act in ("create", "update_identity", "transition", "archive", "move"):
            assert enforcer.enforce(sub, obj, act) is False, (
                f"cross-institution role MUST be READ-only — {act} denied (D11)"
            )

    def test_cross_institution_role_cannot_cross_tenant_read(self, enforcer):
        sub = make_subject("regional_manager", client_id="A")
        obj = make_resource("institution", client_id="B")
        assert enforcer.enforce(sub, obj, "read") is False


# ============================================================
# 12.1 — manifest hook wiring (A5)
# ============================================================

class TestManifestHookWiring:
    """The manifest register_casbin_policies hook registers the matrix on an enforcer (A5)."""

    def test_manifest_hook_registers_role_hierarchy_and_policies(self):
        import casbin

        e = casbin.Enforcer(casbin_model_path())
        # Before: no policies
        assert len(e.get_policy()) == 0
        c01_manifest.register_casbin_policies(e)
        # After: the D11 policies are present
        pols = e.get_policy()
        assert len(pols) > 0
        # Platform Owner wildcard policy is present (ALL)
        assert any(
            p[0] == "platform_owner" and p[1] == "*" and p[2] == "*" for p in pols
        )
        # Role hierarchy links are registered (platform_owner → lower tiers)
        assert e.has_role_for_user("platform_owner", "client_director")
        assert e.has_role_for_user("platform_owner", "institution_admin")
        assert e.has_role_for_user("platform_owner", "cross_institution")

    def test_register_policies_is_idempotent(self):
        """register_policies is safe to call more than once (add skips duplicates)."""
        import casbin

        e = casbin.Enforcer(casbin_model_path())
        register_policies(e)
        n1 = len(e.get_policy())
        register_policies(e)
        n2 = len(e.get_policy())
        assert n1 == n2, "register_policies should be idempotent (12.1)"
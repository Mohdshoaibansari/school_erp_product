"""C-04 Authorization — ABAC enhancement tests (REQ-AUTHZ-ABAC-07, AC-43..AC-48).

Tests the AuthorizationService pipeline with synthetic attribute providers.
No Teacher/Homework/Academic/Student business code is imported — all providers
are test-only synthetic implementations.

Sections:
- Task 9.1: Synthetic-attribute provider fixture
- Task 9.2: Pipeline unit tests
- Task 9.3: Security tests
- Task 9.5: Dependency-direction static check
"""

from __future__ import annotations

import asyncio
import os
import uuid
from typing import Any

import casbin
import pytest

from kernel.authz.models.authorization_types import (
    AuthorizationAttributes,
    AuthorizationDecision,
    AuthorizationRequest,
    AuthorizationAudit,
    ResourceContext,
    SubjectContext,
)
from kernel.authz.models.reason_codes import AuthorizationReasonCode
from kernel.authz.services.attribute_provider import (
    AuthorizationAttributeProvider,
    ProviderRegistry,
    IsSelfAttributeProvider,
)
from kernel.authz.services.authorization_service import AuthorizationService, match_attrs
from kernel.authz import manifest as authz_manifest
from kernel.authz.manifest import AuthorizationManifest
from kernel.authz.services import policy_loader as pl


# ============================================================
# Helpers
# ============================================================

# Default shared IDs for subject/resource scope matching
_DEFAULT_CLIENT_ID = uuid.uuid4()
_DEFAULT_INSTITUTION_ID = uuid.uuid4()

def _model_path() -> str:
    import kernel.authz
    return os.path.join(os.path.dirname(kernel.authz.__file__), "casbin_model.conf")


def _build_enforcer() -> casbin.Enforcer:
    """Build a Casbin enforcer with match_attrs registered."""
    e = casbin.Enforcer(_model_path())
    e.add_function("match_attrs", match_attrs)
    return e


def _make_subject(
    user_id: str = "u1",
    roles: tuple[str, ...] = ("Teacher",),
    client_id: uuid.UUID | None = None,
    institution_id: uuid.UUID | None = None,
    is_platform_owner: bool = False,
) -> SubjectContext:
    return SubjectContext(
        user_id=user_id,
        roles=roles,
        client_id=client_id if client_id is not None else _DEFAULT_CLIENT_ID,
        institution_id=institution_id if institution_id is not None else _DEFAULT_INSTITUTION_ID,
        user_tier="institution",
        is_platform_owner=is_platform_owner,
    )


def _make_resource(
    resource_type: str = "homework",
    resource_id: str = "HW1",
    client_id: uuid.UUID | None = None,
    institution_id: uuid.UUID | None = None,
    data: dict[str, Any] | None = None,
) -> ResourceContext:
    return ResourceContext(
        resource_type=resource_type,
        resource_id=resource_id,
        client_id=client_id if client_id is not None else _DEFAULT_CLIENT_ID,
        institution_id=institution_id if institution_id is not None else _DEFAULT_INSTITUTION_ID,
        data=data or {},
    )


def _make_request(
    subject: SubjectContext | None = None,
    resource: ResourceContext | None = None,
    action: str = "create",
) -> AuthorizationRequest:
    return AuthorizationRequest(
        subject=subject or _make_subject(),
        resource=resource or _make_resource(),
        action=action,
    )


def _build_service(
    enforcer: casbin.Enforcer | None = None,
    registry: ProviderRegistry | None = None,
) -> AuthorizationService:
    """Build an AuthorizationService with the given enforcer and registry."""
    e = enforcer or _build_enforcer()
    r = registry or ProviderRegistry()
    return AuthorizationService(
        enforcer=e,
        provider_registry=r,
        policy_catalog=pl,
    )


def _setup_base_policies(enforcer: casbin.Enforcer) -> None:
    """Register base test policies (Teacher + homework.create at institution scope)."""
    enforcer.add_role_for_user("Teacher", "Teacher")
    enforcer.add_role_for_user("HOD", "HOD")
    enforcer.add_role_for_user("Student", "Student")
    enforcer.add_role_for_user("Parent", "Parent")
    # Teacher: homework.create at institution scope
    enforcer.add_policy("Teacher", "homework", "create", "institution", "")
    # Teacher: homework.read at institution scope
    enforcer.add_policy("Teacher", "homework", "read", "institution", "")
    # HOD: homework.read at institution scope (but NOT create)
    enforcer.add_policy("HOD", "homework", "read", "institution", "")
    # Student: attendance.read at institution scope
    enforcer.add_policy("Student", "attendance", "read", "institution", "")


def _register_prod_po_policies(e: casbin.Enforcer) -> None:
    """Production-shape Platform Owner matrix (D6): explicit perms, no wildcard.

    Mirrors the migration 023 seeds exactly: (resource, action) tuples at scope
    ``'any'`` — no wildcard, no D11 g-hierarchy.
    """
    e.add_role_for_user("platform_owner", "platform_owner")
    for resource, action in [
        ("client", "create"), ("client", "read"), ("client", "update"),
        ("client", "transfer_ownership"), ("client", "transition_lifecycle"),
        ("institution_type", "read"), ("institution_type", "create"),
        ("institution_type", "update"),
    ]:
        e.add_policy("platform_owner", resource, action, "any", "")


# ============================================================
# Task 9.1 — Synthetic-attribute provider fixture
# ============================================================

class SyntheticTeacherProvider(AuthorizationAttributeProvider):
    """Test-only provider that returns is_subject_teacher from a fixed map.

    Keyed by request.resource.data["section_id"]. No Teacher/Homework/Academic
    business code is imported.
    """

    name = "test.synthetic_teacher"
    resource_types = frozenset({"homework"})
    attributes = frozenset({"is_subject_teacher"})

    # section_id → bool (simulates teacher assignment lookup)
    ASSIGNMENTS: dict[str, bool] = {
        "1A": True,   # Teacher is assigned to section 1A
        "4A": True,   # Teacher is assigned to section 4A
        "5A": False,  # Teacher is NOT assigned to section 5A
    }

    async def resolve(self, request: AuthorizationRequest) -> dict[str, Any]:
        section_id = request.resource.data.get("section_id", "")
        return {"is_subject_teacher": self.ASSIGNMENTS.get(section_id, False)}


class SyntheticParentProvider(AuthorizationAttributeProvider):
    """Test-only provider that returns is_parent_of_resource."""

    name = "test.synthetic_parent"
    resource_types = frozenset({"attendance"})
    attributes = frozenset({"is_parent_of_resource"})

    # parent_id → set of student_ids they are parent of
    PARENT_MAP: dict[str, set[str]] = {
        "P001": {"S002"},
    }

    async def resolve(self, request: AuthorizationRequest) -> dict[str, Any]:
        parent_id = request.subject.user_id
        student_id = request.resource.data.get("student_id", "")
        is_parent = parent_id in self.PARENT_MAP and student_id in self.PARENT_MAP[parent_id]
        return {"is_parent_of_resource": is_parent}


class TestSyntheticProvider:
    """Task 9.1: Synthetic-attribute provider fixture tests."""

    def test_synthetic_teacher_provider_registered(self):
        """SyntheticTeacherProvider can be registered and found."""
        r = ProviderRegistry()
        p = SyntheticTeacherProvider()
        r.register(p)
        assert r.providers_for("homework", "is_subject_teacher") is p
        assert r.providers_for("attendance", "is_subject_teacher") is None

    def test_synthetic_teacher_resolves_true(self):
        """Teacher assigned to section 1A → is_subject_teacher=True."""
        p = SyntheticTeacherProvider()
        req = _make_request(
            resource=_make_resource(data={"section_id": "1A"}),
        )
        result = asyncio.run(p.resolve(req))
        assert result == {"is_subject_teacher": True}

    def test_synthetic_teacher_resolves_false(self):
        """Teacher NOT assigned to section 5A → is_subject_teacher=False."""
        p = SyntheticTeacherProvider()
        req = _make_request(
            resource=_make_resource(data={"section_id": "5A"}),
        )
        result = asyncio.run(p.resolve(req))
        assert result == {"is_subject_teacher": False}

    def test_synthetic_allow_with_conditional_policy(self):
        """AC-46: Teacher T001 + homework.create + section 1A → ALLOW."""
        e = _build_enforcer()
        _setup_base_policies(e)
        # Register conditional policy: Teacher + homework.create requires is_subject_teacher
        pl._conditional.clear()
        pl._non_conditional.clear()
        pl._non_conditional["Teacher"] = [("homework", "create", "institution")]
        pl._conditional["Teacher"] = [("homework", "create", "institution", "is_subject_teacher")]

        r = ProviderRegistry()
        r.register(SyntheticTeacherProvider())
        svc = _build_service(enforcer=e, registry=r)

        req = _make_request(
            resource=_make_resource(data={"section_id": "1A"}),
        )
        decision = asyncio.run(svc.authorize(req))
        assert decision.allowed is True
        assert decision.reason == AuthorizationReasonCode.ALLOWED

    def test_synthetic_deny_with_conditional_policy(self):
        """AC-47: Teacher T001 + homework.create + section 5A → DENY."""
        e = _build_enforcer()
        # Do NOT call _setup_base_policies — it adds a non-conditional
        # (Teacher, homework, create, institution, "") policy that always
        # matches, defeating the conditional policy test.
        e.add_role_for_user("Teacher", "Teacher")
        pl._conditional.clear()
        pl._non_conditional.clear()
        # Only conditional policy — no non-conditional fallback
        pl._conditional["Teacher"] = [("homework", "create", "institution", "is_subject_teacher")]

        r = ProviderRegistry()
        r.register(SyntheticTeacherProvider())
        svc = _build_service(enforcer=e, registry=r)

        req = _make_request(
            resource=_make_resource(data={"section_id": "5A"}),
        )
        decision = asyncio.run(svc.authorize(req))
        assert decision.allowed is False
        assert decision.reason == AuthorizationReasonCode.NOT_ASSIGNED_TO_RESOURCE


# ============================================================
# Task 9.2 — Pipeline unit tests
# ============================================================

class TestPipelineUnit:
    """Task 9.2: Pipeline unit tests (REQ-AUTHZ-ABAC-07, AC-43)."""

    def setup_method(self):
        """Reset policy loader catalogs before each test."""
        pl._conditional.clear()
        pl._non_conditional.clear()

    def test_single_role_allow(self):
        """Single role with matching permission → ALLOW."""
        e = _build_enforcer()
        _setup_base_policies(e)
        pl._non_conditional["Teacher"] = [("homework", "create", "institution")]

        svc = _build_service(enforcer=e)
        req = _make_request()
        decision = asyncio.run(svc.authorize(req))
        assert decision.allowed is True

    def test_single_role_deny(self):
        """Single role without matching permission → DENY MISSING_PERMISSION."""
        e = _build_enforcer()
        _setup_base_policies(e)
        pl._non_conditional["Student"] = [("attendance", "read", "institution")]

        svc = _build_service(enforcer=e)
        req = _make_request(
            subject=_make_subject(roles=("Student",)),
        )
        decision = asyncio.run(svc.authorize(req))
        assert decision.allowed is False
        assert decision.reason == AuthorizationReasonCode.MISSING_PERMISSION

    def test_multi_role_any_valid_satisfies(self):
        """[HOD, Teacher] where only Teacher has homework.create → ALLOW."""
        e = _build_enforcer()
        _setup_base_policies(e)
        pl._non_conditional["Teacher"] = [("homework", "create", "institution")]
        pl._non_conditional["HOD"] = [("homework", "read", "institution")]

        svc = _build_service(enforcer=e)
        req = _make_request(
            subject=_make_subject(roles=("HOD", "Teacher")),
        )
        decision = asyncio.run(svc.authorize(req))
        assert decision.allowed is True

    def test_missing_permission(self):
        """No role has the permission → DENY MISSING_PERMISSION."""
        e = _build_enforcer()
        _setup_base_policies(e)
        pl._non_conditional["Teacher"] = [("homework", "read", "institution")]

        svc = _build_service(enforcer=e)
        req = _make_request(action="delete")
        decision = asyncio.run(svc.authorize(req))
        assert decision.allowed is False
        assert decision.reason == AuthorizationReasonCode.MISSING_PERMISSION

    def test_tenant_scope_mismatch(self):
        """sub.client_id != obj.client_id → DENY TENANT_ACCESS_DENIED."""
        e = _build_enforcer()
        _setup_base_policies(e)
        pl._non_conditional["Teacher"] = [("homework", "create", "institution")]

        client_a = uuid.uuid4()
        client_b = uuid.uuid4()
        svc = _build_service(enforcer=e)
        req = _make_request(
            subject=_make_subject(client_id=client_a),
            resource=_make_resource(client_id=client_b),
        )
        decision = asyncio.run(svc.authorize(req))
        assert decision.allowed is False
        assert decision.reason == AuthorizationReasonCode.TENANT_ACCESS_DENIED

    def test_institution_scope_mismatch(self):
        """Same client, different institution → DENY INSTITUTION_ACCESS_DENIED."""
        e = _build_enforcer()
        _setup_base_policies(e)
        pl._non_conditional["Teacher"] = [("homework", "create", "institution")]

        client_id = uuid.uuid4()
        inst_a = uuid.uuid4()
        inst_b = uuid.uuid4()
        svc = _build_service(enforcer=e)
        req = _make_request(
            subject=_make_subject(client_id=client_id, institution_id=inst_a),
            resource=_make_resource(client_id=client_id, institution_id=inst_b),
        )
        decision = asyncio.run(svc.authorize(req))
        assert decision.allowed is False
        assert decision.reason == AuthorizationReasonCode.INSTITUTION_ACCESS_DENIED

    def test_successful_abac(self):
        """is_subject_teacher=true → ALLOW with conditional policy."""
        e = _build_enforcer()
        _setup_base_policies(e)
        pl._non_conditional["Teacher"] = [("homework", "create", "institution")]
        pl._conditional["Teacher"] = [("homework", "create", "institution", "is_subject_teacher")]

        r = ProviderRegistry()
        r.register(SyntheticTeacherProvider())
        svc = _build_service(enforcer=e, registry=r)

        req = _make_request(
            resource=_make_resource(data={"section_id": "1A"}),
        )
        decision = asyncio.run(svc.authorize(req))
        assert decision.allowed is True

    def test_failed_abac(self):
        """D3: is_subject_teacher=false → DENY NOT_ASSIGNED_TO_RESOURCE (real assertion).

        No non-conditional fallback policy is registered — the conditional policy
        is the only grant path, so the denial happens inside the matcher.
        """
        e = _build_enforcer()
        e.add_role_for_user("Teacher", "Teacher")
        pl._conditional.clear()
        pl._non_conditional.clear()
        # Only conditional policy — no non-conditional fallback would defeat the ABAC check
        pl._conditional["Teacher"] = [("homework", "create", "institution", "is_subject_teacher")]

        r = ProviderRegistry()
        r.register(SyntheticTeacherProvider())
        svc = _build_service(enforcer=e, registry=r)

        # section 5A → provider resolves is_subject_teacher=False
        req = _make_request(
            resource=_make_resource(data={"section_id": "5A"}),
        )
        decision = asyncio.run(svc.authorize(req))
        assert decision.allowed is False
        assert decision.reason == AuthorizationReasonCode.NOT_ASSIGNED_TO_RESOURCE

    def test_abac_never_bypasses_rbac(self):
        """D3 case 5: ABAC must not bypass RBAC — attr could resolve True, but the
        requesting role has NO permission for (resource, action) → DENY.

        The provider is registered and would resolve True for section 1A, but the
        pipeline denies at the permission gate (MISSING_PERMISSION) and never
        consults the attribute provider — ABAC cannot turn a no-permission into an
        ALLOW.
        """
        e = _build_enforcer()
        e.add_role_for_user("Parent", "Parent")
        pl._conditional.clear()
        pl._non_conditional.clear()
        # The catalog declares the conditional policy only for Teacher — the
        # requesting role (Parent) has no homework.create permission anywhere.
        pl._conditional["Teacher"] = [("homework", "create", "institution", "is_subject_teacher")]

        calls = {"n": 0}

        class CountingTeacherProvider(SyntheticTeacherProvider):
            async def resolve(self, request):
                calls["n"] += 1
                return await super().resolve(request)

        r = ProviderRegistry()
        r.register(CountingTeacherProvider())
        svc = _build_service(enforcer=e, registry=r)

        # section 1A → CountingTeacherProvider would return is_subject_teacher=True
        req = _make_request(
            subject=_make_subject(roles=("Parent",)),
            resource=_make_resource(data={"section_id": "1A"}),
        )
        decision = asyncio.run(svc.authorize(req))
        assert decision.allowed is False
        assert decision.reason == AuthorizationReasonCode.MISSING_PERMISSION
        assert calls["n"] == 0, "Attribute provider must NOT be consulted on an RBAC denial"

    def test_provider_exception_fails_closed(self):
        """REQ-AUTHZ-FIX-TEST-03: provider raises → DENY UNRESOLVED_ATTRIBUTE, never ALLOW."""
        e = _build_enforcer()
        e.add_role_for_user("Teacher", "Teacher")
        pl._conditional.clear()
        pl._non_conditional.clear()
        pl._conditional["Teacher"] = [("homework", "create", "institution", "is_subject_teacher")]

        class ExplodingProvider(AuthorizationAttributeProvider):
            """Test-only provider that always raises."""

            name = "test.exploding"
            resource_types = frozenset({"homework"})
            attributes = frozenset({"is_subject_teacher"})

            async def resolve(self, request):
                raise RuntimeError("provider exploded")

        r = ProviderRegistry()
        r.register(ExplodingProvider())
        svc = _build_service(enforcer=e, registry=r)

        req = _make_request()
        decision = asyncio.run(svc.authorize(req))
        assert decision.allowed is False
        assert decision.reason == AuthorizationReasonCode.UNRESOLVED_ATTRIBUTE

    def test_missing_required_attribute_fail_closed(self):
        """No provider for required attribute → DENY UNRESOLVED_ATTRIBUTE."""
        e = _build_enforcer()
        _setup_base_policies(e)
        pl._non_conditional["Teacher"] = [("homework", "create", "institution")]
        pl._conditional["Teacher"] = [("homework", "create", "institution", "is_subject_teacher")]

        # No provider registered — fail-closed
        r = ProviderRegistry()
        svc = _build_service(enforcer=e, registry=r)

        req = _make_request()
        decision = asyncio.run(svc.authorize(req))
        assert decision.allowed is False
        assert decision.reason == AuthorizationReasonCode.UNRESOLVED_ATTRIBUTE

    def test_pure_rbac_fallback(self):
        """No attributes required → provider not invoked, pure RBAC."""
        e = _build_enforcer()
        _setup_base_policies(e)
        pl._non_conditional["Teacher"] = [("homework", "create", "institution")]
        # No conditional policies — pure RBAC

        calls = {"n": 0}

        class CountingProvider(AuthorizationAttributeProvider):
            name = "test.counter"
            resource_types = frozenset({"*"})
            attributes = frozenset({"x"})

            async def resolve(self, request):
                calls["n"] += 1
                return {"x": True}

        r = ProviderRegistry()
        r.register(CountingProvider())
        svc = _build_service(enforcer=e, registry=r)

        req = _make_request()
        decision = asyncio.run(svc.authorize(req))
        assert decision.allowed is True
        assert calls["n"] == 0, "Provider should NOT be invoked for pure-RBAC"

    def test_conflicting_assignments(self):
        """Teacher assigned to 1A, requested 1B → DENY."""
        e = _build_enforcer()
        # Only role assignment + conditional policy — no base non-conditional policy
        e.add_role_for_user("Teacher", "Teacher")
        pl._conditional["Teacher"] = [("homework", "create", "institution", "is_subject_teacher")]

        r = ProviderRegistry()
        r.register(SyntheticTeacherProvider())
        svc = _build_service(enforcer=e, registry=r)

        # Section 1B is not in SyntheticTeacherProvider.ASSIGNMENTS → defaults to False
        req = _make_request(
            resource=_make_resource(data={"section_id": "1B"}),
        )
        decision = asyncio.run(svc.authorize(req))
        assert decision.allowed is False

    def test_no_roles_deny(self):
        """No roles → DENY NO_ROLES."""
        e = _build_enforcer()
        svc = _build_service(enforcer=e)
        req = _make_request(
            subject=_make_subject(roles=()),
        )
        decision = asyncio.run(svc.authorize(req))
        assert decision.allowed is False
        assert decision.reason == AuthorizationReasonCode.NO_ROLES


# ============================================================
# Task 9.3 — Security tests
# ============================================================

class TestRawEnforcerBoundary:
    """D2: Casbin raw-enforcer-boundary ABAC tests (REQ-AUTHZ-FIX-ABAC-01/TEST-01).

    Calls ``enforcer.enforce()`` DIRECTLY — no AuthorizationService, no Python
    pre-check — proving the matcher path itself: attr=true → ALLOW, attr=false →
    DENY, attr=missing → DENY (fail-closed), no-attr → RBAC/scope only.
    """

    def _po_boundary_enforcer(self) -> casbin.Enforcer:
        """Enforcer with a conditional policy + a no-attr control policy."""
        e = _build_enforcer()
        e.add_role_for_user("Teacher", "Teacher")
        e.add_policy("Teacher", "homework", "create", "institution", "is_subject_teacher")
        e.add_policy("Teacher", "homework", "read", "institution", "")  # no-attr control
        return e

    def test_attr_true_allows(self):
        """attribute=true + conditional policy → ALLOW at the raw boundary."""
        e = self._po_boundary_enforcer()
        sub = {
            "role": "Teacher",
            "client_id": str(_DEFAULT_CLIENT_ID),
            "institution_id": str(_DEFAULT_INSTITUTION_ID),
            "is_subject_teacher": True,
        }
        obj = {
            "name": "homework",
            "client_id": str(_DEFAULT_CLIENT_ID),
            "institution_id": str(_DEFAULT_INSTITUTION_ID),
        }
        assert e.enforce(sub, obj, "create") is True

    def test_attr_false_denies(self):
        """attribute=false + conditional policy → DENY inside Casbin (no pre-check)."""
        e = self._po_boundary_enforcer()
        sub = {
            "role": "Teacher",
            "client_id": str(_DEFAULT_CLIENT_ID),
            "institution_id": str(_DEFAULT_INSTITUTION_ID),
            "is_subject_teacher": False,
        }
        obj = {
            "name": "homework",
            "client_id": str(_DEFAULT_CLIENT_ID),
            "institution_id": str(_DEFAULT_INSTITUTION_ID),
        }
        assert e.enforce(sub, obj, "create") is False

    def test_attr_missing_denies(self):
        """attribute key ABSENT from subject → DENY (None is True → matcher false)."""
        e = self._po_boundary_enforcer()
        sub = {
            "role": "Teacher",
            "client_id": str(_DEFAULT_CLIENT_ID),
            "institution_id": str(_DEFAULT_INSTITUTION_ID),
            # NOTE: is_subject_teacher key intentionally ABSENT
        }
        obj = {
            "name": "homework",
            "client_id": str(_DEFAULT_CLIENT_ID),
            "institution_id": str(_DEFAULT_INSTITUTION_ID),
        }
        assert e.enforce(sub, obj, "create") is False

    def test_no_attr_falls_back_to_rbac_scope(self):
        """no attribute condition (attrs="") → pure RBAC/scope evaluation."""
        e = self._po_boundary_enforcer()
        sub = {
            "role": "Teacher",
            "client_id": str(_DEFAULT_CLIENT_ID),
            "institution_id": str(_DEFAULT_INSTITUTION_ID),
        }
        obj = {
            "name": "homework",
            "client_id": str(_DEFAULT_CLIENT_ID),
            "institution_id": str(_DEFAULT_INSTITUTION_ID),
        }
        # read policy has attrs="" → allowed via RBAC+scope; create requires the attr → denied
        assert e.enforce(sub, obj, "read") is True
        assert e.enforce(sub, obj, "create") is False


class TestSecurity:
    """Task 9.3: Security tests (REQ-AUTHZ-ABAC-05, AC-44)."""

    def setup_method(self):
        """Reset policy loader catalogs before each test."""
        pl._conditional.clear()
        pl._non_conditional.clear()

    def test_cross_client_denied(self):
        """Client A → Client B resource → DENY TENANT_ACCESS_DENIED."""
        e = _build_enforcer()
        _setup_base_policies(e)
        pl._non_conditional["Teacher"] = [("homework", "create", "institution")]

        client_a = uuid.uuid4()
        client_b = uuid.uuid4()
        svc = _build_service(enforcer=e)
        req = _make_request(
            subject=_make_subject(client_id=client_a),
            resource=_make_resource(client_id=client_b),
        )
        decision = asyncio.run(svc.authorize(req))
        assert decision.allowed is False
        assert decision.reason == AuthorizationReasonCode.TENANT_ACCESS_DENIED

    def test_cross_institution_denied(self):
        """Institution A → Institution B → DENY INSTITUTION_ACCESS_DENIED."""
        e = _build_enforcer()
        _setup_base_policies(e)
        pl._non_conditional["Teacher"] = [("homework", "create", "institution")]

        client_id = uuid.uuid4()
        inst_a = uuid.uuid4()
        inst_b = uuid.uuid4()
        svc = _build_service(enforcer=e)
        req = _make_request(
            subject=_make_subject(client_id=client_id, institution_id=inst_a),
            resource=_make_resource(client_id=client_id, institution_id=inst_b),
        )
        decision = asyncio.run(svc.authorize(req))
        assert decision.allowed is False
        assert decision.reason == AuthorizationReasonCode.INSTITUTION_ACCESS_DENIED

    def test_teacher_assigned_to_1a_allow(self):
        """Teacher assigned to 1A → 1A ALLOW."""
        e = _build_enforcer()
        _setup_base_policies(e)
        pl._non_conditional["Teacher"] = [("homework", "create", "institution")]
        pl._conditional["Teacher"] = [("homework", "create", "institution", "is_subject_teacher")]

        r = ProviderRegistry()
        r.register(SyntheticTeacherProvider())
        svc = _build_service(enforcer=e, registry=r)

        req = _make_request(
            resource=_make_resource(data={"section_id": "1A"}),
        )
        decision = asyncio.run(svc.authorize(req))
        assert decision.allowed is True

    def test_teacher_assigned_to_1a_deny_1b(self):
        """Teacher assigned to 1A → 1B DENY."""
        e = _build_enforcer()
        # Only role assignment + conditional policy — no base non-conditional policy
        e.add_role_for_user("Teacher", "Teacher")
        pl._conditional["Teacher"] = [("homework", "create", "institution", "is_subject_teacher")]

        r = ProviderRegistry()
        r.register(SyntheticTeacherProvider())
        svc = _build_service(enforcer=e, registry=r)

        # 1B not in assignments → False
        req = _make_request(
            resource=_make_resource(data={"section_id": "1B"}),
        )
        decision = asyncio.run(svc.authorize(req))
        assert decision.allowed is False

    def test_student_self_access_allow(self):
        """Student S1 → S1 attendance → is_self=true → ALLOW."""
        e = _build_enforcer()
        _setup_base_policies(e)
        pl._non_conditional["Student"] = [("attendance", "read", "institution")]
        pl._conditional["Student"] = [("attendance", "read", "institution", "is_self")]

        r = ProviderRegistry()
        r.register(IsSelfAttributeProvider())
        svc = _build_service(enforcer=e, registry=r)

        req = _make_request(
            subject=_make_subject(user_id="S1", roles=("Student",)),
            resource=_make_resource(
                resource_type="attendance",
                data={"owner_id": "S1"},
            ),
            action="read",
        )
        decision = asyncio.run(svc.authorize(req))
        assert decision.allowed is True

    def test_student_self_access_deny_other(self):
        """Student S1 → S2 attendance → is_self=false → DENY NOT_SELF."""
        e = _build_enforcer()
        # Only role assignment + conditional policy — no base non-conditional policy
        e.add_role_for_user("Student", "Student")
        pl._conditional["Student"] = [("attendance", "read", "institution", "is_self")]

        r = ProviderRegistry()
        r.register(IsSelfAttributeProvider())
        svc = _build_service(enforcer=e, registry=r)

        req = _make_request(
            subject=_make_subject(user_id="S1", roles=("Student",)),
            resource=_make_resource(
                resource_type="attendance",
                data={"owner_id": "S2"},
            ),
            action="read",
        )
        decision = asyncio.run(svc.authorize(req))
        assert decision.allowed is False
        assert decision.reason == AuthorizationReasonCode.NOT_SELF

    def test_client_supplied_attribute_ignored(self):
        """Client-supplied is_subject_teacher=true in resource.data is IGNORED.

        The attribute must be resolved server-side by the provider.
        """
        e = _build_enforcer()
        # Only role assignment + conditional policy — no base non-conditional policy
        e.add_role_for_user("Teacher", "Teacher")
        pl._conditional["Teacher"] = [("homework", "create", "institution", "is_subject_teacher")]

        r = ProviderRegistry()
        r.register(SyntheticTeacherProvider())
        svc = _build_service(enforcer=e, registry=r)

        # Client tries to supply is_subject_teacher=true in the data
        # But section 5A → provider returns False → DENY
        req = _make_request(
            resource=_make_resource(data={"section_id": "5A", "is_subject_teacher": True}),
        )
        decision = asyncio.run(svc.authorize(req))
        assert decision.allowed is False
        # The provider's result (False) overrides the client-supplied value
        assert decision.reason == AuthorizationReasonCode.NOT_ASSIGNED_TO_RESOURCE


# ============================================================
# Task 9.5 — Dependency-direction static check
# ============================================================

class TestPlatformOwnerSecurity:
    """D7/REQ-AUTHZ-FIX-TEST-02: Platform Owner security matrix.

    Production-shape PO matrix (explicit perms, no wildcard): PO + client.read →
    ALLOW via the normal pipeline; PO on institute operational resources and
    unconfigured permissions → DENY MISSING_PERMISSION.
    """

    def setup_method(self):
        """Reset policy loader catalogs before each test."""
        pl._conditional.clear()
        pl._non_conditional.clear()

    def _po_subject(self, roles: tuple[str, ...] = ("platform_owner",)) -> SubjectContext:
        return SubjectContext(
            user_id="po1",
            roles=roles,
            client_id=None,
            institution_id=None,
            user_tier="platform",
            is_platform_owner=True,
        )

    def _po_request(self, resource: str = "client", action: str = "read") -> AuthorizationRequest:
        return AuthorizationRequest(
            subject=self._po_subject(),
            resource=ResourceContext(
                resource_type=resource, resource_id=None,
                client_id=None, institution_id=None, data={},
            ),
            action=action,
        )

    def test_po_client_read_allows(self):
        """PO + client.read on a client/platform resource → ALLOW through the pipeline."""
        e = _build_enforcer()
        _register_prod_po_policies(e)
        svc = _build_service(enforcer=e)

        decision = asyncio.run(svc.authorize(self._po_request("client", "read")))
        assert decision.allowed is True
        assert decision.reason == AuthorizationReasonCode.ALLOWED
        assert decision.policy_id is not None
        assert len(decision.policy_id.split(":")) == 5, decision.policy_id
        assert decision.policy_id.startswith("platform_owner:client:read:any"), decision.policy_id

    def test_po_raw_enforcer_client_read(self):
        """platform_owner + client.read (scope any) on a cross-client obj → True."""
        e = _build_enforcer()
        _register_prod_po_policies(e)
        sub = {"role": "platform_owner", "client_id": "", "institution_id": ""}
        obj = {"name": "client", "client_id": "client-999", "institution_id": ""}
        assert e.enforce(sub, obj, "read") is True

    @pytest.mark.parametrize("resource", ["student", "teacher", "attendance", "homework"])
    def test_po_denied_operational_resources(self, resource):
        """PO → student/teacher/attendance/homework → DENY MISSING_PERMISSION."""
        e = _build_enforcer()
        _register_prod_po_policies(e)
        svc = _build_service(enforcer=e)

        decision = asyncio.run(svc.authorize(self._po_request(resource, "read")))
        assert decision.allowed is False
        assert decision.reason == AuthorizationReasonCode.MISSING_PERMISSION

    @pytest.mark.parametrize("resource,action", [
        ("user", "create"),
        ("institution", "read"),
    ])
    def test_po_denied_unconfigured_permissions(self, resource, action):
        """PO → user.create / institution.read (exist for other roles, not PO) → DENY."""
        e = _build_enforcer()
        _register_prod_po_policies(e)
        svc = _build_service(enforcer=e)

        decision = asyncio.run(svc.authorize(self._po_request(resource, action)))
        assert decision.allowed is False
        assert decision.reason == AuthorizationReasonCode.MISSING_PERMISSION

    def test_po_subject_normalization(self):
        """from_tenant_context with is_platform_owner=True, roles=[] → ('platform_owner',)."""
        from kernel.tenant_context import TenantContext
        ctx = TenantContext(
            client_id=uuid.uuid4(), institution_id=None,
            user_id="po1", roles=[], is_platform_owner=True,
        )
        s = SubjectContext.from_tenant_context(ctx)
        assert s.roles == ("platform_owner",), s.roles

        ctx2 = TenantContext(
            client_id=uuid.uuid4(), institution_id=None,
            user_id="u1", roles=["Teacher"], is_platform_owner=False,
        )
        assert SubjectContext.from_tenant_context(ctx2).roles == ("Teacher",)

    def test_po_multi_role_no_double_grant(self):
        """PO with [platform_owner, client_director] → granted ONLY via a matching policy."""
        e = _build_enforcer()
        _register_prod_po_policies(e)
        # client_director also holds client.read at tenant scope (production shape)
        e.add_role_for_user("client_director", "client_director")
        e.add_policy("client_director", "client", "read", "tenant", "")
        svc = _build_service(enforcer=e)

        # client.read → ALLOW (matching policy exists for platform_owner)
        req = AuthorizationRequest(
            subject=self._po_subject(roles=("platform_owner", "client_director")),
            resource=ResourceContext(
                resource_type="client", resource_id=None,
                client_id=None, institution_id=None, data={},
            ),
            action="read",
        )
        d1 = asyncio.run(svc.authorize(req))
        assert d1.allowed is True
        assert d1.reason == AuthorizationReasonCode.ALLOWED

        # student.read → DENY — no role holds a matching policy → no second grant
        req2 = AuthorizationRequest(
            subject=self._po_subject(roles=("platform_owner", "client_director")),
            resource=ResourceContext(
                resource_type="student", resource_id=None,
                client_id=None, institution_id=None, data={},
            ),
            action="read",
        )
        d2 = asyncio.run(svc.authorize(req2))
        assert d2.allowed is False
        assert d2.reason == AuthorizationReasonCode.MISSING_PERMISSION


class TestProductionRegistrationAndPolicyId:
    """D8/REQ-AUTHZ-FIX-REG-01 + D9/REQ-AUTHZ-FIX-PID-01."""

    def setup_method(self):
        """Reset policy loader catalogs before each test."""
        pl._conditional.clear()
        pl._non_conditional.clear()

    def test_production_conditional_policy_registration(self):
        """manifest.register_authorization_policies wires declared conditional policies."""
        manifest = AuthorizationManifest()
        e = _build_enforcer()

        original = list(authz_manifest._PRODUCTION_CONDITIONAL_POLICIES)
        saved_map = {k: list(v) for k, v in pl._permission_map.items()}
        try:
            authz_manifest._PRODUCTION_CONDITIONAL_POLICIES = [
                ("Teacher", "homework", "create", "institution", ["is_subject_teacher"])
            ]
            manifest.register_authorization_policies(e)

            # Conditional policy lands as a 5-arg policy in the enforcer
            policies = {tuple(p) for p in e.get_policy()}
            assert ("Teacher", "homework", "create", "institution", "is_subject_teacher") in policies
            # And the in-memory conditional catalog holds the entry
            assert ("homework", "create", "institution", "is_subject_teacher") in pl._conditional["Teacher"]

            # Non-conditional DB path is unchanged — register_policies_from_map adds ""-attrs policies
            pl._permission_map.clear()
            pl._permission_map["Teacher"] = [("homework", "read", "institution")]
            pl.register_policies_from_map(e)
            assert ("Teacher", "homework", "read", "institution", "") in {tuple(p) for p in e.get_policy()}
            assert ("homework", "read", "institution") in pl._non_conditional["Teacher"]
        finally:
            authz_manifest._PRODUCTION_CONDITIONAL_POLICIES = original
            pl._permission_map.clear()
            pl._permission_map.update(saved_map)

    def test_extract_policy_id_includes_attrs(self):
        """Two conditional policies differing only in attrs → distinct 5-part ids."""
        e = _build_enforcer()
        e.add_role_for_user("Teacher", "Teacher")
        e.add_policy("Teacher", "homework", "create", "institution", "is_subject_teacher")
        e.add_policy("Teacher", "homework", "create", "institution", "is_class_teacher")
        svc = _build_service(enforcer=e)

        obj = {
            "name": "homework",
            "client_id": str(_DEFAULT_CLIENT_ID),
            "institution_id": str(_DEFAULT_INSTITUTION_ID),
        }
        sub1 = {
            "role": "Teacher",
            "client_id": str(_DEFAULT_CLIENT_ID),
            "institution_id": str(_DEFAULT_INSTITUTION_ID),
            "is_subject_teacher": True,
        }
        sub2 = {
            "role": "Teacher",
            "client_id": str(_DEFAULT_CLIENT_ID),
            "institution_id": str(_DEFAULT_INSTITUTION_ID),
            "is_class_teacher": True,
        }
        id1 = svc._extract_policy_id(sub1, obj, "create")
        id2 = svc._extract_policy_id(sub2, obj, "create")
        assert id1 == "Teacher:homework:create:institution:is_subject_teacher"
        assert id2 == "Teacher:homework:create:institution:is_class_teacher"
        assert id1 != id2

    def test_extract_policy_id_scope_filtered(self):
        """Scope filter names the matching scope's id, never a non-matching one."""
        e = _build_enforcer()
        e.add_role_for_user("Teacher", "Teacher")
        e.add_policy("Teacher", "homework", "read", "institution", "")
        e.add_policy("Teacher", "homework", "read", "tenant", "")
        svc = _build_service(enforcer=e)

        client_a = str(uuid.uuid4())
        inst_a = str(uuid.uuid4())
        inst_b = str(uuid.uuid4())
        sub = {"role": "Teacher", "client_id": client_a, "institution_id": inst_a}

        # Same client + same institution → institution-scope policy matches first
        obj_same = {"name": "homework", "client_id": client_a, "institution_id": inst_a}
        assert svc._extract_policy_id(sub, obj_same, "read") == "Teacher:homework:read:institution:"

        # Same client, different institution → institution scope does NOT match,
        # so only the tenant-scope policy qualifies (scope filter)
        obj_cross_inst = {"name": "homework", "client_id": client_a, "institution_id": inst_b}
        assert svc._extract_policy_id(sub, obj_cross_inst, "read") == "Teacher:homework:read:tenant:"

    def test_identification_never_grants(self):
        """_extract_policy_id never influences the decision — enforce() outcome unchanged."""
        e = _build_enforcer()
        e.add_role_for_user("Teacher", "Teacher")
        e.add_policy("Teacher", "homework", "create", "institution", "is_subject_teacher")
        svc = _build_service(enforcer=e)

        obj = {
            "name": "homework",
            "client_id": str(_DEFAULT_CLIENT_ID),
            "institution_id": str(_DEFAULT_INSTITUTION_ID),
        }
        # ALLOW case: decision independent of the audit helper
        sub_ok = {
            "role": "Teacher",
            "client_id": str(_DEFAULT_CLIENT_ID),
            "institution_id": str(_DEFAULT_INSTITUTION_ID),
            "is_subject_teacher": True,
        }
        assert e.enforce(sub_ok, obj, "create") is True
        assert svc._extract_policy_id(sub_ok, obj, "create") == "Teacher:homework:create:institution:is_subject_teacher"
        # DENY case: attr false → enforce False; helper must not report a grant
        sub_bad = {
            "role": "Teacher",
            "client_id": str(_DEFAULT_CLIENT_ID),
            "institution_id": str(_DEFAULT_INSTITUTION_ID),
            "is_subject_teacher": False,
        }
        assert e.enforce(sub_bad, obj, "create") is False
        assert svc._extract_policy_id(sub_bad, obj, "create") is None


class TestPlatformOwnerSeedMatrix:
    """D6/REQ-AUTHZ-FIX-PO-01: DB-level check of the seeded PO permission matrix."""

    def test_po_has_client_read(self, db_engine):
        """The seeded matrix grants platform_owner client.read at scope 'any'.

        Depends on the test harness applying Alembic migrations (conftest
        ``_reset_database`` runs ``alembic upgrade head``), which includes
        migration 023_fix_c04_abac_po_permissions.
        """
        from sqlalchemy import text
        with db_engine.connect() as conn:
            row = conn.execute(text("""
                SELECT COUNT(*) FROM role_permission rp
                JOIN role r ON r.id = rp.role_id
                JOIN permission p ON p.id = rp.permission_id
                WHERE r.name = 'platform_owner'
                  AND p.name = 'client.read'
                  AND rp.scope = 'any'
            """)).scalar_one()
        assert row == 1


class TestKernelBoundary:
    """Task 9.5: Dependency-direction static check (AC-9, AC-14, AC-40, AC-41)."""

    def test_kernel_authz_no_business_imports(self):
        """kernel/authz/ must NOT import any business/ symbol."""
        import os
        kernel_authz_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "kernel", "authz",
        )
        business_imports = []
        for root, dirs, files in os.walk(kernel_authz_dir):
            for fname in files:
                if not fname.endswith(".py"):
                    continue
                fpath = os.path.join(root, fname)
                with open(fpath) as f:
                    for i, line in enumerate(f, 1):
                        stripped = line.strip()
                        if stripped.startswith("#"):
                            continue
                        if "from business." in stripped or "import business." in stripped:
                            business_imports.append(f"{fpath}:{i}: {stripped}")
        assert business_imports == [], (
            f"kernel/authz/ imports business/ symbols: {business_imports}"
        )

    def test_kernel_authz_no_business_orm_models(self):
        """kernel/authz/ must NOT import Teacher, Student, Parent, Homework ORM models."""
        import os
        kernel_authz_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "kernel", "authz",
        )
        forbidden = ["Teacher", "Student", "Parent", "Homework", "Attendance"]
        violations = []
        for root, dirs, files in os.walk(kernel_authz_dir):
            for fname in files:
                if not fname.endswith(".py"):
                    continue
                fpath = os.path.join(root, fname)
                with open(fpath) as f:
                    for i, line in enumerate(f, 1):
                        stripped = line.strip()
                        if stripped.startswith("#"):
                            continue
                        for name in forbidden:
                            if f"import {name}" in stripped or f"from.*{name}" in stripped:
                                # Check it's actually an import statement
                                if "import" in stripped and name in stripped:
                                    violations.append(f"{fpath}:{i}: {stripped}")
        assert violations == [], (
            f"kernel/authz/ imports business ORM models: {violations}"
        )

    def test_kernel_authz_no_po_bypass_pattern(self):
        """Static guard: no PO short-circuit remains in service or legacy fallback (D4).

        The unconditional Platform Owner ALLOW is removed from both
        authorization_service.py (Step 1) and dependencies.py (_check_impl_legacy).
        This test fails loudly if the bypass pattern is reintroduced.
        """
        import os
        import re
        base = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "kernel", "authz",
        )
        svc_path = os.path.join(base, "services", "authorization_service.py")
        deps_path = os.path.join(base, "dependencies.py")

        # authorization_service.py: no is_platform_owner-driven ALLOW / early return
        with open(svc_path, encoding="utf-8") as f:
            for i, line in enumerate(f, 1):
                stripped = line.strip()
                if stripped.startswith("#"):
                    continue
                if re.search(r"is_platform_owner.*(allowed\s*=\s*True|return decision)", stripped):
                    raise AssertionError(
                        f"{svc_path}:{i}: PO short-circuit pattern: {stripped}"
                    )

        # dependencies.py: no legacy PO bypass block (returns before role validation)
        with open(deps_path, encoding="utf-8") as f:
            for i, line in enumerate(f, 1):
                if "Platform owner bypass" in line or "Platform Owner bypass" in line:
                    raise AssertionError(
                        f"{deps_path}:{i}: legacy PO bypass marker: {line.strip()}"
                    )

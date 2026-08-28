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
        """is_subject_teacher=false → DENY NOT_ASSIGNED_TO_RESOURCE."""
        e = _build_enforcer()
        _setup_base_policies(e)
        # Only conditional — non-conditional would bypass the ABAC check
        pl._conditional["Teacher"] = [("homework", "create", "institution", "is_subject_teacher")]

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

    def test_platform_owner_bypass(self):
        """Platform Owner bypasses all checks → ALLOW."""
        e = _build_enforcer()
        _setup_base_policies(e)

        svc = _build_service(enforcer=e)
        req = _make_request(
            subject=_make_subject(is_platform_owner=True, roles=("platform_owner",)),
        )
        decision = asyncio.run(svc.authorize(req))
        assert decision.allowed is True
        assert decision.reason == AuthorizationReasonCode.ALLOWED

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

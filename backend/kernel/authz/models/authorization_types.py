"""C-04 Authorization — Kernel-owned authorization types (D1, D13, REQ-AUTHZ-ABAC-01).

Defines five Kernel-owned ``@dataclass`` types with **no ORM imports**:
- ``SubjectContext`` (frozen): identity/security facts from TenantContext.
- ``ResourceContext`` (frozen): resource-specific facts from the business operation.
- ``AuthorizationAttributes`` (mutable): domain attributes + provenance + fail-closed bookkeeping.
- ``AuthorizationRequest`` (frozen): composes subject, resource, action, attributes.
- ``AuthorizationDecision`` (frozen): carries allowed, reason, policy_id, audit.
- ``AuthorizationAudit`` (frozen): structured audit context (D13).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Mapping

if TYPE_CHECKING:
    from kernel.authz.models.reason_codes import AuthorizationReasonCode


@dataclass(frozen=True)
class SubjectContext:
    """Request-scoped subject identity (D1).

    Derived from ``TenantContext`` via ``from_tenant_context()``.
    Carries generic identity/security facts — no business-domain data.
    """

    user_id: str | None
    roles: tuple[str, ...]
    client_id: uuid.UUID | None
    institution_id: uuid.UUID | None
    user_tier: str | None
    is_platform_owner: bool

    @classmethod
    def from_tenant_context(cls, ctx: Any) -> SubjectContext:
        """Construct a SubjectContext from a TenantContext.

        Maps ``TenantContext`` fields (roles list → tuple).
        """
        return cls(
            user_id=ctx.user_id,
            roles=tuple(ctx.roles or []),
            client_id=ctx.client_id,
            institution_id=ctx.institution_id,
            user_tier=ctx.user_tier,
            is_platform_owner=ctx.is_platform_owner,
        )


@dataclass(frozen=True)
class ResourceContext:
    """Request-scoped resource identity (D1).

    Carries resource-specific facts supplied by the business operation.
    ``data`` is the generic extension point for domain-specific fields
    (section_id, subject_id, academic_year_id, student_id, owner_id, etc.)
    without the Kernel importing business models.
    """

    resource_type: str
    resource_id: str | uuid.UUID | None
    client_id: uuid.UUID | None
    institution_id: uuid.UUID | None
    data: Mapping[str, Any] = field(default_factory=dict)


@dataclass
class AuthorizationAttributes:
    """Domain attributes + provenance + fail-closed bookkeeping (D1, D5).

    Mutable — populated during the authorization pipeline.
    ``values``: resolved domain attribute key-value pairs.
    ``resolved_by``: attr name → provider name (provenance).
    ``unresolved``: required-but-unresolved attribute names (fail-closed).
    """

    values: dict[str, Any] = field(default_factory=dict)
    resolved_by: dict[str, str] = field(default_factory=dict)
    unresolved: set[str] = field(default_factory=set)


@dataclass(frozen=True)
class AuthorizationRequest:
    """Composes subject, resource, action, and attributes (D1, REQ-AUTHZ-ABAC-01).

    ``attributes`` is defaulted to an empty ``AuthorizationAttributes`` and
    populated during the pipeline.
    """

    subject: SubjectContext
    resource: ResourceContext
    action: str
    attributes: AuthorizationAttributes = field(default_factory=AuthorizationAttributes)


@dataclass(frozen=True)
class AuthorizationAudit:
    """Structured audit context for every authorization decision (D13).

    Captures the full decision trace: correlation_id, user, client, institution,
    action, resource, roles, scope, policy_id, decision, reason.
    Domain attribute values are redacted by default (AC-33).
    """

    correlation_id: str
    user_id: str | None
    client_id: str | None
    institution_id: str | None
    action: str
    resource_type: str
    resource_id: str | None
    roles: tuple[str, ...]
    scope: str | None
    policy_id: str | None
    decision: bool
    reason: str  # AuthorizationReasonCode.value — stored as str to avoid import cycle


@dataclass(frozen=True)
class AuthorizationDecision:
    """Authorization result (D1, REQ-AUTHZ-ABAC-01).

    Carries ``allowed`` (bool), ``reason`` (structured code), ``policy_id``,
    and optional ``audit`` context.
    """

    allowed: bool
    reason: AuthorizationReasonCode
    policy_id: str | None = None
    audit: AuthorizationAudit | None = None

"""C-04 Authorization — structured reason codes (D2, REQ-AUTHZ-ABAC-03).

Defines the ``AuthorizationReasonCode`` enum and the Kernel-owned static map
``_ATTRIBUTE_DENY_REASON`` that maps false-attribute names to specific reason
codes.  Reason codes are machine-readable, stable, and safe for internal logs
and controlled API responses.
"""

from __future__ import annotations

import enum


class AuthorizationReasonCode(str, enum.Enum):
    """Stable, machine-readable authorization denial reason codes.

    The nine required codes (AC-19) plus two Kernel-internal refinements
    (``NO_ROLES``, ``UNRESOLVED_ATTRIBUTE``).
    """

    # --- Required codes (AC-19) ---
    MISSING_PERMISSION = "MISSING_PERMISSION"
    """No role has the (resource, action) permission in either catalog."""

    INVALID_SCOPE = "INVALID_SCOPE"
    """Permission exists but no scope matches (fallback)."""

    TENANT_ACCESS_DENIED = "TENANT_ACCESS_DENIED"
    """sub.client_id != obj.client_id — tenant scope violated."""

    INSTITUTION_ACCESS_DENIED = "INSTITUTION_ACCESS_DENIED"
    """Client matches, institution differs — institution scope violated."""

    ATTRIBUTE_CONDITION_FAILED = "ATTRIBUTE_CONDITION_FAILED"
    """Required attribute resolved but false (generic default)."""

    NOT_ASSIGNED_TO_RESOURCE = "NOT_ASSIGNED_TO_RESOURCE"
    """is_assigned_to_resource / is_class_teacher / is_subject_teacher resolved false."""

    NOT_SELF = "NOT_SELF"
    """is_self resolved false — self-access attribute failed."""

    NOT_PARENT_OF_RESOURCE = "NOT_PARENT_OF_RESOURCE"
    """is_parent_of_resource resolved false."""

    POLICY_DENIED = "POLICY_DENIED"
    """Explicit deny or unmatched (defensive fallback)."""

    # --- Kernel-internal refinements ---
    NO_ROLES = "NO_ROLES"
    """Subject has zero effective roles (pre-RBAC check)."""

    UNRESOLVED_ATTRIBUTE = "UNRESOLVED_ATTRIBUTE"
    """Required attribute has no provider or provider errored (fail-closed, D6)."""

    # --- Success ---
    ALLOWED = "ALLOWED"
    """Authorization granted."""


# Kernel-owned static map: false-attribute → specific reason code (D2).
# Used by _classify_denial() to produce precise denial reasons.
_ATTRIBUTE_DENY_REASON: dict[str, AuthorizationReasonCode] = {
    "is_self": AuthorizationReasonCode.NOT_SELF,
    "is_parent_of_resource": AuthorizationReasonCode.NOT_PARENT_OF_RESOURCE,
    "is_assigned_to_resource": AuthorizationReasonCode.NOT_ASSIGNED_TO_RESOURCE,
    "is_class_teacher": AuthorizationReasonCode.NOT_ASSIGNED_TO_RESOURCE,
    "is_subject_teacher": AuthorizationReasonCode.NOT_ASSIGNED_TO_RESOURCE,
}

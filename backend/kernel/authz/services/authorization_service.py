"""C-04 Authorization — AuthorizationService pipeline (D6, D7, D8, D9, D13, D14).

Implements the single authorization decision pipeline:
1. Platform Owner bypass
2. No roles → DENY
3. Determine required attributes from policy catalog
4. Resolve required attributes (fail-closed)
5. Casbin — evaluate ALL roles (multi-role loop)
6. Classify denial reason (catalog + attr map)
7. Emit audit record

Also defines:
- ``match_attrs`` — custom Casbin function for domain attribute evaluation (D8)
- ``_classify_denial`` — reason discriminator (D9)
- ``_enforce`` — multi-role Casbin evaluation (D7)
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from kernel.authz.models.authorization_types import (
    AuthorizationAudit,
    AuthorizationDecision,
    AuthorizationRequest,
)
from kernel.authz.models.reason_codes import (
    AuthorizationReasonCode,
    _ATTRIBUTE_DENY_REASON,
)

logger = logging.getLogger("kernel.authz")


# ============================================================
# Custom Casbin function: match_attrs (D8)
# ============================================================

def match_attrs(sub: dict, attrs: str) -> bool:
    """Custom Casbin matcher function for domain attribute evaluation (D8).

    ``attrs`` is a comma-separated list of required boolean attribute names
    (e.g., ``"is_subject_teacher"``, ``"is_self"``). Returns True if ALL
    named attributes are truthy on the subject dict.

    Args:
        sub: The Casbin subject dict (r.sub) — carries role, client_id,
             institution_id, plus resolved domain attributes.
        attrs: Comma-separated attribute names from the policy, or ""/"*"
               for no attribute condition.

    Returns:
        True if all required attributes are truthy, False otherwise.
    """
    if not attrs or attrs in ("*", ""):
        return True
    return all(bool(sub.get(a)) for a in attrs.split(","))


# ============================================================
# AuthorizationService
# ============================================================

class AuthorizationService:
    """Single authorization decision pipeline (D6, REQ-AUTHZ-ABAC-04).

    Orchestrates: Platform Owner bypass → no-roles check → required-attribute
    determination → attribute resolution → Casbin multi-role enforcement →
    denial classification → audit emission.

    The enforcer remains the sole granter. The Python-side reason discriminator
    runs only on DENY to label why; it never grants access.
    """

    def __init__(
        self,
        enforcer: Any,
        provider_registry: Any,  # ProviderRegistry
        policy_catalog: Any,     # module with required_attributes, has_permission, matching_scopes
    ) -> None:
        self._enforcer = enforcer
        self._registry = provider_registry
        self._catalog = policy_catalog

    async def authorize(self, request: AuthorizationRequest) -> AuthorizationDecision:
        """Execute the authorization pipeline and return a structured decision.

        Pipeline order (D6):
        1. Platform Owner bypass → ALLOW
        2. No roles → DENY(NO_ROLES)
        3. Determine required attributes from policy catalog
        4. Resolve required attributes (fail-closed)
        5. Casbin — evaluate ALL roles
        6. On ALLOW → return ALLOWED; on DENY → classify denial reason
        7. Emit audit record on every decision
        """
        # Step 1: Platform Owner bypass (D28) — unchanged
        if request.subject.is_platform_owner or "platform_owner" in request.subject.roles:
            decision = AuthorizationDecision(
                allowed=True,
                reason=AuthorizationReasonCode.ALLOWED,
            )
            self._emit_audit(request, decision)
            return decision

        # Step 2: No roles
        if not request.subject.roles:
            decision = AuthorizationDecision(
                allowed=False,
                reason=AuthorizationReasonCode.NO_ROLES,
            )
            self._emit_audit(request, decision)
            return decision

        # Step 3: Determine required attributes from the policy catalog
        required = self._catalog.required_attributes(
            request.subject.roles,
            request.resource.resource_type,
            request.action,
        )

        # Step 4: Resolve required attributes (fail-closed)
        if required:
            resolved_attrs = await self._registry.resolve_attributes(request, required)
            # Merge resolved attributes into the request for Casbin evaluation
            # We create a new request with the resolved attributes
            request = AuthorizationRequest(
                subject=request.subject,
                resource=request.resource,
                action=request.action,
                attributes=resolved_attrs,
            )
            if resolved_attrs.unresolved:
                decision = AuthorizationDecision(
                    allowed=False,
                    reason=AuthorizationReasonCode.UNRESOLVED_ATTRIBUTE,
                )
                self._emit_audit(request, decision)
                return decision

        # Step 5: Casbin — evaluate ALL roles (D7)
        allow, policy_id = self._enforce(request)

        if allow:
            decision = AuthorizationDecision(
                allowed=True,
                reason=AuthorizationReasonCode.ALLOWED,
                policy_id=policy_id,
            )
            self._emit_audit(request, decision)
            return decision

        # Step 6: Classify the denial reason (D9) — runs ONLY on DENY
        reason = self._classify_denial(request)

        decision = AuthorizationDecision(
            allowed=False,
            reason=reason,
        )
        self._emit_audit(request, decision)
        return decision

    def _enforce(self, request: AuthorizationRequest) -> tuple[bool, str | None]:
        """Multi-role Casbin evaluation (D7).

        Loops ``enforcer.enforce()`` per role (attributes injected into the
        subject once, before the loop) and returns on the first ALLOW.

        Returns:
            (allowed, policy_id) tuple.
        """
        sub_base = {
            "client_id": str(request.subject.client_id or ""),
            "institution_id": str(request.subject.institution_id or ""),
        }
        # Inject resolved domain attributes into the subject dict
        sub_base.update(request.attributes.values)

        obj = {
            "name": request.resource.resource_type,
            "client_id": str(request.resource.client_id or ""),
            "institution_id": str(request.resource.institution_id or ""),
        }

        for role in request.subject.roles:
            sub = {**sub_base, "role": role}
            try:
                result = self._enforcer.enforce(sub, obj, request.action)
                if result:
                    # Extract policy_id if available
                    policy_id = self._extract_policy_id(sub, obj, request.action)
                    return True, policy_id
            except Exception:
                logger.exception(
                    "[AUTHZ] Casbin enforce error for role=%s resource=%s action=%s",
                    role, request.resource.resource_type, request.action,
                )
                continue

        return False, None

    def _extract_policy_id(self, sub: dict, obj: dict, action: str) -> str | None:
        """Extract the matching policy ID for audit purposes."""
        try:
            policies = self._enforcer.get_filtered_policy(0, sub.get("role", ""))
            for p in policies:
                if len(p) >= 4 and (p[1] == "*" or p[1] == obj.get("name")) and (p[2] == "*" or p[2] == action):
                    return f"{p[0]}:{p[1]}:{p[2]}:{p[3]}"
        except Exception:
            pass
        return None

    def _classify_denial(self, request: AuthorizationRequest) -> AuthorizationReasonCode:
        """Reason discriminator — runs ONLY on DENY (D9).

        Classification order:
        1. No role has (resource, action) in either catalog → MISSING_PERMISSION
        2. No matching scope → TENANT_ACCESS_DENIED / INSTITUTION_ACCESS_DENIED / INVALID_SCOPE
        3. Attribute condition failed → _ATTRIBUTE_DENY_REASON lookup
        4. Defensive fallback → POLICY_DENIED
        """
        roles = list(request.subject.roles)
        resource = request.resource.resource_type
        action = request.action

        # 1. Check if any role has the permission at all
        if not self._catalog.has_permission(roles, resource, action):
            return AuthorizationReasonCode.MISSING_PERMISSION

        # 2. Check scope matching
        scopes = self._catalog.matching_scopes(
            roles, resource, action,
            request.subject.client_id, request.subject.institution_id,
            request.resource.client_id, request.resource.institution_id,
        )
        if not scopes:
            # Determine the specific scope violation
            sub_client = str(request.subject.client_id or "")
            obj_client = str(request.resource.client_id or "")
            if sub_client and obj_client and sub_client != obj_client:
                return AuthorizationReasonCode.TENANT_ACCESS_DENIED

            sub_inst = str(request.subject.institution_id or "")
            obj_inst = str(request.resource.institution_id or "")
            if sub_client == obj_client and sub_inst and obj_inst and sub_inst != obj_inst:
                return AuthorizationReasonCode.INSTITUTION_ACCESS_DENIED

            return AuthorizationReasonCode.INVALID_SCOPE

        # 3. An attribute condition failed — check which attribute
        # Look at the request's attributes to find which one is false
        for attr_name, attr_value in request.attributes.values.items():
            if not attr_value and attr_name in _ATTRIBUTE_DENY_REASON:
                return _ATTRIBUTE_DENY_REASON[attr_name]

        # Check for any false attribute with generic mapping
        for attr_name, attr_value in request.attributes.values.items():
            if not attr_value:
                return _ATTRIBUTE_DENY_REASON.get(
                    attr_name, AuthorizationReasonCode.ATTRIBUTE_CONDITION_FAILED
                )

        # 4. Defensive fallback
        return AuthorizationReasonCode.POLICY_DENIED

    def _emit_audit(self, request: AuthorizationRequest, decision: AuthorizationDecision) -> None:
        """Emit structured audit record (D13).

        Populates AuthorizationAudit with the D13 field set and logs via
        the kernel.authz logger. Attribute values are redacted by default.
        """
        correlation_id = str(uuid.uuid4())

        # Determine the scope that was evaluated
        scope = None
        try:
            scopes = self._catalog.matching_scopes(
                list(request.subject.roles),
                request.resource.resource_type,
                request.action,
                request.subject.client_id, request.subject.institution_id,
                request.resource.client_id, request.resource.institution_id,
            )
            scope = scopes[0] if scopes else None
        except Exception:
            pass

        audit = AuthorizationAudit(
            correlation_id=correlation_id,
            user_id=request.subject.user_id,
            client_id=str(request.subject.client_id) if request.subject.client_id else None,
            institution_id=str(request.subject.institution_id) if request.subject.institution_id else None,
            action=request.action,
            resource_type=request.resource.resource_type,
            resource_id=str(request.resource.resource_id) if request.resource.resource_id else None,
            roles=request.subject.roles,
            scope=scope,
            policy_id=decision.policy_id,
            decision=decision.allowed,
            reason=decision.reason.value,
        )

        # Log with redacted attribute values (AC-33)
        resolved_attrs = list(request.attributes.resolved_by.keys())
        if decision.allowed:
            logger.info(
                "[AUTHZ] ALLOW user=%s roles=%s resource=%s:%s action=%s scope=%s policy=%s attrs=%s",
                audit.user_id, audit.roles, audit.resource_type, audit.resource_id,
                audit.action, audit.scope, audit.policy_id, resolved_attrs,
            )
        else:
            logger.warning(
                "[AUTHZ] DENY user=%s roles=%s resource=%s:%s action=%s scope=%s reason=%s attrs=%s",
                audit.user_id, audit.roles, audit.resource_type, audit.resource_id,
                audit.action, audit.scope, audit.reason, resolved_attrs,
            )

        # Attach audit to decision (create a new decision since it's frozen)
        # We use object.__setattr__ to bypass frozen restriction for audit attachment
        object.__setattr__(decision, 'audit', audit)

    # --- Batch seam (D14) — designed, NOT implemented ---
    # Future: authorize_many(requests) -> list[AuthorizationDecision]
    # Contract:
    # 1. Compute the union of required attributes across all requests in one pass.
    # 2. Resolve each distinct (resource_type, attribute) once (batch-wide cache).
    # 3. Group enforcement by subject.
    #
    # No batch API, cache, or tests are shipped in this iteration.

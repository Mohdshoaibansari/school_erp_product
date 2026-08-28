"""C-04 Authorization — module manifest (A5, D9, D12, AC-20, AC-21).

C-04 is kernel-tier (A2) — authorization is infrastructure that every
business module needs.

Extended for ABAC (D12):
- ``register_attribute_providers`` hook for startup provider registration.
- Registers the built-in ``IsSelfAttributeProvider`` (D10).
- ``register_authorization_policies`` hook for conditional policy registration.
"""

from __future__ import annotations

import logging
from typing import Any, Sequence

from fastapi import FastAPI

from kernel.app_factory import ManifestBase

logger = logging.getLogger("kernel.authz")


# Declared production conditional policies: (role, resource, action, scope, required_attrs).
# The Kernel ships NO business conditional policies (self-access must stay gated by an
# explicit permission + attrs policy declared by the owning business module in Phase 7).
# Populate this list (or implement register_authorization_policies in a business manifest)
# when the first real ABAC rule lands — the mechanism below is the production path (D8).
_PRODUCTION_CONDITIONAL_POLICIES: list[tuple[str, str, str, str, Sequence[str]]] = []


class AuthorizationManifest(ManifestBase):
    """C-04 module manifest."""

    def __init__(self) -> None:
        super().__init__(name="c04_authorization", tier="kernel")

    def register_routes(self, app: FastAPI) -> None:
        """Mount C-04 routers (empty in Phase 1 — no authz CRUD endpoints)."""
        pass

    def register_casbin_policies(self, enforcer: Any) -> None:
        """Register C-04 Casbin policies from the role_permission mapping (D24, D29).

        Called by the app factory after the enforcer is created.  Reads the
        in-memory permission map (populated by ``on_startup``) and pushes
        role-permission policies + role hierarchy into the enforcer.
        """
        from kernel.authz.services.policy_loader import register_policies_from_map
        register_policies_from_map(enforcer)

    def register_attribute_providers(self, registry: Any) -> None:
        """Register built-in attribute providers at startup (D12, REQ-AUTHZ-ABAC-02).

        Called by the app factory before service wiring completes.
        Registers the Kernel-owned ``IsSelfAttributeProvider`` (D10).
        Business modules (Phase 7) will register their own providers
        in their own manifests.
        """
        from kernel.authz.services.attribute_provider import IsSelfAttributeProvider
        registry.register(IsSelfAttributeProvider())

    def register_authorization_policies(self, enforcer: Any) -> None:
        """Register conditional authorization policies (D8, REQ-AUTHZ-FIX-REG-01).

        Called by the app factory after the DB loader runs. Uses a declared,
        explicit conditional-policy list; no rules engine, no business rule is
        invented in the Kernel. Non-conditional DB policies are registered
        unchanged by ``register_casbin_policies``.
        """
        from kernel.authz.services.policy_loader import register_conditional_policy
        for role, resource, action, scope, required_attrs in _PRODUCTION_CONDITIONAL_POLICIES:
            register_conditional_policy(
                enforcer, role, resource, action, scope, required_attrs
            )
        logger.debug(
            "[AUTHZ] Registered %d production conditional policies",
            len(_PRODUCTION_CONDITIONAL_POLICIES),
        )

    def on_startup(self) -> None:
        """Load the permission map from the database (D24, D29).

        Runs after DB is ready.  Reads ``role_permission`` and stores the
        mapping in a module-level dict for ``register_casbin_policies``.
        Idempotent — skips if already loaded (may be called twice: factory + lifespan).
        """
        from kernel.authz.services.policy_loader import load_permission_map, get_permission_map
        if not get_permission_map():
            load_permission_map()

    def on_shutdown(self) -> None:
        """Shutdown hook — currently a no-op."""
        pass

    def register_cli(self, cli: Any) -> None:
        """CLI hook — currently a no-op."""
        pass


manifest = AuthorizationManifest()

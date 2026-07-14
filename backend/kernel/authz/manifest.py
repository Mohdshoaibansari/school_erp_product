"""C-04 Authorization — module manifest (A5, D9, AC-20, AC-21).

C-04 is kernel-tier (A2) — authorization is infrastructure that every
business module needs.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI

from kernel.app_factory import ManifestBase


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

    def on_startup(self) -> None:
        """Load the permission map from the database (D24, D29).

        Runs after DB is ready.  Reads ``role_permission`` and stores the
        mapping in a module-level dict for ``register_casbin_policies``.
        """
        from kernel.authz.services.policy_loader import load_permission_map
        load_permission_map()

    def on_shutdown(self) -> None:
        """Shutdown hook — currently a no-op."""
        pass

    def register_cli(self, cli: Any) -> None:
        """CLI hook — currently a no-op."""
        pass


manifest = AuthorizationManifest()

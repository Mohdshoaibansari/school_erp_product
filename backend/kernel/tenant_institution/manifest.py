"""C-01 Tenant & Institution Management — module manifest (A5).

This is the manifest object the app factory imports to compose C-01 into the
FastAPI app. Section 7 routes are registered here via ``register_routes``.
"""

from __future__ import annotations

from fastapi import FastAPI

from kernel.app_factory import ManifestBase
from kernel.middleware import SubdomainJWTMiddleware


class TenantInstitutionManifest(ManifestBase):
    """C-01 module manifest."""

    def __init__(self) -> None:
        super().__init__(name="c01_tenant_institution", tier="kernel")

    def register_routes(self, app: FastAPI) -> None:
        """Mount C-01 routers + subdomain/JWT middleware (A5, A6, 7.1).

        - Subdomain+JWT middleware sets the contextvar (A6, 7.1).
        - Platform-scoped router (Client CRUD, InstitutionType, ownership transfer — 7.3, 7.5, 7.7).
        - Client-portal subdomain router (Institution CRUD, OrgUnit — 7.4, 7.6).
        """
        # Add subdomain+JWT middleware (7.1) — sets the contextvar (A6)
        app.add_middleware(SubdomainJWTMiddleware)

        # Register routers (7.3–7.7)
        from kernel.tenant_institution.routes import platform_router, client_portal_router
        app.include_router(platform_router)
        app.include_router(client_portal_router)

    def register_casbin_policies(self, enforcer) -> None:
        # Sub-phase D (section 12): D11 tiered-delegation matrix as Casbin policies.
        pass

    def on_startup(self) -> None:
        # Future: seed InstitutionType lookup data if configured.
        pass

    def on_shutdown(self) -> None:
        pass

    def register_cli(self, cli) -> None:
        # Future: seed, tenant provisioning helpers.
        pass


manifest = TenantInstitutionManifest()

"""C-01 Tenant & Institution Management — module manifest (A5).

This is the manifest object the app factory imports to compose C-01 into the
FastAPI app. Full routes are sub-phase B (section 7); this skeleton defines the
manifest contract and stubs the hooks.
"""

from __future__ import annotations

from kernel.app_factory import ManifestBase


class TenantInstitutionManifest(ManifestBase):
    """C-01 module manifest."""

    def __init__(self) -> None:
        super().__init__(name="c01_tenant_institution", tier="kernel")

    def register_routes(self, app) -> None:
        # Sub-phase B (section 7): subdomain-resolved client-portal router +
        # platform-scoped router. Stubbed for now.
        pass

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

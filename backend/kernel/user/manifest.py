"""C-02 Identity & User Management — module manifest (A5).

This is the manifest object the app factory imports to compose C-02 into the
FastAPI app. C-02 is entirely kernel (not business) — user management is
platform infrastructure that every business module needs.
"""

from __future__ import annotations

from fastapi import FastAPI

from kernel.app_factory import ManifestBase


class IdentityUserManagementManifest(ManifestBase):
    """C-02 module manifest."""

    def __init__(self) -> None:
        super().__init__(name="c02_identity_user_management", tier="kernel")

    def register_routes(self, app: FastAPI) -> None:
        """Mount C-02 routers (A5).

        - User CRUD + lifecycle endpoints
        - UserProfile endpoints
        - RoleAssignment endpoints
        - UserIdentifier endpoints
        - UserCategory and Role lookup endpoints
        """
        from kernel.user.routes.users import router as users_router
        from kernel.user.routes.profiles import router as profiles_router
        from kernel.user.routes.roles import router as roles_router
        from kernel.user.routes.identifiers import router as identifiers_router
        from kernel.user.routes.lookups import router as lookups_router

        app.include_router(users_router)
        app.include_router(profiles_router)
        app.include_router(roles_router)
        app.include_router(identifiers_router)
        app.include_router(lookups_router)

    def register_casbin_policies(self, enforcer) -> None:
        """Register C-02 Casbin policies (A5).

        C-04 owns the framework; C-02 supplies the user/role content.
        Currently a no-op — C-04 will invoke this hook at startup.
        """
        from kernel.user.policies import register_policies
        register_policies(enforcer)

    def on_startup(self) -> None:
        """Startup hook — currently a no-op."""
        pass

    def on_shutdown(self) -> None:
        """Shutdown hook — currently a no-op."""
        pass

    def register_cli(self, cli) -> None:
        """CLI hook — currently a no-op."""
        pass


manifest = IdentityUserManagementManifest()

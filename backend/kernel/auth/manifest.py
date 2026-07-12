"""C-03 Authentication — module manifest (A5).

This is the manifest object the app factory imports to compose C-03 into the
FastAPI app. C-03 is kernel-tier (A2) — authentication is infrastructure that
every business module needs.
"""

from __future__ import annotations

from fastapi import FastAPI

from kernel.app_factory import ManifestBase


class AuthenticationManifest(ManifestBase):
    """C-03 module manifest."""

    def __init__(self) -> None:
        super().__init__(name="c03_authentication", tier="kernel")

    def register_routes(self, app: FastAPI) -> None:
        """Mount C-03 routers (A5).

        - Auth endpoints (login, refresh, logout, activate, OTP, password)
        """
        from kernel.auth.routes.auth import router as auth_router

        app.include_router(auth_router)

    def register_casbin_policies(self, enforcer) -> None:
        """Register C-03 Casbin policies (A5).

        C-04 owns the framework; C-03 supplies the auth content.
        Currently a no-op — C-04 will invoke this hook at startup.
        """
        pass

    def on_startup(self) -> None:
        """Startup hook — currently a no-op."""
        pass

    def on_shutdown(self) -> None:
        """Shutdown hook — currently a no-op."""
        pass

    def register_cli(self, cli) -> None:
        """CLI hook — register bootstrap command."""
        pass


manifest = AuthenticationManifest()

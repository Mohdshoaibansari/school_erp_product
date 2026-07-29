"""C-08 Configuration Framework — module manifest (A5).

Kernel module: owns the centralized configuration framework.
Wires routes, registers the in-memory cache loader, starts the NOTIFY listener.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI

from kernel.app_factory import ManifestBase

logger = logging.getLogger(__name__)


class ConfigurationManifest(ManifestBase):
    """C-08 module manifest."""

    def __init__(self) -> None:
        super().__init__(name="c08_configuration_framework", tier="kernel")

    def register_routes(self, app: FastAPI) -> None:
        """Mount C-08 routers under /api/v1/config/."""
        from kernel.config.routes.keys import router as keys_router
        from kernel.config.routes.values import router as values_router
        from kernel.config.routes.audit import router as audit_router
        from kernel.config.routes.resolve import router as resolve_router

        app.include_router(keys_router)
        app.include_router(values_router)
        app.include_router(audit_router)
        app.include_router(resolve_router)

    def register_casbin_policies(self, enforcer) -> None:
        """Empty: all C-08 permissions live in the DB (per PRD D15)."""
        pass

    def on_startup(self) -> None:
        """Load in-memory cache + start NOTIFY listener."""
        from kernel.config.resolver import config as cfg
        from kernel.config.notifier import start_listener

        cfg.load_all()
        start_listener()

    def on_shutdown(self) -> None:
        """Stop NOTIFY listener."""
        from kernel.config.notifier import stop_listener
        try:
            stop_listener()
        except Exception as e:
            logger.warning("[C-08 manifest] Shutdown: %s", e)

    def register_cli(self, cli) -> None:
        """CLI hook — currently a no-op."""
        pass


manifest = ConfigurationManifest()

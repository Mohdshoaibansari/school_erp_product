"""FastAPI app factory + module manifest composition (A5).

Reads an explicit module list (NOT auto-discovery) and invokes each module's
manifest hooks in dependency order: kernel → shared → business (A2/A3).
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Callable, Protocol

from fastapi import FastAPI

logger = logging.getLogger(__name__)


class ModuleManifest(Protocol):
    """Protocol for module manifests (A5).

    Each module package exposes a ``manifest`` object satisfying this protocol.
    The app factory invokes hooks in dependency order.
    """

    name: str
    tier: str  # "kernel" | "shared" | "business"

    def register_routes(self, app: FastAPI) -> None: ...
    def register_casbin_policies(self, enforcer: Any) -> None: ...
    def on_startup(self) -> None: ...
    def on_shutdown(self) -> None: ...
    def register_cli(self, cli: Any) -> None: ...


@dataclass
class ManifestBase:
    """Base dataclass implementing ModuleManifest with no-op defaults.

    Subclass and override only the hooks a module needs.
    """

    name: str
    tier: str = "kernel"
    _startup_hooks: list[Callable] = field(default_factory=list)
    _shutdown_hooks: list[Callable] = field(default_factory=list)

    def register_routes(self, app: FastAPI) -> None:
        pass

    def register_casbin_policies(self, enforcer: Any) -> None:
        pass

    def on_startup(self) -> None:
        for hook in self._startup_hooks:
            hook()

    def on_shutdown(self) -> None:
        for hook in self._shutdown_hooks:
            hook()

    def register_cli(self, cli: Any) -> None:
        pass


def create_app(module_manifests: list[ModuleManifest] | None = None) -> FastAPI:
    """Create and configure the FastAPI application.

    Args:
        module_manifests: explicit list of module manifest objects, in dependency
            order (kernel first, then shared, then business). NOT auto-discovery.

    Returns:
        Configured FastAPI app instance.
    """
    app = FastAPI(
        title="School ERP",
        description="Multi-tenant School ERP platform — modular monolith",
        version="0.1.0",
    )

    manifests = module_manifests or []

    # Invoke route registration hooks in dependency order (list is already ordered)
    for manifest in manifests:
        logger.info("Registering module: %s (tier=%s)", manifest.name, manifest.tier)
        manifest.register_routes(app)

    # Invoke on_startup hooks so modules can initialise (DB reads, policy loads, ...)
    # BEFORE the Casbin enforcer is created and policies are registered (D29)
    for manifest in manifests:
        manifest.on_startup()

    # Create Casbin enforcer and register policies from all manifests (D10, D29)
    _create_casbin_enforcer(manifests)

    # Register startup/shutdown hooks via lifespan
    @asynccontextmanager
    async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
        for manifest in manifests:
            logger.info("Starting module: %s", manifest.name)
            manifest.on_startup()
        yield
        for manifest in reversed(manifests):
            logger.info("Shutting down module: %s", manifest.name)
            manifest.on_shutdown()

    app.router.lifespan_context = _lifespan

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


def _create_casbin_enforcer(manifests: list[ModuleManifest]) -> None:
    """Create Casbin enforcer and register policies from all manifests (D10, D29).

    Creates the enforcer from the canonical model at ``kernel/authz/casbin_model.conf``,
    iterates manifests in dependency order calling ``register_casbin_policies(enforcer)``,
    and stores the singleton via ``kernel.authz.dependencies.set_enforcer()``.
    """
    import os
    import casbin
    from kernel.authz.dependencies import set_enforcer

    model_path = os.path.join(
        os.path.dirname(__file__), "authz", "casbin_model.conf",
    )
    if not os.path.exists(model_path):
        logger.warning("Casbin model not found at %s — skipping enforcer creation", model_path)
        return

    enforcer = casbin.Enforcer(model_path)
    logger.info("Casbin enforcer created from %s", model_path)

    for manifest in manifests:
        manifest.register_casbin_policies(enforcer)
        logger.debug("Registered Casbin policies for module: %s", manifest.name)

    set_enforcer(enforcer)
    logger.info("Casbin enforcer registered with %d role definitions", len(enforcer.get_all_roles()))

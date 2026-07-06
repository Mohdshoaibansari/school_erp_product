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

"""C-13 Address Management — module manifest."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI


class AddressManifest:
    """C-13 Address Management module manifest."""

    def __init__(self) -> None:
        self.name = "c13_address"
        self.tier = "kernel"

    def register_routes(self, app: FastAPI) -> None:
        from kernel.address.routes.addresses import router as addresses_router
        from kernel.address.routes.addresses import assignment_router as address_assignment_router
        from kernel.address.routes.person_addresses import router as person_addresses_router
        from kernel.address.routes.institution_addresses import router as institution_addresses_router
        from kernel.address.routes.address_types import router as address_types_router
        from kernel.address.routes.geographic_data import router as geographic_data_router

        app.include_router(addresses_router)
        app.include_router(address_assignment_router)
        app.include_router(person_addresses_router)
        app.include_router(institution_addresses_router)
        app.include_router(address_types_router)
        app.include_router(geographic_data_router)

    def register_casbin_policies(self, enforcer: Any) -> None:
        # G-16: No-op is intentional. C-13 permissions (address.create/read/update/
        # delete/correct, address_type.read/manage, entity_type.read) are seeded
        # idempotently in migration 027_c13_address (INSERT … ON CONFLICT DO NOTHING)
        # and role_permission rows are created there. C-13 uses the existing
        # FastAPI middleware + Casbin via ProviderRegistry/ResourceContext; it does
        # not implement its own engine. All address routes already call
        # require_permission("address"|"address_type", "<action>") matching the
        # seeded (resource, action) pairs — verified in G-16.
        pass

    def on_startup(self) -> None:
        pass

    def on_shutdown(self) -> None:
        pass

    def register_cli(self, cli: Any) -> None:
        pass


manifest = AddressManifest()

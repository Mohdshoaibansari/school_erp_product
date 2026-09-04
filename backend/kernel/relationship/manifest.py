"""C-06 Relationship Management — module manifest."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI


class RelationshipManifest:
    """C-06 Relationship Management module manifest."""

    def __init__(self) -> None:
        self.name = "c06_relationship"
        self.tier = "kernel"

    def register_routes(self, app: FastAPI) -> None:
        from kernel.relationship.routes.relationship_types import router as relationship_types_router
        from kernel.relationship.routes.contact_roles import router as contact_roles_router
        from kernel.relationship.routes.relationships import router as relationships_router
        from kernel.relationship.routes.contact_role_assignments import router as contact_role_assignments_router

        app.include_router(relationship_types_router)
        app.include_router(contact_roles_router)
        app.include_router(relationships_router)
        app.include_router(contact_role_assignments_router)

    def register_casbin_policies(self, enforcer: Any) -> None:
        pass

    def on_startup(self) -> None:
        pass

    def on_shutdown(self) -> None:
        pass

    def register_cli(self, cli: Any) -> None:
        pass


manifest = RelationshipManifest()

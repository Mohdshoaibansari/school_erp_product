"""C-06 Relationship Management — routes package."""

from kernel.relationship.routes.relationship_types import router as relationship_types_router
from kernel.relationship.routes.contact_roles import router as contact_roles_router
from kernel.relationship.routes.relationships import router as relationships_router
from kernel.relationship.routes.contact_role_assignments import router as contact_role_assignments_router

__all__ = [
    "relationship_types_router",
    "contact_roles_router",
    "relationships_router",
    "contact_role_assignments_router",
]

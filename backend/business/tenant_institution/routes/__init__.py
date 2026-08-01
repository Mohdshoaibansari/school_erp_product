"""C-01 route modules (A5)."""

from business.tenant_institution.routes.platform import router as platform_router
from business.tenant_institution.routes.client_portal import router as client_portal_router
from business.tenant_institution.routes.client_users import router as client_users_router

__all__ = ["platform_router", "client_portal_router", "client_users_router"]

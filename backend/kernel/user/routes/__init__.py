"""C-02 route modules (A5)."""

from kernel.user.routes.users import router as users_router
from kernel.user.routes.profiles import router as profiles_router
from kernel.user.routes.roles import router as roles_router
from kernel.user.routes.identifiers import router as identifiers_router
from kernel.user.routes.lookups import router as lookups_router

__all__ = [
    "users_router",
    "profiles_router",
    "roles_router",
    "identifiers_router",
    "lookups_router",
]

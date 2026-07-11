"""C-02 ORM models — exported for Alembic auto-detection and app imports."""

from kernel.user.models.user_category import UserCategory
from kernel.user.models.role import Role
from kernel.user.models.user import User
from kernel.user.models.user_profile import UserProfile
from kernel.user.models.role_assignment import RoleAssignment
from kernel.user.models.user_identifier import UserIdentifier
from kernel.user.models.user_lifecycle_event import UserLifecycleEvent

__all__ = [
    "UserCategory",
    "Role",
    "User",
    "UserProfile",
    "RoleAssignment",
    "UserIdentifier",
    "UserLifecycleEvent",
]

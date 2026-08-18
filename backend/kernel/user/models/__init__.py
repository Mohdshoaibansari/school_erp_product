"""C-02 ORM models — exported for Alembic auto-detection and app imports."""

from kernel.user.models.role import Role
from kernel.user.models.user_account import UserAccount
from kernel.user.models.person import Person
from kernel.user.models.user import User
from kernel.user.models.role_assignment import RoleAssignment
from kernel.user.models.user_identifier import UserIdentifier
from kernel.user.models.user_lifecycle_event import UserLifecycleEvent

__all__ = [
    "Role",
    "UserAccount",
    "Person",
    "User",
    "RoleAssignment",
    "UserIdentifier",
    "UserLifecycleEvent",
]

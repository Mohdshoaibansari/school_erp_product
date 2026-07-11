"""C-02 repositories — exported for service and test imports."""

from kernel.user.repos.user_repo import UserRepository
from kernel.user.repos.user_profile_repo import UserProfileRepository
from kernel.user.repos.role_assignment_repo import RoleAssignmentRepository
from kernel.user.repos.user_identifier_repo import UserIdentifierRepository

__all__ = [
    "UserRepository",
    "UserProfileRepository",
    "RoleAssignmentRepository",
    "UserIdentifierRepository",
]

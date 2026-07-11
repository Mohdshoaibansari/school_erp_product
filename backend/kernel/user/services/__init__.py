"""C-02 services — published interface.

Note: IdentityUserService is NOT imported here to avoid circular imports.
Import it directly: from kernel.user.services.service import IdentityUserService
"""

from kernel.user.services.dtos import (
    UserCategoryDTO,
    RoleDTO,
    UserCreateDTO,
    UserUpdateDTO,
    UserDTO,
    UserProfileCreateDTO,
    UserProfileUpdateDTO,
    UserProfileDTO,
    RoleAssignmentCreateDTO,
    RoleAssignmentDTO,
    UserIdentifierCreateDTO,
    UserIdentifierDTO,
    LifecycleTransitionDTO,
    UserLifecycleEventDTO,
)
from kernel.user.services.state_machine import (
    InvalidUserTransitionError,
    USER_STATES,
    USER_TERMINAL_STATES,
    USER_ARCS,
    validate_user_transition,
    is_user_state_terminal,
)

__all__ = [
    # DTOs
    "UserCategoryDTO",
    "RoleDTO",
    "UserCreateDTO",
    "UserUpdateDTO",
    "UserDTO",
    "UserProfileCreateDTO",
    "UserProfileUpdateDTO",
    "UserProfileDTO",
    "RoleAssignmentCreateDTO",
    "RoleAssignmentDTO",
    "UserIdentifierCreateDTO",
    "UserIdentifierDTO",
    "LifecycleTransitionDTO",
    "UserLifecycleEventDTO",
    # State machine
    "InvalidUserTransitionError",
    "USER_STATES",
    "USER_TERMINAL_STATES",
    "USER_ARCS",
    "validate_user_transition",
    "is_user_state_terminal",
]

"""UserProfileRepository (task 7.2).

Inherits TenantAwareRepositoryBase[UserProfile]. Methods: create, get, update.
Returns UserProfileDTO.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from kernel.tenant_context import TenantContext
from kernel.user.models.user_profile import UserProfile
from kernel.repo_base import TenantAwareRepositoryBase
from kernel.user.services.dtos import UserProfileCreateDTO, UserProfileDTO, UserProfileUpdateDTO


class UserProfileRepository(TenantAwareRepositoryBase[UserProfile]):
    """Repository for the UserProfile entity (Decision 5).

    Returns UserProfileDTO.
    """

    def __init__(self) -> None:
        super().__init__(UserProfile)

    def _to_dto(self, obj: UserProfile) -> UserProfileDTO:
        return UserProfileDTO.model_validate(obj)

    def create(
        self, session: Session, ctx: TenantContext, user_id: uuid.UUID, dto: UserProfileCreateDTO,
    ) -> UserProfileDTO:
        """Create a UserProfile for a User."""
        # Check if profile already exists
        existing = session.execute(
            select(UserProfile).where(UserProfile.user_id == user_id)
        ).scalars().first()
        if existing:
            raise ValueError("User already has a profile")

        obj = UserProfile(
            user_id=user_id,
            photo=dto.photo,
            date_of_birth=dto.date_of_birth,
            gender=dto.gender,
            blood_group=dto.blood_group,
        )
        session.add(obj)
        session.flush()
        return self._to_dto(obj)

    def get_by_user_id(
        self, session: Session, ctx: TenantContext, user_id: uuid.UUID,
    ) -> UserProfileDTO | None:
        """Get a UserProfile by user_id."""
        stmt = select(UserProfile).where(UserProfile.user_id == user_id)
        obj = session.execute(stmt).scalars().first()
        return self._to_dto(obj) if obj else None

    def update(
        self, session: Session, ctx: TenantContext, user_id: uuid.UUID, dto: UserProfileUpdateDTO,
    ) -> UserProfileDTO:
        """Update a UserProfile."""
        stmt = select(UserProfile).where(UserProfile.user_id == user_id)
        obj = session.execute(stmt).scalars().first()
        if not obj:
            raise ValueError("Profile not found")

        data = dto.model_dump(exclude_unset=True)
        for key, value in data.items():
            setattr(obj, key, value)
        session.flush()
        return self._to_dto(obj)

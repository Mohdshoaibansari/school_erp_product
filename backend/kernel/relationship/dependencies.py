"""C-06 Relationship Management — dependencies (FastAPI DI)."""

from __future__ import annotations

from fastapi import Depends
from sqlalchemy.orm import Session

from kernel.db import get_db
from kernel.relationship.services.relationship_type_service import RelationshipTypeService
from kernel.relationship.services.contact_role_service import ContactRoleService
from kernel.relationship.services.relationship_service import RelationshipService
from kernel.relationship.services.contact_role_assignment_service import ContactRoleAssignmentService


def get_relationship_type_service(db: Session = Depends(get_db)) -> RelationshipTypeService:
    return RelationshipTypeService(db)


def get_contact_role_service(db: Session = Depends(get_db)) -> ContactRoleService:
    return ContactRoleService(db)


def get_relationship_service(db: Session = Depends(get_db)) -> RelationshipService:
    return RelationshipService(db)


def get_contact_role_assignment_service(db: Session = Depends(get_db)) -> ContactRoleAssignmentService:
    return ContactRoleAssignmentService(db)

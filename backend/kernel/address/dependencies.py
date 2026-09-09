"""C-13 Address Management — dependencies (FastAPI DI)."""

from __future__ import annotations

from fastapi import Depends
from sqlalchemy.orm import Session

from kernel.db import get_db
from kernel.address.services import (
    AddressService,
    AddressAssignmentService,
    AddressTypeService,
    GeographicService,
)


def get_address_service(db: Session = Depends(get_db)) -> AddressService:
    from kernel.audit import DefaultAuditEmitter

    return AddressService(db, audit_emitter=DefaultAuditEmitter())


def get_address_assignment_service(db: Session = Depends(get_db)) -> AddressAssignmentService:
    return AddressAssignmentService(db)


def get_address_type_service(db: Session = Depends(get_db)) -> AddressTypeService:
    return AddressTypeService(db)


def get_geographic_service(db: Session = Depends(get_db)) -> GeographicService:
    return GeographicService(db)


def get_entity_type_service(db: Session = Depends(get_db)):
    from kernel.address.repos import EntityTypeRepo
    return EntityTypeRepo(db)


def get_address_type_repo(db: Session = Depends(get_db)):
    from kernel.address.repos import AddressTypeRepo
    return AddressTypeRepo(db)

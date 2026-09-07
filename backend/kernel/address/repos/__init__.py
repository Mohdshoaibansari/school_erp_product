"""C-13 Address Management — Repositories."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Sequence

from sqlalchemy import select, and_, or_
from sqlalchemy.orm import Session

from kernel.address.models.entity_type import EntityType
from kernel.address.models.address_type import AddressType
from kernel.address.models.address_type_entity_type import AddressTypeEntityType
from kernel.address.models.address import Address
from kernel.address.models.address_assignment import AddressAssignment
from kernel.address.models.country import Country
from kernel.address.models.state import State
from kernel.address.models.city import City


class EntityTypeRepo:
    """Repository for EntityType entity."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, code: str, name: str) -> EntityType:
        et = EntityType(code=code, name=name)
        self.db.add(et)
        self.db.flush()
        return et

    def get_by_id(self, et_id: uuid.UUID) -> EntityType | None:
        return self.db.get(EntityType, et_id)

    def get_by_code(self, code: str) -> EntityType | None:
        stmt = select(EntityType).where(EntityType.code == code)
        return self.db.execute(stmt).scalar_one_or_none()

    def list_all(self) -> Sequence[EntityType]:
        stmt = select(EntityType).order_by(EntityType.name)
        return list(self.db.execute(stmt).scalars().all())


class AddressTypeRepo:
    """Repository for AddressType entity."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, code: str, name: str) -> AddressType:
        at = AddressType(code=code, name=name)
        self.db.add(at)
        self.db.flush()
        return at

    def get_by_id(self, at_id: uuid.UUID) -> AddressType | None:
        return self.db.get(AddressType, at_id)

    def get_by_code(self, code: str) -> AddressType | None:
        stmt = select(AddressType).where(AddressType.code == code)
        return self.db.execute(stmt).scalar_one_or_none()

    def list_all(self) -> Sequence[AddressType]:
        stmt = select(AddressType).order_by(AddressType.name)
        return list(self.db.execute(stmt).scalars().all())

    def add_compatibility(self, address_type_id: uuid.UUID, entity_type_id: uuid.UUID) -> AddressTypeEntityType:
        compat = AddressTypeEntityType(
            address_type_id=address_type_id,
            entity_type_id=entity_type_id,
        )
        self.db.add(compat)
        self.db.flush()
        return compat

    def get_compatible_entity_types(self, address_type_id: uuid.UUID) -> Sequence[uuid.UUID]:
        stmt = select(AddressTypeEntityType.entity_type_id).where(
            AddressTypeEntityType.address_type_id == address_type_id
        )
        return list(self.db.execute(stmt).scalars().all())

    def get_compatible_address_types(self, entity_type_id: uuid.UUID) -> Sequence[uuid.UUID]:
        stmt = select(AddressTypeEntityType.address_type_id).where(
            AddressTypeEntityType.entity_type_id == entity_type_id
        )
        return list(self.db.execute(stmt).scalars().all())


class AddressRepo:
    """Repository for Address entity."""

    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        address_line_1: str,
        city_id: uuid.UUID,
        state_id: uuid.UUID,
        country_id: uuid.UUID,
        address_line_2: str | None = None,
        locality: str | None = None,
        landmark: str | None = None,
        postal_code: str | None = None,
    ) -> Address:
        addr = Address(
            address_line_1=address_line_1,
            address_line_2=address_line_2,
            locality=locality,
            landmark=landmark,
            postal_code=postal_code,
            city_id=city_id,
            state_id=state_id,
            country_id=country_id,
        )
        self.db.add(addr)
        self.db.flush()
        return addr

    def get_by_id(self, addr_id: uuid.UUID) -> Address | None:
        return self.db.get(Address, addr_id)

    def update(self, addr: Address, **kwargs) -> Address:
        for key, value in kwargs.items():
            setattr(addr, key, value)
        self.db.flush()
        return addr

    def delete(self, addr: Address) -> None:
        self.db.delete(addr)
        self.db.flush()


class AddressAssignmentRepo:
    """Repository for AddressAssignment entity."""

    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        entity_type_id: uuid.UUID,
        entity_id: uuid.UUID,
        address_id: uuid.UUID,
        address_type_id: uuid.UUID,
        valid_from: date,
        valid_to: date | None,
    ) -> AddressAssignment:
        aa = AddressAssignment(
            entity_type_id=entity_type_id,
            entity_id=entity_id,
            address_id=address_id,
            address_type_id=address_type_id,
            valid_from=valid_from,
            valid_to=valid_to,
        )
        self.db.add(aa)
        self.db.flush()
        return aa

    def get_by_id(self, aa_id: uuid.UUID) -> AddressAssignment | None:
        return self.db.get(AddressAssignment, aa_id)

    def list_by_entity(
        self,
        entity_type_id: uuid.UUID,
        entity_id: uuid.UUID,
        effective_date: date | None = None,
    ) -> Sequence[AddressAssignment]:
        stmt = select(AddressAssignment).where(
            AddressAssignment.entity_type_id == entity_type_id,
            AddressAssignment.entity_id == entity_id,
        )

        if effective_date:
            stmt = stmt.where(
                and_(
                    AddressAssignment.valid_from <= effective_date,
                    or_(
                        AddressAssignment.valid_to.is_(None),
                        AddressAssignment.valid_to >= effective_date,
                    ),
                )
            )

        stmt = stmt.order_by(AddressAssignment.valid_from.desc())
        return list(self.db.execute(stmt).scalars().all())

    def check_overlap(
        self,
        entity_type_id: uuid.UUID,
        entity_id: uuid.UUID,
        address_type_id: uuid.UUID,
        valid_from: date,
        valid_to: date | None,
        exclude_id: uuid.UUID | None = None,
    ) -> bool:
        """Check if overlapping assignment exists for entity + address type."""
        stmt = select(AddressAssignment).where(
            AddressAssignment.entity_type_id == entity_type_id,
            AddressAssignment.entity_id == entity_id,
            AddressAssignment.address_type_id == address_type_id,
        )

        if exclude_id:
            stmt = stmt.where(AddressAssignment.id != exclude_id)

        if valid_to:
            stmt = stmt.where(
                and_(
                    AddressAssignment.valid_from <= valid_to,
                    or_(
                        AddressAssignment.valid_to.is_(None),
                        AddressAssignment.valid_to >= valid_from,
                    ),
                )
            )
        else:
            stmt = stmt.where(
                or_(
                    AddressAssignment.valid_to.is_(None),
                    AddressAssignment.valid_to >= valid_from,
                )
            )

        return self.db.execute(stmt).scalar_one_or_none() is not None

    def update(self, aa: AddressAssignment, **kwargs) -> AddressAssignment:
        for key, value in kwargs.items():
            setattr(aa, key, value)
        self.db.flush()
        return aa


class GeographicRepo:
    """Repository for geographic reference data."""

    def __init__(self, db: Session):
        self.db = db

    # Country
    def create_country(self, code: str, name: str) -> Country:
        country = Country(code=code, name=name)
        self.db.add(country)
        self.db.flush()
        return country

    def get_country_by_id(self, country_id: uuid.UUID) -> Country | None:
        return self.db.get(Country, country_id)

    def get_country_by_code(self, code: str) -> Country | None:
        stmt = select(Country).where(Country.code == code)
        return self.db.execute(stmt).scalar_one_or_none()

    def list_countries(self) -> Sequence[Country]:
        stmt = select(Country).order_by(Country.name)
        return list(self.db.execute(stmt).scalars().all())

    # State
    def create_state(self, country_id: uuid.UUID, code: str, name: str) -> State:
        state = State(country_id=country_id, code=code, name=name)
        self.db.add(state)
        self.db.flush()
        return state

    def get_state_by_id(self, state_id: uuid.UUID) -> State | None:
        return self.db.get(State, state_id)

    def list_states_by_country(self, country_id: uuid.UUID) -> Sequence[State]:
        stmt = select(State).where(State.country_id == country_id).order_by(State.name)
        return list(self.db.execute(stmt).scalars().all())

    # City
    def create_city(self, state_id: uuid.UUID, code: str, name: str) -> City:
        city = City(state_id=state_id, code=code, name=name)
        self.db.add(city)
        self.db.flush()
        return city

    def get_city_by_id(self, city_id: uuid.UUID) -> City | None:
        return self.db.get(City, city_id)

    def list_cities_by_state(self, state_id: uuid.UUID) -> Sequence[City]:
        stmt = select(City).where(City.state_id == state_id).order_by(City.name)
        return list(self.db.execute(stmt).scalars().all())

    def validate_hierarchy(self, city_id: uuid.UUID, state_id: uuid.UUID, country_id: uuid.UUID) -> bool:
        """Validate that city belongs to state and state belongs to country."""
        city = self.get_city_by_id(city_id)
        if not city or city.state_id != state_id:
            return False

        state = self.get_state_by_id(state_id)
        if not state or state.country_id != country_id:
            return False

        return True

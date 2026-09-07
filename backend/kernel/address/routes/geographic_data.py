"""C-13 Address Management — Geographic reference data routes."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from kernel.address.dependencies import get_geographic_service
from kernel.address.services import GeographicService
from kernel.address.schemas.dtos import CountryDTO, StateDTO, CityDTO
from kernel.authz.dependencies import require_permission

router = APIRouter(prefix="/api/v1", tags=["geographic-data"])


@router.get("/countries", response_model=list[CountryDTO], summary="List countries")
def list_countries(
    _authz: None = Depends(require_permission("address_type", "read")),
    svc: GeographicService = Depends(get_geographic_service),
) -> list[CountryDTO]:
    countries = svc.list_countries()
    return [CountryDTO.model_validate(c) for c in countries]


@router.get("/countries/{country_id}/states", response_model=list[StateDTO], summary="List states")
def list_states(
    country_id: uuid.UUID,
    _authz: None = Depends(require_permission("address_type", "read")),
    svc: GeographicService = Depends(get_geographic_service),
) -> list[StateDTO]:
    states = svc.list_states(country_id)
    return [StateDTO.model_validate(s) for s in states]


@router.get("/states/{state_id}/cities", response_model=list[CityDTO], summary="List cities")
def list_cities(
    state_id: uuid.UUID,
    _authz: None = Depends(require_permission("address_type", "read")),
    svc: GeographicService = Depends(get_geographic_service),
) -> list[CityDTO]:
    cities = svc.list_cities(state_id)
    return [CityDTO.model_validate(c) for c in cities]

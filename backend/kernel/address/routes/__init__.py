"""C-13 Address Management — routes package."""

from kernel.address.routes.addresses import router as addresses_router
from kernel.address.routes.person_addresses import router as person_addresses_router
from kernel.address.routes.institution_addresses import router as institution_addresses_router
from kernel.address.routes.address_types import router as address_types_router
from kernel.address.routes.geographic_data import router as geographic_data_router

__all__ = [
    "addresses_router",
    "person_addresses_router",
    "institution_addresses_router",
    "address_types_router",
    "geographic_data_router",
]

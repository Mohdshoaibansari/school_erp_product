"""Fees module — business manifest (A5, D16)."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI


class FeesManifest:
    """Fees business module manifest."""

    def __init__(self) -> None:
        self.name = "fees"
        self.tier = "business"

    def register_routes(self, app: FastAPI) -> None:
        from business.fees.routes.fee_types import router as fee_types_router
        from business.fees.routes.fee_assignments import router as fee_assignments_router
        from business.fees.routes.payments import router as payments_router
        app.include_router(fee_types_router)
        app.include_router(fee_assignments_router)
        app.include_router(payments_router)

    def register_casbin_policies(self, enforcer: Any) -> None:
        pass  # Permissions are in C-04's DB tables (D8)

    def on_startup(self) -> None:
        pass

    def on_shutdown(self) -> None:
        pass

    def register_cli(self, cli: Any) -> None:
        pass


manifest = FeesManifest()

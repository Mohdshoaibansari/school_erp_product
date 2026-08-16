"""C-05 Academic Structure — module manifest (T28)."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI


class AcademicStructureManifest:
    """C-05 Academic Structure module manifest."""

    def __init__(self) -> None:
        self.name = "c05_academic_structure"
        self.tier = "kernel"

    def register_routes(self, app: FastAPI) -> None:
        from kernel.academic.routes.academic_years import router as academic_years_router
        from kernel.academic.routes.enrollments import router as enrollments_router
        from kernel.academic.routes.assignments import router as assignments_router
        from kernel.academic.routes.lookups import router as lookups_router

        app.include_router(academic_years_router)
        app.include_router(enrollments_router)
        app.include_router(assignments_router)
        app.include_router(lookups_router)

    def register_casbin_policies(self, enforcer: Any) -> None:
        pass  # Permissions are in C-04's DB tables

    def on_startup(self) -> None:
        pass

    def on_shutdown(self) -> None:
        pass

    def register_cli(self, cli: Any) -> None:
        pass


manifest = AcademicStructureManifest()

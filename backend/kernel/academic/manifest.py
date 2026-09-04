"""C-05 Academic Structure — module manifest."""

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
        from kernel.academic.routes.terms import router as terms_router
        from kernel.academic.routes.grade_levels import router as grade_levels_router
        from kernel.academic.routes.classes import router as classes_router
        from kernel.academic.routes.class_academic_years import router as class_academic_years_router
        from kernel.academic.routes.sections import router as sections_router
        from kernel.academic.routes.curriculum import router as curriculum_router
        from kernel.academic.routes.curriculum_versions import router as curriculum_versions_router
        from kernel.academic.routes.subjects import router as subjects_router
        from kernel.academic.routes.section_subjects import router as section_subjects_router
        from kernel.academic.routes.grade_academic_year_curriculum import router as grade_academic_year_curriculum_router

        app.include_router(academic_years_router)
        app.include_router(terms_router)
        app.include_router(grade_levels_router)
        app.include_router(classes_router)
        app.include_router(class_academic_years_router)
        app.include_router(sections_router)
        app.include_router(curriculum_router)
        app.include_router(curriculum_versions_router)
        app.include_router(subjects_router)
        app.include_router(section_subjects_router)
        app.include_router(grade_academic_year_curriculum_router)

    def register_casbin_policies(self, enforcer: Any) -> None:
        pass  # Permissions are in C-04's DB tables

    def on_startup(self) -> None:
        pass

    def on_shutdown(self) -> None:
        pass

    def register_cli(self, cli: Any) -> None:
        pass


manifest = AcademicStructureManifest()

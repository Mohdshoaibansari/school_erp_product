"""C-05 Academic Structure — routes package."""

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

__all__ = [
    "academic_years_router",
    "terms_router",
    "grade_levels_router",
    "classes_router",
    "class_academic_years_router",
    "sections_router",
    "curriculum_router",
    "curriculum_versions_router",
    "subjects_router",
    "section_subjects_router",
    "grade_academic_year_curriculum_router",
]

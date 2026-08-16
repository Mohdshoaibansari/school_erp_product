"""C-05 Academic Structure — CloneService (T20, D16, D22).

Clones academic structure from a previous year.
Skips archived/deleted entities (D22).
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from kernel.academic.models.academic_year import AcademicYear
from kernel.academic.models.term import Term
from kernel.academic.models.grade_level import GradeLevel
from kernel.academic.models.class_entity import ClassEntity
from kernel.academic.models.section import Section
from kernel.academic.models.subject import Subject

from kernel.academic.repos.academic_repo import TermRepo
from kernel.academic.repos.structure_repo import GradeLevelRepo, ClassRepo, SectionRepo
from kernel.academic.repos.subject_repo import SubjectRepo


class CloneService:
    """Clones academic structure from a previous year."""

    def __init__(self, db: Session):
        self.db = db
        self.term_repo = TermRepo(db)
        self.grade_repo = GradeLevelRepo(db)
        self.class_repo = ClassRepo(db)
        self.section_repo = SectionRepo(db)
        self.subject_repo = SubjectRepo(db)

    def clone_from_year(
        self,
        source_year_id: uuid.UUID,
        target_year_id: uuid.UUID,
        client_id: uuid.UUID,
        institution_id: uuid.UUID,
    ) -> dict:
        """Clone structure from source year to target year.

        Only clones active entities (D22 — skips archived/deleted).
        Clears homeroom_teacher_id on cloned sections.

        Returns dict with counts of cloned entities.
        """
        counts = {"terms": 0, "grade_levels": 0, "classes": 0, "sections": 0, "subjects": 0}

        # Build ID mapping: source_id → target_id
        gl_map: dict[uuid.UUID, uuid.UUID] = {}
        cls_map: dict[uuid.UUID, uuid.UUID] = {}

        # Clone grade levels
        source_gls = self.db.execute(
            select(GradeLevel).where(
                GradeLevel.academic_year_id == source_year_id,
                GradeLevel.archived_at.is_(None),
            ).order_by(GradeLevel.sort_order)
        ).scalars().all()

        for gl in source_gls:
            new_gl = self.grade_repo.create(client_id, institution_id, target_year_id, gl.name, gl.sort_order)
            gl_map[gl.id] = new_gl.id
            counts["grade_levels"] += 1

        # Clone classes
        source_classes = self.db.execute(
            select(ClassEntity).where(
                ClassEntity.academic_year_id == source_year_id,
            ).order_by(ClassEntity.sort_order)
        ).scalars().all()

        for cls in source_classes:
            new_gl_id = gl_map.get(cls.grade_level_id)
            if not new_gl_id:
                continue
            new_cls = self.class_repo.create(client_id, institution_id, target_year_id, new_gl_id, cls.name, cls.sort_order)
            cls_map[cls.id] = new_cls.id
            counts["classes"] += 1

        # Clone sections (clear homeroom_teacher_id)
        source_sections = self.db.execute(
            select(Section).where(Section.academic_year_id == source_year_id)
        ).scalars().all()

        for section in source_sections:
            new_cls_id = cls_map.get(section.class_id)
            if not new_cls_id:
                continue
            self.section_repo.create(
                client_id, institution_id, target_year_id, new_cls_id,
                section.name, homeroom_teacher_id=None, sort_order=section.sort_order,
            )
            counts["sections"] += 1

        # Clone subjects
        source_subjects = self.db.execute(
            select(Subject).where(Subject.academic_year_id == source_year_id)
        ).scalars().all()

        for subj in source_subjects:
            self.subject_repo.create(client_id, institution_id, target_year_id, subj.name, subj.code, subj.sort_order)
            counts["subjects"] += 1

        return counts

    def find_latest_closed_year(self, institution_id: uuid.UUID) -> AcademicYear | None:
        """Find the most recent closed AcademicYear for cloning."""
        stmt = select(AcademicYear).where(
            AcademicYear.institution_id == institution_id,
            AcademicYear.status == "closed",
        ).order_by(AcademicYear.start_date.desc()).limit(1)
        return self.db.execute(stmt).scalar_one_or_none()

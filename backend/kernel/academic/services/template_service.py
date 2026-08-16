"""C-05 Academic Structure — TemplateService (T19).

Generates academic structure from config template.
"""

from __future__ import annotations

import uuid
import json

from sqlalchemy.orm import Session

from kernel.academic.repos.academic_repo import TermRepo
from kernel.academic.repos.structure_repo import GradeLevelRepo, ClassRepo, SectionRepo
from kernel.academic.repos.subject_repo import SubjectRepo
from kernel.config.services.configuration_service import ConfigurationService


class TemplateService:
    """Generates academic structure from C-08 config template."""

    def __init__(self, db: Session):
        self.db = db
        self.term_repo = TermRepo(db)
        self.grade_repo = GradeLevelRepo(db)
        self.class_repo = ClassRepo(db)
        self.section_repo = SectionRepo(db)
        self.subject_repo = SubjectRepo(db)

    def generate_from_template(
        self,
        academic_year_id: uuid.UUID,
        client_id: uuid.UUID,
        institution_id: uuid.UUID,
        start_date,
        end_date,
        config_service: ConfigurationService | None = None,
    ) -> dict:
        """Generate full academic structure from config template.

        Returns dict with counts of created entities.
        """
        # Get template from config
        if config_service:
            template_json = config_service.get_value("academic.schoolTemplate", institution_id=institution_id, client_id=client_id)
            if template_json and isinstance(template_json, str):
                template = json.loads(template_json)
            elif template_json and isinstance(template_json, dict):
                template = template_json
            else:
                template = self._default_template()
        else:
            template = self._default_template()

        grade_names = template.get("gradeLevels", [])
        section_names = template.get("sections", ["A", "B", "C"])
        subject_names = template.get("defaultSubjects", [])
        term_structure = template.get("termStructure", "yearly")

        counts = {"terms": 0, "grade_levels": 0, "classes": 0, "sections": 0, "subjects": 0}

        # Create terms based on term structure
        if term_structure == "yearly":
            self.term_repo.create(client_id, institution_id, academic_year_id, "Term 1", start_date, end_date, 1)
            counts["terms"] = 1
        elif term_structure == "semester":
            mid = start_date.replace(month=start_date.month + 6) if start_date.month <= 6 else end_date
            self.term_repo.create(client_id, institution_id, academic_year_id, "Semester 1", start_date, mid, 1)
            self.term_repo.create(client_id, institution_id, academic_year_id, "Semester 2", mid, end_date, 2)
            counts["terms"] = 2

        # Create grade levels, classes, sections
        for gl_idx, gl_name in enumerate(grade_names, 1):
            gl = self.grade_repo.create(client_id, institution_id, academic_year_id, gl_name, gl_idx)
            counts["grade_levels"] += 1

            for cls_idx, section_name in enumerate(section_names, 1):
                cls_name = f"{gl_name.replace('Grade ', '')}{section_name}"
                cls = self.class_repo.create(client_id, institution_id, academic_year_id, gl.id, cls_name, cls_idx)
                counts["classes"] += 1

                # Create sections within class (one section per class for now)
                self.section_repo.create(client_id, institution_id, academic_year_id, cls.id, section_name, sort_order=1)
                counts["sections"] += 1

        # Create subjects
        for subj_idx, subj_name in enumerate(subject_names, 1):
            self.subject_repo.create(client_id, institution_id, academic_year_id, subj_name, sort_order=subj_idx)
            counts["subjects"] += 1

        return counts

    def _default_template(self) -> dict:
        """Default template when config is not available."""
        return {
            "gradeLevels": [
                "Grade 1", "Grade 2", "Grade 3", "Grade 4", "Grade 5",
                "Grade 6", "Grade 7", "Grade 8", "Grade 9", "Grade 10",
                "Grade 11", "Grade 12",
            ],
            "sections": ["A", "B", "C"],
            "defaultSubjects": ["Mathematics", "Science", "English", "Hindi", "Social Studies", "Computer Science"],
            "termStructure": "yearly",
        }

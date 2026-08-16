"""C-05 Academic Structure — LifecycleService (T21, D6, D20).

AcademicYear lifecycle transitions: planning → active → closed.
Close is non-blocking (D20) — in-flight entities become read-only.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from kernel.academic.models.academic_year import AcademicYear
from kernel.academic.models.student_enrollment import StudentEnrollment
from kernel.academic.models.teacher_assignment import TeacherAssignment


class LifecycleService:
    """AcademicYear lifecycle state machine."""

    VALID_TRANSITIONS = {
        "planning": ["active"],
        "active": ["closed"],
        "closed": [],  # No reverse transitions
    }

    def __init__(self, db: Session):
        self.db = db

    def transition(
        self,
        academic_year: AcademicYear,
        new_state: str,
        reason: str | None = None,
    ) -> AcademicYear:
        """Transition AcademicYear to new state.

        Rules:
        - planning → active: Auto-closes previous active year
        - active → closed: Non-blocking, in-flight entities become read-only (D20)
        - No reverse transitions
        """
        current_state = academic_year.status

        if new_state not in self.VALID_TRANSITIONS.get(current_state, []):
            raise ValueError(
                f"Invalid transition: {current_state} → {new_state}. "
                f"Valid transitions from {current_state}: {self.VALID_TRANSITIONS[current_state]}"
            )

        if new_state == "active":
            self._activate(academic_year)
        elif new_state == "closed":
            self._close(academic_year)

        return academic_year

    def _activate(self, academic_year: AcademicYear) -> None:
        """Activate a planning year. Auto-closes previous active year."""
        # Close any currently active year
        previous_active = self.db.execute(
            select(AcademicYear).where(
                AcademicYear.institution_id == academic_year.institution_id,
                AcademicYear.status == "active",
            )
        ).scalar_one_or_none()

        if previous_active:
            self._close(previous_active)

        academic_year.status = "active"
        self.db.flush()

    def _close(self, academic_year: AcademicYear) -> None:
        """Close an active year. Non-blocking (D20).

        In-flight homework, enrollments, and teacher assignments become read-only.
        """
        academic_year.status = "closed"
        self.db.flush()

        # Mark enrollments as archived (read-only)
        self.db.execute(
            update(StudentEnrollment).where(
                StudentEnrollment.academic_year_id == academic_year.id,
                StudentEnrollment.status == "active",
            ).values(status="archived")
        )

        # Mark teacher assignments as archived (read-only)
        self.db.execute(
            update(TeacherAssignment).where(
                TeacherAssignment.academic_year_id == academic_year.id,
                TeacherAssignment.status == "active",
            ).values(status="archived")
        )

        self.db.flush()

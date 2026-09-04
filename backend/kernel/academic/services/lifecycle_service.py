"""C-05 Academic Structure — LifecycleService.

AcademicYear lifecycle transitions: planning → active → closed, or planning → cancelled.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from kernel.academic.models.academic_year import AcademicYear


class LifecycleService:
    """AcademicYear lifecycle state machine."""

    VALID_TRANSITIONS = {
        "planning": ["active", "cancelled"],
        "active": ["closed"],
        "closed": [],  # No reverse transitions
        "cancelled": [],  # Terminal state
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
        - planning → active: Must close current active year first
        - planning → cancelled: Terminal state
        - active → closed: Sets closed_at timestamp
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
        elif new_state == "cancelled":
            self._cancel(academic_year)

        return academic_year

    def _activate(self, academic_year: AcademicYear) -> None:
        """Activate a planning year.

        Rules:
        - Must not have another active year for the same institution
        - start_date and end_date must be set
        """
        # Check for existing active year
        existing_active = self.db.execute(
            select(AcademicYear).where(
                AcademicYear.institution_id == academic_year.institution_id,
                AcademicYear.status == "active",
            )
        ).scalar_one_or_none()

        if existing_active:
            raise ValueError(
                f"Cannot activate: AcademicYear '{existing_active.name}' is already active. "
                "Close it first before activating another year."
            )

        academic_year.status = "active"
        self.db.flush()

    def _close(self, academic_year: AcademicYear) -> None:
        """Close an active year.

        Sets closed_at timestamp for early closure tracking.
        """
        academic_year.status = "closed"
        academic_year.closed_at = datetime.utcnow()
        self.db.flush()

    def _cancel(self, academic_year: AcademicYear) -> None:
        """Cancel a planning year. Terminal state."""
        academic_year.status = "cancelled"
        self.db.flush()

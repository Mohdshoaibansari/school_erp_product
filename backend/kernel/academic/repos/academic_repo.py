"""C-05 Academic Structure — AcademicYear and Term repos."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from kernel.academic.models.academic_year import AcademicYear
from kernel.academic.models.term import Term


class AcademicYearRepo:
    """Repository for AcademicYear entity."""

    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        client_id: uuid.UUID,
        institution_id: uuid.UUID,
        name: str,
        start_date,
        end_date,
        status: str = "planning",
    ) -> AcademicYear:
        year = AcademicYear(
            client_id=client_id,
            institution_id=institution_id,
            name=name,
            start_date=start_date,
            end_date=end_date,
            status=status,
        )
        self.db.add(year)
        self.db.flush()
        return year

    def get_by_id(self, year_id: uuid.UUID) -> AcademicYear | None:
        return self.db.get(AcademicYear, year_id)

    def list_by_institution(
        self, institution_id: uuid.UUID, status: str | None = None
    ) -> Sequence[AcademicYear]:
        stmt = select(AcademicYear).where(AcademicYear.institution_id == institution_id)
        if status:
            stmt = stmt.where(AcademicYear.status == status)
        stmt = stmt.order_by(AcademicYear.start_date.desc())
        return list(self.db.execute(stmt).scalars().all())

    def get_active(self, institution_id: uuid.UUID) -> AcademicYear | None:
        stmt = select(AcademicYear).where(
            AcademicYear.institution_id == institution_id,
            AcademicYear.status == "active",
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def update(self, year: AcademicYear, **kwargs) -> AcademicYear:
        for key, value in kwargs.items():
            setattr(year, key, value)
        self.db.flush()
        return year

    def check_overlap(
        self,
        institution_id: uuid.UUID,
        start_date,
        end_date,
        exclude_id: uuid.UUID | None = None,
    ) -> bool:
        """Check if date range overlaps with existing AcademicYears."""
        stmt = select(AcademicYear).where(
            AcademicYear.institution_id == institution_id,
            AcademicYear.status != "cancelled",
            AcademicYear.start_date < end_date,
            AcademicYear.end_date > start_date,
        )
        if exclude_id:
            stmt = stmt.where(AcademicYear.id != exclude_id)
        return self.db.execute(stmt).scalar_one_or_none() is not None


class TermRepo:
    """Repository for Term entity."""

    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        client_id: uuid.UUID,
        institution_id: uuid.UUID,
        academic_year_id: uuid.UUID,
        name: str,
        start_date,
        end_date,
        sort_order: int = 0,
    ) -> Term:
        term = Term(
            client_id=client_id,
            institution_id=institution_id,
            academic_year_id=academic_year_id,
            name=name,
            start_date=start_date,
            end_date=end_date,
            sort_order=sort_order,
        )
        self.db.add(term)
        self.db.flush()
        return term

    def get_by_id(self, term_id: uuid.UUID) -> Term | None:
        return self.db.get(Term, term_id)

    def list_by_academic_year(self, academic_year_id: uuid.UUID) -> Sequence[Term]:
        stmt = select(Term).where(Term.academic_year_id == academic_year_id).order_by(Term.sort_order)
        return list(self.db.execute(stmt).scalars().all())

    def update(self, term: Term, **kwargs) -> Term:
        for key, value in kwargs.items():
            setattr(term, key, value)
        self.db.flush()
        return term

    def delete(self, term: Term) -> None:
        self.db.delete(term)
        self.db.flush()

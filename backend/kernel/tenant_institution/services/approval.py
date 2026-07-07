"""Approval flow service (Q3, AC-19).

Provides the blocking approval semantics:
- ``request_approval`` creates a pending ``Approval`` row.
- ``approve_approval`` marks it ``approved``.
- ``deny_approval`` marks it ``denied``.
- ``assert_approved`` is a guard that the dependent transition/transfer calls
  before executing — it raises if the approval is not yet granted (pending)
  or has been denied.

This module is a pure service layer helper — it operates on the
``ApprovalRepository`` and is called by the lifecycle/transfer orchestration.
"""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from kernel.tenant_context import TenantContext
from kernel.tenant_institution.repos import ApprovalRepository
from kernel.tenant_institution.services.dtos import ApprovalDTO


class ApprovalNotGrantedError(ValueError):
    """Raised when a dependent operation is attempted before approval is granted."""

    def __init__(self, approval_id: uuid.UUID, status: str) -> None:
        self.approval_id = approval_id
        self.status = status
        super().__init__(
            f"Approval {approval_id} is '{status}' — operation blocked (AC-19)"
        )


class ApprovalDeniedError(ValueError):
    """Raised when a dependent operation is attempted after approval was denied."""

    def __init__(self, approval_id: uuid.UUID) -> None:
        self.approval_id = approval_id
        super().__init__(
            f"Approval {approval_id} was denied — operation permanently blocked (AC-19)"
        )


def request_approval(
    session: Session,
    ctx: TenantContext,
    approval_repo: ApprovalRepository,
    *,
    requested_by: str,
    context_type: str | None = None,
    context_id: uuid.UUID | None = None,
    reason: str | None = None,
) -> ApprovalDTO:
    """Create a pending Approval row (Q3, AC-19).

    The dependent transition/transfer cannot complete until this approval is
    granted via ``approve_approval``.
    """
    return approval_repo.create(
        session, ctx,
        requested_by=requested_by,
        context_type=context_type,
        context_id=context_id,
        reason=reason,
    )


def approve_approval(
    session: Session,
    ctx: TenantContext,
    approval_repo: ApprovalRepository,
    approval_id: uuid.UUID,
    approved_by: str,
) -> ApprovalDTO:
    """Mark an Approval as approved (Q3, AC-19)."""
    return approval_repo.approve(session, ctx, approval_id, approved_by)


def deny_approval(
    session: Session,
    ctx: TenantContext,
    approval_repo: ApprovalRepository,
    approval_id: uuid.UUID,
    approved_by: str,
) -> ApprovalDTO:
    """Mark an Approval as denied (Q3, AC-19). The dependent operation is blocked."""
    return approval_repo.deny(session, ctx, approval_id, approved_by)


def assert_approved(
    session: Session,
    ctx: TenantContext,
    approval_repo: ApprovalRepository,
    approval_id: uuid.UUID,
) -> ApprovalDTO:
    """Guard: assert that an Approval is approved before proceeding (Q3, AC-19).

    Raises:
        ``ApprovalNotGrantedError`` — if the approval is still pending.
        ``ApprovalDeniedError`` — if the approval was denied.
        ``ValueError`` — if the approval does not exist.
    """
    approval = approval_repo.get(session, ctx, approval_id)
    if approval is None:
        raise ValueError(f"Approval {approval_id} not found")
    if approval.status == "pending":
        raise ApprovalNotGrantedError(approval_id, approval.status)
    if approval.status == "denied":
        raise ApprovalDeniedError(approval_id)
    # status == "approved" → proceed
    return approval

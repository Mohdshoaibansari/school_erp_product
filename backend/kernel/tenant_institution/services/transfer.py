"""Ownership transfer coordinator (D12, AC-11) — boundary hooks.

Defines the ``TransferCoordinator`` protocol with extension points for
downstream capabilities to plug into the single-transaction ownership transfer:

- ``migrate_academic_structure(institution_id, from_client, to_client, session)``
  → C-05 (Academic Structure) — boundary, owned by C-05.
- ``migrate_users(institution_id, from_client, to_client, session)``
  → C-02 (Users) — boundary, owned by C-02.
- ``migrate_billing(institution_id, from_client, to_client)``
  → C-07/C-23 (Subscriptions/Billing) — boundary, owned by C-07/C-23.
- ``preserve_audit_client_ids(institution_id, from_client, to_client, session)``
  → C-11 (Audit) — boundary invariant, owned by C-11.

The default implementation (``DefaultTransferCoordinator``) is a **no-op stub**
for each hook. It logs the boundary call and returns. C-05/C-02/C-07/C-23/C-11
will provide their own implementations when those capabilities are built.

The C-01-owned parts (Institution row + OrgUnit ``client_id`` migration +
``OwnershipTransferEvent`` recording) are handled directly in
``OwnershipTransferRepository.approve_transfer`` — NOT in these hooks.
"""

from __future__ import annotations

import logging
import uuid
from typing import Protocol, runtime_checkable

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


@runtime_checkable
class TransferCoordinator(Protocol):
    """Protocol defining extension points for the ownership transfer (D12).

    C-01 owns the transfer workflow and calls these hooks within the
    single-transaction boundary. Each downstream capability provides its own
    implementation. The default (``DefaultTransferCoordinator``) is a no-op.
    """

    def migrate_academic_structure(
        self,
        institution_id: uuid.UUID,
        from_client_id: uuid.UUID,
        to_client_id: uuid.UUID,
        session: Session,
    ) -> None:
        """C-05 boundary: migrate academic structure client_id A→B.

        Owned by C-05 (Academic Structure). C-01 calls this hook within the
        transfer transaction; C-05 plugs in its own implementation to update
        ``AcademicYear``, ``Term``, ``Subject``, and academic assignment rows.
        """
        ...

    def migrate_users(
        self,
        institution_id: uuid.UUID,
        from_client_id: uuid.UUID,
        to_client_id: uuid.UUID,
        session: Session,
    ) -> None:
        """C-02 boundary: migrate user-institution assignments + student records.

        Owned by C-02 (Users). C-01 calls this hook within the transfer
        transaction; C-02 plugs in its own implementation to update
        user-institution assignments and student records' ``client_id``.

        D12 user migration rules:
        - Users whose ONLY Institution is the transferred one → migrate to Client B.
        - Users with other Client-A Institutions → stay in Client A, lose the
          transferred Institution.
        """
        ...

    def migrate_billing(
        self,
        institution_id: uuid.UUID,
        from_client_id: uuid.UUID,
        to_client_id: uuid.UUID,
    ) -> None:
        """C-07/C-23 boundary: move subscription to Client B next billing cycle.

        Owned by C-07 (Subscriptions) and C-23 (Billing). C-01 notes the
        billing-handoff coordination point; C-07/C-23 own the billing behavior.
        This hook is called AFTER the transfer transaction commits (billing
        handoff is next-cycle, not in-transaction).
        """
        ...

    def preserve_audit_client_ids(
        self,
        institution_id: uuid.UUID,
        from_client_id: uuid.UUID,
        to_client_id: uuid.UUID,
        session: Session,
    ) -> None:
        """C-11 boundary invariant: pre-transfer audit events keep original ClientId.

        The transfer transaction MUST NOT rewrite pre-existing audit-event
        ``client_id`` values. C-11 audit events recorded before the transfer
        stay immutable under their original ClientId (ADR §5 constraint 14).

        C-11 owns the audit event log. This hook is a no-op by default — the
        invariant is that the transfer transaction does NOT touch audit event
        rows. C-11 may add verification logic when it exists.
        """
        ...


class DefaultTransferCoordinator:
    """Default no-op implementation of ``TransferCoordinator`` (boundary stubs).

    All hooks are no-ops with a log message marking the boundary. Downstream
    capabilities (C-05, C-02, C-07/C-23, C-11) will provide real implementations
    in their own changes. C-01's transfer transaction calls these hooks; the
    no-op ensures the hook is CALLED (testable) without fake-completing the
    downstream behavior.
    """

    def migrate_academic_structure(
        self,
        institution_id: uuid.UUID,
        from_client_id: uuid.UUID,
        to_client_id: uuid.UUID,
        session: Session,
    ) -> None:
        # BOUNDARY: C-05 (Academic Structure) owns this migration.
        # C-01 calls the hook; C-05 plugs in its own implementation.
        logger.info(
            "TransferCoordinator.migrate_academic_structure: BOUNDARY — "
            "institution %s A→B (clients %s→%s). "
            "C-05 owns academic-structure client_id migration.",
            institution_id, from_client_id, to_client_id,
        )

    def migrate_users(
        self,
        institution_id: uuid.UUID,
        from_client_id: uuid.UUID,
        to_client_id: uuid.UUID,
        session: Session,
    ) -> None:
        # BOUNDARY: C-02 (Users) owns user-institution assignments + student records.
        # C-01 calls the hook; C-02 plugs in its own implementation.
        # D12 user migration rules: only-Institution users → B; multi-Institution
        # users → stay in A, lose transferred Institution.
        logger.info(
            "TransferCoordinator.migrate_users: BOUNDARY — "
            "institution %s A→B (clients %s→%s). "
            "C-02 owns user-institution assignment + student record migration.",
            institution_id, from_client_id, to_client_id,
        )

    def migrate_billing(
        self,
        institution_id: uuid.UUID,
        from_client_id: uuid.UUID,
        to_client_id: uuid.UUID,
    ) -> None:
        # BOUNDARY: C-07/C-23 (Subscriptions/Billing) own the billing handoff.
        # C-01 notes the coordination point; C-07/C-23 own the billing behavior.
        # Billing handoff is next-cycle (NOT in-transaction).
        logger.info(
            "TransferCoordinator.migrate_billing: BOUNDARY — "
            "institution %s A→B (clients %s→%s). "
            "C-07/C-23 own billing handoff (next billing cycle).",
            institution_id, from_client_id, to_client_id,
        )

    def preserve_audit_client_ids(
        self,
        institution_id: uuid.UUID,
        from_client_id: uuid.UUID,
        to_client_id: uuid.UUID,
        session: Session,
    ) -> None:
        # BOUNDARY INVARIANT: C-11 audit events keep their original client_id.
        # The transfer transaction MUST NOT rewrite pre-existing audit-event
        # client_ids (ADR §5 constraint 14). This hook is a no-op — the
        # invariant is that the transfer does NOT touch audit event rows.
        # C-11 may add verification logic when it exists.
        logger.info(
            "TransferCoordinator.preserve_audit_client_ids: BOUNDARY INVARIANT — "
            "institution %s A→B (clients %s→%s). "
            "Pre-transfer audit events keep original client_id (immutable). "
            "C-11 owns the audit log; transfer MUST NOT rewrite audit client_ids.",
            institution_id, from_client_id, to_client_id,
        )

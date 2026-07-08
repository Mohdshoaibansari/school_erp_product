"""C-11 audit emission boundary hook (D8, D9, Q7, D12, AC-5, AC-6, AC-10, AC-11).

C-11 (Audit) is a **BOUNDARY** — C-11 owns the audit log (storage, retention,
the immutable event table). C-01 implements a **synchronous** AuditEmitter
Protocol + a default capture implementation so the emission is testable
without depending on C-11's storage (which does not exist yet). The real
C-11 storage is C-11's responsibility; C-11 will plug in its own emitter
implementation in a future change (Q4 deferred — no message broker / async
event bus is introduced for C-01; emission is synchronous, in-process).

This mirrors the ``TransferCoordinator`` boundary-hook pattern from Apply-C:
a Protocol with extension points + a default no-op/capture stub that C-01's
own code calls. Tests assert the emitter is CALLED with the right payload
(ClientId, InstitutionId, action, actor, ...). The default implementation
captures events in an instance-level list + logs them — both testable.

Boundary contract:
- C-01 emits synchronous audit events tagged with ClientId (+ InstitutionId
  where applicable) on every lifecycle transition, OrgUnit move, and ownership
  transfer (ADR §5 constraint 14, AC-5/AC-6/AC-10/AC-11).
- Audit events recorded BEFORE an ownership transfer keep their original
  ClientId across the transfer — the immutability invariant (D12, ADR §5
  constraint 14). The transfer transaction MUST NOT rewrite pre-existing
  audit-event ``client_id`` values. C-01's ``preserve_audit_client_ids`` hook
  (TransferCoordinator) is a no-op that expresses this invariant; the
  AuditEmitter itself never rewrites past events.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Protocol, runtime_checkable

logger = logging.getLogger(__name__)


@runtime_checkable
class AuditEmitter(Protocol):
    """Protocol for C-11 audit emission (boundary hook, A4 published interface).

    C-01 calls ``emit(...)`` synchronously after each audited write
    (lifecycle transition, OrgUnit move, ownership transfer). C-11 owns the
    real implementation (audit-table persistence, retention); the default
    capture implementation below is a testable no-op until C-11 exists.

    The emitter is SYNCHRONOUS (Q4 deferred — no message broker / async event
    bus for C-01). No ``import pika/kafka/redis/celery``.
    """

    def emit(
        self,
        *,
        action: str,
        client_id: uuid.UUID,
        institution_id: uuid.UUID | None = None,
        actor: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        """Emit a synchronous C-11 audit event.

        Args:
            action: the audit action (e.g. ``"client_lifecycle_transition"``,
                ``"institution_lifecycle_transition"``, ``"org_unit_moved"``,
                ``"ownership_transferred"``).
            client_id: the Client (tenant) the event is tagged with. This is
                the original ClientId AT EMISSION TIME — it is immutable across
                later ownership transfers (D12, ADR §5 constraint 14).
            institution_id: the Institution the event relates to, if applicable
                (lifecycle transitions, OrgUnit moves, transfers).
            actor: the user identity that performed the write (from
                ``TenantContext.user_id``). All C-01 writes record actor
                identity via C-11 (AC-15).
            payload: action-specific provenance, e.g. for OrgUnit moves
                ``{from_parent, to_parent, moved_by, ...}`` (Q7).
        """
        ...


class DefaultAuditEmitter:
    """Default capture implementation of ``AuditEmitter`` (boundary stub).

    Captures emitted events in an instance-level list (testable) and logs each
    event structurally. C-11 plugs in its own persistence implementation later;
    this default does NOT touch any audit table (C-11 owns the audit log).

    The capture list is exposed via ``events`` so tests can assert the emitted
    payloads without a real audit table. In production the singleton service
    uses one instance; events accumulate in-memory (acceptable for the boundary
    stub — C-11 owns real storage/retention).
    """

    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    def emit(
        self,
        *,
        action: str,
        client_id: uuid.UUID,
        institution_id: uuid.UUID | None = None,
        actor: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        event = {
            "action": action,
            "client_id": client_id,
            "institution_id": institution_id,
            "actor": actor,
            "payload": payload or {},
        }
        self.events.append(event)
        # Synchronous structured log (also testable where caplog is used).
        logger.info(
            "c11_audit_event: action=%s client_id=%s institution_id=%s actor=%s payload=%s",
            action, client_id, institution_id, actor, payload,
        )

    def clear(self) -> None:
        """Clear captured events (test helper)."""
        self.events.clear()
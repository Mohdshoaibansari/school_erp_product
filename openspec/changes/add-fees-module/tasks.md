# Implementation Tasks — Fees Module

> **Traceability:** Each task traces to PRD AC-IDs and grill-me decision IDs (D1–D22).

---

## 1. Module structure & manifest (D7, D16)

- [ ] 1.1 Create directory structure at `backend/business/fees/` with `__init__.py`, `manifest.py`, `models/`, `repos/`, `services/`, `routes/`, `dependencies.py`.
- [ ] 1.2 Implement `FeesManifest` (subclass of `ManifestBase`) with `register_routes`, `register_casbin_policies` (empty), `on_startup`, `on_shutdown`, `register_cli`. Create `manifest` singleton.
- [ ] 1.3 Register fees manifest in `tests/conftest.py` app fixture: `create_app([..., fees_manifest])`.

## 2. Database schema — migration `005_fees_module.py` (D3, D4, D5, D20)

- [ ] 2.1 Create `fee_type` table with RLS (standard C-01/C-02 pattern).
- [ ] 2.2 Create `fee_assignment` table with RLS.
- [ ] 2.3 Create `payment` table with RLS.
- [ ] 2.4 Insert 11 fee-related permission rows into C-04's `permission` table (ON CONFLICT DO NOTHING).
- [ ] 2.5 Insert ~17 role-permission rows into C-04's `role_permission` table.

## 3. ORM models (D3, D4, D5)

- [ ] 3.1 Implement `FeeType` model.
- [ ] 3.2 Implement `FeeAssignment` model.
- [ ] 3.3 Implement `Payment` model.

## 4. DTOs (D4, D5)

- [ ] 4.1 Implement `FeeTypeCreateDTO`, `FeeTypeDTO`, `FeeTypeUpdateDTO`.
- [ ] 4.2 Implement `FeeAssignmentCreateDTO` (with `user_ids` list), `FeeAssignmentDTO`, `FeeAssignmentUpdateDTO`, `WaiveDTO`.
- [ ] 4.3 Implement `PaymentCreateDTO`, `PaymentDTO`.

## 5. Repositories (D3, D4, D5)

- [ ] 5.1 Implement `FeeTypeRepository` (inherits `TenantAwareRepositoryBase`).
- [ ] 5.2 Implement `FeeAssignmentRepository` (with `list` supporting `user_id`, `status`, `overdue` filters, `get_total_payments`).
- [ ] 5.3 Implement `PaymentRepository` (with `get_next_receipt_number` using row-level lock).

## 6. Service layer (D6, D10, D11, D12, D13, D17, D19)

- [ ] 6.1 Implement `FeesService` class with injected repos, session_factory, audit_emitter.
- [ ] 6.2 Implement fee type CRUD methods.
- [ ] 6.3 Implement `create_fee_assignments` (bulk, validates user_category='Learner', atomic transaction).
- [ ] 6.4 Implement fee assignment list/get/update/waive methods.
- [ ] 6.5 Implement `record_payment` (auto status update via SUM, receipt generation, atomic).
- [ ] 6.6 Implement payment list method.
- [ ] 6.7 Implement ownership enforcement (Student/Parent → own records only).

## 7. Routes (D9, D13)

- [ ] 7.1 Implement `routes/fee_types.py` (5 endpoints, all with `require_permission`).
- [ ] 7.2 Implement `routes/fee_assignments.py` (5 endpoints, all with `require_permission`, student ownership).
- [ ] 7.3 Implement `routes/payments.py` (2 endpoints, all with `require_permission`, student ownership).

## 8. Dependencies (D16)

- [ ] 8.1 Implement `get_fees_service()` dependency.
- [ ] 8.2 Wire dependency into all route handlers.

## 9. Audit (D14)

- [ ] 9.1 Emit `fee_type_created` on POST /fee-types.
- [ ] 9.2 Emit `fee_type_updated` on PATCH /fee-types.
- [ ] 9.3 Emit `fee_assigned` on POST /fee-assignments.
- [ ] 9.4 Emit `fee_waived` on POST /fee-assignments/{id}/waive.
- [ ] 9.5 Emit `payment_recorded` on POST /payments.

## 10. Integration tests (AC-1 through AC-10)

- [ ] 10.1 Test fee type CRUD (AC-1): create, list, get, update, delete.
- [ ] 10.2 Test fee assignment (AC-2): single + bulk creation, validates Learner category.
- [ ] 10.3 Test payment recording (AC-3): full payment → paid, partial → partial, receipt generated.
- [ ] 10.4 Test lifecycle statuses (AC-4): pending → paid/partial/waived, overdue computed.
- [ ] 10.5 Test student access (AC-5): own fees visible, other student's fees blocked.
- [ ] 10.6 Test authorization (AC-6): Teacher cannot create fee type, Student cannot waive.
- [ ] 10.7 Test audit (AC-7): 5 event types emitted.
- [ ] 10.8 Test bulk assignment (AC-8): atomic, invalid user_id → rollback.
- [ ] 10.9 Test receipt numbers (AC-9): sequential, no duplicates.
- [ ] 10.10 Test tenant isolation (AC-10): School A cannot see School B's fees.

## 11. Regression

- [ ] 11.1 All 288 existing tests pass.
- [ ] 11.2 Import-linter: 2 kept, 0 broken.

# Fees Module — Specification

> **Domain:** `fees`  
> **Classification:** ADDED  
> **Tier:** Business  
> **Depends on:** C-01 (tenant isolation), C-02 (student identity), C-04 (authorization), C-11 (audit)

---

## FR-1: Fee Type Management

### FR-1.1: Create Fee Type
An Admin can create a fee type with name, description, default_amount, institution_id. The fee type is tenant-scoped (inherits client_id from TenantContext).

**Acceptance:**
- `POST /api/v1/fee-types` with `{ name, description?, default_amount }` returns 201 with FeeTypeDTO.
- `FeeType.client_id` is auto-injected from TenantContext.
- `FeeType.institution_id` from the request body.
- Duplicate names within the same institution are rejected.

### FR-1.2: List Fee Types
List all fee types for the current institution. Supports optional `?institution_id=` filter for cross-institution roles.

**Acceptance:**
- `GET /api/v1/fee-types` returns list of FeeTypeDTO.
- Tenant-filtered: shows only fee types for the user's institution.

### FR-1.3: Get Fee Type
Get a single fee type by ID.

**Acceptance:**
- `GET /api/v1/fee-types/{id}` returns FeeTypeDTO or 404.

### FR-1.4: Update Fee Type
Update a fee type's name, description, default_amount, or is_active.

**Acceptance:**
- `PATCH /api/v1/fee-types/{id}` with partial fields returns updated FeeTypeDTO.

### FR-1.5: Delete Fee Type
Soft-delete a fee type (sets is_active = false).

**Acceptance:**
- `DELETE /api/v1/fee-types/{id}` returns 204.

---

## FR-2: Fee Assignment

### FR-2.1: Create Fee Assignment
An Admin can assign a fee to a student. Supports single and bulk assignment.

**Acceptance:**
- `POST /api/v1/fee-assignments` with `{ fee_type_id, amount, due_date, academic_term, user_ids: [...] }` returns 201 with list of FeeAssignmentDTO.
- Bulk: one assignment per user_id. All in one transaction.
- Validates that each user_id belongs to user_category 'Learner'.
- `assigned_by` is set to `ctx.user_id`.
- Status starts as `pending`.

### FR-2.2: List Fee Assignments
List fee assignments with optional filters.

**Acceptance:**
- `GET /api/v1/fee-assignments` supports `?user_id=`, `?status=`, `?overdue=true`.
- `?overdue=true` computes: `due_date < today AND status IN ('pending', 'partial')`.
- Student/Parent can only query `?user_id=<self>`.

### FR-2.3: Get Fee Assignment
Get a single fee assignment with its payment history.

**Acceptance:**
- `GET /api/v1/fee-assignments/{id}` returns FeeAssignmentDTO with payment_summary.

### FR-2.4: Update Fee Assignment
Update amount, due_date, academic_term, or notes.

**Acceptance:**
- `PATCH /api/v1/fee-assignments/{id}` returns updated FeeAssignmentDTO.
- Cannot update if status is `paid` or `waived`.

### FR-2.5: Waive Fee
Admin waives a fee assignment (terminal).

**Acceptance:**
- `POST /api/v1/fee-assignments/{id}/waive` with `{ reason }` returns updated FeeAssignmentDTO.
- Status changes to `waived`. No further updates allowed.
- Audit event emitted.

---

## FR-3: Payment Recording

### FR-3.1: Record Payment
Admin records a payment against a fee assignment.

**Acceptance:**
- `POST /api/v1/payments` with `{ fee_assignment_id, amount, payment_method, payment_date?, reference_number?, notes? }` returns 201 with PaymentDTO.
- Receipt number auto-generated: `REC-{INST}-{NNNNNN}`.
- FeeAssignment status auto-updated:
  - If total_payments >= assignment.amount → `paid`.
  - If total_payments > 0 AND < assignment.amount → `partial`.
- All in one transaction.
- Audit event emitted.

### FR-3.2: List Payments
List payments with optional filters.

**Acceptance:**
- `GET /api/v1/payments` supports `?fee_assignment_id=`, `?user_id=`.
- Student/Parent can only query `?user_id=<self>`.

### FR-3.3: Receipt Number
Receipt numbers are sequential per institution.

**Acceptance:**
- Format: `REC-{INST}-{NNNNNN}`.
- Generated on payment insert with row-level locking.
- No duplicates within the same institution.

---

## FR-4: Authorization

### FR-4.1: All endpoints are protected
Every fees endpoint has `Depends(require_permission(resource, action))`.

**Acceptance:**
- Without required permission → 403.
- Platform owner bypasses all checks.

### FR-4.2: Role-based access
- Admin: all fee.*, fee_assignment.*, payment.*.
- Principal: fee.read, fee_assignment.read, payment.read, receipt.read.
- HOD: fee_assignment.read, payment.read.
- Teacher/Staff: fee_assignment.read.
- Student: fee_assignment.read, payment.read (own only).
- Parent: fee_assignment.read, payment.read (own children — Phase 2).

### FR-4.3: Ownership enforcement
Student/Parent roles can only access their own assignments/payments.

**Acceptance:**
- If role is Student/Parent and `user_id != ctx.user_id` → 403.

---

## FR-5: Audit

### FR-5.1: Audit events
All significant financial actions emit audit events via AuditEmitter.

**Acceptance:**
- `fee_type_created` — on POST /fee-types.
- `fee_type_updated` — on PATCH /fee-types.
- `fee_assigned` — on POST /fee-assignments.
- `fee_waived` — on POST /fee-assignments/{id}/waive.
- `payment_recorded` — on POST /payments.

---

## FR-6: Data Isolation

### FR-6.1: RLS policies
All 3 tables have RLS enforced.

**Acceptance:**
- `ENABLE ROW LEVEL SECURITY` + `FORCE ROW LEVEL SECURITY`.
- SELECT/INSERT/UPDATE: `is_platform_owner() OR client_id = current_client_id()`.
- DELETE: platform owner only.

### FR-6.2: Repository layer
All repositories inherit `TenantAwareRepositoryBase`. `client_id` is auto-injected from TenantContext.

# Fees Module — Product Requirements Document

> **Status:** Draft  
> **Version:** 1.0  
> **Date:** 2026-07-14  
> **Author:** Platform Team  
> **Purpose:** Define the Fees business module — the first business module built on the completed platform foundation (C-01 through C-04). Validates platform integration patterns.

---

## 1. Problem

Schools manage fee collection for hundreds of students across multiple fee types (tuition, transport, library, activities). Currently, each school uses spreadsheets or standalone tools with no integration to the student identity system, no multi-tenant isolation, and no audit trail. The platform needs a business module that:

- Consumes C-01 (tenant/institution isolation)
- Consumes C-02 (student identity, lifecycle states)
- Consumes C-03 (authentication)
- Consumes C-04 (role-based authorization)
- Emits C-11 (audit events)
- Proves the platform integration pattern works end-to-end

This module intentionally has limited Phase 1 scope — it's an integration test for the platform, not a full-featured billing system.

---

## 2. Goals & Non-Goals

### Goals
- G1: Administrators can define fee types per institution.
- G2: Administrators can assign fees to students with due dates.
- G3: Administrators can record payments against fee assignments.
- G4: Fee assignments track lifecycle (pending → paid/partial/overdue/waived).
- G5: Students and parents can view their own fees and payments.
- G6: Every financial action generates an audit event.
- G7: All endpoints are protected by C-04 role-based authorization.
- G8: All data is tenant-isolated via RLS and TenantAwareRepositoryBase.

### Non-Goals
- Late fee calculations and discounts
- Installment plans
- Grade/class-based bulk assignment (requires C-05 Academic Structure)
- Parent-child fee visibility (requires C-06 Relationship Management)
- Overdue notifications (requires C-09 Notification Framework)
- Receipt PDF generation
- Reports and dashboards
- Integration with C-12 Code Engine (manual receipt numbers in Phase 1)
- Online payment gateway integration

---

## 3. Users / Personas

| Persona | Role | Needs |
|---|---|---|
| **Institution Admin** | Admin role in C-02 | Create fee types, assign fees to students, record payments, waive fees, view all financial data |
| **Principal** | Principal role in C-02 | View fees and payments (read-only oversight) |
| **Teacher / HOD** | Teacher/HOD role | View which fees their students owe |
| **Student** | Student role | View their own fees and payment history |
| **Parent** | Parent role | View their children's fees (Phase 2 — requires C-06) |

---

## 4. User Journeys

### J1: Admin creates a fee type
1. Admin logs in, navigates to Fee Types.
2. Clicks "New Fee Type", fills in name (e.g., "Tuition Fee Term 1"), amount (₹5,000), description.
3. Fee type is created and appears in the catalog.
4. Admin can edit or soft-delete (deactivate) the fee type.

### J2: Admin assigns fees to students (bulk)
1. Admin navigates to Fee Assignments.
2. Selects a fee type, enters amount, due date, academic term.
3. Selects multiple students from a list.
4. Submits — all selected students get a fee assignment.
5. Each assignment is in `pending` status.

### J3: Student views their fees
1. Student logs in, navigates to "My Fees."
2. Sees a list of all their fee assignments with status (pending/paid/partial/overdue).
3. Clicks a fee to see payment history.
4. Student can only see their own fees (ownership enforced).

### J4: Admin records a payment
1. Admin navigates to Payments.
2. Selects a student, selects their pending fee assignment.
3. Enters payment amount, payment method (Cash/Card/Online), optional reference number.
4. Submits — payment is recorded, receipt number auto-generated.
5. Fee assignment status updates to `paid` (if full) or `partial` (if partial).
6. Audit event emitted.

### J5: Admin waives a fee
1. Admin navigates to a fee assignment.
2. Clicks "Waive", enters reason (e.g., "Scholarship student").
3. Fee assignment status changes to `waived` (terminal).
4. Audit event emitted.

### J6: Admin checks overdue fees
1. Admin navigates to Fee Assignments, filters by "Overdue."
2. System shows all assignments where `due_date < today AND status IN ('pending', 'partial')`.
3. Admin can take action: record payment, waive, or follow up.

### J7: Platform owner oversees fees across clients
1. Platform owner logs in with `platform_owner` role.
2. Can view fee types, assignments, and payments across all clients.
3. RLS bypass ensures full visibility.

---

## 5. Entities & Data Model

### 5.1 FeeType

| Field | Type | Notes |
|---|---|---|
| `id` | UUID PK | — |
| `client_id` | UUID FK → client | Tenant isolation (RLS) |
| `institution_id` | UUID FK → institution | Per-institution catalog |
| `name` | TEXT NOT NULL | "Tuition Fee", "Transport Fee" |
| `description` | TEXT | Optional |
| `default_amount` | DECIMAL(10,2) NOT NULL | Default (override per assignment) |
| `is_active` | BOOLEAN DEFAULT true | Soft-delete |
| `created_at` | TIMESTAMPTZ | — |

### 5.2 FeeAssignment

| Field | Type | Notes |
|---|---|---|
| `id` | UUID PK | — |
| `client_id` | UUID FK → client | Tenant isolation (RLS) |
| `institution_id` | UUID FK → institution | — |
| `user_id` | UUID FK → app_user | The student |
| `fee_type_id` | UUID FK → fee_type | What kind of fee |
| `amount` | DECIMAL(10,2) NOT NULL | Explicit per-assignment |
| `due_date` | DATE NOT NULL | Payment deadline |
| `academic_term` | TEXT | Free-text (Phase 2 → C-05 FK) |
| `status` | TEXT NOT NULL DEFAULT 'pending' | pending/paid/partial/overdue/waived |
| `assigned_by` | UUID FK → app_user | Admin who assigned |
| `notes` | TEXT | Optional |
| `created_at` | TIMESTAMPTZ | — |

Status transitions:
- `pending` → `paid` (full payment)
- `pending` → `partial` (partial payment)
- `partial` → `paid` (remaining paid)
- `pending` / `partial` → `overdue` (computed — due_date < today)
- `pending` / `partial` → `waived` (admin action, terminal)

### 5.3 Payment

| Field | Type | Notes |
|---|---|---|
| `id` | UUID PK | — |
| `client_id` | UUID FK → client | Tenant isolation (RLS) |
| `institution_id` | UUID FK → institution | — |
| `fee_assignment_id` | UUID FK → fee_assignment | Which fee this pays |
| `amount` | DECIMAL(10,2) NOT NULL | Amount paid |
| `payment_date` | DATE NOT NULL DEFAULT today | — |
| `payment_method` | TEXT NOT NULL | Free-text |
| `receipt_number` | TEXT | Auto-generated: REC-{INST}-{NNNNNN} |
| `reference_number` | TEXT | Optional — cheque number, TXN ID |
| `recorded_by` | UUID FK → app_user | Staff who recorded |
| `notes` | TEXT | Optional |
| `created_at` | TIMESTAMPTZ | — |

---

## 6. API Endpoints

### Fee Types
| Method | Path | Permission | Description |
|---|---|---|---|
| GET | `/api/v1/fee-types` | `fee.read` | List fee types (filter: ?institution_id=) |
| POST | `/api/v1/fee-types` | `fee.create` | Create fee type |
| GET | `/api/v1/fee-types/{id}` | `fee.read` | Get fee type |
| PATCH | `/api/v1/fee-types/{id}` | `fee.update` | Update fee type |
| DELETE | `/api/v1/fee-types/{id}` | `fee.delete` | Deactivate fee type |

### Fee Assignments
| Method | Path | Permission | Description |
|---|---|---|---|
| GET | `/api/v1/fee-assignments` | `fee_assignment.read` | List assignments (?user_id=, ?status=, ?overdue=) |
| POST | `/api/v1/fee-assignments` | `fee_assignment.create` | Create assignment(s) — bulk via user_ids[] |
| GET | `/api/v1/fee-assignments/{id}` | `fee_assignment.read` | Get assignment |
| PATCH | `/api/v1/fee-assignments/{id}` | `fee_assignment.update` | Update assignment |
| POST | `/api/v1/fee-assignments/{id}/waive` | `fee_assignment.waive` | Waive fee |

### Payments
| Method | Path | Permission | Description |
|---|---|---|---|
| GET | `/api/v1/payments` | `payment.read` | List payments (?fee_assignment_id=, ?user_id=) |
| POST | `/api/v1/payments` | `payment.create` | Record payment |

### Ownership rules
- **Student/Parent roles** can only access `?user_id=<own_id>`. Backend enforces: if role is Student/Parent and `user_id != ctx.user_id` → 403.
- **Admin/Principal/HOD/Teacher** roles bypass ownership.

---

## 7. C-04 Authorization

### 7.1 New permissions (added to C-04's `permission` table via migration)

| Permission | Resource | Action |
|---|---|---|
| `fee.read` | fee | read |
| `fee.create` | fee | create |
| `fee.update` | fee | update |
| `fee.delete` | fee | delete |
| `fee_assignment.read` | fee_assignment | read |
| `fee_assignment.create` | fee_assignment | create |
| `fee_assignment.update` | fee_assignment | update |
| `fee_assignment.waive` | fee_assignment | waive |
| `payment.read` | payment | read |
| `payment.create` | payment | create |
| `receipt.read` | receipt | read |

### 7.2 Role mappings

| Role | Permissions |
|---|---|
| Admin | All 11 |
| Principal | fee.read, fee_assignment.read, payment.read, receipt.read |
| HOD | fee_assignment.read, payment.read |
| Teacher | fee_assignment.read |
| Staff | fee_assignment.read |
| Student | fee_assignment.read, payment.read (own only) |
| Parent | fee_assignment.read, payment.read (own children — Phase 2) |

---

## 8. C-11 Audit Events

| Event | When | Payload |
|---|---|---|
| `fee_type_created` | POST /fee-types | `{ fee_type_id, name, amount }` |
| `fee_type_updated` | PATCH /fee-types | `{ fee_type_id, changes }` |
| `fee_assigned` | POST /fee-assignments | `{ assignment_id, user_id, amount, due_date }` |
| `fee_waived` | POST /fee-assignments/{id}/waive | `{ assignment_id, user_id, reason }` |
| `payment_recorded` | POST /payments | `{ payment_id, assignment_id, amount, method, receipt_number }` |

---

## 9. Acceptance Criteria

### AC-1: Fee type CRUD
- [ ] Admin can create a fee type with name, description, default_amount.
- [ ] Admin can list all fee types for their institution.
- [ ] Admin can update a fee type.
- [ ] Admin can deactivate (DELETE) a fee type.
- [ ] Fee types are tenant-isolated — School A cannot see School B's fee types.

### AC-2: Fee assignment
- [ ] Admin can assign a fee to a single student.
- [ ] Admin can assign a fee to multiple students in bulk (user_ids array).
- [ ] Each assignment has amount, due_date, academic_term.
- [ ] Assignments start in `pending` status.

### AC-3: Payment recording
- [ ] Admin can record a payment against a fee assignment.
- [ ] Payment includes amount, payment_date, method, optional reference.
- [ ] Receipt number is auto-generated: REC-{INST}-{NNNNNN}.
- [ ] Recording payment updates assignment status automatically:
  - Total ≥ amount → `paid`
  - Partial → `partial`

### AC-4: Lifecycle statuses
- [ ] Assignment statuses work: pending, paid, partial, waived.
- [ ] `overdue` is computed when `due_date < today AND status IN ('pending', 'partial')`.
- [ ] Waived is terminal — no further changes allowed.

### AC-5: Student access
- [ ] Student can list their own fee assignments via `?user_id=<self>`.
- [ ] Student can list their own payments.
- [ ] Student cannot access another student's fees (ownership enforced).

### AC-6: Authorization
- [ ] Every endpoint has `Depends(require_permission(...))`.
- [ ] Teacher cannot create/update/delete fee types.
- [ ] Teacher can read fee assignments.
- [ ] Student cannot waive fees.
- [ ] Platform owner bypasses all checks.

### AC-7: Audit
- [ ] 5 audit events are emitted as defined.
- [ ] Audit includes actor (ctx.user_id), client_id, institution_id.

### AC-8: Bulk assignment
- [ ] Bulk assignment creates N fee assignments in one transaction.
- [ ] If any user_id is invalid → all assignments roll back.

### AC-9: Receipt numbers
- [ ] Receipt numbers are sequential per institution.
- [ ] No duplicate receipt numbers within the same institution.

### AC-10: RLS
- [ ] All 3 tables have RLS enforced.
- [ ] Cross-tenant access prevented at DB level.

---

## 10. Risks

| Risk | Mitigation |
|---|---|
| R1: First business module — integration patterns may have gaps | Intentionally small scope; validate platform before building more modules |
| R2: Receipt sequential generation with row locking may cause contention | Acceptable for Phase 1 (low-frequency financial operations) |
| R3: C-04 `owner_id` parameter not wired — ownership enforced via app-level code | Consistent with C-04 D22 deferral; rewired when C-04 implements ownership |
| R4: Payment method as free-text → inconsistent data | Acceptable for Phase 1; Phase 2 adds lookup table |

---

## 11. Open Questions

- Q1: Should fee types be cloneable (copy from another institution)?
- Q2: Should there be a "due date reminder" threshold (notify 3 days before due)?
- Q3: Should receipt format be configurable per institution?

All deferred to Phase 2.

---

## 12. Decision Log

| # | Topic | Decision |
|---|---|---|
| D1 | Core entities | FeeType + FeeAssignment + Payment (3 tables) |
| D2 | C-04 permissions | ~11 fine-grained |
| D3 | FeeType schema | Minimal, institution-scoped |
| D4 | FeeAssignment schema | Lifecycle: pending/paid/partial/overdue/waived |
| D5 | Payment schema | Full: method, receipt_number, reference |
| D6 | Overdue | Computed on read (virtual) |
| D7 | Module location | `backend/business/fees/` |
| D8 | Permission registration | Migration adds to C-04 tables |
| D9 | Endpoints | ~13 REST endpoints |
| D10 | Bulk assignment | Array of user_ids, atomic |
| D11 | Payment recording | Auto status update via SUM, atomic |
| D12 | Receipt numbers | Sequential per-institution |
| D13 | Student access | `?user_id=` filter + ownership check |
| D14 | Audit | 5 event types |
| D15 | Permission mapping | 11 permissions, ~17 role mappings |
| D16 | Manifest | Full hooks (A5) |
| D17 | Student validation | User category = 'Learner' |
| D18 | Payment method | Free-text |
| D19 | Amount | Always explicit |
| D20 | RLS | All 3 tables |
| D21 | Academic term | Free-text |
| D22 | Scope | Phase 1 confirmed |

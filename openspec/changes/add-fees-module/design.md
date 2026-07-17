# Fees Module — Technical Design

## 1. Module Structure

```
backend/business/fees/
├── __init__.py
├── manifest.py              # ModuleManifest (A5)
├── models/
│   ├── __init__.py
│   ├── fee_type.py
│   ├── fee_assignment.py
│   └── payment.py
├── repos/
│   ├── __init__.py
│   ├── fee_type_repo.py
│   ├── fee_assignment_repo.py
│   └── payment_repo.py
├── services/
│   ├── __init__.py
│   ├── service.py           # FeesService
│   └── dtos.py
├── routes/
│   ├── __init__.py
│   ├── fee_types.py
│   ├── fee_assignments.py
│   └── payments.py
└── dependencies.py          # get_fees_service()
```

## 2. Database Schema (Migration 005)

### fee_type
```sql
CREATE TABLE fee_type (
    id UUID PK DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES client(id),
    institution_id UUID NOT NULL REFERENCES institution(id),
    name TEXT NOT NULL,
    description TEXT,
    default_amount DECIMAL(10,2) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now()
);
-- RLS: same pattern as C-01/C-02
```

### fee_assignment
```sql
CREATE TABLE fee_assignment (
    id UUID PK DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES client(id),
    institution_id UUID NOT NULL REFERENCES institution(id),
    user_id UUID NOT NULL REFERENCES app_user(id),
    fee_type_id UUID NOT NULL REFERENCES fee_type(id),
    amount DECIMAL(10,2) NOT NULL,
    due_date DATE NOT NULL,
    academic_term TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    assigned_by UUID REFERENCES app_user(id),
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);
-- RLS: same pattern
-- CHECK: user_id must have user_category = 'Learner' (validated in service)
```

### payment
```sql
CREATE TABLE payment (
    id UUID PK DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES client(id),
    institution_id UUID NOT NULL REFERENCES institution(id),
    fee_assignment_id UUID NOT NULL REFERENCES fee_assignment(id),
    amount DECIMAL(10,2) NOT NULL,
    payment_date DATE NOT NULL DEFAULT CURRENT_DATE,
    payment_method TEXT NOT NULL,
    receipt_number TEXT,
    reference_number TEXT,
    recorded_by UUID REFERENCES app_user(id),
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);
-- RLS: same pattern
```

### C-04 extension (in same migration)
```sql
-- 11 permission rows
INSERT INTO permission (id, name, description, resource, action) VALUES ...
ON CONFLICT (name) DO NOTHING;

-- ~17 role_permission rows
INSERT INTO role_permission (id, role_id, permission_id)
SELECT gen_random_uuid(), r.id, p.id FROM role r, permission p
WHERE r.name = '{role}' AND p.name = '{perm}'
ON CONFLICT (role_id, permission_id) DO NOTHING;
```

## 3. Repository Layer

All repos inherit `TenantAwareRepositoryBase[ModelT]`. `client_id` is auto-injected.

### FeeTypeRepository
- `create(session, ctx, dto)` → FeeTypeDTO
- `list(session, ctx, institution_id?)` → list[FeeTypeDTO]
- `get(session, ctx, id)` → FeeTypeDTO | None
- `update(session, ctx, id, dto)` → FeeTypeDTO
- `deactivate(session, ctx, id)` → None

### FeeAssignmentRepository
- `create_bulk(session, ctx, dtos)` → list[FeeAssignmentDTO]
- `list(session, ctx, filters)` → list[FeeAssignmentDTO] (supports user_id, status, overdue)
- `get(session, ctx, id)` → FeeAssignmentDTO | None
- `update(session, ctx, id, dto)` → FeeAssignmentDTO
- `waive(session, ctx, id, reason)` → FeeAssignmentDTO
- `get_total_payments(session, assignment_id)` → Decimal

### PaymentRepository
- `create(session, ctx, dto)` → PaymentDTO
- `list(session, ctx, filters)` → list[PaymentDTO]
- `get_next_receipt_number(session, institution_id)` → str (with FOR UPDATE lock)

## 4. Service Layer

### FeesService
- `create_fee_type(ctx, dto)` → FeeTypeDTO
- `list_fee_types(ctx, institution_id?)` → list[FeeTypeDTO]
- `get_fee_type(ctx, id)` → FeeTypeDTO
- `update_fee_type(ctx, id, dto)` → FeeTypeDTO
- `deactivate_fee_type(ctx, id)` → None
- `create_fee_assignments(ctx, dto)` → list[FeeAssignmentDTO] (bulk, atomic)
- `list_fee_assignments(ctx, filters)` → list[FeeAssignmentDTO] (ownership enforced)
- `get_fee_assignment(ctx, id)` → FeeAssignmentDTO
- `update_fee_assignment(ctx, id, dto)` → FeeAssignmentDTO
- `waive_fee_assignment(ctx, id, reason)` → FeeAssignmentDTO
- `record_payment(ctx, dto)` → PaymentDTO (auto status update + receipt)
- `list_payments(ctx, filters)` → list[PaymentDTO] (ownership enforced)

### Status transitions (on payment)
```python
total = repo.get_total_payments(session, assignment_id)
if total >= assignment.amount:
    assignment.status = "paid"
elif total > 0:
    assignment.status = "partial"
```

### Overdue computation
```python
if filters.get("overdue"):
    stmt = stmt.where(
        FeeAssignment.due_date < date.today(),
        FeeAssignment.status.in_(["pending", "partial"]),
    )
```

### Receipt generation
```python
# Row-level lock to prevent duplicates
last = session.execute(
    select(Payment.receipt_number)
    .where(Payment.institution_id == institution_id)
    .order_by(Payment.receipt_number.desc())
    .with_for_update()
).scalars().first()
next_num = int(last.split("-")[-1]) + 1 if last else 1
receipt = f"REC-{inst_code}-{next_num:06d}"
```

## 5. Authorization

All endpoints use `Depends(require_permission(resource, action))`.
Student ownership check: `if role in ['Student', 'Parent'] and user_id != ctx.user_id → 403`.

## 6. Testing

- Unit tests: service logic, status transitions, receipt generation
- Integration tests: endpoint CRUD, authorization, ownership, bulk assignment
- Test fixture: `AlwaysAllowEnforcer` updated for fee permissions

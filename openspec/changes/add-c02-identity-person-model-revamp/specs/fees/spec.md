# Delta Spec — Fees (Person-Model Revamp)

> **Change:** `add-c02-identity-person-model-revamp`
> **Domain:** fees
> **Delta type:** MODIFIED + Cross-cutting
> **Base spec:** `openspec/specs/fees/spec.md` (frontend-only archived spec)
> **Source ADR:** `docs/architecture/adr-c02-identity-person-model-revamp.md` (D3a, D6a)
> **Source PRD:** `docs/prd/c02-identity-person-model-revamp.md` (AC-14, AC-16)

---

## MODIFIED Requirements

### REQ-FE-FEE-02: Fee Assignment Management (Modified — student key shift)

Fee assignments target a student. The student reference SHALL shift from `app_user`-keyed to `student`-keyed (via `person`). Frontend behavior is largely unchanged (the admin still picks from a roster), but the underlying student identity is `student.id` (linked to `person`), not `app_user.id`. The `user_category='Learner'` proxy check SHALL be dropped — student status is derived from the `student` domain entity (next capability) or `role_assignment`, never from `user_category`. Per AC-14, AC-16.

> **Note:** The `student` table lands in the next capability (domain split). This revamp delivers `person` as the anchor and drops the `Learner` proxy; the actual `student`-keyed fee assignment executes after the domain split.

#### Scenario: Fee assignment targets student entity (after domain split)
- **WHEN** an Institution Admin creates a fee assignment
- **THEN** the assignment SHALL target a `student.id` (linked to `person`)
- **AND** SHALL NOT reference `app_user.id` as the student identity

#### Scenario: No Learner proxy check
- **WHEN** the fees module determines whether a user is a student for fee assignment
- **THEN** it SHALL NOT check `user_category = 'Learner'`
- **AND** student status SHALL be derived from the `student` domain entity or `role_assignment`

---

### REQ-FE-FEE-03: Payments (Modified — student filter key shift)

Payments SHALL be filterable by student. The student filter key SHALL shift to `student`-keyed (via `person`). Frontend behavior is unchanged (still filters by student from a roster), but the underlying identity changes. Per AC-16.

#### Scenario: Payment filter by student entity
- **WHEN** an Institution Admin filters payments by student
- **THEN** the filter SHALL use the `student` identity (via `person`)
- **AND** SHALL NOT use `app_user.id` as the student filter key

---

## Cross-Cutting Notes (backend, not in archived spec)

> **Gap:** There is no archived backend-fees OpenSpec spec. The `fee_assignment.student_id` FK repoint and the `user_category='Learner'` proxy drop are implementation/migration concerns, not spec'd behavior. The design phase should decide whether a backend-fees delta spec is needed or whether this is captured purely as a migration/implementation concern.

- **`fee_assignment.student_id` FK** repoints `app_user.id` → `student.id` (via `person`). Setup in this revamp's migration; execution in the next capability.
- **Drops `user_category='Learner'` proxy check** (AC-14, D6a). The one abuse flagged in the domain-split ADR (fees using category as a student test) is corrected.

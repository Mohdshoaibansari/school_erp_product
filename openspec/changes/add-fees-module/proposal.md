# Add Fees Business Module

## Summary

Add the Fees business module — the first business module built on the completed platform foundation (C-01 through C-04). Validates that the platform integration patterns (tenant isolation, authorization, audit) work end-to-end for a real business domain.

## Motivation

- Validate platform integration: C-01 (tenant isolation), C-02 (student identity), C-03 (auth), C-04 (authorization), C-11 (audit).
- Provide a working reference for future business modules (Homework, Attendance, Exams, etc.).
- Enable schools to manage fee types, assign fees to students, and record payments.

## Scope

### In Scope
- 3 entities: FeeType, FeeAssignment, Payment
- ~13 REST endpoints
- C-04 authorization (11 new permissions, ~17 role mappings)
- C-11 audit (5 event types)
- Bulk fee assignment
- Receipt number generation
- Overdue computation (virtual)
- RLS on all tables

### Out of Scope
- Late fees, discounts, installment plans
- C-05 Academic Structure integration (grade/class-based assignment)
- C-06 Relationship Management (parent-child fee visibility)
- C-09 Notifications (overdue reminders)
- C-12 Code Engine (manual receipt numbers)
- Payment gateway integration

## Impact

- **ADDED:** `fees` domain — new business module at `backend/business/fees/`
- **MODIFIED:** `authorization` domain — 11 new permission rows + ~17 role_permission rows in C-04's tables (no C-04 code changes)
- **No changes** to C-01, C-02, C-03, C-11

## References

- PRD: `docs/prd/fees-module.md`
- Impact: `docs/prd/fees-module-impact.md`
- Grill decisions: D1–D22

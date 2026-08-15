# Proposal: Capability C-01 Tenant & Institution Management

## 1. Executive Summary

This proposal establishes the root capability **C-01 Tenant & Institution Management** in the platform. C-01 is a zero-dependency (Level 1) kernel capability that defines:
1. The legal, contracting, and billing boundary (**Client**).
2. The operational school structure (**Institution**).
3. The hierarchical administrative container tree (**OrgUnit**).
4. The template mechanism for default school structures (**InstitutionType**).
5. The full lifecycle state machines, permissions, approval flows, cycle-prevented moves, and platform-approved ownership transfers.

Decisional source of truth: `docs/architecture/adr-c01-tenant-institution-implementation.md` (12 locked decisions D1–D12 + 10 spec resolutions Q1–Q10).
Product requirements source of truth: `docs/prd/c-01-tenant-institution.md` (20 acceptance criteria AC-1..AC-20).

## 2. Rationale & Problem Statement

Every business module in the ERP (Identity, AuthZ, Attendance, Fees, Homework, Exams, etc.) requires a tenant boundary to isolate data against and a structural container hierarchy to organize operational entities. Without C-01:
- There is no tenant fence for data isolation.
- There is no legal contracting entity for C-07/C-23 subscription and billing.
- There is no structural hierarchy for C-05 Academic Structure and downstream modules to attach to.

C-01 provides the definitive single source of truth for Client, Institution, and OrgUnit domain models.

## 3. Scope of Changes

### In Scope
- **Client entity**: Identity + legal identity + contact + address-FK + lifecycle (`Prospective`, `Active`, `Suspended`, `Archived`, `Terminated`).
- **Subdomain routing**: Client subdomain slug rules (lowercase 3–63 chars, immutable, globally unique, no per-institution subdomains).
- **Institution entity**: Operational school entity + type-FK + contact + address-FK + lifecycle (`Onboarding`, `Active`, `Inactive`, `Archived`). Effective-state runtime gating by Client state.
- **InstitutionType & Templates**: JSONB template (`default_org_unit_template`) materialized into actual OrgUnit rows at institution creation.
- **OrgUnit & Hierarchy**: Adjacency list (`parent_id`) with recursive CTE for subtree queries; archive-only soft delete; immutable type; application-level cycle-prevented moves.
- **C-01 Permission Matrix**: Tiered delegation (Platform Owner / Client Director / Institution Admin / Cross-institution read-only).
- **Institution Ownership Transfer**: Platform-approved, both-client-consented, single-transaction operational transfer with immutable C-11 audit log.
- **Lookup Tables**: Configurable enums (`legal_entity_type`, `org_unit_type`, `institution_type_name`) backed by lookup tables.
- **Hybrid Isolation Model**: Tenant-aware repository abstraction as the primary data-access contract + Postgres RLS as a defense-in-depth backstop.

### Out of Scope
- Users / Profiles / Identity (C-02).
- AuthN / IdP / Session management (C-03).
- Authorization framework & Casbin engine (C-04).
- Academic structure & subjects (C-05).
- Subscription entitlements (C-07).
- Configuration framework (C-08).
- Audit framework (C-11).
- Address entity storage (C-13).
- Invoicing and billing (C-23).

## 4. Dependencies & Impact Analysis

- **Upstream Dependencies**: None (C-01 is Level 1 root capability).
- **Downstream Capabilities Impacted**: All downstream capabilities (C-02, C-03, C-04, C-05, C-07, C-08, C-11, C-12, C-13, C-23) consume C-01 entities via foreign keys or boundary declarations.
- **Breakage Risk**: Low to None for existing code (C-01 is introduced as the base kernel implementation).

## 5. Verification Plan

1. Schema & Migration verification via Alembic migrations creating lookup tables, Client, Institution, OrgUnit, InstitutionType, Approval, and Lifecycle Event tables.
2. Tenant isolation tests (repository filter + Postgres RLS policies).
3. Unit and Integration tests for state machine transitions, OrgUnit cycle-prevention moves, template materialization, and ownership transfer single-transaction execution.
4. API endpoint verification for subdomain-resolved routes.

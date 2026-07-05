## Why

A multi-tenant School ERP SaaS has no foundation without an authoritative way to represent (a) the contracting, billing, and legal boundary — the *Client* — and (b) the operational school structure underneath it — *Institutions* and their *OrgUnit* hierarchy. C-01 (Tenant & Institution Management) is the zero-dependency root capability of the platform; every other business module (Attendance, Fees, Homework, Exams, Users, Auth, AuthZ, Subscriptions, Billing, Audit, …) keys off it for the tenant boundary, the legal/billing entity, and the home of the hierarchical school structure. Nothing else can be implemented safely until C-01 exists and is unambiguous, because downstream capabilities hold foreign keys to it (per architecture-v1 §3/§5.3, platform-capabilities-v3 §C-01, ADR §1). It must be built first.

## What Changes

This change introduces a brand-new capability domain (`tenant-institution`) with ADDED requirements only (no MODIFY/REMOVE — `openspec/specs/` is empty). Specifically, it adds:

- **Tenant isolation contract (D1, AC-1):** Hybrid model — tenant-aware repositories as the data-access contract + Postgres RLS as the defense-in-depth backstop. Two-level: `client_id` hard legal boundary (RLS-enforced) + `institution_id` default business filter (overridable by cross-institution roles).
- **UUID v4 identifiers (D2, AC-2):** UUID v4 primary keys for Client, Institution, InstitutionType, OrgUnit, and all lifecycle/event entities. No autoincrement; no C-12 codes for C-01 PKs (preserves zero-dependency).
- **Client entity + identity (D4, AC-17):** Client carries identity + legal-identity + contact + address-FK + lifecycle only. No timezone/locale/branding/subscription/billing on the entity (those live in C-08/C-07/C-23).
- **Client slug rules + immutability (D3, AC-3, AC-13):** Subdomain identifies the Client (never the institution); lowercase 3–63 chars `[a-z0-9-]`, alphanumeric at both ends; globally unique; reserved-name block; collision returns "taken" with no suggestions; immutable after creation; no per-institution subdomains (AC-4).
- **Client lifecycle state machine (D8, AC-5):** Prospective→Active→Suspended→Archived→Terminated with locked arcs; `Terminated` terminal; `Archived` the only re-activatable inactive state; every transition records reason + approver + actor and is audited via C-11.
- **Institution entity + identity (D5, AC-17):** Institution carries identity + type-FK + contact + address-FK + lifecycle only.
- **Institution lifecycle + effective-state gating (D9, AC-6, AC-7):** Onboarding→Active→Inactive→Archived (no Terminated); runtime effective-state gating by Client state without persisted cascade; `Archived` re-activatable.
- **InstitutionType + default OrgUnit template materialization (D7, AC-16):** Configurable via API (not hardcoded); JSONB `default_org_unit_template` materialized into actual OrgUnit rows at institution creation; immutable on an Institution after creation; not a runtime driver.
- **OrgUnit hierarchy + restructuring rules (D6, AC-8, AC-9, AC-10):** Adjacency list + recursive CTE; archive-only (no hard delete); type immutable after creation; move is audited + cycle-prevented (app-side) + subtree moves with the node.
- **OrgUnit purity / C-05 boundary (D10, AC-18):** OrgUnit is pure structure (Grade/Class/Section/Program/Batch are OrgUnit *types*); C-01 has NO FK to C-05; `homeroom_teacher_id` does not live on OrgUnit.
- **API shape (subdomain-resolved, Q5, AC-12):** APIs are subdomain-resolved (Client implicit from subdomain); the c-01-explained illustrative `POST /api/clients/{slug}/institutions` form is SUPERSEDED; Platform-Owner-only endpoints under a platform-scoped base.
- **C-01 write-permission matrix (D11, AC-15):** Tiered delegation — Platform Owner ALL; Client Director own-client institutional CRUD + identity; Institution Admin own-institution OrgUnit + identity; cross-institution roles READ-only; all writes audited via C-11 with actor identity.
- **Institution ownership transfer (D12, AC-11):** Platform-Owner-approved, full operational transfer, single transaction across Institution row + OrgUnits + C-05 academic structure + student records + user-institution assignments, partial-failure rollback, `OwnershipTransferEvent` record, immutable C-11 audit, user-migration rules, billing-handoff coordination point (C-07/C-23 next cycle).
- **Configurable enums as lookup tables (Q2, AC-20):** `legal_entity_type`, OrgUnit `type`, InstitutionType name stored as lookup tables; adding a new type is a data insert, no code/deploy.
- **Approval record storage (Q3, AC-19):** Separate `Approval` table (`requested_by`, `approved_by`, `status`, `timestamps`) supporting a pending-approval state for lifecycle transitions and ownership transfer.
- **Self-visible Client RLS (Q1, AC-14):** A Client Director can read their own Client row via RLS `id = current_client_id` (the Client table has no `client_id` column — the Client *is* the tenant).

### Scope boundaries — what C-01 owns vs. references but defers

C-01 **owns** its entities and their contracts outright: Client, Institution, InstitutionType, OrgUnit, lifecycles, the D11 write-permission matrix, the D12 ownership-transfer workflow, and the D1 tenant-isolation contract. C-01 **references but defers** to other capabilities (recorded as boundary notes in C-01's own spec, NOT as modifications to those domains):

- C-02 (Users): user-institution assignments migrate on ownership transfer (C-01 states the migration contract; C-02 owns the user entity).
- C-03 (Auth): resolves Client via subdomain; JWT carries `client_id` + selected `institution_id` (C-01 exposes Client identity; C-03 owns session/IdP).
- C-04 (AuthZ framework): encodes the D11 matrix as Casbin RBAC+ABAC policies (C-01 supplies matrix *content*; C-04 owns the framework).
- C-05 (Academic structure): holds FKs to C-01 OrgUnit/Institution; C-01 has NO FK to C-05 (D10).
- C-07 (Subscriptions): gates modules at Client level; C-01 exposes Client identity.
- C-08 (Config): owns tz/locale/currency/branding/academic-year-start/grading-scale; C-01 explicitly excludes those.
- C-11 (Audit): owns the immutable event log; C-01 consumes it (emits synchronous events tagged with ClientId + InstitutionId).
- C-12 (Business codes): reserved for institution-scoped codes; deliberately NOT used for C-01 PKs.
- C-13 (Address): owns the address entity; C-01 holds the `address_id` FK.
- C-23 (Billing): owns billing; ownership transfer notes the billing-handoff coordination point.

## Capabilities

### New Capabilities
- `tenant-institution`: C-01 Tenant & Institution Management — Client, Institution, InstitutionType, OrgUnit hierarchy, lifecycles (Client + Institution + OrgUnit), two-level tenant isolation, UUID v4 identifiers, subdomain-resolved API, write-permission matrix, ownership transfer, configurable-enums lookup tables, Approval flow, boundary declarations to C-02/C-03/C-04/C-05/C-07/C-08/C-11/C-12/C-13/C-23.

### Modified Capabilities
<!-- None. The openspec/specs/ tree is empty (confirmed via `openspec list --specs`), so every requirement in this change is ADDED under one new domain. No MODIFIED or REMOVED deltas. -->

## Impact

- **New OpenSpec domain:** `tenant-institution` (first domain in the repo; `openspec/specs/` is empty, so this is greenfield).
- **New entities/tables (C-01 owned):** `clients`, `institutions`, `institution_types`, `org_units`, lookup tables (`legal_entity_type`, `org_unit_type`, `institution_type_name`), `approvals`, `client_lifecycle_events`, `institution_lifecycle_events`, `ownership_transfer_events`. All with UUID v4 PKs and `client_id` RLS column where tenant-scoped.
- **Isolation layers:** tenant-aware repositories (data-access contract) + Postgres RLS policies on `client_id` (defense-in-depth backstop). RLS on the `client` table itself is self-visible (`id = current_client_id`).
- **APIs (subdomain-resolved):** institution/OrgUnit management under the client portal subdomain; Platform-Owner-only endpoints (Client lifecycle, ownership-transfer approval, InstitutionType management) under a platform-scoped base.
- **Cross-capability coordination points (boundary declarations, not modifications):** D12 ownership transfer orchestrates updates into C-05/C-02 tables (C-01 owns the transfer; those capabilities own their schema); C-11 audit emission contract (synchronous, immutable, ClientId+InstitutionId tagged); C-08 config delegation (tz/locale/currency/branding/academic config); C-07/C-23 billing handoff (effective next billing cycle).
- **Dependencies:** C-01 is zero-dependency (Level 1 of the capability dependency map). No upstream capability must be implemented first. Every downstream capability (C-02+) depends on C-01.
- **Tech stack:** NOT yet chosen (no package.json, no code exists). Tasks are stack-agnostic where possible and flag stack-dependent steps as "stack TBD — confirm before implementation."
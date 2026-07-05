# PRD — C-01 Tenant & Institution Management

> **Capability:** C-01 Tenant & Institution Management
> **Capability layer / phase:** Kernel · Critical · Phase 1
> **Status:** Draft for impact classification → proposal/spec/design/tasks
> **Last updated:** 2026-07-05
> **Decisional source of truth:** `docs/architecture/adr-c01-tenant-institution-implementation.md` (12 locked decisions D1–D12 + 10 spec-resolution decisions Q1–Q10)
> **Companion docs:** `docs/platform-capabilities/platform-capabilities-v3.md` §C-01; `docs/platform-capabilities/c-01-tenant-institution-explained.md`; `docs/architecture/architecture-v1.md`; `docs/requirements/functional-requirements.md` §1.1, §1.2
> **Scope note:** This is a **product** requirements document. It is deliberately free of implementation detail (DB columns, API shapes, RLS policy text, Casbin rule syntax). Those belong in the spec/design phase, sourced from the ADR. Decisions are referenced by ID (e.g., "per D1") rather than re-specified here.

---

## 1. Problem

A School ERP SaaS serves many independent customer organizations simultaneously, each of which may operate one or more schools, colleges, or universities. The platform needs a single, authoritative way to represent (a) the **contracting, billing, and legal boundary** — the *Client* — and (b) the **operational school structure** underneath it — *Institutions* and their internal *OrgUnit* hierarchy. Without this root capability there is no tenant boundary to isolate data against, no legal/billing entity for C-07/C-23 to invoice, no home for the hierarchical school structure that every business module (Attendance, Fees, Homework, Exams, …) keys off, and no consistent place for lifecycle, ownership-transfer, and audit semantics to live. C-01 is the zero-dependency root capability that everything else builds on; it must exist first and must be unambiguous so that downstream capabilities can safely hold foreign keys to it (per architecture-v1 §3/§5.3, platform-capabilities-v3 §C-01, ADR §1).

## 2. Goals & Non-goals

### 2.1 In scope — C-01 owns

| Entity / concern | Per | Notes |
|---|---|---|
| **Client** (contract signer, bill recipient, tenant) | D4 | Identity + legal-identity + contact + address-FK + lifecycle only. No subscription/billing/branding/config on the entity itself (those live in C-07/C-23/C-08). |
| **Institution** (operational school/college/university) | D5 | Identity + type-FK + contact + address-FK + lifecycle only. No per-institution subdomain; timezone/locale/currency/branding/academic config live in C-08/C-05. |
| **InstitutionType** + default OrgUnit template | D7 | Setup-time-only convenience that materializes a default OrgUnit tree at institution creation. Not a runtime driver. Configurable via API, not hardcoded. Immutable on an Institution after creation. |
| **OrgUnit** + hierarchy (administrative/structural container) | D6, D10 | Adjacency-list hierarchy; archive-only; type immutable; moves audited + cycle-prevented + subtree-moving. |
| **Grade / Class / Section / Program / Batch** as OrgUnit *types* | D10 | Pure structural containers owned by C-01; academic metadata on top is C-05. |
| **Client lifecycle** (Prospective→Active→Suspended→Archived→Terminated) | D8 | Terminated is terminal; Archived is the only re-activatable inactive state. |
| **Institution lifecycle** (Onboarding→Active→Inactive→Archived) | D9 | No Terminated at institution level. Runtime effective-state gating by Client state; no cascade on Client suspension. |
| **C-01 write-operation permission matrix** | D11 | Tiered delegation: Platform Owner / Client Director / Institution Admin / cross-institution read-only roles. (C-04 owns the *framework*; C-01 owns *who can act on C-01 entities*.) |
| **Institution ownership transfer** | D12 | Platform-approved, full operational transfer, single transaction, immutable audit. |
| **Tenant isolation model** | D1 | Hybrid: tenant-aware repositories as the data-access contract + RLS as defense-in-depth backstop. Two-level: `client_id` hard boundary, `institution_id` default business filter. |
| **ID strategy for C-01 entities** | D2 | UUID v4 primary keys. |

### 2.2 Out of scope — owned by other capabilities

| Concern | Owned by | Per |
|---|---|---|
| Users / people / profiles | C-02 | — |
| Authentication / sessions / IdP | C-03 | C-03 also resolves Client from subdomain at request start |
| Authorization *framework* (roles, policies, scope engine) | C-04 | C-01 only supplies the matrix *content* (D11); C-04 encodes it |
| AcademicYear / Term / Subject / class-subject mapping / homeroom-teacher | C-05 | D10 — C-05 holds FKs to C-01 OrgUnits; C-01 has NO FK to C-05 |
| Subscriptions / module entitlements | C-07 | C-07 gates modules at Client level |
| Config (timezone, locale, currency, branding, academic_year_start, grading_scale) | C-08 | Inherited Platform→Client→Institution→Module |
| Audit *framework* (append-only event store) | C-11 | C-01 only *consumes* C-11 to tag and persist lifecycle/move/transfer events |
| Address ownership | C-13 | C-01 holds an FK to a C-13 address |
| Billing / invoices / payments | C-23 | One invoice per Client, itemized per Institution |
| Human-readable business codes (Student ID, Employee ID, receipt #) | C-12 | UUID v4 PKs for C-01 entities are internal only (D2) |

### 2.3 Explicit non-goals for Phase 1

- No per-institution subdomains (per D3 — subdomain identifies the Client only; multi-institution navigation is via the in-app institution switcher).
- No temporal / per-row client_id history tracking (per Q10 — full-transfer + immutable C-11 audit covers provenance; revisit only if a concrete near-term requirement emerges).
- No lifecycle-event-history table partitioning (per Q8 — defer until volume matters; candidate is monthly partitioning on `entered_at`).
- No async event bus for lifecycle changes / ownership transfer (per Q4 — C-11 audit only, synchronous; consumers wire in directly or poll; defer until a cross-capability event-bus requirement materializes).
- No split-at-watermark ownership-transfer model (per D12 alternative — rejected; full operational transfer only).
- No runtime module behavior driven by InstitutionType (per D7 — all modules operate identically regardless of type).

## 3. Users / Personas

The personas below are the C-01 *actors*. Their precise role definitions and Casbin encoding are owned by C-04; C-01 only defines what each persona can do against C-01 entities, per the locked matrix in D11.

| Persona | Who they are | Scope | C-01 reach (per D11) |
|---|---|---|---|
| **Platform Owner** | The SaaS provider operating the platform. | All tenants. | **ALL** C-01 operations: create/suspend/archive/terminate Clients, manage InstitutionTypes, approve ownership transfers (D12), and any lower-tier operation as higher authority. |
| **Client Director** | The client's top administrator (e.g., trust director, chain owner). | Own client only. | Create institutions; activate/inactive/archive/reinstate institutions; update Client + Institution identity; manage OrgUnits. **Cannot** create/suspend/terminate the Client itself (must request Platform Owner). |
| **Institution Admin / Principal** | The institution's top in-building administrator. | Own institution only. | Update institution identity; create/move/archive/reactivate OrgUnits within the institution. **Cannot** create/suspend/archive the institution itself (must request Client Director). |
| **Cross-institution roles** (Regional Manager, Group Academic Head, Finance Controller) | Roles that span institutions within one client for oversight. | Across institutions within a client. | **READ-only** oversight on C-01 entities. No C-01 write operations. |

All writes are audited via C-11 with actor identity (D11, D8, D9, D12). The subdomain resolves the Client at request start (per D3); after login the user picks/switches the active institution via the in-app institution switcher (per D3, D1).

## 4. User Journeys

| # | Persona | Journey | Key ADR refs |
|---|---|---|---|
| **J1** | Platform Owner | **Onboard a new Client + first Institution.** Create a Client (choose a globally-unique immutable slug, supply legal identity + contact + address). Client starts in `Prospective`. Create the first Institution, choosing an `InstitutionType` whose default OrgUnit template is materialized into actual OrgUnit rows (Grade/Class/Section/etc.) stamped with the new Client + Institution. When contract + onboarding complete, transition Client `Prospective → Active` and Institution `Onboarding → Active`. | D3, D4, D5, D7, D8, D9, D11, Q3 |
| **J2** | Client Director | **Add a second Institution under the existing Client.** Pick an `InstitutionType`; its template materializes a default OrgUnit tree. Configure/extend the tree as needed. Institution starts in `Onboarding`; go-live transitions it to `Active`. The same subdomain portal serves both institutions; the in-app switcher selects which is active. | D3, D5, D7, D9, D11 |
| **J3** | Institution Admin / Principal | **Build / extend the OrgUnit tree** (incl. Grade/Class/Section nodes). Add new OrgUnits of valid types; reorder; move subtrees (cycle-prevented); archive a node the school no longer uses (never hard-delete); reactivate an archived node when needed. To "change" a node's type, archive it and create a new one. | D6, D10, D11 |
| **J4** | Platform Owner (and Client Director for institution-level flows) | **Client lifecycle transitions** (Prospective→Active→Suspended→Archived→Terminated). Each transition is requested, approved (per Q3 Approval flow), recorded with reason + actor, and audited via C-11. `Terminated` is terminal; `Archived` is the only re-activatable inactive state. | D8, Q3, D11 |
| **J5** | Client Director (with Institution Admin for go-live approval) | **Institution lifecycle** (Onboarding→Active→Inactive→Archived). An institution can only be operationally Active while its Client is Active; if the Client goes Suspended/Archived/Terminated the institution's access is gated at runtime (effective state) **without** its own row state being mutated. `Archived` re-activatable. | D9, Q3 |
| **J6** | Institution Admin / Principal | **Move an OrgUnit within the tree.** The move is cycle-prevented (cannot move a node under its own descendant), audited via C-11 as a generic `org_unit_moved` event (no dedicated move-event table), and the whole subtree moves with the node. | D6, Q6, Q7 |
| **J7** | Platform Owner | **Transfer ownership of an Institution from Client A to Client B.** Both clients consent; Platform Owner approves (cross-tenant boundary change — neither side can self-serve). Operational data (Institution, its OrgUnits, C-05 academic structure, student records, user-institution assignments) is moved in a **single transaction**, with isolation verified post-move. Audit events (C-11) are **immutable** — they keep the ClientId they were recorded with (historical truth). An `OwnershipTransferEvent` is recorded (`from_client`, `to_client`, `institution`, `approved_by`, `consent_source`, `consent_dest`, `transferred_at`, `reason`). Users whose *only* institution is the transferred one migrate to Client B; users with other Client-A institutions stay in Client A and lose the transferred institution (coordination point with C-02). Billing moves to Client B's invoice effective next billing cycle (C-07/C-23). | D12, D11, Q3 |

## 5. Acceptance Criteria

All criteria are testable and trace to an ADR decision. Implementation detail (column names, policy text, request shapes) is intentionally omitted — it belongs in the spec/design phase.

| # | Criterion | Trace |
|---|---|---|
| **AC-1** | A Client's data is never visible to, or editable by, a user belonging to a different Client, even if a tenant-aware repository method is invoked incorrectly. The `client_id` boundary is enforced at two layers: the repository contract (data access from business logic) and a Postgres RLS backstop. | D1, ADR §5 constraint 1–2 |
| **AC-2** | All C-01 entities — Client, Institution, OrgUnit, InstitutionType, and lifecycle/event entities — use UUID v4 primary keys. No autoincrement, no C-12-generated codes for these PKs. | D2 |
| **AC-3** | The Client subdomain slug is set once at creation and is immutable thereafter. The display name may change freely without affecting the URL. The slug is globally unique, lowercase, 3–63 chars, `[a-z0-9-]`, alphanumeric at both ends, and rejects reserved platform labels. | D3 |
| **AC-4** | There are no per-institution subdomains. Multi-institution clients are served through the same Client portal subdomain; the active institution is chosen via the in-app institution switcher after login. | D3 |
| **AC-5** | Client lifecycle transitions adhere to the D8 state machine: `Prospective→Active`, `Prospective→Archived`, `Active→Suspended`, `Suspended→Active`, `Active→Archived`, `Archived→Active`, `Suspended→Archived`, `Active/Suspended/Archived→Terminated`. `Terminated` is terminal (no exit arcs). `Archived` is the only re-activatable inactive state. Every transition records a reason + approver + actor and is audited via C-11. | D8, Q3 |
| **AC-6** | Institution lifecycle transitions adhere to the D9 state machine: `Onboarding→Active`, `Onboarding→Archived`, `Active→Inactive`, `Inactive→Active`, `Active→Archived`, `Inactive→Archived`, `Archived→Active`. There is **no** `Terminated` state for institutions. Every transition is audited via C-11. | D9, Q3 |
| **AC-7** | An Institution is operationally Active **only if** its Client is Active. If the Client enters Suspended/Archived/Terminated, the Institution's access is gated at runtime (effective state) **without** the Institution row's lifecycle state being mutated — i.e., no cascade on transient Client suspension. | D9 |
| **AC-8** | OrgUnits support archive-only deletion (soft-delete with reactivation allowed); there is no hard-delete path. The OrgUnit `type` is immutable after creation — to "change" type, archive the node and create a new one. | D6, D10 |
| **AC-9** | Moving an OrgUnit (parent change) is cycle-prevented: a node cannot be moved under its own descendant. Cycle prevention is enforced on the application/repository side; the database schema does **not** add a duplicating trigger. The whole subtree moves with the node. | D6, Q6 |
| **AC-10** | Every OrgUnit move is audited via C-11 as a generic `org_unit_moved` audit event; there is no dedicated `org_unit_move_event` table. | Q7 |
| **AC-11** | Institution ownership transfer is Platform-Owner-approved, both-source-and-destination-consented, executed in a **single transaction**, and recorded as an `OwnershipTransferEvent`. Audit events (C-11) created before the transfer remain immutable under their original ClientId (historical truth preserved). | D12, Q3 |
| **AC-12** | APIs for C-01 entities are subdomain-resolved: the Client is implicit from the subdomain (per D3), not embedded in the path. Platform-Owner-only endpoints (e.g., Client create/suspend/terminate, ownership-transfer approval, InstitutionType management) live under a platform-scoped base. | Q5 |
| **AC-13** | Create-time slug collision returns a "taken" outcome with no auto-suffix and no near-match suggestions. The caller must propose a new slug. | D3, Q9 |
| **AC-14** | A Client Director can read their own Client row (self-visible); RLS above the `client` table itself enforces `id = current_client_id` — there is no `client_id` column on the Client table itself, since the Client **is** the tenant. | Q1 |
| **AC-15** | The C-01 write-operation permission matrix (D11) is honored for every C-01 mutation: Platform Owner = all; Client Director = own-client institution/OrgUnit management (cannot mutate the Client itself); Institution Admin = own-institution OrgUnit management (cannot mutate the institution itself); cross-institution roles = read-only. All writes record actor identity via C-11. | D11 |
| **AC-16** | `InstitutionType` is a setup-time convenience only. At institution creation its `default_org_unit_template` is materialized into actual OrgUnit rows; thereafter the type on the Institution is immutable (to "change" type, archive and recreate). No business module's runtime behavior depends on InstitutionType. | D7, D10 |
| **AC-17** | C-01 carries identity + lifecycle + address-FK only. Timezone, locale, currency, branding, academic-year-start, grading-scale, and similar tunable behavior are **not** stored as intrinsic columns on Client or Institution — they are served by C-08. | D4, D5 |
| **AC-18** | C-01 has no foreign key to C-05. C-05 entities (AcademicYear, Term, Subject, class-subject mapping, homeroom-teacher assignment) hold FKs to C-01 OrgUnits/Institution; the reverse relationship does not exist. The `homeroom_teacher_id` is **not** a field on OrgUnit (it belongs in C-05 or a C-02 RoleAssignment scoped to OrgUnit + AcademicYear). | D10 |
| **AC-19** | Approval for lifecycle transitions is recorded via a dedicated Approval mechanism (one record per approval: requester, approver, status, timestamps). A transition requiring approval cannot complete until approval is granted. | Q3 |
| **AC-20** | Configurable enums (`legal_entity_type`, OrgUnit `type`, InstitutionType `name`, etc.) are backed by lookup tables — adding a new value is a data insert, no code/deploy. | Q2 |

## 6. Risks

| # | Risk | Mitigation / ADR anchor |
|---|---|---|
| **R1** | **Cross-tenant data leakage** if a tenant-aware repository method forgets to inject `client_id` — a single missed call leaks data across Clients. This is a *legal* boundary, not just a business filter. | Hybrid isolation: repositories are the data-access contract **plus** Postgres RLS as a defense-in-depth backstop that filters even if the repo is bypassed (D1, ADR §5 constraints 1–2). The repository-first rule must be enforced in code review and linting. |
| **R2** | **Partial-failure rollback on ownership transfer.** D12 transfers Institution row, its OrgUnits, C-05 academic structure, student records, and user-institution assignments in a single cross-table transaction; a partial failure could leave the institution half-attached to two Clients. | Single-transaction execution (D12); careful test coverage of the transfer path; isolation verification post-move (D12). |
| **R3** | **Cycle creation in OrgUnit moves** if the app-side cycle-prevention check (Q6) is bypassed by direct SQL or a future repository method that skips the check. | Repository-first rule (D1/AC-9); the DB schema deliberately does not add a trigger, so all writes flow through the checked repository path. |
| **R4** | **Historical ownership ambiguity.** D12's full-transfer model moves audit-eligible operational data to Client B; past audit events stay under their original ClientId (immutable). A downstream report that needs "history of this institution including pre-transfer period" must span two Client contexts. | Acknowledged in ADR §3/§7 as the cost of rejecting the watermark alternative. If a concrete requirement emerges for historical data staying with the seller, D12 must be redesigned (not a toggle). |
| **R4b** | **Explainer doc drift.** `c-01-tenant-institution-explained.md` shows an illustrative `POST /api/clients/{slug}/institutions` API example that is **superseded** by Q5's subdomain-resolved form. Readers following the explainer will be misled. | Flagged in §7 Open Questions; the explainer should get a "Superseded by" note pointing to the future API contracts doc. (This PRD does not modify the explainer.) |
| **R5** | **Two isolation layers to build and maintain from day one** (repositories + RLS) — more upfront setup than app-level-only. | Accepted in ADR §3; the layered model preserves §12 migration-readiness and is the foundation for future separate-schema/DB moves. |
| **R6** | **JSONB template validation has no DB-level enforcement** (D7) — invalid/acyclic violations of the InstitutionType `default_org_unit_template` are app-side only. | Application-side validation + test coverage of template materialization (D7). |

## 7. Open Questions / Notes

Items the ADR explicitly defers to a later phase, or non-blocking notes that need a one-time housekeeping step.

| # | Item | ADR anchor | Disposition |
|---|---|---|---|
| **OQ-1** | Temporal / per-row client_id history tracking. | Q10, ADR §7 | **Deferred.** Not built in Phase 1. Revisit only if a concrete near-term requirement for per-row ownership history emerges; that would be a D12 redesign, not a toggle. |
| **OQ-2** | Lifecycle-event history table partitioning. | Q8 | **Deferred.** Phase 1 ships without partitioning. Candidate is monthly partitioning on `entered_at`; revisit when volume matters. |
| **OQ-3** | Async events on lifecycle change / ownership transfer. | Q4 | **Deferred.** Phase 1 emits C-11 audit only (synchronous, internal). Consumers wire in directly or poll. A message-bus / event-stream layer is deferred until a cross-capability event-bus requirement materializes. |
| **OQ-4** | `c-01-tenant-institution-explained.md` supersede note. | Q5 | **Housekeeping (non-blocking for this PRD).** The explainer's illustrative `POST /api/clients/{slug}/institutions` example is superseded by Q5's subdomain-resolved `POST /api/v1/institutions` form. The explainer should get a "Superseded by API contracts doc" note. This PRD does not edit the explainer — recommended for the parent to schedule as a small follow-up doc update. |
| **OQ-5** | UUID v7 (time-ordered) revisit. | D2, ADR §7 | **Deferred.** UUID v4 is the locked Phase 1 choice. UUID v7 is a drop-in candidate if pagination/indexing benchmarks later show value. No action now. |

No gaps were found that block drafting this PRD. Every product behavior traces to a locked ADR decision.

---

## 8. Traceability Matrix (compact)

| PRD section | Primary ADR anchors |
|---|---|
| §1 Problem | ADR §1; architecture-v1 §3/§5.3; platform-capabilities-v3 §C-01 |
| §2.1 In scope | D1, D2, D4, D5, D6, D7, D8, D9, D10, D11, D12 |
| §2.2 Out of scope | C-02/C-03/C-04/C-05/C-07/C-08/C-11/C-12/C-13/C-23 (with D10/D11 boundary notes) |
| §2.3 Phase 1 non-goals | D3, Q4, Q8, Q10, D12-alt |
| §3 Personas | D11 |
| §4 Journeys J1–J7 | D3, D5, D6, D7, D8, D9, D10, D11, D12, Q3, Q5, Q6, Q7 |
| §5 Acceptance criteria AC-1…AC-20 | D1, D2, D3, D4, D5, D6, D7, D8, D9, D10, D11, D12, Q1, Q2, Q3, Q5, Q6, Q7, Q9 |
| §6 Risks | D1, D7, D12, Q5, Q6, ADR §3/§5/§7 |
| §7 Open questions | Q4, Q5, Q8, Q10, D2 |

---

> End of PRD — C-01 Tenant & Institution Management. Next SDD phase: impact classification → proposal/spec/design/tasks.
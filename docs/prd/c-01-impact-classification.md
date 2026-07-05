# Impact Classification — C-01 Tenant & Institution Management

> **Status:** Impact classification (input to prd-to-sdd phase)
> **Capability:** C-01 — Tenant & Institution Management
> **Decisional inputs:** `docs/prd/c-01-tenant-institution.md` (PRD), `docs/architecture/adr-c01-tenant-institution-implementation.md` (ADR, Final v1.0)
> **Verification:** `openspec list --specs` returns "No specs found" — `openspec/specs/` is empty.

---

## Classification
- Domain status: **NEW**
- Delta type: **ADDED**
- Cross-cutting: **NO**
- Recommended OpenSpec domain name: `tenant-institution`
- Recommended OpenSpec change name: `add-c01-tenant-institution`

## Reasoning

C-01 is the root capability of the platform (zero upstream dependencies per ADR §4.1 and the capability catalog's dependency map Level 1). The `openspec/specs/` directory is empty — confirmed by running `openspec list --specs`, which returns "No specs found" — so there is no existing OpenSpec domain for C-01 to modify. This makes C-01's delta type ADDED exclusively: it introduces a brand-new domain. A new domain has no prior requirements to MODIFY or REMOVE; every requirement in the spec delta will be under the ADDED bucket. This is the simplest and cleanest possible classification — a greenfield domain creation.

The cross-cutting analysis is the most consequential judgment here. C-01 references many other capabilities per the PRD §2.2 table and ADR §4.1: C-02 (users belong-to-client), C-03 (auth resolves client via subdomain), C-04 (authorization framework encodes the D11 matrix), C-05 (academic structure holds FKs TO C-01 OrgUnit), C-07 (subscription gates modules at Client level), C-08 (config inherits Platform→Client→Institution→Module), C-11 (audit — C-01 consumes, emitting synchronous events with ClientId+InstitutionId tagged), C-12 (business codes — deliberately kept off C-01 PKs to preserve zero-dependency), C-13 (address — C-01 holds an address FK), and C-23 (billing). These are interface dependencies and boundary declarations, **not** modifications to those domains. Critically, none of those referenced capabilities has an OpenSpec spec yet either (the entire `openspec/specs/` tree is empty), so there is literally nothing for C-01's change to MODIFY. One cannot apply a MODIFIED delta to a spec that does not exist.

C-01 OWNS its entities and their contracts outright: Client, Institution, InstitutionType, OrgUnit, their lifecycles, the D11 write-permission matrix, the D12 ownership-transfer workflow, and the D1 tenant-isolation contract. The references to other capabilities are recorded as boundary notes **within C-01's own spec** — e.g., "C-01 holds an address FK to C-13 (address entity is C-13)", "C-05 holds FKs to C-01 OrgUnit; C-01 has NO FK to C-05 (D10)", "C-11 audit events are emitted with ClientId tagged (C-01 consumes C-11)". These statements describe C-01's own external interface surface; they impose constraints on C-01's entities, not on the other domains' specs. When C-02, C-04, C-05, C-11, C-13, etc. are later fed to sdd-stack as their own capabilities, their specs will define their own sides of these boundaries (and may add MODIFIED deltas to C-01's domain at that time). For now, C-01's change is a SINGLE-domain ADDED delta under one domain, `tenant-institution`. This keeps the change folder containing exactly one `specs/tenant-institution/spec.md` delta, avoiding premature cross-domain coupling.

The D12 ownership-transfer workflow deserves a specific note: although the single-transaction execution (D12 step 4) updates rows in C-05 academic structure, student records (C-02 scope), and user-institution assignments (C-02 scope), **C-01 owns the transfer workflow and its `OwnershipTransferEvent` record**. C-01's spec describes the transfer as an explicit orchestration with named downstream coordination points; the actual schema/behavior for those downstream tables belongs to their respective capabilities' specs. C-01's spec states the contract (C-01 issues the transfer, downstream tables get `client_id` A→B atomically, C-11 records the event immutably); it does not define the schema of C-05 or C-02 entities. This is a boundary declaration, not a cross-domain modification.

## ADDED requirements (high-level)

These are the requirement areas that will become requirements/scenarios in `specs/tenant-institution/spec.md` during prd-to-sdd. Each maps to PRD §5 Acceptance Criteria and ADR decisions.

- **Tenant isolation contract** — two-level isolation model: `client_id` hard boundary (RLS-enforced) + `institution_id` default business filter (overridable for cross-institution roles); repository-first data-access contract; defense-in-depth backstop. (D1, AC-1)
- **Client CRUD + identity** — Client creation (display name + legal identity + slug + contact + address FK), identity update (display name mutable). (D4, AC-17)
- **Client slug rules + mutability** — lowercase 3–63 chars `[a-z0-9-]`, globally unique, reserved-name block, collision returns "taken" with no suggestions, immutable after creation. (D3, AC-3, AC-13)
- **Client lifecycle state machine** — Prospective→Active→Suspended→Archived→Terminated with the allowed arcs in D8; `Terminated` terminal; `Archived` the only re-activatable inactive state; every transition requires reason + Platform approval (Approval table) and is recorded in `ClientLifecycleEvent` + audited via C-11. (D8, AC-5)
- **Institution CRUD + identity** — Institution creation under a Client, identity update. (D5, AC-17)
- **Institution lifecycle state machine + effective-state gating** — Onboarding→Active→Inactive→Archived (no Terminated for institutions); runtime effective-state gating when Client is Suspended/Archived/Terminated (no persisted cascade); re-activation from Archived; Approval-table flow; `InstitutionLifecycleEvent` history + C-11 audit. (D9, AC-6, AC-7)
- **InstitutionType + default OrgUnit template materialization** — InstitutionType configurable via API (not hardcoded), JSONB `default_org_unit_template` materialized into actual OrgUnit rows at Institution creation, immutable on an Institution after creation, does not drive runtime module behavior. (D7, AC-16)
- **OrgUnit hierarchy + restructuring rules** — adjacency list + recursive CTE, archive-only (no hard delete), type immutable after creation, move is audited + cycle-prevented (application-side check) + subtree moves with the node, generic C-11 event `action="org_unit_moved"`. (D6, AC-8, AC-9, AC-10)
- **OrgUnit purity / C-05 boundary** — OrgUnit carries no academic metadata; C-01 holds no FK to C-05; `homeroom_teacher_id` does not live on OrgUnit. (D10, AC-18)
- **Identifiers** — UUID v4 PKs for all C-01 entities (Client, Institution, InstitutionType, OrgUnit, lifecycle/event entities); never autoincrement; never C-12 codes. (D2, AC-2)
- **API shape (subdomain-resolved)** — API is subdomain-resolved (Client implicit from subdomain); the illustrative client-in-path form is superseded; Platform-Owner-only endpoints under a platform-scoped base. (Q5, AC-12)
- **C-01 write-permission matrix** — tiered delegation: Platform Owner ALL; Client Director own-client institutional CRUD + identity; Institution Admin own-institution OrgUnit + identity; cross-institution roles READ-only; cross-tenant writes Platform-gated; all C-01 writes audited via C-11 with actor identity. (D11, AC-15)
- **Institution ownership transfer** — Platform-Owner-approved full operational transfer, single transaction across Institution row + OrgUnits + C-05 academic structure + student records + user-institution assignments, partial-failure rollback, `OwnershipTransferEvent` record, immutable C-11 audit across the transfer, user-migration rules, billing-handoff coordination point (C-07/C-23 effective next billing cycle). (D12, AC-11)
- **Configurable enums as lookup tables** — `legal_entity_type`, OrgUnit `type`, InstitutionType name stored as lookup tables (id + name, FK-referenced); adding a new type is a data insert, no code/deploy. (Q2, AC-20)
- **Approval record storage** — separate `Approval` table (`requested_by`, `approved_by`, `status`, `timestamps`) supporting a pending-approval state for lifecycle transitions and ownership transfer. (Q3, AC-19)
- **Purity / config delegation** — Client and Institution carry identity + legal-identity + contact + lifecycle + address-FK only; timezone/locale/currency/branding/grading-scale/academic-year-start live in C-08; no commercial metadata on C-01. (D4, D5, AC-17)

## Boundary relationships (NOT modifications)

| C-01 relationship | Direction | Other capability | Nature | Why it is NOT a modification to the other domain |
|---|---|---|---|---|
| Client owns users' client context; user-institution assignments migrate on ownership transfer | C-01 → C-02 | C-02 (Users) | Boundary / coordination point | C-01 states the user-migration contract on transfer; C-02 owns the user entity and will define its own schema in its own domain spec. No C-02 spec exists yet to modify. |
| Auth resolves Client via subdomain; JWT carries `client_id` + selected `institution_id` | C-01 → C-03 | C-03 (Auth) | Boundary / interface dependency | C-01 exposes the Client identity and slug; C-03 owns session/IdP logic and will define it in its own spec. C-01 only notes the subdomain→client lookup contract from its side. |
| C-04 encodes the D11 matrix as Casbin RBAC+ABAC policies | C-01 → C-04 | C-04 (Authz framework) | Boundary / first-cut matrix | C-01 states the product-level permission reach per role for its own entities; C-04 refines precise role definitions and encodes policies in its own spec. D11 is C-01-owned (it governs who can act on C-01 entities); the Casbin encoding is C-04's concern. |
| C-05 holds FKs TO C-01 OrgUnit and Institution; C-01 has NO FK to C-05 | C-05 → C-01 | C-05 (Academic structure) | Boundary / FK direction | C-01 is the upstream (zero-dependency) side; C-05 will define its own entities with FKs to OrgUnit. C-01's spec declares the boundary and the no-FK-from-C-01 invariant (D10), not a modification to a C-05 spec. |
| Subscription gates modules at Client level; C-01 exposes the Client identity | C-01 → C-07 | C-07 (Subscriptions) | Boundary / identity exposure | C-01 exposes Client identity for subscription gating; C-07 owns subscription state and module gating in its own spec. |
| Config inherits Platform→Client→Institution→Module | C-01 → C-08 | C-08 (Config) | Boundary / config delegation | C-01 explicitly excludes tz/locale/branding/etc. from its own schema and delegates to C-08. C-08 will define the config framework in its own spec. |
| C-11 audit events tagged with ClientId (+ InstitutionId); C-01 emits/retains lifecycle history; audit is immutable across transfers | C-01 → C-11 | C-11 (Audit) | Boundary / consumer | C-01 consumes C-11 (emits synchronous audit events, retains its own lifecycle-event history tables). C-11 owns the immutable event log and will define it in its own spec. C-01 only states its emission contract and the immutability invariant (ADR §5 constraint #14). |
| C-12 reserved for institution-scoped business codes; not used for C-01 PKs (circular dependency avoidance) | C-01 → C-12 | C-12 (Business codes) | Boundary / avoidance contract | C-01 explicitly does NOT consume C-12 for its PKs (D2); C-12 will define its own code-generation behavior in its own spec. The boundary is a non-dependency declaration within C-01's own spec. |
| C-01 holds an address FK to C-13 | C-01 → C-13 | C-13 (Address) | Boundary / FK holder | C-01 holds the `address_id` FK; C-13 owns the address entity and will define it in its own spec. C-01 only references the FK direction. |
| Billing issues one invoice per Client, itemized per-Institution; transfer moves subscription to Client B next cycle | C-01 → C-23 | C-23 (Billing) | Boundary / coordination point | C-01 carries no commercial metadata (D4); C-23 owns billing. Ownership transfer notes the billing-handoff coordination point (D12), but the billing behavior is C-23's concern in its own spec. |

## Recommendation for next phase (prd-to-sdd)

The prd-to-sdd subagent should create **one change folder** and **one domain delta spec**, with ADDED requirements only — no MODIFIED or REMOVED deltas:

- Change folder: `openspec/changes/add-c01-tenant-institution/`
- Single delta spec: `openspec/changes/add-c01-tenant-institution/specs/tenant-institution/spec.md`
- Delta type: ADDED exclusively (new domain)
- Requirements/scenarios: derived from the ADDED requirements list above, each traceable to a PRD AC and an ADR decision ID (D1–D12, Q1–Q10).
- Boundary notes: record the boundary relationships (table above) as part of C-01's own spec text (e.g., in a "Boundaries" section or as scenario preconditions), NOT as edits to other domains. The other domains will define their own sides of these boundaries in their own future change specs.
- Downstream coordination points (D12 ownership transfer's updates to C-05/C-02 tables, C-07/C-23 billing handoff, C-11 audit emission) should be described in C-01's spec as C-01's orchestration contract and event-emission contract, with explicit "coordinated with <capability>, owned by <capability>" annotations — NOT as modifications to those domains.
- No MODIFIED deltas to any other domain. No cross-domain delta specs in this change. The change is single-domain: `tenant-institution`.
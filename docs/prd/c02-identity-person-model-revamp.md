# PRD — C-02 Identity Person-Model Revamp

> **Capability:** C-02 Identity & User Management (person-model revamp)
> **Capability layer / phase:** Kernel · Critical · Phase 1 (structural overhaul of an already-archived capability)
> **Status:** Draft for impact classification → proposal/spec/design/tasks
> **Last updated:** 2026-08-17
> **Decisional source of truth:** `docs/architecture/adr-c02-identity-person-model-revamp.md` (D3a–D3e, D6a)
> **Companion docs:** `docs/architecture/adr-c02-identity-user-management-implementation.md` (creation/activation — NOT amended, still applies), `docs/architecture/adr-student-employee-domain-implementation.md` (v1.1 — D3/D6 superseded by this revamp; D1,D2,D4,D5,D7–D13 depend on this landing first), `docs/platform-capabilities/platform-capabilities-v3.md` §C-02, §C-06
> **Scope note:** This is a **product** requirements document. It is deliberately free of implementation detail (DB column types, API shapes, RLS policy text, migration SQL). Those belong in the spec/design phase, sourced from the ADR. Decisions are referenced by ID (e.g., "per D3a") rather than re-specified here.

---

## 1. Problem

The School ERP platform models **people as a single identity table**: `app_user`. A student *is* an `app_user` row with role=Student; a teacher *is* an `app_user` row with role=Teacher. The account table is forced to be both **the login** (credentials, auth, roles, tenant) *and* **the person** (name, DOB, contact, demographics via `user_profile`, coarse classification via `user_category_id`).

This conflation cracks in three concrete scenarios a complete School ERP cannot avoid:

1. **Staff-parent** — a teacher with a child enrolled at the same school: one human, an `employee` projection *and* a future C-06 parent relationship. `app_user`'s singular `user_category_id` cannot represent "teacher and parent at once."
2. **Lifecycle-crosser** — a student graduates, then years later is hired as a teacher: one human, a historical `student` + a current `employee`. If the account was archived at graduation and recreated at hire, the human continuity is lost.
3. **Cross-institution staff** — a teacher works at two schools in the same client chain. `app_user.institution_id` is `NOT NULL` and singular; she cannot exist as one human.

All three share one root cause: **there is no `person` entity.** `app_user` is really an account, but it is being asked to also be the person.

The C-02 capability is **already built and archived** — the `app_user`, `client_user`, `role`, `role_assignment`, `user_profile`, `user_category` tables and their services/repos/routes exist and are in production (dev/test). This revamp restructures the underlying model: introduces `person` as the enduring-human anchor, thins `app_user`/`client_user` into pure accounts, drops `user_category_id` and `user_profile`, and repoints domain links (`student`/`employee`) to `person`.

**Goal:** Deliver `person` as the ERP-wide-correct human anchor — so that staff-parents, lifecycle-crossers, and cross-institution staff all resolve cleanly through one `person` row, and so the next capabilities (student/employee domain split, then C-06 Relationship Management) build on a clean anchor instead of a conflation.

---

## 2. Goals & Non-goals

### 2.1 In scope — this feature owns

| Concern | Per | Notes |
|---|---|---|
| **Introduce `person` as the enduring-human anchor** | D3a | One human = one `person` row. `app_user`/`client_user` become thin accounts linked to `person` via `person_id`. `student`/`employee` link to `person` (not `app_user`). |
| **Multiple accounts per person; one institution per account** | D3b | `app_user.institution_id` stays `NOT NULL` and singular. A cross-institution teacher = one `person`, multiple `app_user` rows. Cross-institution *reporting* via `person`; cross-institution *login* is per-account (no SSO across institutions). |
| **`person.status` orthogonal classifier** | D3c | `Active \| Inactive \| Deceased \| ErasureRequested \| Anonymized` — set by external processes (GDPR, registrar, verification), NOT a behavioral lifecycle. Student/employee keep their behavioral lifecycles. |
| **`person` is role-agnostic** | D3d | No person-level role/classification. "What can this human do" is answered by account + institution + `role_assignment`. No `person_type` field is introduced. |
| **Keep `client_user` as separate client-level account table** | D3e | Three account tiers: platform (`is_platform_owner` flag), client (`client_user`), institution (`app_user`). Both account tables link to `person`. |
| **`person` owns all human data; `app_user` is thin** | D6a | Name, DOB, gender, blood group, photo, contact, demographics move to `person`. `app_user` carries auth + `person_id` + tenant + lifecycle only. |
| **Drop `user_category_id` entirely** | D6a | Role-in-institution derived from `person→student`/`employee` projections + `role_assignment` + `is_platform_owner` flag. No proxy label. |
| **Drop `user_profile` (folded into `person`)** | D6a | The generic profile keyed by `app_user` is gone; its columns move to `person`. Domain-extended data stays on `student_profile`/`employee_profile` (domain-split ADR D7 — those land in the next capability). |
| **Preserve creation/activation workflow semantics** | C-02 v1.0 ADR | The unified create→invite→activate→login flow (D1–D13 of the creation/activation ADR) is preserved; only the underlying model is restructured. |
| **Keep the authz pipeline untouched** | D3d, D8 | Roles stay on `app_user`/`client_user`; Casbin middleware reads roles off the account; no per-request `person` joins in authz. |
| **One coordinated clean-cut migration (schema + reseed)** | D4, D5 | Disposable DB — migration is schema + reseed; no backfill script. No adapter/dual-write phase. |

### 2.2 Out of scope — owned by other capabilities or deferred

| Concern | Owned by / Phase | Notes |
|---|---|---|
| **Student/employee domain tables, lifecycles, profiles** | Student/Employee Domain Split (next capability) | That ADR's D1,D2,D4,D5,D7–D13 stand and run AFTER this revamp. This revamp delivers `person`; the domain split builds `student`/`employee` on it. |
| **C-06 Relationship Management** | C-06 (next-next capability) | Guardian relationships link `person`→`student`. The Parent role stays a placeholder until C-06. |
| **Single sign-on / account federation across institutions** | Future (D3b deferred trade) | If cross-institution-within-one-client becomes painful, revisit toward a membership join. `person` makes that future migration possible. |
| **Person verification / KYC** | Future | A future verification status belongs on `person` as a non-role attribute (D3d). |
| **GDPR / right-to-be-forgotten workflow** | Future | `person.status = ErasureRequested → Anonymized` is the hook; the actual retention/anonymization pipeline is a future capability. |
| **Bulk person import** | Future | The `role_id`-optional pattern from the creation ADR is preserved; bulk import is a separate future feature. |
| **Non-disposable migration path** | Future (explicitly scoped) | The disposable-DB assumption is scoped to this revamp's migration only. Once real data lands, future schema changes need proper backfill. |

### 2.3 Explicit non-goals for this revamp

- No change to the authz pipeline — roles stay on accounts; no per-request person joins (D3d, D8).
- No SSO across institutions (accepted trade per D3b).
- No behavioral lifecycle on `person` (D3c — only an orthogonal status classifier).
- No person-level role/classification / `person_type` field (D3d — the exact crack D6a retired).
- No `user_category`-based logic survives anywhere — platform-owner discovery moves to the `is_platform_owner` flag (D6a).
- No C-06 guardian/parent relationships in this revamp (Parent role stays a placeholder).
- No student/employee domain tables in this revamp — `person` is delivered as the clean anchor the domain split will build on.

---

## 3. Users / Personas

This revamp is structural — it changes the identity model beneath the platform, not a user-facing screen. The personas below describe who is affected and how the person model serves them.

| Persona | Current role on platform | Impact of this revamp |
|---|---|---|
| **Platform Owner** | SaaS operator (flagged via `is_platform_owner`) | Discovery moves off `user_category='Executive Leadership'` onto the `is_platform_owner` flag. No behavior change; cleaner bootstrap. The PO's own human data (if any) now lives on `person`. |
| **Client Director** | Client-leadership account (`client_user`) | Account becomes thin; human data moves to a linked `person`. Creation/activation flow is preserved. A CD who is also (one day) an institution employee is one `person` with two accounts across tiers — not yet exercised, but now possible. |
| **Institution Admin** | Institution-scoped account (`app_user`, role=Admin/institution_admin) | Admin manages people, not just logins. After the revamp, admin can represent a human (`person`) independent of whether they have a login — enabling pre-login student/teacher records (the domain split + bulk import will use this). |
| **Student** *(persona does not exist as a domain entity yet)* | Today: an `app_user` with role=Student | The revamp prepares the anchor so the domain split can extract `student` as a domain entity linked to `person` — surviving login deletion, supporting alumni records, and decoupling "who is being taught" from "who can log in." |
| **Teacher / Staff** *(persona does not exist as a domain entity yet)* | Today: an `app_user` with role=Teacher/Staff | The revamp prepares `person` so `employee` can be extracted as a domain entity — supporting employment lifecycle, leave, and the staff-parent scenario (one `person`, an `employee` projection + a future C-06 parent relationship). |
| **Parent** *(placeholder role until C-06)* | Today: an `app_user` with role=Parent (no relationship modeling) | The `person` entity is the anchor C-06 will use for guardian relationships (`relationship.related_person_id → person`). Until C-06, the Parent role remains a placeholder. |
| **Backend Developer** | Builds new people-centric modules | One correct human anchor. A teacher-with-a-child is one `person` row, not a category-label conflict. Cross-institution reporting is a `person` join. No more two-sources-of-truth between `user_category` and reality. |

---

## 4. User Journeys

### 4.1 Staff-parent (the scenario that breaks `user_category_id` today)

**Today (broken):** A teacher, Anita, has a child enrolled at her school. Anita is an `app_user` with `user_category='Academic Staff'`. To also be a parent, she'd need `user_category='Learner'`-adjacent or a second account — a singular classification can't hold both.

**After this revamp (anchor ready, full resolution after domain split + C-06):**
1. Anita is one `person` row (name, DOB, contact, demographics).
2. She has an `app_user` account at her institution with role=Teacher (via `role_assignment`).
3. When C-06 lands, she gets a `relationship` row linking her `person` to her child's `student` (which links to the same or a different `person`). One human, an `employee` projection and a parent relationship — no category conflict, because `person` is role-agnostic (D3d).

### 4.2 Lifecycle-crosser (student → alumni → teacher)

**Today (broken):** Priya graduates; her `app_user` is archived (login gone). Years later she's hired as a teacher; a new `app_user` is created. The human continuity between "student Priya" and "teacher Priya" is lost — transcripts and employment history anchor on different account rows.

**After this revamp:**
1. Priya is one `person` row from the day she's admitted.
2. As a student, she has a `student` domain entity (next capability) linked to `person`.
3. At graduation, her `student` transitions to Graduated; her `app_user` is archived per config (domain-split D12). Her `person` and `student` records persist.
4. Years later, hired as a teacher: the same `person` gets a new `app_user` (active) and an `employee` domain entity. Her academic history (anchored on `student.person_id`) and employment history (anchored on `employee.person_id`) both resolve to one human.

### 4.3 Cross-institution staff (one human, two schools)

**Today (broken):** A teacher works at School A1 and School A2 (same client). `app_user.institution_id` is singular — she can't be one human in two schools.

**After this revamp (per D3b):**
1. One `person` row for the teacher.
2. Two `app_user` rows — one per institution, each with its own `institution_id` (NOT NULL), its own `role_assignment`, its own lifecycle.
3. Cross-institution *reporting*: "show me all of her classes across both schools" is a single `person`-keyed join.
4. Cross-institution *login*: she logs in per-account (one login per institution). No SSO across institutions in this revamp (accepted trade, D3b).

### 4.4 Institution admin creates a person before any login exists

**Today (broken):** Schools import 1,500 students from a spreadsheet before any logins exist. Every row would require an `app_user` (a login) — mandatory login-on-creation breaks bulk import and pre-primary students who may never get logins.

**After this revamp (anchor ready; full flow after domain split):**
1. Admin creates a `person` (name, DOB, demographics) — no account required.
2. The domain split (next capability) will let admin create a `student` linked to that `person` — also no account required.
3. Later, when the school activates a login, an `app_user` is created and linked to the same `person`. A person may have zero, one, or many accounts (D3b).

### 4.5 GDPR / deceased handling (orthogonal status)

**After this revamp (per D3c):**
1. A person's `status` is `Active` by default.
2. A registrar marks a person `Deceased`; a GDPR request sets `ErasureRequested` → later `Anonymized`. These are set by external processes, not by student/employee lifecycle transitions.
3. Student/employee behavioral lifecycles continue independently — `person.status` is the *existence/retention* classifier, orthogonal to "is this student enrolled."

---

## 5. Acceptance Criteria

### 5.1 The `person` entity

| ID | Criterion | Per |
|----|-----------|-----|
| AC-1 | A `person` entity exists as the enduring-human anchor, owning name, DOB, gender, blood group, photo, contact, and demographics | D3a, D6a |
| AC-2 | `person` carries an orthogonal status classifier: `Active \| Inactive \| Deceased \| ErasureRequested \| Anonymized` | D3c |
| AC-3 | `person` is role-agnostic — no person-level role, classification, or `person_type` field exists | D3d |
| AC-4 | A `person` may exist with zero accounts (no `app_user`, no `client_user`) | D3a |
| AC-5 | A `person` may have multiple `app_user` accounts (one per institution) | D3b |

### 5.2 Thinned accounts

| ID | Criterion | Per |
|----|-----------|-----|
| AC-6 | `app_user` carries only auth + `person_id` + tenant (`client_id`, `institution_id`) + lifecycle + last-login — no human data (name, DOB, demographics) | D6a |
| AC-7 | `client_user` carries only auth + `person_id` + client scope + lifecycle — no human data | D3e, D6a |
| AC-8 | `app_user.person_id` and `client_user.person_id` link to `person` | D3a, D3e |
| AC-9 | `app_user.institution_id` remains `NOT NULL` and singular | D3b |
| AC-10 | `client_user` remains a separate client-level account table (not folded into `app_user`) | D3e |

### 5.3 Dropped artifacts

| ID | Criterion | Per |
|----|-----------|-----|
| AC-11 | `user_category_id` is dropped from `app_user` (and everywhere); no singular human classification exists | D6a |
| AC-12 | `user_profile` table is dropped; its columns (photo, DOB, contact, etc.) live on `person` | D6a |
| AC-13 | No code discovers platform owners by `user_category`; discovery uses the `is_platform_owner` flag/claim | D6a |
| AC-14 | No fees/other module logic uses a `user_category='Learner'` proxy check | D6a |

### 5.4 Domain link repointing (anchor delivered for the next capability)

| ID | Criterion | Per |
|----|-----------|-----|
| AC-15 | `student.person_id` and `employee.person_id` link to `person` (NOT to `app_user`) — these tables land in the next capability, but the revamp's migration + model must make this repointable | D3a |
| AC-16 | `enrollment`, `homework.submission`, `fees.fee_assignment` FKs are repointable to `student.id`/`employee.id` via `person` — the revamp sets up the anchor; the actual domain-table creation is the next capability | D3a, domain-split D4 |

### 5.5 Authorization pipeline unchanged

| ID | Criterion | Per |
|----|-----------|-----|
| AC-17 | Roles remain on `app_user`/`client_user` via `role_assignment`; the Casbin middleware reads roles off the account with no per-request `person` joins | D3d, D8 |
| AC-18 | No authz policy, permission, or role definition changes as a result of this revamp | D3d |

### 5.6 Creation/activation flow preserved

| ID | Criterion | Per |
|----|-----------|-----|
| AC-19 | The unified create→invite→activate→login flow (C-02 v1.0 ADR D1–D13) continues to work: creating a user mints an invite, activate sets password + transitions lifecycle, login mints tokens | C-02 v1.0 ADR |
| AC-20 | User creation now also creates/links a `person` (the human data that used to live on `app_user`/`user_profile`) | D3a, D6a |
| AC-21 | `POST /api/v1/users` and the CD bootstrap endpoint continue to return `invite_url`; activate continues to return `{message, user_id, user_tier, client_slug}` | C-02 v1.0 ADR D1, D4 |

### 5.7 Migration

| ID | Criterion | Per |
|----|-----------|-----|
| AC-22 | One coordinated clean-cut migration (schema + reseed); no backfill script; no adapter/dual-write phase | D4, D5 |
| AC-23 | The migration introduces `person`, adds `person_id` to both account tables, drops `user_category_id` and `user_profile`, and repoints domain links — in a single change | D3a, D6a |
| AC-24 | Existing archived modules' external contracts change only where structurally unavoidable (flagged as breaking changes, §7) | constraint 4 |

### 5.8 Breaking changes (flagged)

| ID | Criterion | Per |
|----|-----------|-----|
| AC-25 | User DTOs gain a `person` projection (human data); the flat `user_profile`/`user_category` fields disappear — flagged as a breaking contract change | D6a, constraint 4 |
| AC-26 | The `user_category` field disappears from all user-facing DTOs and filters — flagged as a breaking contract change | D6a |

---

## 6. Architecture (conceptual — product shape only)

> Implementation detail (column types, API shapes, RLS, migration SQL) belongs in the spec/design phase, sourced from the ADR. This section captures only the product-relevant shape.

```
                              PERSON (new — enduring human)
                       ┌───────────────────────────────────────┐
                  ┌────│ person                                │────┐
                  │    │  name, dob, gender, blood_group,      │    │
                  │    │  photo, contact, demographics         │    │
                  │    │  status: Active|Inactive|Deceased|    │    │  (orthogonal, D3c)
                  │    │         ErasureRequested|Anonymized   │    │
                  │    │  (role-agnostic — D3d)                │    │
                  │    └───────────────────────────────────────┘    │
                  │            │1            │1            │1        │1
                  │            ▼             ▼             ▼         ▼
       ┌──────────┴──┐  ┌─────────────┐  ┌─────────────┐  ┌───────────────┐
       │ app_user    │  │  student*    │  │  employee*   │  │ client_user   │
       │ (inst acct) │  │  (domain)*   │  │  (domain)*   │  │ (client acct) │
       │  person_id  │  │  person_id   │  │  person_id   │  │  person_id    │
       │  thin: auth │  │  (next cap.) │  │  (next cap.) │  │  thin: auth   │
       │  + tenant   │  │              │  │              │  │  + client     │
       └──────┬──────┘  └──────────────┘  └──────────────┘  └───────────────┘
              │ 1:N
              ▼
   ┌──────────────────┐
   │ role_assignment  │  roles stay on the ACCOUNT (D8) — not on person
   │  user_id→app_user│
   └──────────────────┘

   * student/employee tables land in the NEXT capability (domain split).
     This revamp delivers person as the anchor they will link to.

   DROPPED: user_category_id, user_profile  (D6a)
   UNCHANGED: authz pipeline (D3d, D8), creation/activation flow (C-02 v1.0 ADR)
```

**Key product invariants (from the ADR constraints):**
- Domain entities link to `person`, never directly to an account (D3a).
- Accounts link to `person` via nullable `person_id` — a person may have no account (D3a).
- `person` is role-agnostic; roles attach to accounts (D3d, D8).
- `person.status` is orthogonal to student/employee behavioral lifecycles (D3c).
- Terminal domain transitions cascade to the account *through* `person` (domain-split D12).

---

## 7. Risks

| Risk | Impact | Mitigation |
|------|--------|-----------|
| **Bigger clean-cut blast radius** — migration touches C-02 (user repo, DTOs, create/activate, auth bootstrap), C-05 (enrollment FK), Fees, Homework, middleware fallback, plus drops `user_category`/`user_profile` and adds `person_id` to both account tables | Larger coordinated change; higher regression surface | One coordinated migration (D4/D5); disposable DB reseed; comprehensive test update in the same PR. Scope is the model restructure only — no new business logic. |
| **Breaking contract changes on user DTOs** — `user_category` field disappears; human data moves to a `person` projection | Downstream consumers (frontend, journey flows) break if not updated | Flag as breaking changes (AC-25, AC-26). Update in-repo consumers in the same PR. Frontend already built/archived — its user-display paths must be updated. |
| **Multi-account UX** — a cross-institution human has multiple logins; no SSO across institutions | User friction for cross-institution staff (multiple logins) | Accepted trade per D3b. `person` makes a future SSO/membership migration possible without losing human continuity. Frontend institution switcher does not span accounts. |
| **Platform Owner bootstrap path changes** — moves off `user_category='Executive Leadership'` onto `is_platform_owner` flag | Bootstrap script and any category-based discovery code must be updated | Update bootstrap + remove all category-based PO discovery (AC-13). The `is_platform_owner` flag is already in the JWT. |
| **`IdentityDomainLinkingService` more complex** — resolves account↔domain through `person` (two links) and handles both `app_user` and `client_user` | More linking logic; two account-table paths | Acknowledged cost (ADR §3). The service handles both tiers via the strategy pattern already in place (C-02 v1.0 ADR D6–D8). |
| **Cascade indirection** — terminal domain transitions cascade domain→person→account (one extra hop) | Slightly more coordination; same-transaction | Still same-transaction (domain-split D12); the extra hop is a join, not a cross-transaction risk. |
| **Disposable-DB assumption scoped to this revamp only** | Sets a false precedent if not flagged | Explicitly scoped (ADR constraint 11, AC-22). Once real data lands, future schema changes need backfill. |
| **Frontend (already archived) depends on `user_profile`/`user_category`** | Frontend user-display and filter paths break | Breaking change flagged; frontend update is part of this revamp's blast radius (constraint 4). |
| **`person` is hard to undo later** | If the person model is wrong, retrofitting is expensive | This is precisely why it's introduced now (ADR §2 D3a rationale) — the alternatives all crack under multi-projection people. The ADR's alternatives section documents why each lighter option was rejected. |

---

## 8. Open Questions

These are product-level questions surfaced while deriving the PRD from the ADR. Where the ADR has already resolved them, the status is "Decided." The ones marked "Needs product decision" require input before or during spec/design.

| # | Question | Status |
|---|----------|--------|
| Q1 | **What human-data fields exactly move to `person`?** The ADR names name, DOB, gender, blood group, photo, contact, demographics. Should `user_profile`'s full column set map 1:1, or is this an opportunity to normalize contact (e.g., separate phone/email/address)? | Needs product decision — field-level shape belongs in spec/design, but the PRD should confirm whether contact stays flat or normalizes. The ADR treats it as "contact" generically. |
| Q2 | **Does `person` get its own CRUD API surface, or is person management always mediated through user creation?** Today users are created via `/api/v1/users` (which would now also create/link a `person`). Should an admin be able to create a `person` with no account directly (the pre-login student record scenario, §4.4)? | Needs product decision — the revamp's scope is the model restructure + preserving the creation flow. A standalone person-creation endpoint may be needed for the pre-login scenario, but that might belong to the domain-split capability rather than this revamp. |
| Q3 | **How is `person` deduplication handled?** If an admin creates a `person` for "Priya Sharma" and later a CD creates an `app_user` for the same Priya, does the system detect the duplicate `person`, or are two `person` rows created (to be merged later)? | Needs product decision — the ADR does not specify a dedup/merge strategy. For a disposable-DB clean cut this is not blocking, but the product should decide whether person-merge is a future feature or a non-goal. |
| Q4 | **Is `person.status` exposed in the user DTO / admin UI in this revamp, or only set via backend processes?** The ADR says status is set by external processes (GDPR, registrar). Should admins see/set it now, or is it backend-only until a GDPR/retention capability lands? | Needs product decision — affects the admin UI scope for this revamp. Recommend: backend-only in this revamp (no admin UI for status), since the processes that set it don't exist yet. |
| Q5 | **Does the revamp update the frontend's user-display and user-filter paths, or is that a separate follow-up?** The frontend is archived; `user_category` filters and `user_profile` displays exist there. | Needs product decision on sequencing — the revamp's blast radius includes the frontend (constraint 4), but the parent may want to scope frontend updates as a residual follow-up (like the frontend ADR's R-items) versus in-this-PR. |
| Q6 | **Should the `person` entity carry audit/created_by/updated_by like other entities?** The creation/activation ADR's `user_account` pattern generates a shared UUID across `user_account`/`app_user`/`client_user`. Does `person` follow the same shared-UUID pattern with its accounts, or get its own UUID? | Needs product decision / spec clarification — the ADR model shows `person.id` as PK with account `person_id` FKs, but doesn't specify whether `person.id` equals the account UUID or is independent. Affects the `user_account` parent-table pattern from the creation ADR (D12). |
| Q7 | **Cross-institution reporting UX** — the revamp enables `person`-keyed cross-institution reporting (D3b). Is any reporting UI in scope for this revamp, or is that purely a future capability? | Decided — out of scope for this revamp (non-goal). The revamp delivers the anchor; reporting is future. Listed here for traceability. |
| Q8 | **Relationship to the existing `user_account` parent table (C-02 v1.0 ADR D12).** The creation ADR introduced `user_account` as the shared identity parent for `app_user`/`client_user` (for `role_assignment`/`login_attempt` FKs). The revamp introduces `person` as the human anchor. Are `user_account` and `person` two distinct entities (account-parent vs human), or does `person` absorb `user_account`'s role? | Needs product decision — this is the most consequential structural question. The ADR model shows `person` linking to accounts, while the creation ADR has `user_account` as the account parent. The spec/design phase must resolve whether `person` supersedes `user_account` or they coexist. |

---

## 9. Sequencing & Dependencies

| Dependency | Direction | Notes |
|---|---|---|
| **Student/Employee Domain Split** | Runs AFTER this revamp | That ADR's D3 (link target) and D6 (`app_user` shape) are superseded by this revamp. Its D1,D2,D4,D5,D7–D13 depend on `person` landing first. This revamp must deliver `person` as a clean anchor. |
| **C-06 Relationship Management** | Runs after the domain split | Links `person`→`student` as guardian relationships. Parent role stays a placeholder until C-06. |
| **C-02 v1.0 (creation/activation)** | Predecessor — still applies, NOT amended | This revamp preserves the creation/activation workflow semantics but restructures the underlying model. |
| **Fees, Homework, C-05 Academic Structure** | Consumers — FK repoint blast radius | `enrollment.student_id`, `homework.submission.student_id`, `fees.fee_assignment.student_id` repoint through `person`. Fees drops the `user_category='Learner'` proxy. These repoints are set up by this revamp's migration; the actual `student`/`employee` table creation is the next capability. |
| **Frontend (archived)** | Consumer — breaking contract changes | User DTOs gain a `person` projection; `user_category` field disappears. Frontend update is in the revamp's blast radius (constraint 4). |

---

## 10. Success Criteria

| ID | Success Measure | How Verified |
|----|-----------------|--------------|
| SC-1 | One `person` row per human; multi-projection people (staff-parent, lifecycle-crosser, cross-institution staff) resolve through `person` without category conflicts | AC-1 through AC-5; integration tests covering the three scenarios |
| SC-2 | `app_user`/`client_user` are thin accounts (auth + `person_id` + tenant + lifecycle); no human data on account tables | AC-6 through AC-10 |
| SC-3 | `user_category_id` and `user_profile` are gone; no proxy-classification logic survives | AC-11 through AC-14 |
| SC-4 | The authz pipeline is byte-for-byte unchanged in behavior | AC-17, AC-18; existing auth tests pass |
| SC-5 | The creation/activation flow continues to work end-to-end (create → invite → activate → login) | AC-19 through AC-21; journey-flow tests |
| SC-6 | One coordinated migration lands; DB reseeded; no backfill/dual-write | AC-22, AC-23 |
| SC-7 | Breaking contract changes are explicitly flagged and in-repo consumers updated | AC-25, AC-26; review gate |
| SC-8 | The domain split (next capability) can build `student`/`employee` on a clean `person` anchor with no rework | AC-15, AC-16; design review with the domain-split ADR |

---

> **End of PRD.** This document is the product requirements input to the sdd-stack lifecycle. Per AGENTS.md §2, the ADR is the decisional source of truth; this PRD derives from it and does not re-specify decisions. Open questions requiring product decisions are listed in §8.

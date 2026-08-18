# C-02 Identity & User Management — Person-Model Revamp

> **Status:** Final
> **Version:** 1.1
> **Last Updated:** 2026-08-18
> **Author:** AI (grill session with product owner)
> **Source:** `adr-c02-identity-user-management-implementation.md` (v1.0 — creation/activation); `adr-student-employee-domain-implementation.md` (v1.0 — D3/D6 amended here); backend surface map (migrations 001-021); grill-session decisions (Q1–Q9 → D3a–D3e, D6a)
> **Purpose:** Revamp the C-02 identity module to introduce a `person` entity as the enduring-human anchor, reshaping `app_user`/`client_user` into thin accounts and dropping `user_category_id`/`user_profile` — so the identity model supports multi-projection people (student-and-staff), lifecycle-crossers (student→alumni→employee), cross-institution staff, and the full upcoming ERP module set.
> **Cross-References:**
> - [C-02 Identity & User Management — ADR (v1.0)](./adr-c02-identity-user-management-implementation.md) — creation/activation flow
> - [Student & Employee Domain Model — ADR](./adr-student-employee-domain-implementation.md) — D3/D6 of that ADR are amended by this one
> - [Architecture v1](./architecture-v1.md)
> - [Platform Capabilities v3](../platform-capabilities/platform-capabilities-v3.md)

---

## 1. Context

The platform's identity module (C-02) models people as a single identity table: `app_user`. A student *is* an `app_user` row with role=Student; a teacher *is* an `app_user` row with role=Teacher. There is a second account table, `client_user`, for client-level directors. Platform owners are flagged via `is_platform_owner`.

The student/employee domain-split grill (grill #1, `adr-student-employee-domain-implementation.md`) chose **Camp B** — extract `student`/`employee` as domain entities with an optional link to `app_user`. That ADR's **D3** linked domain entities directly to `app_user` (`student.app_user_id`), and its **D6** kept `app_user` as both account *and* person (keeping `user_category_id`, `user_profile`).

The product owner then ran a second grill (grill #2) to "completely revamp the user and identity module" ERP-wide. That grill exposed that the domain-split ADR's identity-side decisions (D3, D6) force `app_user` to be both **the account** (login, credentials) *and* **the person** (name, DOB, contact, demographics) — which cracks in three concrete scenarios that a complete School ERP cannot avoid:

1. **Staff-parent** — a teacher with a child enrolled at the same school: one human, an `employee` projection *and* a C-06 parent relationship. `app_user`'s singular `user_category_id` can't represent both.
2. **Lifecycle-crosser** — a student graduates, then years later is hired as a teacher: one human, a historical `student` + a current `employee`. If the account was archived at graduation and recreated at hire, the human continuity is lost.
3. **Cross-institution staff** — a teacher works at two schools in the same client chain. `app_user.institution_id` is `NOT NULL` and singular (migration 012); she can't exist as one human.

All three share one root cause: **there is no `person` entity.** `app_user` is forced to be the person, but `app_user` is really an account.

This ADR records the nine decisions (Q1–Q9, mapped to D3a–D3e + D6a) that amend the domain-split ADR's D3 and D6, and define the person-centric identity model. It is the decisional input to a later sdd-stack run (per AGENTS.md §2, ADRs are captured WITHOUT sdd-stack involvement; OpenSpec specs are derived afterward).

---

## 2. Decision

| # | Decision | Choice | Rationale |
|---|---|---|---|
| **D3a** | **`person` entity** | **Introduce a `person` entity as the enduring human.** `app_user` (and `client_user`) become **thin accounts** (auth + `person_id` + tenant + lifecycle). `student`/`employee` link to **`person`** (not `app_user`): `student.person_id`, `employee.person_id`. One human = one `person`; a human with multiple accounts (cross-institution) = one `person`, multiple `app_user` rows. | The original domain-split D3 linked domain→account, forcing `app_user` to be both account and person — which cracks for staff-parents, lifecycle-crossers, and cross-institution staff. `person` is the one decision that's hard to undo later; introducing it now gives the ERP-wide-correct anchor. **This amends domain-split D3.** |
| **D3b** | **Account↔institution shape (multi-account)** | **Multiple accounts per person; one institution per account.** `app_user.institution_id` stays `NOT NULL` and singular. A cross-institution teacher = one `person`, multiple `app_user` rows (one per institution), each with its own `role_assignment`. Cross-institution *reporting* works via `person`; cross-institution *login* is per-account (no single-sign-on across institutions — accepted trade). | Rejected single-account-multi-membership (would have required amending D8 to membership-scoped roles and rewriting the authz middleware). Multi-account keeps D8 (roles on account) and the singular `institution_id` intact while still giving a unified `person` for reporting and lifecycle-crossers. |
| **D3c** | **`person` lifecycle (orthogonal status)** | **`person` has a small orthogonal status classifier, not a behavioral state machine:** `Active \| Inactive \| Deceased \| ErasureRequested \| Anonymized`. Set by external processes (GDPR, registrar, verification), not by student/employee transitions. Student/employee keep the behavioral lifececles (domain-split D9/D10); `person.status` is the *existence/retention* classifier. | A human doesn't have a behavioral lifecycle the way a student/employee does — people don't transition through behavioral states, their projections do. A full lifecycle on `person` would compete with student/employee lifecycles and re-create the two-sources-of-truth problem. The orthogonal classifier gives deceased/GDPR/retention a clean home without that conflict. |
| **D3d** | **`person` is role-agnostic** | **No person-level role concept.** `person` carries no role/classification; all capabilities are account-scoped (D8 + D3b). Human-intrinsic facts (minor, verified) are non-role attributes on `person` or derived from projections. The system will **not** reintroduce a singular human classification. | D6a (below) retires `user_category_id` precisely because a singular human classification breaks for multi-projection people. A `person_type` field would repeat that crack in a new home. "What can this human do" is correctly answered by "which account, which institution, which `role_assignment`" — that's how login already works. |
| **D3e** | **Account tiers (`client_user` fate)** | **Keep `client_user` as a separate client-level account table; `app_user` for institution-level; platform-owner via the existing `is_platform_owner` flag.** Both account tables link to `person` (`app_user.person_id`, `client_user.person_id`). Three account tiers: platform (flag), client (`client_user`), institution (`app_user`). | The platform has three real account tiers with different scopes. Keeping `client_user` separate preserves its non-null client scope, its purpose-built fields, and the working `cd_strategy`/`institution_strategy` auth split. Folding into one `app_user` (nullable `institution_id`) would amend D3b's NOT NULL and collapse the strategy split. |
| **D6a** | **`person` owns all human data; `app_user` is thin** | `person` carries name, DOB, gender, blood group, photo, contact, demographics (the enduring-human attributes). `app_user` carries `sub`, email, `person_id`, `client_id`, `institution_id`, lifecycle, last-login — **pure account/auth**, no human data. **Drop `user_category_id` entirely**; derive role-in-institution from `person→student`/`employee` projections + `role_assignment` + the existing `is_platform_owner` flag. The generic `user_profile` (keyed by `app_user`) is **gone** — its columns move to `person`. | D3a made `person` the human anchor; a singular `user_category_id` breaks for multi-projection people (student-and-staff, lifecycle-crossers). Platform Owner bootstrap moves off category onto the `is_platform_owner` flag (already in the JWT); client-director classification stays on its tier/role; fees already repoint to `student.id`. One redundant proxy retired. **This amends domain-split D6.** |
| **D3f** | **`person` and `user_account` coexist (Q8 resolution)** | **`person` and `user_account` are two distinct entities with distinct roles; `person` does NOT absorb `user_account`.** `user_account` (from creation ADR D12) remains the **account parent** — the shared FK target so `role_assignment.user_id` and `login_attempt.user_id` point to one UUID whether the account is an `app_user` or `client_user`. `person` is the **human anchor** (demographics, status, projections). **`person.id` is independent** (NOT equal to the account UUID) — a person may have zero accounts (bulk-imported student) or multiple accounts (cross-institution), so `person.id` cannot equal "the account UUID." Accounts link to `person` via `app_user.person_id` / `client_user.person_id` (nullable); `user_account` keeps D12's shared-UUID-with-child pattern unchanged. **`role_assignment`/`login_attempt`/RLS `app.current_user_id` continue to target the account parent (`user_account.id`), NOT `person.id`** — because roles and login attempts are account-scoped (D8/D3b), not human-scoped. | Roles are account-scoped (D8 + D3b): a cross-institution human has different roles per account; if `role_assignment.user_id` pointed at `person.id`, the per-account role scoping would be lost. Same for `login_attempt` (a credential attempts login, not a human) and `app.current_user_id` RLS (it scopes by the acting account, not the human). Coexistence keeps the account-parent FK integrity intact while `person` carries the human concerns — clean separation of concerns. Absorption (rejected) would have conflated human-anchor with account-parent and broken account-scoped roles. |

### Relationship to the domain-split ADR

| Domain-split decision | Status under this revamp |
|---|---|
| D1 (Camp B), D2 (two domain tables), D4 (clean cut), D5 (disposable DB), D7 (separate profiles), D9 (student lifecycle), D10 (employee lifecycle), D11 (enforcement), D12 (cascade), D13 (C-06 deferred) | ✅ **Survive unchanged** in policy. Cascade targets the account via the `person` link. |
| D3 (link domain→`app_user`) | ❌ **Amended by D3a** — link target is `person`, not `app_user`. |
| D6 (keep `user_category_id`, `user_profile`) | ❌ **Amended by D6a** — `user_category_id` dropped, `user_profile` folded into `person`, `app_user` thin. |
| D8 (roles on `app_user`) | ✅ **Survives** — roles stay on the account; `person` is role-agnostic (D3d). |

---

## 3. Consequences

**Positive:**
- **`person` is the ERP-wide-correct human anchor** — the one decision that's hard to undo later. Staff-parents, lifecycle-crossers, and cross-institution staff all resolve cleanly through one `person` row.
- **`app_user`/`client_user` become thin, purpose-built accounts** — auth and tenant only, no human-data overload. The account/person split mirrors how identity actually works (a human has credentials, not the other way around).
- **`user_category_id` retired** — a singular human classification that broke for multi-projection people is gone. Role-in-institution is derived from real projections (`student`/`employee`/`role_assignment`), not a proxy label.
- **`user_profile` collapse** — the generic profile keyed by `app_user` is gone; human data lives on `person`, domain-extended data on `student_profile`/`employee_profile`. No overlap, no redundancy.
- **Cross-institution reporting works** — one `person` joins across multiple `app_user` rows; "show me all of Priya's classes across both schools" is a single query.
- **GDPR / deceased / retention are first-class** — `person.status` (D3c) gives human-level existence/retention a real home, orthogonal to behavioral lifecycles.
- **The authz pipeline is untouched** — roles stay on `app_user` (D8); the middleware reads `ctx.roles` off the account; no per-request person joins in authz.

**Negative / cost:**
- **Bigger clean-cut blast radius** — the migration now introduces `person` *and* repoints `student`/`employee` links to `person` (not just to `student.id`/`employee.id`), *and* drops `user_category_id`/`user_profile`, *and* adds `person_id` to both account tables. Touches C-02 (user repo, DTOs, create/activate flows, auth bootstrap), C-05 (enrollment FK), Fees, Homework, and the middleware fallback. Larger than the domain-split-alone migration; still one coordinated clean cut (D5 disposable DB applies).
- **Multi-account UX** — a cross-institution human has multiple logins (one per institution). No single-sign-on across institutions in this revamp (accepted trade, D3b). The frontend institution switcher does not span accounts.
- **Platform Owner bootstrap path changes** — moves off `user_category = 'Executive Leadership'` onto the `is_platform_owner` flag. Requires updating the bootstrap script and any code that discovers platform owners by category.
- **`IdentityDomainLinkingService` is more complex** — it resolves account↔domain through `person` (two links: account→person, person→domain), not one. Must handle both `app_user` and `client_user` account tables (D3e).
- **Cascade indirection** — terminal domain transitions (D12) now cascade to the account *through* `person` (domain→person→account), one extra hop. Still same-transaction; slightly more coordination.
- **Two account tables to maintain** — `client_user` + `app_user` both need `person_id`, linking logic, and lifecycle management. The `IdentityDomainLinkingService` handles both, but it's two paths.

---

## 4. Model

```
                              PERSON (new — enduring human)
                       ┌───────────────────────────────────────┐
                  ┌────│ person                                │────┐
                  │    │  id (PK)                              │    │
                  │    │  name, dob, gender, blood_group,      │    │
                  │    │  photo, contact, demographics         │    │
                  │    │  status: Active|Inactive|Deceased|    │    │  (orthogonal classifier, D3c —
                  │    │         ErasureRequested|Anonymized   │    │   NOT a behavioral lifecycle)
                  │    │  (role-agnostic — D3d; no user_type)  │    │
                  │    └───────────────────────────────────────┘    │
                  │            │1            │1            │1        │1
                  │            ▼             ▼             ▼         ▼
       ┌──────────┴──┐  ┌─────────────┐  ┌─────────────┐  ┌───────────────┐
       │ app_user    │  │  student     │  │  employee    │  │ client_user   │
       │ (inst acct) │  │  (domain)    │  │  (domain)    │  │ (client acct) │
       │  person_id ─┘  │  person_id ──┘  │  person_id ──┘  │  person_id ───┘
       │  sub, email    │  institution_id │  institution_id │  client_id     │
       │  client_id,    │  admission_no   │  employee_no    │  role_id       │
       │  institution_id│  lifecycle:     │  lifecycle:     │  lifecycle    │
       │  (NOT NULL)    │   Applicant→    │   Hired→        │  (client-tier)│
       │  lifecycle     │   Admitted→     │   Onboarding→  │               │
       │  (invited→…→   │   Enrolled→     │   Active→       │  [platform    │
       │   archived)    │   Graduated/    │   On-Leave→     │   owner =     │
       │  NO user_      │   Withdrawn     │   Resigned/     │   is_platform │
       │   category_id  │   (+Rejected/   │   Terminated    │   _owner flag │
       │   (D6a)        │   Waitlisted)   │                 │   on app_user]│
       └──────┬─────────┘  └──────┬───────┘  └──────┬───────┘  └───────────────┘
              │ 1:N                │ 1:N              │ 1:1
              ▼                    ▼ (per a.y.)       ▼
   ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
   │ role_assignment  │  │ enrollment       │  │ employee_profile │
   │  user_id→app_user│  │  student_id→     │  │  qualifications, │
   │  role_id→role    │  │   student.id     │  │  certs, empl hist│
   │  (Teacher/HOD/..)│  │  academic_year_id│  └──────────────────┘
   │  [multi=multir..]│  │  section_id      │
   └──────────────────┘  │  status          │
                         │  ← "Promoted" =  │
   ┌──────────────────┐  │   open new yr row│
   │ student_profile  │  │   (not lifecycle)│
   │  student_id→     │  └──────────────────┘
   │   student.id     │
   │  admission-form, │     C-06 (NEXT capability)
   │  school-medical, │     ┌──────────────────────────┐
   │  academic anchors│     │ relationship             │
   └──────────────────┘     │  student_id → student.id │
                            │  related_person_id→person│
                            │  type, contact_roles,    │
                            │  custody, ... (deferred) │
                            └──────────────────────────┘


   FK REPOINT (clean cut, one migration — links move to person.id / student.id):
     student.person_id          NEW ──►  person.id
     employee.person_id         NEW ──►  person.id
     app_user.person_id         NEW ──►  person.id
     client_user.person_id      NEW ──►  person.id
     enrollment.student_id      app_user.id  ──►  student.id
     homework.submission.student_id  app_user.id  ──►  student.id
     fees.fee_assignment.student_id  app_user.id  ──►  student.id
     (fees drops the user_category='Learner' proxy check)
     role_assignment.user_id    app_user.id  (UNCHANGED — roles stay on account, D8)
     user_profile               DROPPED — columns move to person (D6a)
     app_user.user_category_id  DROPPED (D6a)


   CASCADE (domain-split D12 — cascade targets the account via the person link):
     Employee: Active→Resigned/Terminated  ──auto──►  app_user.lifecycle = archived
     Student:  Enrolled→Withdrawn           ──auto──►  app_user.lifecycle = archived
     Student:  Enrolled→Graduated           ──config──► archive (identity.archiveGraduatedStudentLogin = true)
     Student:  Admitted→Enrolled (pre-created login) ──config──► require explicit activation
                                                        (identity.autoActivateStudentLoginOnEnroll = false)
```

> **Link direction (D3a vs domain-split D3):** the domain-split ADR linked domain entities directly to `app_user` (`student.app_user_id`). This revamp inserts `person` between them: domain entities link to `person`, and accounts (`app_user`/`client_user`) also link to `person`. A domain entity no longer knows about any specific account — it knows about the human, who may have zero, one, or many accounts. The `IdentityDomainLinkingService` resolves account↔domain through `person`.

---

## 5. Constraints

1. **`person` is the enduring-human anchor; accounts (`app_user`/`client_user`) are thin auth records.** No human-level attribute (name, DOB, contact, demographics) lives on an account table. `app_user`/`client_user` carry only auth/tenant fields + `person_id`.
2. **Domain entities link to `person`, never directly to an account.** `student.person_id` / `employee.person_id` (NOT NULL — a domain entity must know which human it projects). Accounts link to `person` via `app_user.person_id` / `client_user.person_id` (NULLABLE — a person may have no account). A domain entity is unaware of any specific account; it knows about the human.
3. **`user_category_id` is dropped; no singular human classification exists anywhere.** Role-in-institution is derived from `person→student`/`employee` projections + `role_assignment` + the `is_platform_owner` flag. The system will not reintroduce a person-type/account-type field (the D6a/D3d lesson: a multi-projection person can't be a singular type).
4. **`person.status` is an orthogonal classifier, not a behavioral lifecycle.** Set by external processes (GDPR, registrar); never competes with student/employee behavioral lifecycles.
5. **Roles attach to `app_user` (or `client_user`), never to `employee` or `person`.** A role change is a `role_assignment` edit, not a domain/person lifecycle transition. Multi-role is multiple `role_assignment` rows. `person` is role-agnostic.
6. **One institution per `app_user` (`institution_id NOT NULL`, singular).** A cross-institution human has multiple `app_user` rows (one per institution), each with its own `role_assignment`. Cross-institution reporting joins through `person`; cross-institution login is per-account.
7. **`client_user` stays a separate client-level account table** (D3e). Three account tiers: platform (flag), client (`client_user`), institution (`app_user`). Both account tables link to `person`.
8. **Terminal domain transitions cascade to the linked account(s) via `person`.** Resigned/Terminated/Withdrawn auto-archive the linked `app_user` in the same transaction (if linked). Graduated and enrollment-activation cascades are config-gated (domain-split D12).
9. **Config-first cascade policy.** The two policy-dependent cascade behaviors are controlled by C-08 config keys, not hardcoded booleans.
10. **Platform Owner discovery moves off `user_category`** onto the `is_platform_owner` flag/claim (already in the JWT). No code may discover platform owners by category after this revamp.
11. **Disposable-DB assumption is scoped to this revamp's migration only.** The clean cut relies on re-seeding; it does not establish a precedent for no-backfill migrations once real data exists.
12. **`person` and `user_account` coexist as distinct entities (D3f / Q8).** `user_account` (creation ADR D12) remains the **account parent** — the shared FK target for `role_assignment.user_id`, `login_attempt.user_id`, and the `app.current_user_id` RLS var. `person` is the **human anchor**. `person.id` is **independent** of the account UUID (a person may have zero or many accounts). `role_assignment`/`login_attempt`/RLS target the account parent, NOT `person.id` — roles and login attempts are account-scoped (D8/D3b).

---

## 6. Alternatives Considered

| Alternative | Reason for Rejection |
|---|---|
| **Keep `app_user` as person+account** (domain-split D6 shape, no `person` entity). | Forces `app_user` to be both the account and the person — cracks for staff-parents (one account, two roles, singular category can't represent both), lifecycle-crossers (student→alumni→employee, account re-linked, human continuity lost if account was archived/recreated), and cross-institution staff (singular `institution_id`). Introducing `person` (D3a) decouples the enduring human from the login. |
| **One account per person, multi-institution via membership join** (Shape 2a). | Would require amending D8 to membership-scoped roles (role per membership, not per account) and rewriting the authz middleware to resolve `ctx.roles` from the active membership. Rejected to keep D8 (roles on account) and the working authz pipeline intact; multi-account (D3b) preserves single-sign-on simplicity at the cost of multiple logins for cross-institution humans — an accepted trade. |
| **`person` carries a coarse person-type classification** (Role model B). | Reintroduces a singular human classification (Learner/Staff/Mixed/…) — the exact crack D6a retired. A person who is both learner (historical) and staff (current) can't be a singular type. D3d keeps `person` role-agnostic. |
| **Full behavioral lifecycle on `person`** (`Active→Inactive→Archived`). | A human doesn't transition through behavioral states the way a student/employee does; a full lifecycle on `person` would compete with student/employee lifecycles and re-create the two-sources-of-truth problem. D3c uses an orthogonal status classifier set by external processes instead. |
| **Unify `client_user` into `app_user` with nullable `institution_id` + tier discriminator** (Tier model B). | Breaks D3b's "one institution per account, NOT NULL" lock and collapses the working `cd_strategy`/`institution_strategy` auth split. D3e keeps `client_user` separate with its clean non-null client scope. |
| **Keep `user_category_id` on `app_user` as an account label** (Fate C). | A manually-maintained label that drifts from reality; no longer a source of truth for anything. D6a drops it entirely and derives from real projections. |
| **Keep `user_profile` keyed by `app_user`** (Ownership C, minimal person). | `person` becomes underweight — the whole point of introducing it was to own the human; if it only holds name+DOB, demographics/medical/contact get re-split later. D6a makes `person` own all human data. |
| **`person_capability` table for intrinsic human gating facts** (Role model C). | Over-models what is, today, 2-3 booleans (minor, verified). D3d keeps these as non-role attributes on `person` or derived from projections. |

---

## 7. Future Evolution

- **Single sign-on / account federation across institutions** (deferred from D3b). If cross-institution-within-one-client becomes a real, painful requirement, revisit toward the rejected Shape 2a (membership join + membership-scoped roles). The `person` entity makes this migration possible without losing human continuity — the anchor is already correct.
- **C-06 Relationship Management** links to `person` (not `app_user`) — guardians are `person` rows related to a `student` via a typed relationship. The `person` anchor makes "one human is both a teacher and a parent" natural: one `person`, an `employee` projection, and a C-06 parent relationship to a `student`.
- **Person verification / KYC** — a future verification status (background check, identity-doc verification) belongs on `person` as a non-role attribute (D3d), carrying across projections.
- **GDPR / right-to-be-forgotten workflow** — `person.status = ErasureRequested` → `Anonymized` drives a retention/anonymization pipeline that preserves legally-required academic/financial records while scrubbing human-identifying data on `person`.
- **Non-disposable migration path** — once real data lands, the clean-cut pattern (D5) must be replaced by proper backfill. The `person` introduction would, in a real-data migration, backfill `person` rows from existing `app_user` human columns, then link.
- **Service accounts / API tokens** — if needed, model as a third account type linking to `person` (or to a `system` person), following the same optional-link pattern, rather than overloading `app_user`.

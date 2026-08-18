# Student & Employee Domain Model — Architecture Decision Record

> **Status:** Final
> **Version:** 2.0
> **Last Updated:** 2026-08-17
> **Author:** AI (grill session with product owner — v1.0 domain split, v2.0 identity revamp introducing `person`)
> **Source:** `adr-c02-identity-user-management-implementation.md`; backend surface map (migrations 001-021); frontend gap analysis; grill-session decisions (D1–D13 + D3a/D3b/D3c/D3d/D3e/D6a identity revamp)
> **Purpose:** Extract `student` and `employee` as first-class domain entities (with their own lifecycles) out of `app_user`, decoupling "who can log in" (identity) from "who is being taught / who is employed" (domain) — and introduce a `person` entity as the enduring-human anchor so the identity model supports multi-projection people, lifecycle-crossers, cross-institution staff, and the full upcoming ERP module set.
> **Cross-References:**
> - [C-02 Identity & User Management — ADR](./adr-c02-identity-user-management-implementation.md)
> - [Architecture v1](./architecture-v1.md)
> - [Platform Capabilities v3](../platform-capabilities/platform-capabilities-v3.md)
> - [Functional Requirements](../reference/functional-requirements.md)
>
> **v2.0 changelog:** Identity revamp (grill session #2). Introduces `person` entity (D3a), multi-account-per-person (D3b), orthogonal person status (D3c), role-agnostic person (D3d), preserved account tiers (D3e). Supersedes original D3 (link now via `person`) and D6 (`user_category_id` dropped, `user_profile` folded into `person`). D7/D8/D9/D10/D11/D12/D13 survive unchanged in policy; cascade targets account via the `person` link.

---

## 1. Context

The platform's built modules (C-01 Tenant/Institution, C-02 Identity, C-03 Auth, C-04 Authz, C-05 Academic Structure, C-08 Config, Fees, Homework) model **people as a single identity table**: `app_user`. A student *is* an `app_user` row whose `role.name = 'Student'`. A teacher *is* an `app_user` row whose `role.name = 'Teacher'`.

This identity-centric model (Camp A) was fine for the first capabilities, but it starts to fail the moment we build the next wave of people-centric modules — Attendance, Exams/Report Cards, Admissions, Parent Communication, and the flagged-next **C-06 Relationship Management**:

- **Student-specific workflows have no home.** Promotion, transfer, withdrawal, alumni, admission-funnel states, guardians — these are *domain* concerns, but they would have to live as `user_profile` columns or role tricks on identity, polluting `app_user` into a god-table.
- **Academic records are coupled to login identity.** A student's enrollment, fee history, and grades point at `app_user.id`. If the login is archived (student leaves), the academic record loses its anchor. Transcripts must survive login deletion.
- **The Parent role is a placeholder** because `parent_child_relationship` does not exist (noted in the Parent journey). Parents are not enrolled and not employed — they are *related to* a learner. Identity-centric modeling has no clean place for them.
- **A login is not the person.** Schools import 1,500 students from a spreadsheet before any logins exist; pre-primary students may never get logins (only their parents do); alumni records must persist after the login is gone. Mandatory 1:1 coupling of "student" to "login account" breaks on day one of real use.

The product owner ran a structured grill session and locked thirteen decisions (D1–D13 below), choosing **Camp B** — domain entities with an optional link to identity. This ADR records those decisions and is the decisional input to a later sdd-stack run (per AGENTS.md §2, ADRs are captured WITHOUT sdd-stack involvement; OpenSpec specs are derived afterward).

---

## 2. Decision

| # | Decision | Choice | Rationale |
|---|---|---|---|
| **D1** | **Domain model** | **Camp B** — `student` and `employee` are first-class domain entities that *optionally* link to an `app_user` (the login). `app_user` stays pure identity (login + auth + roles + tenant membership). | Decouples "who can log in" from "who is being taught / employed." Academic records survive login deletion. Domain workflows (promotion, admission, guardians) hang off the domain entity, not identity. |
| **D2** | **Domain taxonomy** | **Two domain tables** — `student` (enrollment lifecycle) and `employee` (employment lifecycle). Teacher / HOD / Principal / Staff are **roles** on the `employee` entity, not separate tables. Guardians/parents are handled by **C-06 Relationship Management** (the next capability), not a `parent` domain table. | Matches how schools actually operate. Avoids six tables + six lifecycles. A role change (Teacher→HOD) is a data update, not a row migration between tables. |
| **D3** | **Identity→domain link** | **Optional 1:1, link on the domain side** — `student.app_user_id NULL UNIQUE`, `employee.app_user_id NULL UNIQUE`. A domain entity exists with or without a login; the link is attached when the school activates an account. | Matches real school flow: admit → enroll → *later* activate login. Lets historical alumni exist without credentials. Lets a young student's parent act on their behalf without the student having an account. **Superseded/amended by D3a (person entity) — domain entities now link to `person`, not `app_user`.** |
| **D3a** | **`person` entity (identity revamp)** | **Introduce a `person` entity as the enduring human**; `app_user` (and `client_user`) become **thin accounts** (auth + `person_id` + tenant + lifecycle). `student`/`employee` link to **`person`** (not `app_user`): `student.person_id`, `employee.person_id`. One human = one `person`; a human with multiple accounts (cross-institution) = one `person`, multiple `app_user` rows. | The original D3 linked domain→account, forcing `app_user` to be both *the account* and *the person* — which cracks for staff-parents, lifecycle-crossers (student→alumni→employee), and cross-institution staff. `person` is the one decision that's hard to undo later; introducing it now gives the ERP-wide-correct anchor. |
| **D4** | **Migration strategy** | **Clean cut** — one coordinated migration: introduce `student`/`employee`, repoint enrollment + homework + fees FKs from `app_user.id` → `student.id`/`employee.id` in the same change, update tests in the same PR. No adapter/dual-write phase. | Doing this piecemeal is how ERPs accrue the two-sources-of-truth debt that kills them. One coordinated change keeps the codebase honest. |
| **D5** | **Data preservation** | **Disposable DB** — the current database is test/dev data re-seedable from `scripts/seed_data.py`. The migration is schema + reseed + test updates; **no backfill script is required.** | Keeps the clean cut a ~1-2 day job instead of a ~1 week backfill exercise. |
| **D6** | **`app_user` shape** | **Keep `app_user` columns** — `institution_id` (tenant scoping of the login) and `user_category_id` (coarse identity classification: Learner / Academic Staff / Academic Leadership / Administrative Staff / Executive Leadership) both stay. Keep a **single generic `user_profile`** (photo, DOB, contact — person attributes on identity). Domain-specific attributes live on the domain entities. **Source-of-truth invariant:** `user_category = 'Learner'` ⟺ a `student` row is linked; staff categories ⟺ an `employee` row is linked (kept consistent; `user_category` is the fast index, the domain link is the truth). **Fees repoint to `student.id`** and drop the `user_category = 'Learner'` proxy check. | Verified against code: `user_category_id` is load-bearing (auth bootstrap for platform owner, client-user classification, list/filter). `institution_id` is the middleware tenant fallback. Neither is redundant with the domain split. The one abuse (fees using category as a student test) is corrected by repointing. **Superseded/amended by D6a (person owns human data) — `user_category_id` is dropped; `user_profile` is folded into `person`; `app_user` becomes thin.** |
| **D6a** | **`person` owns all human data; `app_user` is thin** | `person` carries name, DOB, gender, blood group, photo, contact, demographics (the enduring-human attributes). `app_user` carries `sub`, email, `person_id`, `client_id`, `institution_id`, lifecycle, last-login — **pure account/auth**, no human data. **Drop `user_category_id` entirely**; derive role-in-institution from `person→student`/`employee` projections + `role_assignment` + the existing `is_platform_owner` flag. The generic `user_profile` (keyed by `app_user`) is **gone** — its columns move to `person`. | Q4 made `person` the human anchor; Q5 retired `user_category_id` (a singular label that breaks for multi-projection people — student-and-staff, lifecycle-crossers). Platform Owner bootstrap moves off category onto the `is_platform_owner` flag (already in the JWT); client-director classification stays on its tier/role; fees already repoint to `student.id`. One redundant proxy retired. |
| **D7** | **Profile tables** | **Separate `student_profile` and `employee_profile` tables** for extended domain data (admission-form fields, demographics, medical for students; qualifications, certifications, employment history for employees), alongside the generic `user_profile`. | Keeps `student`/`employee` lean (what you join on for enrollment/fees) while isolating the heavy admission-form / HR blobs. Clean normalization; the login profile stays generic. |
| **D8** | **Roles location** | **Roles stay on `app_user`** (identity). `employee` has **no role column**. Multi-role (a Principal who also teaches one class) = multiple `role_assignment` rows on the same `app_user`. The authz pipeline (middleware → `ctx.roles` → Casbin) is **unchanged**. | Roles are an identity concern; the domain split's whole point was to not move identity concerns. Keeps the working authz pipeline intact; no sync tax. The domain entity is self-describing for *employment status* (lifecycle), not for *job function* (role). |
| **D9** | **Student lifecycle** | `Applicant → Admitted → Enrolled → Graduated → Withdrawn`, plus `Rejected` / `Waitlisted` as admissions-only side states. **"Promoted" is NOT a lifecycle state** — it is an **enrollment-record event**: current grade/section lives in per-academic-year `enrollment` rows (close this year → open next year's), and `student.lifecycle_status` stays `Enrolled` throughout. | Enrollment status (in the school?) and current grade (Grade 5 vs 6) are different facts with different rates of change. Promotion churns every June for every student; keeping it out of the state machine avoids 1,500 transitions/year and preserves grade history as enrollment rows (not audit-log replay). Aligns with the already-built `kernel/academic` enrollment model — the clean cut just repoints `enrollment.student_id` to `student.id`. |
| **D10** | **Employee lifecycle** | `Hired → Onboarding → Active → On-Leave → Resigned | Terminated`. `Active ↔ On-Leave` is reversible (sabbatical, maternity, medical). `Resigned`/`Terminated` are terminal (employee record persists; `app_user` archived). Role changes (Teacher→HOD→Principal) are **not** lifecycle transitions — they are `role_assignment` edits (per D8). | Employment has no "promotion every year" analog, but it has the On-Leave subtlety. The lifecycle is purely about employment status, not job function, which keeps it clean. |
| **D11** | **Enforcement of domain state on actions** | **Split enforcement.** Identity/authz is **untouched** (no live `app_user → employee` joins in the authz pipeline). Business modules (homework, attendance, grading) check `employee.lifecycle_status` locally on the domain entity they already hold (e.g., refuse to let an `On-Leave` employee create homework). The **resignation/termination workflow archives the `app_user`** as a cascade action — belt-and-suspenders for the terminal case. | Preserves the split's decoupling (no per-request identity↔domain join) while giving a guardrail where it is cheap (modules check an entity they already load). Handles the "On-Leave teacher assigning homework" bug at the domain layer, where it belongs. |
| **D12** | **Domain→identity cascade** | **Hybrid cascade.** *Auto-cascade* (same transaction) for unambiguous terminal transitions: Resigned/Terminated employee → archive login; Withdrawn student → archive login. *Event + config* for policy-dependent transitions: Graduated student → archive login by default (config `identity.archiveGraduatedStudentLogin = true`); Enrolled student with a pre-created login → **require explicit activation** by default (config `identity.autoActivateStudentLoginOnEnroll = false`). Both config keys are seeded in C-08. | Safety where it is unambiguous; flexibility where schools genuinely differ (alumni portal access, early-login policy). Slots into the existing config-first pattern (AGENTS.md §8). |
| **D13** | **Scope boundary** | **This capability is the domain split only** (`student`/`employee` + lifecycles + cascade + FK repoint). **C-06 Relationship Management is the next capability**, with its own grill (custody, contact roles, emergency priority, multi-guardian). The **Parent role remains a placeholder** until C-06 lands; the ADR records C-06 as a documented deferred dependency. | Relationship modeling has enough decisions to warrant its own grill; bundling risks under-deciding it. The `student` entity is what C-06 will link *to*, so landing the domain split first gives C-06 a clean anchor. |
| **D3b** | **Account↔institution shape (multi-account)** | **Multiple accounts per person; one institution per account.** `app_user.institution_id` stays `NOT NULL` and singular (Q3=B). A cross-institution teacher = one `person`, multiple `app_user` rows (one per institution), each with its own `role_assignment`. Cross-institution *reporting* works via `person`; cross-institution *login* is per-account (no single-sign-on across institutions — accepted trade). | Rejected single-account-multi-membership (would have required amending D8 to membership-scoped roles and rewriting the authz middleware). Multi-account keeps D8 (roles on account) and D6's singular `institution_id` intact while still giving a unified `person` for reporting and lifecycle-crossers. |
| **D3c** | **`person` lifecycle (orthogonal status)** | **`person` has a small orthogonal status classifier, not a behavioral state machine:** `Active | Inactive | Deceased | ErasureRequested | Anonymized`. Set by external processes (GDPR, registrar, verification), not by student/employee transitions. Student/employee keep the behavioral lifecycles (D9/D10); `person.status` is the *existence/retention* classifier. | A human doesn't have a behavioral lifecycle the way a student/employee does — people don't transition through behavioral states, their projections do. A full lifecycle on `person` would compete with student/employee lifecycles and re-create the two-sources-of-truth problem. The orthogonal classifier gives deceased/GDPR/retention a clean home without that conflict. |
| **D3d** | **`person` is role-agnostic** | **No person-level role concept.** `person` carries no role/classification; all capabilities are account-scoped (D8 + D3b). Human-intrinsic facts (minor, verified) are non-role attributes on `person` or derived from projections. The system will **not** reintroduce a singular human classification (the lesson of D6a/Q5: a person who is both learner and staff can't be a singular type). | Q5 retired `user_category_id` precisely because a singular human classification breaks for multi-projection people. A `person_type` field would repeat that crack in a new home. "What can this human do" is correctly answered by "which account, which institution, which `role_assignment`" — that's how login already works. |
| **D3e** | **Account tiers (client_user fate)** | **Keep `client_user` as a separate client-level account table; `app_user` for institution-level; platform-owner via the existing `is_platform_owner` flag.** Both account tables link to `person` (`app_user.person_id`, `client_user.person_id`). Three account tiers: platform (flag), client (`client_user`), institution (`app_user`). | The platform has three real account tiers (platform/client/institution) with different scopes. Keeping `client_user` separate preserves its non-null client scope, its purpose-built fields, and the working `cd_strategy`/`institution_strategy` auth split. Folding into one `app_user` (nullable `institution_id`) would amend D3b's NOT NULL and collapse the strategy split. |

---

## 3. Consequences

**Positive:**
- Clean separation of "who can log in" (`app_user`) vs "who is being taught / employed" (`student`/`employee`). Each has the lifecycle it actually needs.
- Academic and financial records (enrollment, homework, fees, payments) anchor on domain entities that **survive login deletion** — transcripts and fee history persist for alumni and ex-employees.
- Domain workflows (admissions funnel, promotion-as-enrollment-event, leave, resignation) get first-class homes instead of polluting `user_profile`.
- The authz pipeline is **untouched** — no per-request identity↔domain joins, no sync tax. The working C-04 Casbin model keeps doing what it does.
- Parent/guardian modeling is *not* forced prematurely; C-06 gets a clean `student` anchor to link to and its own decision cycle.
- Config-first cascade policy (`identity.archiveGraduatedStudentLogin`, `identity.autoActivateStudentLoginOnEnroll`) lets schools differ on alumni/early-login policy without code changes.

**Negative / cost:**
- **Clean-cut blast radius** — one coordinated change touches `kernel/academic` (enrollment FK), `business/homework` (submission/grade FKs), `business/fees` (fee_assignment FK + the `Learner`-category proxy check), plus the user-creation flow (now must optionally create a domain entity), plus tests. Bigger now, clean forever.
- **Two lifecycles to manage** per person-type — `student`/`employee` lifecycle *and* the linked `app_user` login lifecycle. The cascade policy (D12) keeps them consistent, but it is inherent complexity of Camp B.
- **The "link" step is a real workflow** — linking an existing `app_user` to a `student`/`employee` (vs creating a new login + inviting) needs care and a clear UI/API.
- **`user_category_id` ⟺ domain-link invariant** must be maintained by the creation/link/transition code; if it drifts, the fast-index (`user_category`) and the truth (domain link) disagree.
- **D5 (disposable DB) is a one-time concession.** Once real data lands, future schema changes on these tables will need proper backfill — the disposable assumption does not persist beyond this capability.
- **Parent role stays a placeholder** one capability longer — parent-facing journeys remain blocked until C-06.

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


   CASCADE (D12 — cascade targets the account via the person link):
     Employee: Active→Resigned/Terminated  ──auto──►  app_user.lifecycle = archived
     Student:  Enrolled→Withdrawn           ──auto──►  app_user.lifecycle = archived
     Student:  Enrolled→Graduated           ──config──► archive (identity.archiveGraduatedStudentLogin = true)
     Student:  Admitted→Enrolled (pre-created login) ──config──► require explicit activation
                                                        (identity.autoActivateStudentLoginOnEnroll = false)
```

> **Note on the link direction (D3a vs original D3):** the original ADR linked domain entities directly to `app_user` (`student.app_user_id`). The identity revamp (D3a) inserts `person` between them: domain entities link to `person`, and accounts (`app_user`/`client_user`) also link to `person`. A domain entity no longer knows about any specific account — it knows about the human, who may have zero, one, or many accounts. The `IdentityDomainLinkingService` resolves account↔domain through `person`.

---

## 5. Constraints

1. **`person` is the enduring-human anchor; accounts (`app_user`/`client_user`) are thin auth records.** No human-level attribute (name, DOB, contact, demographics) lives on an account table. `app_user`/`client_user` carry only auth/tenant fields + `person_id`.
2. **Domain entities link to `person`, never directly to an account.** `student.person_id` / `employee.person_id` (NOT NULL — a domain entity must know which human it projects). Accounts link to `person` via `app_user.person_id` / `client_user.person_id` (NULLABLE — a person may have no account, e.g., bulk-imported students, alumni). A domain entity is unaware of any specific account; it knows about the human.
3. **`user_category_id` is dropped; no singular human classification exists anywhere.** Role-in-institution is derived from `person→student`/`employee` projections + `role_assignment` + the `is_platform_owner` flag. The system will not reintroduce a person-type/account-type field (the D6a/D3d lesson: a multi-projection person can't be a singular type).
4. **"Promoted" is never a `student.lifecycle_status` value.** Promotion is an enrollment-record event (per academic year). Current grade/section is read from the active `enrollment` row.
5. **Domain records are never deleted.** `student` and `employee` rows persist through Graduated/Withdrawn/Resigned/Terminated. Only the linked account may be archived. Academic/financial FKs remain valid forever.
6. **`person.status` is an orthogonal classifier, not a behavioral lifecycle.** It is set by external processes (GDPR, registrar) and never competes with student/employee behavioral lifecycles.
7. **Roles attach to `app_user` (or `client_user`), never to `employee` or `person`.** A role change is a `role_assignment` edit, not a domain/person lifecycle transition. Multi-role is multiple `role_assignment` rows. `person` is role-agnostic.
8. **One institution per `app_user` (`institution_id NOT NULL`, singular).** A cross-institution human has multiple `app_user` rows (one per institution), each with its own `role_assignment`. Cross-institution reporting joins through `person`; cross-institution login is per-account (no SSO across institutions in this revamp).
9. **Terminal domain transitions cascade to the linked account(s).** Resigned/Terminated/Withdrawn auto-archive the linked `app_user` in the same transaction (if linked). Graduated and enrollment-activation cascades are config-gated (D12).
10. **Config-first cascade policy.** The two policy-dependent cascade behaviors are controlled by C-08 config keys, not hardcoded booleans.
11. **No C-06 in this capability.** Guardians/parents are out of scope; the Parent role stays a placeholder. The `student` entity is delivered as the anchor C-06 will later link to.
12. **Disposable-DB assumption is scoped to this capability only.** The clean cut relies on re-seeding; it does not establish a precedent for no-backfill migrations once real data exists.

---

## 6. Alternatives Considered

| Alternative | Reason for Rejection |
|---|---|
| **Camp A — Student/Teacher are just `app_user` with a role** (keep current model). | Breaks on real school use: no home for admission/promotion/transfer/alumni workflows; academic records coupled to login identity; parent-child links have no anchor; mandatory login-on-creation breaks bulk import and pre-primary. |
| **Six domain tables — one per role** (`student`, `teacher`, `principal`, `hod`, `staff`, `parent`). | Six tables, six lifecycles, and a mess when a Principal retires but stays on as a part-time Teacher, or a Staff member is promoted to HOD. Role is a job function, not a person-type. |
| **Mandatory 1:1 link (`student.app_user_id NOT NULL`)** (Pattern 1). | Breaks on day one: schools import 1,500 students before any logins exist; pre-primary students never get logins; admission records must exist before enrollment, let alone account activation. |
| **Link on the identity side (`app_user.student_id`)** (Pattern 3). | Every consumer pays an indirection to answer "does this student have a login?"; `app_user` grows a nullable FK per future domain type (contractor, visitor, …). Domain-first link is cleaner. |
| **Adapter / dual-write migration** (Strategy 2 — keep FKs on `app_user`, add domain tables, migrate module-by-module later). | Lives with a lie for months — two sources of truth for "who is this student," and every new module decides which world it is in. The "clean cut later" rarely happens; debt compounds. |
| **Slim `app_user` / drop `user_category_id`** (Shape 2 original). | Rejected after code verification: `user_category_id` is load-bearing (auth bootstrap for platform owner, client-user classification, list/filter). Kept instead, with the category⟺domain-link invariant. **Later superseded by D6a** — once `person` was introduced (D3a) as the human anchor, `user_category_id`'s singular classification broke for multi-projection people (student-and-staff, lifecycle-crossers) and was dropped entirely; the invariant it supported became unnecessary because domain truth lives in `person→student`/`employee` projections, not in an account label. |
| **Keep `app_user` as person+account** (no `person` entity; original ADR D6 shape). | Forces `app_user` to be both the account and the person — which cracks for staff-parents (one account, two roles, singular category can't represent both), lifecycle-crossers (student→alumni→employee, account re-linked, human continuity lost if account was archived/recreated), and cross-institution staff (singular `institution_id`). Introducing `person` (D3a) decouples the enduring human from the login. |
| **One account per person, multi-institution via membership join** (Shape 2a). | Would require amending D8 to membership-scoped roles (role per membership, not per account) and rewriting the authz middleware to resolve `ctx.roles` from the active membership. Rejected to keep D8 (roles on account) and the working authz pipeline intact; multi-account (D3b) preserves single-sign-on simplicity at the cost of multiple logins for cross-institution humans — an accepted trade. |
| **`person` carries a coarse person-type classification** (Role model B). | Reintroduces a singular human classification (Learner/Staff/Mixed/…) — the exact crack Q5/D6a retired. A person who is both learner (historical) and staff (current) can't be a singular type. D3d keeps `person` role-agnostic. |
| **Full behavioral lifecycle on `person`** (`Active→Inactive→Archived`). | A human doesn't transition through behavioral states the way a student/employee does; a full lifecycle on `person` would compete with student/employee lifecycles and re-create the two-sources-of-truth problem. D3c uses an orthogonal status classifier set by external processes instead. |
| **Unify `client_user` into `app_user` with nullable `institution_id` + tier discriminator** (Tier model B). | Breaks the D3b "one institution per account, NOT NULL" lock and collapses the working `cd_strategy`/`institution_strategy` auth split. D3e keeps `client_user` separate with its clean non-null client scope. |
| **Three profile tables merged into one role-aware `user_profile`** (vs D7 separate profiles). | Couples heavy admission-form / HR blobs to the generic identity profile; harder to isolate and validate per-domain. Separate `student_profile` / `employee_profile` keep `student`/`employee` lean and the blobs isolated. |
| **"Promoted" as a `student.lifecycle_status`** (vs D9 demotion). | Churns the state machine for every student every June (1,500 transitions/year); `lifecycle_status` becomes almost-always "Promoted" (uninformative); grade history requires audit-log replay instead of enrollment-row queries. |
| **Employee lifecycle without On-Leave** (Option B, 4 states). | "Is this teacher available to teach?" becomes a composite check (Active AND not on a current leave_record) rather than a single state read — messier for downstream rostering/attendance. |
| **Central authz guardrail on employee lifecycle** (Option B, live `app_user→employee` joins in authz). | Re-couples identity and domain — the opposite of the split's goal — and adds per-request join cost. Replaced by split enforcement (D11): modules check the entity they already hold. |
| **Automatic cascade for all transitions** (Pattern X). | Hardcodes policy; "Withdrawn students keep logins for 30 days" or alumni-portal access would need conditional logic in the domain service. Hybrid (D12) keeps policy in config. |
| **Bundle C-06 minimal into this capability** (Option B scope). | Relationship modeling (custody, contact roles, emergency priority, multi-guardian) deserves its own grill; bundling risks under-deciding it. C-06 is the next capability. |

---

## 7. Future Evolution

- **C-06 Relationship Management (next capability)** will introduce the `relationship` entity linking `student` ←→ `person` (guardian) with typed relationships, contact roles, custody, and emergency-contact priority. This capability delivers `student` as the anchor; C-06 fills the guardian layer and unblocks the Parent role. (Note: C-06 links to `person`, not `app_user`, per the D3a link direction.)
- **Single sign-on / account federation across institutions** (deferred from D3b). If cross-institution-within-one-client becomes a real, painful requirement, revisit toward D3b's rejected alternative (membership join + membership-scoped roles). The `person` entity makes this migration possible without losing human continuity — the anchor is already correct.
- **Admissions module** can be built on top of the `Applicant → Admitted` states already in the student lifecycle, without re-modeling the person.
- **Alumni portal** is enabled by D12's configurable graduated-login archive (`identity.archiveGraduatedStudentLogin = false` keeps alumni logins for transcript access).
- **Cohort bulk fee assignment** (the R6 deferred frontend item) becomes natural once fees target `student.id` and enrollment gives section/grade cohorts — a follow-up Fees backend change.
- **Non-disposable migration path:** once real data lands, the clean-cut pattern established here must be replaced by proper backfill migrations for any further schema change on `student`/`employee`. The D5 disposable assumption is explicitly scoped to this capability.
- **Employee sub-types** (e.g., `contractor`, `visitor`) — if needed, extend the `employee` taxonomy or add a parallel domain entity following the same optional-1:1-link pattern, rather than growing `app_user` columns.
- **Revisit D8 (roles on identity) only if** a genuine requirement emerges for job-function history on the domain entity (e.g., "track every position this employee held over 10 years"). That would introduce an `employee_role_history` table derived from `role_assignment`, still without moving authz off `app_user`.

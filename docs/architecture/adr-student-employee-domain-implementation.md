# Student & Employee Domain Model — Architecture Decision Record

> **Status:** Final
> **Version:** 1.1
> **Last Updated:** 2026-08-17
> **Author:** AI (grill session with product owner)
> **Source:** `adr-c02-identity-user-management-implementation.md`; backend surface map (migrations 001-021); frontend gap analysis; grill-session decisions
> **Purpose:** Extract `student` and `employee` as first-class domain entities (with their own lifecycles) out of `app_user`, decoupling "who can log in" (identity) from "who is being taught / who is employed" (domain), before building any new people-centric business module.
> **Cross-References:**
> - [C-02 Identity & User Management — ADR](./adr-c02-identity-user-management-implementation.md)
> - [C-02 Identity Person-Model Revamp — ADR](./adr-c02-identity-person-model-revamp.md) ← amends D3/D6 below (introduces `person` entity)
> - [Architecture v1](./architecture-v1.md)
> - [Platform Capabilities v3](../platform-capabilities/platform-capabilities-v3.md)
> - [Functional Requirements](../reference/functional-requirements.md)
>
> **v1.1 changelog:** D3 (link target) and D6 (`app_user` shape) are amended by a separate identity-revamp ADR (`adr-c02-identity-person-model-revamp.md`). That ADR introduces a `person` entity between domain and accounts — the domain link target becomes `person` (not `app_user`), and `user_category_id`/`user_profile` are dropped. This ADR's domain-split decisions (D1, D2, D4, D5, D7–D13) stand unchanged; only the identity-side assumptions (D3, D6) are superseded. See the identity-revamp ADR for the current identity model.

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
| **D3** | **Identity→domain link** | **Optional 1:1, link on the domain side** — `student.app_user_id NULL UNIQUE`, `employee.app_user_id NULL UNIQUE`. A domain entity exists with or without a login; the link is attached when the school activates an account. | Matches real school flow: admit → enroll → *later* activate login. Lets historical alumni exist without credentials. Lets a young student's parent act on their behalf without the student having an account. **⚠️ Superseded by D3a in [Identity Person-Model Revamp ADR](./adr-c02-identity-person-model-revamp.md) — domain entities now link to `person` (not `app_user`); a `person` entity sits between domain and accounts.** |
| **D4** | **Migration strategy** | **Clean cut** — one coordinated migration: introduce `student`/`employee`, repoint enrollment + homework + fees FKs from `app_user.id` → `student.id`/`employee.id` in the same change, update tests in the same PR. No adapter/dual-write phase. | Doing this piecemeal is how ERPs accrue the two-sources-of-truth debt that kills them. One coordinated change keeps the codebase honest. |
| **D5** | **Data preservation** | **Disposable DB** — the current database is test/dev data re-seedable from `scripts/seed_data.py`. The migration is schema + reseed + test updates; **no backfill script is required.** | Keeps the clean cut a ~1-2 day job instead of a ~1 week backfill exercise. |
| **D6** | **`app_user` shape** | **Keep `app_user` columns** — `institution_id` (tenant scoping of the login) and `user_category_id` (coarse identity classification: Learner / Academic Staff / Academic Leadership / Administrative Staff / Executive Leadership) both stay. Keep a **single generic `user_profile`** (photo, DOB, contact — person attributes on identity). Domain-specific attributes live on the domain entities. **Source-of-truth invariant:** `user_category = 'Learner'` ⟺ a `student` row is linked; staff categories ⟺ an `employee` row is linked (kept consistent; `user_category` is the fast index, the domain link is the truth). **Fees repoint to `student.id`** and drop the `user_category = 'Learner'` proxy check. | Verified against code: `user_category_id` is load-bearing (auth bootstrap for platform owner, client-user classification, list/filter). `institution_id` is the middleware tenant fallback. Neither is redundant with the domain split. The one abuse (fees using category as a student test) is corrected by repointing. **⚠️ Superseded by D6a in [Identity Person-Model Revamp ADR](./adr-c02-identity-person-model-revamp.md) — `user_category_id` is dropped; `user_profile` is folded into `person`; `app_user` becomes a thin account.** |
| **D7** | **Profile tables** | **Separate `student_profile` and `employee_profile` tables** for extended domain data (admission-form fields, demographics, medical for students; qualifications, certifications, employment history for employees), alongside the generic `user_profile`. | Keeps `student`/`employee` lean (what you join on for enrollment/fees) while isolating the heavy admission-form / HR blobs. Clean normalization; the login profile stays generic. |
| **D8** | **Roles location** | **Roles stay on `app_user`** (identity). `employee` has **no role column**. Multi-role (a Principal who also teaches one class) = multiple `role_assignment` rows on the same `app_user`. The authz pipeline (middleware → `ctx.roles` → Casbin) is **unchanged**. | Roles are an identity concern; the domain split's whole point was to not move identity concerns. Keeps the working authz pipeline intact; no sync tax. The domain entity is self-describing for *employment status* (lifecycle), not for *job function* (role). |
| **D9** | **Student lifecycle** | `Applicant → Admitted → Enrolled → Graduated → Withdrawn`, plus `Rejected` / `Waitlisted` as admissions-only side states. **"Promoted" is NOT a lifecycle state** — it is an **enrollment-record event**: current grade/section lives in per-academic-year `enrollment` rows (close this year → open next year's), and `student.lifecycle_status` stays `Enrolled` throughout. | Enrollment status (in the school?) and current grade (Grade 5 vs 6) are different facts with different rates of change. Promotion churns every June for every student; keeping it out of the state machine avoids 1,500 transitions/year and preserves grade history as enrollment rows (not audit-log replay). Aligns with the already-built `kernel/academic` enrollment model — the clean cut just repoints `enrollment.student_id` to `student.id`. |
| **D10** | **Employee lifecycle** | `Hired → Onboarding → Active → On-Leave → Resigned | Terminated`. `Active ↔ On-Leave` is reversible (sabbatical, maternity, medical). `Resigned`/`Terminated` are terminal (employee record persists; `app_user` archived). Role changes (Teacher→HOD→Principal) are **not** lifecycle transitions — they are `role_assignment` edits (per D8). | Employment has no "promotion every year" analog, but it has the On-Leave subtlety. The lifecycle is purely about employment status, not job function, which keeps it clean. |
| **D11** | **Enforcement of domain state on actions** | **Split enforcement.** Identity/authz is **untouched** (no live `app_user → employee` joins in the authz pipeline). Business modules (homework, attendance, grading) check `employee.lifecycle_status` locally on the domain entity they already hold (e.g., refuse to let an `On-Leave` employee create homework). The **resignation/termination workflow archives the `app_user`** as a cascade action — belt-and-suspenders for the terminal case. | Preserves the split's decoupling (no per-request identity↔domain join) while giving a guardrail where it is cheap (modules check an entity they already load). Handles the "On-Leave teacher assigning homework" bug at the domain layer, where it belongs. |
| **D12** | **Domain→identity cascade** | **Hybrid cascade.** *Auto-cascade* (same transaction) for unambiguous terminal transitions: Resigned/Terminated employee → archive login; Withdrawn student → archive login. *Event + config* for policy-dependent transitions: Graduated student → archive login by default (config `identity.archiveGraduatedStudentLogin = true`); Enrolled student with a pre-created login → **require explicit activation** by default (config `identity.autoActivateStudentLoginOnEnroll = false`). Both config keys are seeded in C-08. | Safety where it is unambiguous; flexibility where schools genuinely differ (alumni portal access, early-login policy). Slots into the existing config-first pattern (AGENTS.md §8). |
| **D13** | **Scope boundary** | **This capability is the domain split only** (`student`/`employee` + lifecycles + cascade + FK repoint). **C-06 Relationship Management is the next capability**, with its own grill (custody, contact roles, emergency priority, multi-guardian). The **Parent role remains a placeholder** until C-06 lands; the ADR records C-06 as a documented deferred dependency. | Relationship modeling has enough decisions to warrant its own grill; bundling risks under-deciding it. The `student` entity is what C-06 will link *to*, so landing the domain split first gives C-06 a clean anchor. |

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
                         IDENTITY (kernel/user)                DOMAIN (new)
   ┌─────────────────────────────────────────────┐    ┌──────────────────────────────┐
   │ app_user                                     │    │ student                       │
   │  id (PK)                                     │◄───│  id (PK)                      │
   │  sub (Supabase auth sub)                     │  1 │  app_user_id NULL UNIQUE ─────┘  (optional 1:1)
   │  email                                       │  : │  institution_id (enrolled-at)
   │  client_id, institution_id  (tenant scope)  │  1 │  admission_no                 │
   │  user_category_id  (Learner / Staff / ...)   │    │  lifecycle_status             │
   │  lifecycle_status (invited→…→archived)       │    │   Applicant→Admitted→Enrolled │
   │  created_at, updated_at                      │    │   →Graduated→Withdrawn        │
   └──────────────┬───────────────────────────────┘    │   (+Rejected/Waitlisted)      │
                  │ 1:N                                  └──────────────┬───────────────┘
                  ▼                                                     │ 1:N (per academic year)
   ┌──────────────────────────────┐                          ┌─────────▼──────────────┐
   │ role_assignment              │                          │ enrollment              │
   │  user_id → app_user.id       │                          │  student_id → student.id│
   │  role_id → role              │                          │  academic_year_id       │
   │  (Teacher/HOD/Principal/...) │                          │  section_id             │
   │  [multi-row = multi-role]    │                          │  status (active/completed)
   └──────────────────────────────┘                          │  ← "Promoted" = open new │
                                                             │     year's row, not a    │
   ┌──────────────────────────────┐                          │     lifecycle transition │
   │ user_profile (generic)       │                          └──────────────────────────┘
   │  user_id → app_user.id       │
   │  photo, dob, contact         │              ┌──────────────────────────────┐
   └──────────────────────────────┘              │ student_profile (extended)   │
                                                  │  student_id → student.id     │
   ┌──────────────────────────────┐              │  admission-form, demographics│
   │ app_user ────► employee       │              │  medical, ...                │
   │              id (PK)          │              └──────────────────────────────┘
   │              app_user_id NULL │
   │              institution_id   │     C-06 (NEXT capability)
   │              employee_no      │     ┌──────────────────────────────┐
   │              lifecycle_status │     │ relationship                 │
   │               Hired→Onboarding│     │  student_id → student.id     │
   │               →Active→On-Leave│     │  related_user_id → app_user  │
   │               →Resigned|Term. │     │  type (Mother/Father/Guardian)
   │              ...              │     │  contact_roles, custody, ... │
   └──────────────┬───────────────┘     │  (deferred — D13)            │
                  │ 1:1 optional          └──────────────────────────────┘
                  ▼
   ┌──────────────────────────────┐
   │ employee_profile (extended)  │
   │  employee_id → employee.id   │
   │  qualifications, certs,      │
   │  employment history, ...     │
   └──────────────────────────────┘


   FK REPOINT (clean cut, one migration):
     enrollment.student_id        app_user.id  ──►  student.id
     homework.submission.student_id  app_user.id  ──►  student.id
     fees.fee_assignment.student_id  app_user.id  ──►  student.id
     (fees drops the user_category='Learner' proxy check)
     role_assignment.user_id     app_user.id  (UNCHANGED — roles are identity)
     user_profile.user_id        app_user.id  (UNCHANGED — generic identity profile)


   CASCADE (D12):
     Employee: Active→Resigned/Terminated  ──auto──►  app_user.lifecycle = archived
     Student:  Enrolled→Withdrawn           ──auto──►  app_user.lifecycle = archived
     Student:  Enrolled→Graduated           ──config──► archive (identity.archiveGraduatedStudentLogin = true)
     Student:  Admitted→Enrolled (pre-created login) ──config──► require explicit activation
                                                        (identity.autoActivateStudentLoginOnEnroll = false)
```

---

## 5. Constraints

1. **`app_user` remains the sole identity table.** No login/auth/role logic moves to `student`/`employee`. The authz pipeline reads roles off `app_user` and never joins to domain entities per-request.
2. **The identity→domain link is optional and on the domain side.** `student.app_user_id` / `employee.app_user_id` are `NULL UNIQUE`. A domain entity may exist with no login; a login may (transiently) exist with no domain entity (e.g., a platform owner, or before linking).
3. **`user_category_id` ⟺ domain-link invariant.** `user_category = 'Learner'` iff a `student` row is linked; a staff category iff an `employee` row is linked. Creation/link/transition code must maintain this. `user_category` is the fast index; the domain link is the truth.
4. **"Promoted" is never a `student.lifecycle_status` value.** Promotion is an enrollment-record event (per academic year). Current grade/section is read from the active `enrollment` row.
5. **Domain records are never deleted.** `student` and `employee` rows persist through Graduated/Withdrawn/Resigned/Terminated. Only the linked `app_user` may be archived. Academic/financial FKs remain valid forever.
6. **Roles attach to `app_user`, never to `employee`.** A role change is a `role_assignment` edit, not a domain lifecycle transition. Multi-role is multiple `role_assignment` rows.
7. **Terminal domain transitions cascade to identity.** Resigned/Terminated/Withdrawn auto-archive the linked `app_user` in the same transaction (if linked). Graduated and enrollment-activation cascades are config-gated (D12).
8. **Config-first cascade policy.** The two policy-dependent cascade behaviors are controlled by C-08 config keys, not hardcoded booleans. New schools/settings change behavior via config, not code.
9. **No C-06 in this capability.** Guardians/parents are out of scope; the Parent role stays a placeholder. The `student` entity is delivered as the anchor C-06 will later link to.
10. **Disposable-DB assumption is scoped to this capability only.** The clean cut relies on re-seeding; it does not establish a precedent for no-backfill migrations once real data exists.

---

## 6. Alternatives Considered

| Alternative | Reason for Rejection |
|---|---|
| **Camp A — Student/Teacher are just `app_user` with a role** (keep current model). | Breaks on real school use: no home for admission/promotion/transfer/alumni workflows; academic records coupled to login identity; parent-child links have no anchor; mandatory login-on-creation breaks bulk import and pre-primary. |
| **Six domain tables — one per role** (`student`, `teacher`, `principal`, `hod`, `staff`, `parent`). | Six tables, six lifecycles, and a mess when a Principal retires but stays on as a part-time Teacher, or a Staff member is promoted to HOD. Role is a job function, not a person-type. |
| **Mandatory 1:1 link (`student.app_user_id NOT NULL`)** (Pattern 1). | Breaks on day one: schools import 1,500 students before any logins exist; pre-primary students never get logins; admission records must exist before enrollment, let alone account activation. |
| **Link on the identity side (`app_user.student_id`)** (Pattern 3). | Every consumer pays an indirection to answer "does this student have a login?"; `app_user` grows a nullable FK per future domain type (contractor, visitor, …). Domain-first link is cleaner. |
| **Adapter / dual-write migration** (Strategy 2 — keep FKs on `app_user`, add domain tables, migrate module-by-module later). | Lives with a lie for months — two sources of truth for "who is this student," and every new module decides which world it is in. The "clean cut later" rarely happens; debt compounds. |
| **Slim `app_user` / drop `user_category_id`** (Shape 2 original). | Rejected after code verification: `user_category_id` is load-bearing (auth bootstrap for platform owner, client-user classification, list/filter). Kept instead, with the category⟺domain-link invariant. |
| **Three profile tables merged into one role-aware `user_profile`** (vs D7 separate profiles). | Couples heavy admission-form / HR blobs to the generic identity profile; harder to isolate and validate per-domain. Separate `student_profile` / `employee_profile` keep `student`/`employee` lean and the blobs isolated. |
| **"Promoted" as a `student.lifecycle_status`** (vs D9 demotion). | Churns the state machine for every student every June (1,500 transitions/year); `lifecycle_status` becomes almost-always "Promoted" (uninformative); grade history requires audit-log replay instead of enrollment-row queries. |
| **Employee lifecycle without On-Leave** (Option B, 4 states). | "Is this teacher available to teach?" becomes a composite check (Active AND not on a current leave_record) rather than a single state read — messier for downstream rostering/attendance. |
| **Central authz guardrail on employee lifecycle** (Option B, live `app_user→employee` joins in authz). | Re-couples identity and domain — the opposite of the split's goal — and adds per-request join cost. Replaced by split enforcement (D11): modules check the entity they already hold. |
| **Automatic cascade for all transitions** (Pattern X). | Hardcodes policy; "Withdrawn students keep logins for 30 days" or alumni-portal access would need conditional logic in the domain service. Hybrid (D12) keeps policy in config. |
| **Bundle C-06 minimal into this capability** (Option B scope). | Relationship modeling (custody, contact roles, emergency priority, multi-guardian) deserves its own grill; bundling risks under-deciding it. C-06 is the next capability. |

---

## 7. Future Evolution

- **C-06 Relationship Management (next capability)** will introduce the `relationship` entity linking `student` ←→ `app_user` (guardian) with typed relationships, contact roles, custody, and emergency-contact priority. This capability delivers `student` as the anchor; C-06 fills the guardian layer and unblocks the Parent role.
- **Admissions module** can be built on top of the `Applicant → Admitted` states already in the student lifecycle, without re-modeling the person.
- **Alumni portal** is enabled by D12's configurable graduated-login archive (`identity.archiveGraduatedStudentLogin = false` keeps alumni logins for transcript access).
- **Cohort bulk fee assignment** (the R6 deferred frontend item) becomes natural once fees target `student.id` and enrollment gives section/grade cohorts — a follow-up Fees backend change.
- **Non-disposable migration path:** once real data lands, the clean-cut pattern established here must be replaced by proper backfill migrations for any further schema change on `student`/`employee`. The D5 disposable assumption is explicitly scoped to this capability.
- **Employee sub-types** (e.g., `contractor`, `visitor`) — if needed, extend the `employee` taxonomy or add a parallel domain entity following the same optional-1:1-link pattern, rather than growing `app_user` columns.
- **Revisit D8 (roles on identity) only if** a genuine requirement emerges for job-function history on the domain entity (e.g., "track every position this employee held over 10 years"). That would introduce an `employee_role_history` table derived from `role_assignment`, still without moving authz off `app_user`.

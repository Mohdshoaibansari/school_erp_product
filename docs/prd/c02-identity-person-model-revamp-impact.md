# Impact Classification — C-02 Identity Person-Model Revamp

> **Phase:** sdd-stack-impact-classification
> **Change:** C-02 Identity Person-Model Revamp
> **Decisional source:** `docs/architecture/adr-c02-identity-person-model-revamp.md` (D3a–D3e, D6a)
> **PRD:** `docs/prd/c02-identity-person-model-revamp.md`
> **Baseline classified against:** `openspec/specs/` (archived main specs for all built capabilities)
> **Date:** 2026-08-17
> **Method:** Shallow targeted scan of every spec under `openspec/specs/` against the revamp's ADR decisions + PRD acceptance criteria.

---

## 1. Summary — Affected OpenSpec Domains

The revamp produces delta specs under `openspec/changes/<change-id>/specs/<domain>/spec.md`. The following `<domain>` folders will carry deltas:

| # | OpenSpec domain | Severity | Impact classes | One-line reason |
|---|---|---|---|---|
| 1 | `identity-user-management` | **High** | Added + Modified + Removed + Q8 | Core of the revamp: `person` introduced, `app_user` thinned, `user_category_id`/`user_profile` dropped, creation/activation restructured. |
| 2 | `client-user-bootstrap` | **High** | Modified + Removed + Q8 | `client_user` thinned (gains `person_id`, drops `user_category_id`, name→`person`); two-tier creation flow restructured. |
| 3 | `authentication` | **Medium** | Modified + Q8 | Activate/login resolve account that now links to `person`; token claims may carry `person_id`; `user_account` parent (Q8) affects `login_attempt` FK. |
| 4 | `frontend-shell` | **Medium (Breaking)** | Modified | User DTO contract changes — `person` projection added, `user_category` field disappears. Breaking downstream contract. |
| 5 | `academic-structure` | **Medium** | Modified | `student_enrollment.student_id` FK (→`app_user.id`) repoints to `student.id` via `person`; teacher/homeroom FKs stay on `app_user` (roles stay on accounts). |
| 6 | `fees` | **Medium** | Modified + Cross-cutting | `fee_assignment.student_id` FK repoint setup; drops `user_category='Learner'` proxy check. |
| 7 | `homework` | **Medium** | Modified + Cross-cutting | `submission.student_id` FK repoint setup. |
| 8 | `authorization` | **Low** | Modified (minimal) | Underlying `app_user`/`role_assignment` shape shifts, but authz pipeline behavior is byte-for-byte unchanged (D3d, D8). Casbin loader sources unchanged. |
| 9 | `platform-owner-separation` | **Low** | Modified (minimal) | Residual `user_category='Executive Leadership'` discovery path (if any) moves to `is_platform_owner` flag; PO model otherwise unaffected. |
| 10 | `platform-owner-followups` | **Low** | Modified (minimal) | Middleware fallback reads `client_id`/`institution_id` from `app_user` — fields remain, but `app_user` is thinned. |
| 11 | `auth-infrastructure` | **Low** | Modified (minimal) | `app.current_user_id` RLS var still maps to account id; `user_account` parent (Q8) may shift the `user_id` referent. |
| 12 | `tenant-institution` | **Low** | Modified (minimal) | `app_user.institution_id NOT NULL` invariant preserved (D3b); `app_user` shape change is referenced but the NOT-NULL requirement stands. |
| 13 | `person` **(NEW — conditional)** | **High (if added)** | Added | If the design phase gives `person` its own CRUD API surface (PRD Q2), a new `person` domain folder is created. Otherwise person requirements live inside `identity-user-management`. **Design-phase decision.** |

**Domains confirmed NOT affected** (scanned, no delta needed):
- `configuration` — cascade config keys (`identity.archiveGraduatedStudentLogin`, `identity.autoActivateStudentLoginOnEnroll`) belong to the **domain-split** capability, not this revamp. No new config keys introduced by this revamp per the PRD.
- `configuration-framework` — no interaction with the person model.

---

## 2. Per-Domain Classification

### 2.1 `identity-user-management` — High · Added + Modified + Removed + Q8

**Source spec:** `openspec/specs/identity-user-management/spec.md`

#### ADDED
- **`person` entity as enduring-human anchor** — new requirements for `person` owning name, DOB, gender, blood group, photo, contact, demographics (AC-1, D3a, D6a). If `person` gets its own domain folder (PRD Q2), these move to a new `person` spec; otherwise they are added here.
- **`person.status` orthogonal classifier** — `Active | Inactive | Deceased | ErasureRequested | Anonymized`, set by external processes (AC-2, D3c).
- **`person` is role-agnostic** — no person-level role/classification/`person_type` (AC-3, D3d).
- **Multiple accounts per person; one institution per account** — `app_user.person_id` nullable, a person may have 0–N accounts (AC-4, AC-5, D3b).
- **`app_user`/`client_user` link to `person` via `person_id`** (AC-8, D3a, D3e).
- **User creation now creates/links a `person`** (AC-20, D3a, D6a) — the human data that used to live on `app_user`/`user_profile`.

#### MODIFIED
- **`POST /api/v1/users` request body** — currently `{email, name, user_category_id, institution_id, role_id}`. `user_category_id` removed; `name` (and human data) now targets `person`; `person_id` link created (AC-20, AC-26). Affects requirements: *Unified invite token minting*, *Optional role_id on user creation*.
- **`UserDTO` contract** — gains a `person` projection; flat `user_profile`/`user_category` fields disappear (AC-25, AC-26). **Breaking.**
- **`app_user` shape** — thinned to auth + `person_id` + tenant (`client_id`, `institution_id`) + lifecycle + last-login; no human data (AC-6, D6a).
- **Single lifecycle arc for all user tiers** — preserved (AC-19), but the underlying row now carries `person_id`; the `invited → active` arc is unchanged in behavior.
- **REQ-USER-AC-02: Student Enrollment Reference** — `student_enrollment.student_id` FK currently → `app_user.id`; repoints to `student.id` via `person` (AC-16). The `student` table lands in the next capability, but this revamp's migration sets up the repoint.
- **Teacher assignment / homeroom FKs** (`teacher_assignment.teacher_id`, `section.homereoom_teacher_id` → `app_user.id`) — **stay on `app_user`** (roles stay on accounts, D8). No repoint; but the requirement text referencing "Teacher must exist in `app_user` table" still holds.

#### REMOVED
- **`user_category_id`** dropped from `app_user` and everywhere (AC-11, D6a). Removes the `user_category_id` field from every creation/list/filter requirement and DTO.
- **`user_profile` table** dropped; columns folded into `person` (AC-12, D6a). Removes the generic-profile-keyed-by-`app_user` requirements.
- **`user_category = 'Learner'` ⟺ student-link invariant** (domain-split D6 constraint 3) — the proxy-classification invariant is retired entirely (AC-14).
- **Platform-owner discovery by `user_category`** — removed (AC-13, D6a).

#### Q8 ambiguity
- The creation/activation ADR (v1.0 D12) introduced **`user_account`** as the shared identity parent for `app_user`/`client_user` (so `role_assignment.user_id` and `login_attempt.user_id` can point to one parent). The revamp introduces **`person`** as the human anchor. Q8: does `person` absorb `user_account`, or do they coexist? This affects the creation flow's shared-UUID pattern (D12 inserts `user_account` first, then the child row with the same UUID) and every requirement that assumes the `user_account` parent. **No archived OpenSpec spec mentions `user_account` by name** (verified via grep — it lives only in the ADR), so the specs are silent; the design phase must decide and the delta spec must state the chosen model explicitly.

---

### 2.2 `client-user-bootstrap` — High · Modified + Removed + Q8

**Source spec:** `openspec/specs/client-user-bootstrap/spec.md`

#### MODIFIED
- **Two-tier user model** — `client_user` becomes a thin account (auth + `person_id` + client scope + lifecycle); human data (name) moves to `person` (AC-7, D3e, D6a). The "physically distinct tables" invariant survives, but `client_user` columns change.
- **`client_user` table structure** — currently `{id, email, name, user_category_id, lifecycle_status, role_id, client_id, ...}`. `name` → `person`; `user_category_id` dropped; `person_id` added (AC-7, AC-8, AC-11).
- **Login lookup by `user_metadata.user_tier`** — behavior preserved (CD→`client_user`, institution→`app_user`), but both tables now link to `person`. The `user_tier` stamping at creation is unchanged.
- **CD own-row access** — CD updates "display name" via `PATCH .../$SELF_ID`; the name now lives on `person`, so the update path routes through the person link. RLS on `client_user` (own-row) is unchanged in shape but the `name` column leaves the table.
- **Bootstrap creates an invited CD** — now also creates/links a `person` (AC-20).
- **Casbin policy loader — dual source** — `role_assignment` (institution) + `client_user.role_id` (client-leadership). `role_assignment.user_id` referent may shift if `person` absorbs `user_account` (Q8).

#### REMOVED
- **`user_category_id` from `client_user`** (AC-11, D6a). The column-set requirement that lists `user_category_id` is removed.

#### Q8 ambiguity
- The `user_account` parent (D12) is the FK target for cross-tier referential integrity. If `person` absorbs `user_account`, the `client_user`↔parent relationship and the creation flow's insert order change. Affects: *Two-tier user model*, *client_user table structure*, *Casbin policy loader*.

---

### 2.3 `authentication` — Medium · Modified + Q8

**Source spec:** `openspec/specs/authentication/spec.md`

#### MODIFIED
- **Unified activation for both user tiers** — activate looks up by UUID in `app_user` then `client_user`. Behavior preserved (AC-19, AC-21), but the underlying account now carries `person_id`. The activate response `{message, user_id, user_tier, client_slug}` is unchanged in shape (AC-21).
- **Token claims** — the PRD flags that token claims may carry `person_id` (impact area list). The current CD JWT carries `{sub, user_tier, client_id, role_id, exp}`; the institution JWT carries tenant + roles. Whether `person_id` is added to claims is a **design-phase decision** (not mandated by an AC, but listed as an impact area). Flag as Modified-pending-design.
- **Password validation / OTP / password-reset flows** — unchanged in behavior (operate on the Supabase Auth user, not on `app_user` human columns). No human data on the account anymore, so these flows are unaffected structurally.

#### Q8 ambiguity
- `login_attempt.user_id` FK currently → `user_account.id` (per ADR D12). If `person` absorbs `user_account`, the `login_attempt` referent and any login-audit requirements shift. The archived spec does not mention `login_attempt` or `user_account` explicitly, so the delta must clarify.

---

### 2.4 `frontend-shell` — Medium (Breaking) · Modified

**Source spec:** `openspec/specs/frontend-shell/spec.md`

#### MODIFIED
- **REQ-SHELL-09: Typed DTO API Layer** — the typed DTOs mirror backend DTOs. The `UserDTO` changes (gains `person` projection, loses `user_category`/flat profile fields). The frontend API layer's `UserDTO` type must be updated. **Breaking contract change** (AC-25, AC-26).
- **REQ-SHELL-10: All 10 Backend Roles** — role list unchanged; `is_platform_owner` fallback stays. No role-definition change (D3d, D8). Minimal/no delta here beyond the DTO.
- **Context switcher / tenant context** — `client_id`/`institution_id` still come from the JWT; unaffected by the person model. No delta.
- **User-display & filter paths** (REQ-FE-USR-01 through REQ-FE-USR-05, which live in the `identity-user-management` spec but are frontend requirements) — `user_category` dropdown/filter disappears; profile fields now come from the `person` projection. **Breaking.** These REQ-FE-USR-* requirements are physically in `identity-user-management/spec.md` but semantically frontend; the delta should address them wherever they live.

> **Note:** The frontend is already archived. PRD Q5 asks whether frontend updates land in this revamp's PR or as a residual follow-up. The impact classification flags the breaking change; **sequencing is a product decision** (PRD Q5).

---

### 2.5 `academic-structure` — Medium · Modified

**Source spec:** `openspec/specs/academic-structure/spec.md`

#### MODIFIED
- **REQ-AC-10: StudentEnrollment** — `student_id` (UUID, FK → `app_user.id`) repoints to `student.id` (via `person`). The `student` table lands in the **next** capability (domain split); this revamp's migration sets up the anchor so the repoint is possible (AC-16). The requirement text "Student must exist in `app_user` table" / "Student must have 'Student' role" changes to reference the `student` domain entity.
- **REQ-AC-05: Section.homeroom_teacher_id** (FK → `app_user.id`) — **stays on `app_user`** (teachers are accounts with roles; D8). No repoint.
- **REQ-AC-09: TeacherAssignment.teacher_id** (FK → `app_user.id`) — **stays on `app_user`**. No repoint.
- **REQ-USER-AC-02** (lives in `identity-user-management` spec but is a C-05 cross-reference) — same repoint as REQ-AC-10.

#### Cross-cutting
- The enrollment FK repoint is a cross-cutting concern spanning `academic-structure` + `identity-user-management` + the future domain-split. This revamp delivers `person` as the anchor; the actual `student` table creation + FK repoint execution is the next capability. The delta here records the **setup** (anchor delivered, repoint declared).

---

### 2.6 `fees` — Medium · Modified + Cross-cutting

**Source spec:** `openspec/specs/fees/spec.md`

> The archived `fees` spec is **frontend-only** (fee type/assignment/payment UI). The backend `fee_assignment.student_id` FK and the `user_category='Learner'` proxy check live in backend code, not in an archived OpenSpec backend-fees spec. The impact is therefore **cross-cutting** (migration touches backend fees) with a **minimal frontend delta** (the student reference in fee-assignment UI points to the roster, which will be person/student-keyed).

#### MODIFIED
- **REQ-FE-FEE-02: Fee Assignment Management** — fee assignments target a student; the student reference shifts from `app_user`-keyed to `student`-keyed (via `person`). Frontend behavior largely unchanged (still picks from a roster), but the underlying student identity changes.
- **REQ-FE-FEE-03: Payments** — "filterable by student" — the student filter key shifts. Minimal frontend delta.

#### Cross-cutting (backend, not in archived spec)
- **`fee_assignment.student_id` FK** repoints `app_user.id` → `student.id` (AC-16, D3a). Setup in this revamp's migration; execution in the next capability.
- **Drops `user_category='Learner'` proxy check** (AC-14, D6a). The one abuse flagged in the domain-split ADR (fees using category as a student test) is corrected.

> **Gap:** there is no archived backend-fees OpenSpec spec; the FK/proxy logic is implementation, not spec'd behavior. The design phase should decide whether a backend-fees delta spec is needed or whether this is captured purely as a migration/implementation concern. **Residual gap — flag to design.**

---

### 2.7 `homework` — Medium · Modified + Cross-cutting

**Source spec:** `openspec/specs/homework/spec.md`

> Like fees, the archived `homework` spec is **frontend-only**. The backend `submission.student_id` FK repoint is a migration/implementation concern.

#### MODIFIED
- **REQ-FE-HW-02: Submissions and Grading** — submissions are "per student"; the student key shifts to `student.id` (via `person`). Frontend behavior unchanged (still lists per-student submissions), but the underlying identity changes.

#### Cross-cutting (backend, not in archived spec)
- **`homework.submission.student_id` FK** repoints `app_user.id` → `student.id` (AC-16, D3a). Setup in this revamp's migration; execution in the next capability.

> **Gap:** same as fees — no archived backend-homework OpenSpec spec. **Residual gap — flag to design.**

---

### 2.8 `authorization` — Low · Modified (minimal)

**Source spec:** `openspec/specs/authorization/spec.md`

#### MODIFIED (minimal)
- The archived spec contains only the C-05 academic-structure permission additions. **No authz policy, permission, or role definition changes** result from this revamp (AC-17, AC-18, D3d, D8). Roles stay on `app_user`/`client_user` via `role_assignment`; Casbin middleware reads roles off the account with no per-request `person` joins.
- The only shift is that `role_assignment.user_id` may change its referent if `person` absorbs `user_account` (Q8) — but the **behavior** is unchanged. If Q8 resolves to "person absorbs user_account," the delta records the new FK target; if they coexist, no delta is needed here beyond a note.
- **Likely no delta spec required** unless Q8 resolves to absorption. Flag as conditional.

---

### 2.9 `platform-owner-separation` — Low · Modified (minimal)

**Source spec:** `openspec/specs/platform-owner-separation/spec.md`

#### MODIFIED (minimal)
- The PO exists only in Supabase Auth (`is_platform_owner = true`), with no `app_user` row. This is **already** the model in the archived spec. The revamp's AC-13 ("no code discovers platform owners by `user_category`") targets residual category-based discovery code, not the PO spec itself.
- The PO's own human data (if any) now lives on `person` — but the PO has no `app_user`/`client_user` row, so the `person` link for the PO is an open question (does the PO get a `person`? PRD §3 says "The PO's own human data (if any) now lives on `person`"). **Minor design clarification needed.**
- **Likely no delta spec required** beyond a note on PO↔person linkage. Flag as conditional.

---

### 2.10 `platform-owner-followups` — Low · Modified (minimal)

**Source spec:** `openspec/specs/platform-owner-followups/spec.md`

#### MODIFIED (minimal)
- **Middleware role resolution** — the subdomain-missing fallback looks up `client_id`/`institution_id` from `app_user`. Those fields **remain** on `app_user` (D6a keeps tenant fields on the account), so the fallback still works. No behavioral change.
- **Client Director lifecycle support** — references `app_user.institution_id` nullable (legacy, superseded by migration 012 NOT NULL). Unaffected by the person model.
- **Likely no delta spec required.** The `app_user` thinning removes human columns, not tenant columns. Flag as no-op unless design surfaces a dependency.

---

### 2.11 `auth-infrastructure` — Low · Modified (minimal)

**Source spec:** `openspec/specs/auth-infrastructure/spec.md`

#### MODIFIED (minimal)
- **RLS session variables** — `app.current_user_id` maps to the authenticated user's UUID. If `person` absorbs `user_account` (Q8), the `user_id` referent may shift from account-id to person-id, which would change what `app.current_user_id` means for RLS. **Q8-dependent.**
- **`update_user` accepts `user_metadata`** — unchanged; the activate flow still stamps `user_tier`. No delta.
- **Likely no delta spec required** unless Q8 resolves to absorption and the `user_id` referent changes. Flag as conditional.

---

### 2.12 `tenant-institution` — Low · Modified (minimal)

**Source spec:** `openspec/specs/tenant-institution/spec.md`

#### MODIFIED (minimal)
- **`app_user.institution_id` NOT NULL** (migration 012) — **preserved** (D3b keeps it NOT NULL and singular). No delta to this invariant.
- The spec references `app_user` table structure in migration requirements (011/012). The `app_user` thinning (dropping human columns, `user_category_id`) is a structural change to the table, but the NOT-NULL `institution_id` requirement stands. **Minor note** in the delta that the table shape changes while the invariant is preserved.
- **Likely no delta spec required** beyond a structural note. Flag as conditional.

---

## 3. Cross-Cutting Concerns (span multiple domains)

| Cross-cutting concern | Domains touched | ADR ref | Notes |
|---|---|---|---|
| **FK repoints to `student.id`/`employee.id` via `person`** | academic-structure, fees, homework, identity-user-management | D3a, AC-16 | `enrollment.student_id`, `fee_assignment.student_id`, `submission.student_id` repoint from `app_user.id` → `student.id`. The `student`/`employee` tables land in the **next** capability; this revamp delivers `person` + sets up the repoint in one coordinated migration. |
| **`user_category_id` dropped everywhere** | identity-user-management, client-user-bootstrap, frontend-shell, fees (proxy), platform-owner-separation (discovery) | D6a, AC-11, AC-13, AC-14 | No singular human classification survives. Fees drops the `Learner` proxy; PO discovery moves to `is_platform_owner`. |
| **`user_profile` folded into `person`** | identity-user-management, frontend-shell (REQ-FE-USR-02), client-user-bootstrap | D6a, AC-12 | Generic profile keyed by `app_user` is gone; human data on `person`, domain-extended data on `student_profile`/`employee_profile` (next capability). |
| **User DTO contract change (breaking)** | identity-user-management, frontend-shell, authentication (response shapes) | AC-25, AC-26 | `person` projection added; `user_category` field disappears. All in-repo consumers updated in the same PR. |
| **One coordinated clean-cut migration** | all touched domains | D4, D5, AC-22, AC-23 | Schema + reseed; no backfill; no dual-write. Disposable-DB assumption scoped to this revamp only. |
| **`IdentityDomainLinkingService` complexity** | identity-user-management, academic-structure | ADR §3 | Resolves account↔domain through `person` (two links); handles both `app_user` and `client_user`. |
| **Q8: `person` vs `user_account` parent** | identity-user-management, client-user-bootstrap, authentication, authorization, auth-infrastructure | PRD Q8 | See §4. |

---

## 4. Q8 Ambiguity — `person` vs `user_account` parent table

**The question (PRD Q8):** The creation/activation ADR (v1.0 D12) introduced `user_account` as the shared identity parent for `app_user`/`client_user` — so `role_assignment.user_id` and `login_attempt.user_id` can point to one cross-tier parent. The revamp introduces `person` as the human anchor. **Are `user_account` and `person` two distinct entities (account-parent vs human), or does `person` absorb `user_account`'s role?**

**Specs affected by Q8 (where the delta must state the chosen model):**

| Domain | Requirement / concern | How Q8 affects it |
|---|---|---|
| `identity-user-management` | Creation flow shared-UUID pattern (D12 inserts `user_account` first, then child row with same UUID); `role_assignment.user_id` referent | If `person` absorbs `user_account`: creation flow inserts `person` first; `role_assignment.user_id` may → `person.id` or stay → account id. If they coexist: two parents, `person` for human data, `user_account` for FK integrity. |
| `client-user-bootstrap` | Two-tier model; CD creation inserts `user_account` then `client_user` | Same fork as above. |
| `authentication` | `login_attempt.user_id` FK target; activate lookup-by-UUID | If absorbed, `login_attempt` referent shifts. |
| `authorization` | `role_assignment.user_id` referent; Casbin loader source | If absorbed and `role_assignment.user_id` → `person.id`, the loader query changes (but behavior is unchanged). |
| `auth-infrastructure` | `app.current_user_id` RLS var meaning | If the `user_id` referent shifts to `person.id`, RLS policies keyed on `current_user_id` may need reinterpretation. |

**Key finding:** **No archived OpenSpec spec mentions `user_account` by name** (verified via `grep -r "user_account" openspec/specs/` → zero hits). The `user_account` parent exists only in the ADR (D12) and presumably the implementation/migrations. This means:
1. The specs are currently silent on the parent-table model — the delta specs must **state it explicitly** for the first time.
2. The design phase must resolve Q8 **before** the spec deltas can be written definitively, because the chosen model changes the creation-flow requirement text, the `role_assignment`/`login_attempt` FK targets, and the RLS `user_id` semantics.
3. PRD Q6 (shared-UUID pattern) is related — whether `person.id` equals the account UUID or is independent.

**Recommendation:** Q8 is the **most consequential structural open question** and should be resolved in the ADR (Change Loop, AGENTS.md §3) **before** the proposal/spec phase finalizes the delta requirements, because it changes the referential-integrity model across 5 domains.

---

## 5. Added / Modified / Removed / Cross-cutting — Consolidated

### ADDED (new requirements introduced by the revamp)
1. `person` entity — enduring-human anchor (name, DOB, gender, blood group, photo, contact, demographics). [identity-user-management or new `person` domain — design decision, PRD Q2]
2. `person.status` orthogonal classifier (`Active|Inactive|Deceased|ErasureRequested|Anonymized`). [identity-user-management / person]
3. `person` is role-agnostic — no `person_type`/classification. [identity-user-management / person]
4. Multiple accounts per person (0–N `app_user`, one institution each); `app_user.person_id`/`client_user.person_id` nullable FK → `person.id`. [identity-user-management, client-user-bootstrap]
5. User creation creates/links a `person`. [identity-user-management, client-user-bootstrap]
6. `is_platform_owner` flag as the sole platform-owner discovery mechanism (replaces `user_category='Executive Leadership'`). [identity-user-management, platform-owner-separation]

### MODIFIED (existing requirements that change)
1. `POST /api/v1/users` request body — `user_category_id` removed; human data → `person`; `person_id` link created. [identity-user-management]
2. `UserDTO` contract — gains `person` projection; loses `user_category`/flat profile fields. **Breaking.** [identity-user-management, frontend-shell]
3. `app_user` shape — thinned to auth + `person_id` + tenant + lifecycle. [identity-user-management, tenant-institution, platform-owner-followups]
4. `client_user` shape — thinned; `name`→`person`, `user_category_id` dropped, `person_id` added. [client-user-bootstrap]
5. CD own-row update (display name) routes through `person` link. [client-user-bootstrap]
6. Activate/login resolve account that now links to `person`; token claims may carry `person_id` (design decision). [authentication]
7. `student_enrollment.student_id` FK → `app_user.id` repoints to `student.id` via `person` (setup; execution next capability). [academic-structure, identity-user-management]
8. `fee_assignment.student_id` FK repoint setup; drops `Learner` proxy. [fees]
9. `submission.student_id` FK repoint setup. [homework]
10. Frontend user-display/filter paths — `user_category` dropdown/filter gone; profile from `person` projection. [frontend-shell, identity-user-management REQ-FE-USR-*]
11. `role_assignment.user_id` / `login_attempt.user_id` referent — **Q8-dependent**. [authorization, authentication, auth-infrastructure]

### REMOVED (requirements dropped)
1. `user_category_id` column + all requirements keyed on it (creation, list, filter, DTO). [identity-user-management, client-user-bootstrap, frontend-shell]
2. `user_profile` table + requirements keyed on it (generic profile keyed by `app_user`). [identity-user-management, frontend-shell]
3. `user_category = 'Learner'` ⟺ student-link invariant (domain-split D6 constraint 3). [identity-user-management, fees]
4. Platform-owner discovery by `user_category` (any residual code). [identity-user-management, platform-owner-separation]

### CROSS-CUTTING (spans multiple domains)
1. FK repoints to `student.id`/`employee.id` via `person` — academic-structure + fees + homework + identity-user-management.
2. `user_category_id` dropped everywhere — identity-user-management + client-user-bootstrap + frontend-shell + fees + platform-owner-separation.
3. `user_profile` → `person` fold — identity-user-management + frontend-shell + client-user-bootstrap.
4. User DTO breaking contract change — identity-user-management + frontend-shell + authentication.
5. One coordinated clean-cut migration (schema + reseed) — all touched domains.
6. Q8 `person` vs `user_account` parent — identity-user-management + client-user-bootstrap + authentication + authorization + auth-infrastructure.

---

## 6. Residual Gaps & Narrowest Useful Next Rerun

### Residual gaps (flagged for the design phase)
1. **Q8 unresolved** — `person` vs `user_account` parent. Must be resolved in the ADR (Change Loop) before delta specs are final. Affects 5 domains' requirement text.
2. **PRD Q2** — whether `person` gets its own CRUD API surface / domain folder, or person management is always mediated through user creation. Determines whether a new `person` domain spec is created or person requirements live inside `identity-user-management`. Design decision.
3. **PRD Q5** — frontend update sequencing (in-this-PR vs residual follow-up). The breaking DTO change is flagged; sequencing is a product decision.
4. **No archived backend-fees / backend-homework OpenSpec specs** — the FK repoints and the `Learner`-proxy drop are implementation/migration concerns not captured in spec'd behavior. The design phase must decide whether backend-fees/homework delta specs are needed or whether this is migration-only.
5. **PO ↔ `person` linkage** — the PO has no `app_user`/`client_user` row. Does the PO get a `person`? PRD §3 implies yes ("PO's own human data now lives on `person`") but no AC covers it. Minor design clarification.
6. **Token claims carrying `person_id`** — listed as an impact area but not mandated by an AC. Design decision.

### Narrowest useful next rerun (if residual unknowns persist after Q8 resolution)
- A **code-level scan** of `kernel/user/`, `kernel/auth/`, and the migrations (001–021) to confirm exactly which files reference `user_account`, `user_category_id`, and `user_profile` — to convert this spec-level impact classification into a file-level implementation impact map for the design/tasks phases. This is **optional** and belongs to the design or current-state-exploration phase, not this classification.

---

## 7. Affected OpenSpec Domains — Final List (for delta spec folders)

Delta specs will be produced under `openspec/changes/<change-id>/specs/<domain>/spec.md` for:

| Domain | Impact severity | Confidence |
|---|---|---|
| `identity-user-management` | High | High — core of revamp |
| `client-user-bootstrap` | High | High — client_user thinned |
| `authentication` | Medium | High — activate/login + Q8 |
| `frontend-shell` | Medium (Breaking) | High — DTO contract |
| `academic-structure` | Medium | High — enrollment FK repoint setup |
| `fees` | Medium | Medium — backend spec gap; frontend delta minimal |
| `homework` | Medium | Medium — backend spec gap; frontend delta minimal |
| `authorization` | Low (conditional) | Medium — no delta unless Q8 → absorption |
| `platform-owner-separation` | Low (conditional) | Medium — minimal/conditional |
| `platform-owner-followups` | Low (conditional) | High — likely no-op (tenant fields remain) |
| `auth-infrastructure` | Low (conditional) | Medium — Q8-dependent |
| `tenant-institution` | Low (conditional) | High — likely no-op (NOT NULL preserved) |
| `person` (NEW) | High (conditional) | Medium — depends on PRD Q2 (own API surface?) |

**Definitely affected (delta required):** `identity-user-management`, `client-user-bootstrap`, `authentication`, `frontend-shell`, `academic-structure`.
**Likely affected (delta required, pending design):** `fees`, `homework`.
**Conditionally affected (delta only if Q8/design resolves a certain way):** `authorization`, `platform-owner-separation`, `auth-infrastructure`, `tenant-institution`, `platform-owner-followups`, `person` (new).

---

> **End of impact classification.** This document is the input to the proposal/spec/design phases. Q8 must be resolved in the ADR (Change Loop, AGENTS.md §3) before delta specs are finalized.

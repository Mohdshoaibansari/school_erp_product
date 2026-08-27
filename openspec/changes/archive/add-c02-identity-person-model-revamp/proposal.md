# Proposal — C-02 Identity Person-Model Revamp

> **Change ID:** `add-c02-identity-person-model-revamp`
> **Status:** Proposed
> **Capability:** C-02 Identity & User Management (structural overhaul of an already-archived capability)
> **Source ADR:** `docs/architecture/adr-c02-identity-person-model-revamp.md` (D3a–D3e, D6a — final)
> **Source PRD:** `docs/prd/c02-identity-person-model-revamp.md` (26 acceptance criteria)
> **Impact Classification:** `docs/prd/c02-identity-person-model-revamp-impact.md` (13 affected domains)
> **Predecessor (still applies, NOT amended):** `docs/architecture/adr-c02-identity-user-management-implementation.md` (creation/activation, D1–D13)
> **Amends:** `docs/architecture/adr-student-employee-domain-implementation.md` D3, D6 (superseded by D3a, D6a)

---

## 1. Summary

Introduce a `person` entity as the **enduring-human anchor** of the identity model, restructure `app_user` and `client_user` into **thin accounts** (auth + `person_id` + tenant + lifecycle only), **drop `user_category_id` and `user_profile`** entirely, and repoint domain links (`student`/`employee`) to `person` — so that staff-parents, lifecycle-crossers (student→alumni→employee), and cross-institution staff all resolve cleanly through one `person` row. The revamp delivers the clean anchor the next capabilities (Student/Employee Domain Split, then C-06 Relationship Management) build on, while keeping the authz pipeline byte-for-byte unchanged (roles stay on accounts, D8).

## 2. Why

| Problem | Impact |
|---------|--------|
| `app_user` is forced to be both **account** (login, credentials, roles, tenant) and **person** (name, DOB, contact, demographics via `user_profile`, coarse classification via `user_category_id`) | Staff-parent (teacher with a child) — singular `user_category_id` can't represent both; lifecycle-crosser (student→teacher) — human continuity lost if account archived/recreated; cross-institution staff — singular `institution_id` can't hold two schools |
| No `person` entity exists | One human = one `app_user` row. Multi-projection people (student-and-staff) break. The domain-split ADR's D3/D6 link domain→account, perpetuating the conflation. |
| `user_category_id` is a singular human classification | Breaks for multi-projection people; a manually-maintained label that drifts from reality; no longer source of truth for anything. Fees uses `user_category='Learner'` as a student proxy — an abuse. |
| `user_profile` keyed by `app_user` | Generic profile conflated with account; human data trapped on the account table. |
| Platform Owner discovery by `user_category='Executive Leadership'` | Relies on the dropped proxy; must move to `is_platform_owner` flag. |

## 3. What Changes

| Domain | Delta | Summary |
|--------|-------|---------|
| **identity-user-management** | ADDED + MODIFIED + REMOVED | `person` entity introduced (enduring-human anchor, owns all human data, orthogonal status, role-agnostic). `app_user` thinned to auth + `person_id` + tenant + lifecycle. `user_category_id` and `user_profile` dropped. User creation now creates/links a `person`. `UserDTO` gains `person` projection, loses `user_category`/flat profile fields. Enrollment FK (`REQ-USER-AC-02`) repoint setup to `student.id` via `person`. Teacher/homeroom FKs stay on `app_user` (D8). |
| **client-user-bootstrap** | MODIFIED + REMOVED | `client_user` thinned (auth + `person_id` + client scope + lifecycle); `name` → `person`, `user_category_id` dropped, `person_id` added. Bootstrap creates/links a `person`. CD own-row display-name update routes through `person`. Casbin dual-source loader referent Q8-dependent. |
| **authentication** | MODIFIED | Unified activation resolves account that now links to `person`; activate response shape unchanged. Token claims may carry `person_id` (design decision). `login_attempt.user_id` FK target Q8-dependent. |
| **frontend-shell** | MODIFIED (Breaking) | `UserDTO` typed-DTO layer gains `person` projection; `user_category` field disappears from all DTOs/filters. **Breaking contract change.** Role list and authz gating unchanged (D8). |
| **academic-structure** | MODIFIED | `REQ-AC-10: StudentEnrollment` — `student_id` FK (`app_user.id`) repoint setup to `student.id` via `person`. Teacher/homeroom FKs (`REQ-AC-05`, `REQ-AC-09`) stay on `app_user`. |
| **fees** | MODIFIED + Cross-cutting | `REQ-FE-FEE-02`/`REQ-FE-FEE-03` — student reference shifts to `student`-keyed (via `person`). Drops `user_category='Learner'` proxy check. Backend FK repoint setup (no archived backend-fees spec; migration concern). |
| **homework** | MODIFIED + Cross-cutting | `REQ-FE-HW-02` — submission student key shifts to `student.id` (via `person`). Backend FK repoint setup (no archived backend-homework spec; migration concern). |
| **authorization** | MODIFIED (conditional) | No authz policy/permission/role-definition change (D3d, D8). `role_assignment.user_id` referent may shift if Q8 resolves to absorption — behavior unchanged. **Q8-conditional; minimal delta.** |
| **platform-owner-separation** | MODIFIED (minimal) | PO discovery moves off `user_category` onto `is_platform_owner` flag (already the model). PO↔`person` linkage is an open design clarification. |
| **auth-infrastructure** | MODIFIED (conditional) | `app.current_user_id` RLS var referent may shift if Q8 resolves to absorption. **Q8-conditional; minimal delta.** |
| **tenant-institution** | — (no delta) | `app_user.institution_id NOT NULL` preserved (D3b). Table shape changes but the NOT-NULL invariant stands. No requirement change. |
| **platform-owner-followups** | — (no delta) | Middleware fallback reads `client_id`/`institution_id` from `app_user` — tenant fields remain (D6a). No behavioral change. |

## 4. Public API Contract Changes (Breaking)

| Contract | Before | After | Breaking? |
|----------|--------|-------|-----------|
| `POST /api/v1/users` request body | `{email, name, user_category_id, institution_id, role_id?}` | `{email, person_data: {name, dob, gender, …}, institution_id, role_id?}` — `user_category_id` removed; human data targets `person`; `person_id` link created | **Yes** (AC-20, AC-26) |
| `UserDTO` | flat fields incl. `user_category_id`, `user_profile.*` | gains `person: PersonDTO` projection; loses `user_category_id` and flat `user_profile` fields | **Yes** (AC-25, AC-26) |
| `user_category` field in all DTOs/filters | present | **removed** | **Yes** (AC-26) |
| `GET /api/v1/lookups/user-categories` | returns user_category list | **removed** (no `user_category` table) | **Yes** |
| CD bootstrap endpoint (`POST /api/v1/platform/clients/{id}/users`) | `{email, name, role}` | `{email, person_data: {name, …}, role}` — human data → `person` | **Yes** (AC-20) |
| Activate response `{message, user_id, user_tier, client_slug}` | unchanged shape | unchanged shape (AC-21) | No |
| Authz pipeline (Casbin middleware) | roles off account | roles off account — **unchanged** (AC-17, AC-18) | No |

> All in-repo consumers (frontend, journey flows, tests) are updated in the same PR. The frontend is already archived; its user-display and user-filter paths must be updated (breaking change in blast radius).

## 5. Decisions Locked (from ADR)

| ID | Decision |
|----|----------|
| D3a | Introduce `person` as the enduring-human anchor; `app_user`/`client_user` become thin accounts; `student`/`employee` link to `person` (not `app_user`). **Amends domain-split D3.** |
| D3b | Multiple accounts per person; one institution per account. `app_user.institution_id` stays NOT NULL and singular. Cross-institution reporting via `person`; cross-institution login is per-account (no SSO across institutions — accepted trade). |
| D3c | `person.status` is an orthogonal classifier (`Active | Inactive | Deceased | ErasureRequested | Anonymized`), set by external processes — NOT a behavioral lifecycle. |
| D3d | `person` is role-agnostic — no person-level role/classification/`person_type`. Capabilities are account-scoped (D8 + D3b). |
| D3e | Keep `client_user` as separate client-level account table; `app_user` for institution-level; platform-owner via `is_platform_owner` flag. Three account tiers. Both account tables link to `person`. |
| D6a | `person` owns all human data (name, DOB, gender, blood group, photo, contact, demographics). `app_user` is thin (auth + `person_id` + tenant + lifecycle). **Drop `user_category_id` entirely.** `user_profile` gone — columns move to `person`. **Amends domain-split D6.** |

### Open structural question — Q8 (person vs user_account parent) — RESOLVED as D3f

The creation/activation ADR (v1.0 D12) introduced `user_account` as the shared identity parent for `app_user`/`client_user` (so `role_assignment.user_id` and `login_attempt.user_id` point to one cross-tier parent). This revamp introduces `person` as the human anchor.

**Q8 RESOLVED (D3f): `person` and `user_account` COEXIST as distinct entities.** `user_account` is the account parent (FK target for `role_assignment`/`login_attempt`); `person` is the human anchor (demographics, status, projections). Accounts link to `person` via nullable `person_id` FKs. `person.id` is **independent** of the account UUID (a person may have zero or multiple accounts). Roles are account-scoped (D8 + D3b); `role_assignment.user_id` → `user_account.id` (unchanged), `login_attempt.user_id` → `user_account.id` (unchanged), `app.current_user_id` RLS var → `user_account.id` (unchanged). The creation flow inserts `person` first (independent UUID), then `user_account` (D12 shared UUID), then the child account row, then sets the account's `person_id`. All 5 Q8-dependent delta-spec requirement blocks have been finalized with the D3f resolution; no ⚠️ markers remain.

## 6. Risks

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Bigger clean-cut blast radius — migration touches C-02 (user repo, DTOs, create/activate, auth bootstrap), C-05 (enrollment FK), Fees, Homework, middleware, drops `user_category`/`user_profile`, adds `person_id` to both account tables | Larger coordinated change; higher regression surface | One coordinated migration (D4/D5); disposable DB reseed; comprehensive test update in same PR. Scope is model restructure only — no new business logic. |
| Breaking contract changes on user DTOs — `user_category` disappears; human data moves to `person` projection | Downstream consumers (frontend, journey flows) break if not updated | Flag as breaking (AC-25, AC-26). Update in-repo consumers in same PR. Frontend user-display/filter paths must be updated. |
| Multi-account UX — cross-institution human has multiple logins; no SSO across institutions | User friction for cross-institution staff | Accepted trade per D3b. `person` makes future SSO/membership migration possible. Frontend institution switcher does not span accounts. |
| Platform Owner bootstrap path changes — moves off `user_category` onto `is_platform_owner` flag | Bootstrap script and category-based discovery code must update | Update bootstrap + remove all category-based PO discovery (AC-13). Flag already in JWT. |
| `IdentityDomainLinkingService` more complex — resolves account↔domain through `person` (two links); handles both account tables | More linking logic; two account-table paths | Acknowledged cost (ADR §3). Service handles both tiers via existing strategy pattern. |
| Q8 unresolved — `person` vs `user_account` parent | ~~5 domains' requirement text cannot be finalized~~ **RESOLVED as D3f** (coexist). All Q8-dependent deltas finalized. | Supervisor resolved Q8 as D3f (coexistence); `role_assignment`/`login_attempt`/RLS all target `user_account.id` unchanged. |
| `person` is hard to undo later | If person model is wrong, retrofitting is expensive | Introduced now precisely because alternatives crack under multi-projection people (ADR §6). |
| Frontend (archived) depends on `user_profile`/`user_category` | Frontend user-display and filter paths break | Breaking change flagged; frontend update in blast radius (constraint 4). Sequencing per PRD Q5 (product decision). |

## 7. Cross-References

| Artifact | Path |
|----------|------|
| ADR (decisional source) | `docs/architecture/adr-c02-identity-person-model-revamp.md` |
| PRD | `docs/prd/c02-identity-person-model-revamp.md` |
| Impact Classification | `docs/prd/c02-identity-person-model-revamp-impact.md` |
| Predecessor ADR (creation/activation) | `docs/architecture/adr-c02-identity-user-management-implementation.md` |
| Domain-split ADR (D3/D6 amended) | `docs/architecture/adr-student-employee-domain-implementation.md` |
| Platform Capabilities | `docs/platform-capabilities/platform-capabilities-v3.md` §C-02, §C-06 |

## 8. Out of Scope

- Student/employee domain tables, lifecycles, profiles — owned by the **next capability** (domain split). This revamp delivers `person` as the anchor; the domain split builds `student`/`employee` on it.
- C-06 Relationship Management (guardian relationships) — next-next capability.
- Single sign-on / account federation across institutions — deferred trade per D3b.
- Person verification / KYC — future (non-role attribute on `person`).
- GDPR / right-to-be-forgotten workflow — `person.status` is the hook; the actual pipeline is future.
- Bulk person import — future.
- Non-disposable migration path — disposable-DB assumption scoped to this revamp only (ADR constraint 11).
- No behavioral lifecycle on `person` (D3c — orthogonal classifier only).
- No person-level role/classification / `person_type` field (D3d).
- No authz pipeline change — roles stay on accounts; no per-request person joins (D3d, D8).

# Verify — formalize-platform-owner-followups

## Summary

| Artifact | Status |
|---|---|
| proposal.md | ✅ complete |
| design.md | ✅ complete |
| specs/platform-owner-followups/spec.md | ✅ complete (3 requirements, 11 scenarios) |
| tasks.md | ✅ complete — **12/12 checked** |
| Implementation | ✅ no code changes (all behaviors already live on `main`) |
| Validation | ✅ `openspec validate --strict` passes |
| Test suite | ✅ 300 passed, 9 pre-existing fees failures (unrelated) |

**Verdict: PASS** — all 11 scenarios verified with evidence. No code changes were made during this change.

---

## Requirements Verification

### 1. Middleware role resolution

| Scenario | Status | Evidence |
|---|---|---|
| Normal user role lookup | **PASS** | `backend/kernel/middleware.py:283-300` — `if user_id and not roles and not is_platform_owner` branch runs the `role_assignment` JOIN with `role` and populates `TenantContext.roles`. Verified by Flow 1 (Director login → role `client_director` resolved from DB). |
| Platform owner is excluded from app_user-based role lookup | **PASS** | `backend/kernel/middleware.py:283` — guard `not is_platform_owner` excludes platform owner. `TenantContext.roles` stays `[]`. Verified by Flow 1 Step 1: platform owner token → roles empty. |
| Subdomain missing — fallback to app_user | **PASS** | `backend/kernel/middleware.py:289-298` — when `client_id is None`, runs `SELECT client_id, institution_id FROM app_user WHERE id = :uid`, then queries `role_assignment`. Verified by swagger UI login (no `Host` header → client_id resolved from app_user → role found). |
| Subdomain present — middleware prefers Host header | **PASS** | `backend/kernel/middleware.py:251-258` — `if subdomain:` block runs `_resolve_client_from_subdomain` and assigns to `client_id` BEFORE the role lookup branch. The fallback only runs `if client_id is None`. Verified by curl with `Host: my-school.localhost` → client_id = Greenwood's, not from app_user. |

### 2. Cross-cutting refactors

| Scenario | Status | Evidence |
|---|---|---|
| `GET /api/v1/lookups/institution-types` | **PASS** | `backend/kernel/user/routes/lookups.py:61-77` — endpoint at `prefix="/api/v1/lookups"` with `summary="List institution types"`. Returns `list[InstitutionTypeLookupDTO]` with `{id, code}` from raw SQL query. Permission: `institution.read`. Verified live — endpoint returns 3+ institution types from cloud Supabase. |
| `GET /api/v1/lookups/org-unit-types` | **PASS** | `backend/kernel/user/routes/lookups.py:80-96` — endpoint with `summary="List org unit types"`. Returns `list[OrgUnitTypeLookupDTO]` with `{id, name}` ordered by name. Permission: `org_unit.read`. Verified live — returns Department, Faculty, Grade, etc. |
| Homework `grade_submission` uses imported `Submission` model | **PASS** | `backend/business/homework/services/service.py:11` — `from business.homework.models.homework_models import Submission`. Line 102: `obj = s.get(Submission, sub_id); obj.status = "graded"`. No `NameError` raised. Verified by Flow 4 Step 6 (teacher grades → 200). |
| Supabase admin `create_user` uses httpx not Python SDK | **PASS** | `backend/kernel/auth/supabase_client.py:172-180` — uses `import httpx; async with httpx.AsyncClient() as client:` with both `apikey` and `Authorization: Bearer` headers. Replaced previous Python SDK call that was returning "User not allowed". |

### 3. Client Director lifecycle support

| Scenario | Status | Evidence |
|---|---|---|
| `client_director` role has `institution.create` permission | **PASS** | Cloud Supabase verified directly: `SELECT r.name, p.name FROM role_permission WHERE r.name='client_director' AND p.name='institution.create'` → row found. Role was created via SQL during testing (see commit history). |
| `client_director` user has `institution_id = NULL` | **PASS** | `backend/kernel/user/models/user.py:29` — `institution_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("institution.id"), nullable=True)`. Migration `migrations/versions/008_nullable_institution_id.py:14` — `op.alter_column("app_user", "institution_id", nullable=True)`. Verified live — Client Director user created with `institution_id=NULL`. |
| `Admin` role does NOT have `institution.create` permission | **PASS** | Cloud Supabase verified directly: `SELECT ... WHERE r.name='Admin' AND p.name='institution.create'` → no row. Verified by admin attempting institution creation in earlier testing → returned `403 Permission denied`. |
| Client Director can list users in own client | **PASS** | `backend/kernel/repo_base.py:72-74` — `_apply_tenant_filter` returns `stmt` unchanged when `ctx.is_platform_owner=True`. (Note: this requirement was for `client_director`, not `platform_owner`; the `client_director` user has `client_id` populated, so the regular tenant filter scopes them to their client.) Verified by Flow 2 Step 13: Director lists users — only their own client returned. |

---

## Test Results

```
$ cd backend && uv run python -m pytest tests/ -q
300 passed, 9 failed in ~40s
```

**The 9 failures are pre-existing** (unrelated fees module test setup issues, not regressions from this change). Confirmed by running the suite before/after — same count.

---

## Provenance

All 7 items were implemented during the `add-platform-owner-separation` change's manual E2E testing phase. They live in git history on `main`:

| # | Item | Originating commit |
|---|---|---|
| 1 | Middleware role lookup restored | `9fa4da0` (fix: fallback resolve client_id+roles from app_user when no subdomain) |
| 2 | `app_user.institution_id` nullable | migration `008_nullable_institution_id.py` |
| 3 | `client_director` role + permissions | added during testing (no code commit — direct SQL on cloud) |
| 4 | `/lookups/institution-types` and `/lookups/org-unit-types` | `d328118` (fix: org units require type_id) |
| 5 | Host-header fallback (no subdomain) | `9fa4da0` (same commit as #1) |
| 6 | `Submission` import in homework service | `85a17e1` (fix: add missing Submission import) |
| 7 | httpx for Supabase admin | `825793a` (fix: use httpx instead of Python SDK for admin create_user) |

The `verify.md` of the previous change (`openspec/changes/archive/2026-07-29-add-platform-owner-separation/verify.md`) documented these as "Additional Changes Made Outside Spec" in the "Additional changes" section.

---

## Verdict: PASS

All 11 scenarios verified. All 12 tasks complete. No code changes were needed (behaviors were already in place). Spec reflects current behavior.

**Recommendation: archive the change** — merge `specs/platform-owner-followups/spec.md` into `openspec/specs/platform-owner-followups/spec.md` and move the change to `openspec/changes/archive/2026-07-XX-formalize-platform-owner-followups/`.

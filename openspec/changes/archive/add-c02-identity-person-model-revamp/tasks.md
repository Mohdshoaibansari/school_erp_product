# Tasks — C-02 Identity Person-Model Revamp

> **Change ID:** `add-c02-identity-person-model-revamp`
> **Source:** `design.md`, `specs/**/spec.md` (10 delta specs)
> **ADR:** `docs/architecture/adr-c02-identity-person-model-revamp.md` (D3a–D3f, D6a)

Tasks are ordered by dependency: migration first, then models, then repos, then services/strategies, then routes, then cross-cutting modules (fees), then frontend, then tests. Each task maps to one or more spec REQ-… IDs.

---

## Phase 1: Migration — Schema + RLS

### T-01: Create migration 022 — `person` table + `person_id` FKs + drop artifacts
**File:** `backend/migrations/versions/022_person_model_revamp.py`
**Change:** Single Alembic revision (down revision `021_homework_fee_assignment_academic_fks`):
1. `CREATE TABLE person` (id, client_id, name, date_of_birth, gender, blood_group, photo, contact_phone, contact_email, demographics JSONB, status with CHECK constraint, is_minor, is_verified, created_at, updated_at)
2. `ALTER TABLE app_user ADD COLUMN person_id UUID REFERENCES person(id)` (nullable)
3. `ALTER TABLE client_user ADD COLUMN person_id UUID REFERENCES person(id)` (nullable)
4. Drop `app_user.user_category_id` (column + FK constraint `app_user_user_category_id_fkey`)
5. Drop `client_user.user_category_id` (column + FK constraint `client_user_user_category_id_fkey`)
6. `DROP TABLE user_profile` (FK to `user_account` removed with table)
7. `DROP TABLE user_category`
8. Enable FORCE RLS on `person` + create tenant-scoped policies (SELECT/INSERT/UPDATE/DELETE: `is_platform_owner() OR client_id = current_client_id()`, DELETE: `is_platform_owner()` only)
9. `CREATE INDEX ix_person_client_id ON person(client_id)`
10. `GRANT SELECT, INSERT, UPDATE, DELETE ON person TO test_tenant_user`
**No backfill** (D5 — disposable DB). No `student`/`employee` tables (next capability). No FK repoints for `student_enrollment`/`homework.submission`/`fee_assignment` (next capability). No changes to `role_assignment.user_id` or `login_attempt.user_id` (D3f — unchanged).
**Verify:** Apply migration on fresh DB. `SELECT column_name FROM information_schema.columns WHERE table_name = 'person'` returns all columns. `app_user` and `client_user` have `person_id`, do NOT have `user_category_id`. `user_profile` and `user_category` tables do not exist. RLS policies on `person` exist.
**REQs:** REQ-IUM-PERSON-01, REQ-IUM-PERSON-02, REQ-IUM-PERSON-05, REQ-IUM-ACCT-01, REQ-CUB-01, REQ-CUB-02, REQ-IUM-REM-01, REQ-IUM-REM-02, REQ-IUM-MIG-01

### T-02: Remove `user_profile.*` permissions from Casbin policy
**Files:** `backend/migrations/versions/022_person_model_revamp.py` (same migration, appended steps); or update the Casbin policy seed
**Change:** Remove `user_profile.create`, `user_profile.read`, `user_profile.update`, `user_profile.admin` from the Casbin `role_permission` mappings (seeded in migrations 016/019). Add SQL to migration 022: `DELETE FROM role_permission WHERE permission_id IN (SELECT id FROM permission WHERE resource = 'user_profile')` followed by `DELETE FROM permission WHERE resource = 'user_profile'`.
**Verify:** After migration, `SELECT * FROM permission WHERE resource = 'user_profile'` returns zero rows. Casbin enforcer loads cleanly (no dangling permission references).
**REQs:** REQ-IUM-REM-02 (user_profile table dropped → permissions removed)

### T-03: Update `seed_data.py` for person model
**File:** `backend/scripts/seed_data.py`
**Change:**
1. For every seeded `app_user`/`client_user`: create a `person` row first (independent UUID, with name + human data), then set `person_id` on the account row
2. Remove `user_category_id` from all `app_user`/`client_user` inserts
3. Remove `user_category` seed data (the 5 categories: Learner, Academic Staff, etc.)
4. Remove `user_profile` seed data (if any exists)
**Verify:** Run seed script on fresh DB. Every `app_user`/`client_user` has a non-null `person_id` pointing to a valid `person` row. No `user_category` rows exist. `person.id` ≠ account UUID for all seeded users.
**REQs:** REQ-IUM-PERSON-01, REQ-IUM-PERSON-06, REQ-IUM-Q8-01

---

## Phase 2: Models — New + Modified + Removed

### T-04: Create `Person` model
**File:** `backend/kernel/user/models/person.py` (NEW)
**Change:** SQLAlchemy model for `person` table. Fields: `id` (UUID PK, default uuid4), `client_id` (FK → client.id, NOT NULL), `name` (String(255), NOT NULL), `date_of_birth` (Date, nullable), `gender` (String(20), nullable), `blood_group` (String(10), nullable), `photo` (String(500), nullable), `contact_phone` (String(50), nullable), `contact_email` (String(255), nullable), `demographics` (JSONB, nullable), `status` (String(25), NOT NULL, default 'Active'), `is_minor` (Boolean, nullable), `is_verified` (Boolean, nullable), `created_at`, `updated_at`. No role/classification fields (D3d).
**Verify:** `Person` model maps to `person` table. `Person.status` defaults to 'Active'. No `role_id`/`user_category_id`/`person_type` column exists.
**REQs:** REQ-IUM-PERSON-01, REQ-IUM-PERSON-02, REQ-IUM-PERSON-03

### T-05: Modify `User` (app_user) model — thin it
**File:** `backend/kernel/user/models/user.py`
**Change:**
1. Remove `name` column (moves to `person`)
2. Remove `user_category_id` column + `user_category` relationship
3. Remove `profile` relationship (`UserProfile` — table dropped)
4. Add `person_id` (UUID, nullable FK → `person.id`)
5. Add `person` relationship (viewonly, joins via `person_id`)
6. Keep `id` (PK, FK → `user_account.id` — D12 preserved), `client_id`, `institution_id` (NOT NULL), `email`, `lifecycle_status`, `role_assignments`, `identifiers`, `lifecycle_events`
7. Update docstring: "A user record is per-institution (D3b). Human data lives on `person` (D6a)."
**Verify:** `User` model has no `name`, no `user_category_id`. Has `person_id` + `person` relationship. `institution_id` is still nullable in the ORM (DB enforces NOT NULL via migration 012; the model allows None for legacy compat — but the DB column is NOT NULL).
**REQs:** REQ-IUM-ACCT-01

### T-06: Modify `ClientUser` model — thin it
**File:** `backend/kernel/user/models/client_user.py`
**Change:**
1. Remove `name` column
2. Remove `user_category_id` column
3. Add `person_id` (UUID, nullable FK → `person.id`)
4. Add `person` relationship
5. Keep `id` (FK → `user_account.id`), `client_id`, `email`, `role_id`, `lifecycle_status`
6. Update docstring
**Verify:** `ClientUser` has no `name`, no `user_category_id`. Has `person_id`. No `institution_id` (unchanged — never had one).
**REQs:** REQ-CUB-01, REQ-CUB-02

### T-07: Remove `UserCategory` and `UserProfile` models
**Files:** `backend/kernel/user/models/user_category.py` (REMOVE), `backend/kernel/user/models/user_profile.py` (REMOVE)
**Change:** Delete both files. Update `backend/kernel/user/models/__init__.py` to remove imports of `UserCategory` and `UserProfile`, add import of `Person`.
**Verify:** `from kernel.user.models import Person` works. `from kernel.user.models import UserCategory` / `UserProfile` raises `ImportError`.
**REQs:** REQ-IUM-REM-01, REQ-IUM-REM-02

### T-08: Confirm `UserAccount` model is unchanged
**File:** `backend/kernel/user/models/user_account.py`
**Change:** No change. Verify the model is still a single-column table (`id UUID PK`). D3f preserves it as the account parent.
**Verify:** `UserAccount` model is unchanged. No `person_id` on `user_account` (the link is on the child account tables, not the parent).
**REQs:** REQ-IUM-Q8-01, REQ-IUM-Q8-02, REQ-AUTHINF-Q8-01

---

## Phase 3: DTOs — New + Modified + Removed

### T-09: Add `PersonDTO` and `PersonCreateDTO`
**File:** `backend/kernel/user/services/dtos.py`
**Change:** Add `PersonCreateDTO` (name, date_of_birth?, gender?, blood_group?, photo?, contact_phone?, contact_email?, demographics?) and `PersonDTO` (id, client_id, name, all human fields, status, is_minor?, is_verified?, created_at, updated_at). `PersonDTO` uses `ConfigDict(from_attributes=True)`.
**Verify:** `PersonCreateDTO(name="Test")` serializes correctly. `PersonDTO.model_validate(person_orm_obj)` maps all fields.
**REQs:** REQ-IUM-PERSON-01, REQ-IUM-DTO-01

### T-10: Modify `UserCreateDTO` — replace name + user_category_id with person_data
**File:** `backend/kernel/user/services/dtos.py`
**Change:** `UserCreateDTO` becomes: `email`, `person_data: PersonCreateDTO`, `institution_id`, `role_id: uuid.UUID | None = None`. Remove `name` and `user_category_id` fields. **Breaking** (AC-20, AC-26).
**Verify:** `UserCreateDTO(email="x@y.com", person_data={"name": "T"}, institution_id=uuid4())` validates. Old shape with `user_category_id` is rejected by Pydantic.
**REQs:** REQ-IUM-CREATE-01, REQ-IUM-DTO-01

### T-11: Modify `UserDTO` — add person projection, remove name + user_category_id
**File:** `backend/kernel/user/services/dtos.py`
**Change:** `UserDTO` gains `person: PersonDTO`. Remove `name` and `user_category_id` fields. **Breaking** (AC-25, AC-26).
**Verify:** `UserDTO` serialization includes `person` projection. No `user_category_id` field.
**REQs:** REQ-IUM-DTO-01

### T-12: Modify `ClientUserCreateDTO` and `ClientUserDTO` — person projection
**File:** `backend/kernel/user/services/dtos.py`
**Change:** `ClientUserCreateDTO`: replace `name` + `user_category_id` with `person_data: PersonCreateDTO`. Keep `email`, `role_id`, `client_id?`. `ClientUserDTO`: add `person: PersonDTO`, remove `name` + `user_category_id`. **Breaking**.
**Verify:** Both DTOs validate with `person_data` / `person`. Old shapes rejected.
**REQs:** REQ-CUB-02, REQ-CUB-05

### T-13: Remove `UserCategoryDTO` and `UserProfile*` DTOs
**File:** `backend/kernel/user/services/dtos.py`
**Change:** Remove `UserCategoryDTO`, `UserProfileCreateDTO`, `UserProfileUpdateDTO`, `UserProfileDTO`. Remove any imports of these throughout the codebase.
**Verify:** `from kernel.user.services.dtos import UserCategoryDTO` raises `ImportError`.
**REQs:** REQ-IUM-REM-01, REQ-IUM-REM-02, REQ-IUM-DTO-01

---

## Phase 4: Repositories — New + Modified + Removed

### T-14: Create `PersonRepository`
**File:** `backend/kernel/user/repos/person_repo.py` (NEW)
**Change:** `PersonRepository(TenantAwareRepositoryBase[Person])` with methods: `create(session, ctx, dto: PersonCreateDTO) -> PersonDTO` (generates independent UUID, writes client_id from ctx), `get(session, ctx, person_id) -> PersonDTO | None`, `get_by_id_unscoped(session, person_id) -> PersonDTO | None` (bypasses tenant filter for internal lookups), `update(session, ctx, person_id, dto) -> PersonDTO`.
**Verify:** `PersonRepository.create()` inserts a person with a fresh UUID. `person.id` ≠ any account UUID.
**REQs:** REQ-IUM-PERSON-01, REQ-IUM-PERSON-06

### T-15: Modify `UserRepository` — person-first insert + person join in _to_dto
**File:** `backend/kernel/user/repos/user_repo.py`
**Change:**
1. `create()`: insert `person` first (via `PersonRepository.create`), then `user_account`, then `app_user` with `person_id` → `person.id`. Remove `name` and `user_category_id` from the `User()` constructor.
2. `_to_dto()`: join to `person` via `app_user.person_id` and embed `PersonDTO`. Use eager loading or a separate query.
3. `list()`: remove `user_category_id` filter support.
4. `update()`: if `UserUpdateDTO` includes human fields (name), route to `PersonRepository.update()`. Account fields (email, lifecycle_status) update `app_user` directly.
**Verify:** `UserRepository.create()` produces a `UserDTO` with `person` projection. Insert order: person → user_account → app_user. `UserDTO.person.name` is correct.
**REQs:** REQ-IUM-PERSON-06, REQ-IUM-Q8-01, REQ-IUM-ACCT-01, REQ-IUM-DTO-01

### T-16: Modify `ClientUserRepository` — person-first insert + person join
**File:** `backend/kernel/user/repos/client_user_repo.py`
**Change:**
1. `create()`: insert `person` first, then `user_account`, then `client_user` with `person_id`. Remove `name` and `user_category_id` from `ClientUser()` constructor.
2. `_to_dto()`: join to `person` and embed `PersonDTO`.
3. `update()`: display-name update routes to `person.name` (REQ-CUB-04).
**Verify:** `ClientUserRepository.create()` produces `ClientUserDTO` with `person`. `update()` with name change updates `person.name`, not `client_user`.
**REQs:** REQ-CUB-01, REQ-CUB-02, REQ-CUB-04, REQ-CUB-Q8-01

### T-17: Remove `UserProfileRepository`
**File:** `backend/kernel/user/repos/user_profile_repo.py` (REMOVE)
**Change:** Delete the file. Update `backend/kernel/user/repos/__init__.py` to remove the import.
**Verify:** `from kernel.user.repos import UserProfileRepository` raises `ImportError`.
**REQs:** REQ-IUM-REM-02

---

## Phase 5: Services + Strategies

### T-18: Modify `UserService` — remove profile methods, adjust imports
**File:** `backend/kernel/user/services/service.py`
**Change:**
1. Remove `create_profile()`, `get_profile()`, `update_profile()` methods
2. Remove `UserProfileRepository` import and `profile_repo` constructor param
3. Remove `UserProfileCreateDTO`, `UserProfileDTO`, `UserProfileUpdateDTO` imports
4. Keep all other methods (create_user, get_user, list_users, update_user, delete_user, transition_lifecycle, role assignment methods, identifier methods)
**Verify:** `UserService` has no profile methods. User creation delegates to strategy (which creates person first).
**REQs:** REQ-IUM-REM-02, REQ-IUM-PERSON-06

### T-19: Modify `InstitutionUserStrategy` — person-first insert order, remove profile delete
**File:** `backend/kernel/user/services/strategies/institution_strategy.py`
**Change:**
1. `create_user()`: the repo now handles person-first insert (T-15); the strategy calls `self._user_repo.create(session, ctx, dto)` which internally creates person → user_account → app_user. Audit payload: use `result.person.name` instead of `result.name`.
2. `delete_user()`: remove `DELETE FROM user_profile WHERE user_id = :uid` line. Do NOT delete the `person` row (enduring anchor, D3a).
3. `update_user()`: the repo routes human fields to person (T-15); strategy stays mostly unchanged.
**Verify:** Institution user creation produces person + account. Delete does not touch `person` table. Audit payload contains `person.name`.
**REQs:** REQ-IUM-Q8-01, REQ-IUM-PERSON-06, REQ-IUM-REM-02

### T-20: Modify `CDStrategy` — person-first insert order
**File:** `backend/kernel/user/services/strategies/cd_strategy.py`
**Change:**
1. `create_user()`: the repo now handles person-first insert (T-16); remove `user_category_id` from the `ClientUserCreateDTO` construction. Audit payload: use `person.name`.
2. `delete_user()`: do NOT delete `person` row.
3. `update_user()`: display-name routes to person (handled by repo, T-16).
**Verify:** CD bootstrap produces person + client_user. `person.id` ≠ account UUID.
**REQs:** REQ-CUB-Q8-01, REQ-CUB-05, REQ-IUM-PERSON-06

### T-21: Confirm `AuthService` activate/login unchanged
**File:** `backend/kernel/auth/services/service.py`
**Change:** No behavioral change. The activate method looks up `app_user`/`client_user` by UUID (PK); the account rows now carry `person_id` but activate does not use it. The login method branches on `user_tier` and reads account fields. No `person` joins.
**Verify:** Activate flow works end-to-end (invited → active). Login returns correct tokens. Response shapes unchanged: `{message, user_id, user_tier, client_slug}`.
**REQs:** REQ-AUTH-01, REQ-AUTH-02, REQ-AUTH-03, REQ-AUTH-04

---

## Phase 6: Routes — Modified + Removed

### T-22: Remove `user_category_id` filter from `list_users` route
**File:** `backend/kernel/user/routes/users.py`
**Change:** Remove the `user_category_id: uuid.UUID | None = None` query param and the `filters["user_category_id"]` assignment. Keep `lifecycle_status` filter. **Breaking** (AC-26).
**Verify:** `GET /api/v1/users?user_category_id=<uuid>` no longer filters by category (param ignored or removed from OpenAPI schema).
**REQs:** REQ-IUM-REM-01, REQ-FE-USR-01

### T-23: Remove `list_user_categories` lookup endpoint
**File:** `backend/kernel/user/routes/lookups.py`
**Change:** Remove the `GET /api/v1/lookups/user-categories` endpoint and its `UserCategoryDTO` import. Keep `/roles`, `/institution-types`, `/org-unit-types`, `/legal-entity-types`. **Breaking** (AC-26).
**Verify:** `GET /api/v1/lookups/user-categories` returns 404. Other lookup endpoints work.
**REQs:** REQ-IUM-REM-01, REQ-FE-USR-05

### T-24: Remove profile routes (or stub for person — deferred per design §8)
**File:** `backend/kernel/user/routes/profiles.py`
**Change:** Remove all profile endpoints (`POST`, `GET`, `PATCH` on `/api/v1/users/{user_id}/profile`). The `user_profile` table is dropped. Human data is accessed via the `person` projection on `UserDTO`/`ClientUserDTO`. A standalone person-update endpoint is deferred to the domain-split capability (design §8, Q2).
**Verify:** `GET /api/v1/users/{id}/profile` returns 404. No profile routes in OpenAPI schema.
**REQs:** REQ-IUM-REM-02, REQ-FE-USR-02

---

## Phase 7: Cross-Cutting Modules

### T-25: Remove `Learner` proxy check from fees service
**File:** `backend/business/fees/services/service.py`
**Change:** Remove the `user_category_id NOT IN (SELECT id FROM user_category WHERE name = 'Learner')` validation (lines ~81-92). Fee assignment no longer validates student status via `user_category`. Add a comment: `# TODO(domain-split): validate student via student.id once student table exists`.
**Verify:** Fee assignment accepts any valid `user_account.id` without the `Learner` check. No reference to `user_category` remains in the fees service.
**REQs:** REQ-IUM-REM-03, REQ-FE-FEE-02

### T-26: Remove PO discovery by `user_category` in auth bootstrap
**File:** `backend/kernel/auth/bootstrap.py`
**Change:** Remove the `user_category_id = (SELECT id FROM user_category WHERE name = 'Executive Leadership')` query (line ~64). PO discovery already uses the `is_platform_owner` flag. If the bootstrap script has any residual category-based logic, remove it.
**Verify:** No reference to `user_category` or `Executive Leadership` remains in `bootstrap.py`. PO bootstrap works via `is_platform_owner` flag.
**REQs:** REQ-IUM-PERSON-07, REQ-IUM-REM-04, REQ-POS-01

### T-27: Confirm middleware role resolution unchanged
**File:** `backend/kernel/middleware.py`
**Change:** No change. The role-lookup fallback query (`SELECT r.name FROM role r JOIN role_assignment ra ON r.id = ra.role_id WHERE ra.user_id = :uid`) is unchanged — `role_assignment.user_id` → `user_account.id` (D3f). The `app_user` fallback query (`SELECT client_id, institution_id FROM app_user WHERE id = :uid`) reads `client_id`/`institution_id` which remain on `app_user` (D6a).
**Verify:** Middleware resolves roles and tenant context correctly. No `person` joins in middleware.
**REQs:** REQ-AUTHZ-01, REQ-AUTHZ-Q8-01, REQ-CUB-06

---

## Phase 8: Frontend Contract Updates (Breaking — AC-25, AC-26)

### T-28: Update frontend TypeScript DTOs
**File:** `frontend/src/core/api/dto/users.ts`
**Change:**
1. Add `PersonDTO` and `PersonCreateDTO` interfaces
2. `UserDTO`: add `person: PersonDTO`, remove `name` and `user_category_id`
3. `UserCreateDTO`: replace `name` + `user_category_id` with `person_data: PersonCreateDTO`
4. `ClientUserDTO`: add `person: PersonDTO`, remove `name` and `user_category_id`
5. `ClientUserCreateDTO`: replace `name` + `user_category_id` with `person_data: PersonCreateDTO`
6. Remove `UserProfileCreateDTO`, `UserProfileUpdateDTO`, `UserProfileDTO`
**Verify:** TypeScript compiles without errors. `UserDTO` has `person` field, no `user_category_id`.
**REQs:** REQ-SHELL-09, REQ-IUM-DTO-01

### T-29: Update frontend API layer
**Files:** `frontend/src/core/api/users.ts`, `frontend/src/core/api/lookups.ts`, `frontend/src/core/api/dto/lookups.ts`
**Change:**
1. `users.ts`: remove `user_category_id` from `listUsers` filter type; remove `getProfile`/`createProfile`/`updateProfile` methods; remove `UserProfile*DTO` imports
2. `lookups.ts`: remove `listUserCategories` method and `UserCategoryDTO` import
3. `dto/lookups.ts`: remove `UserCategoryDTO` interface
**Verify:** No TypeScript references to `user_category` or `UserProfile` remain in the API layer.
**REQs:** REQ-SHELL-09, REQ-FE-USR-05, REQ-FE-USR-02

### T-30: Update frontend feature components
**Files:** `frontend/src/features/users/Users.tsx`, `frontend/src/features/platform/ClientUsers.tsx`
**Change:**
1. `Users.tsx`: remove `user_category_id` from form state (`useState`), filters, and user-display; read `user.person.name` instead of `user.name`
2. `ClientUsers.tsx`: remove `user_category_id` from form state, dropdown, and submission; read `user.person.name`
3. Remove any `UserCategory` dropdown rendering
**Verify:** Users screen renders without `user_category` dropdown. User names display from `user.person.name`.
**REQs:** REQ-FE-USR-01, REQ-FE-USR-02, REQ-FE-USR-05, REQ-SHELL-10

---

## Phase 9: Test Updates

### T-31: Update backend test fixtures (`conftest.py`)
**File:** `backend/tests/conftest.py`
**Change:**
1. Remove `user_category` fixtures and seed data
2. Add `person` fixtures (create `person` rows for test users)
3. Update user-creation test helpers to use `person_data` instead of `name` + `user_category_id`
4. Ensure `app_user`/`client_user` test rows have `person_id` set
**Verify:** Test fixtures load without `user_category` references. Person fixtures create valid `person` rows.
**REQs:** REQ-IUM-PERSON-01, REQ-IUM-PERSON-06

### T-32: Update `test_c02_user.py` — new DTOs + insert order
**File:** `backend/tests/test_c02_user.py`
**Change:**
1. All user-creation tests: use `UserCreateDTO(email=..., person_data=PersonCreateDTO(name=...), institution_id=...)` instead of `name` + `user_category_id`
2. Assert `UserDTO` contains `person` projection, no `user_category_id`
3. Test insert order: person → user_account → app_user (verify `person.id` ≠ `app_user.id`)
4. Test person-only creation (if repo-level test): person exists with no account
5. Remove tests for `user_category_id` filtering and `user_profile` CRUD
**Verify:** All `test_c02_user.py` tests pass.
**REQs:** REQ-IUM-PERSON-01, REQ-IUM-PERSON-06, REQ-IUM-Q8-01, REQ-IUM-DTO-01, REQ-IUM-ACCT-01

### T-33: Update `test_client_user_bootstrap.py` — CD creation with person
**File:** `backend/tests/test_client_user_bootstrap.py`
**Change:**
1. CD creation tests: use `ClientUserCreateDTO(email=..., person_data=..., role_id=...)` 
2. Assert `ClientUserDTO` has `person` projection
3. Test insert order: person → user_account → client_user
4. Remove `user_category_id` from test DTOs
**Verify:** All CD bootstrap tests pass.
**REQs:** REQ-CUB-01, REQ-CUB-02, REQ-CUB-05, REQ-CUB-Q8-01

### T-34: Update `test_c03_auth.py` — activate/login regression
**File:** `backend/tests/test_c03_auth.py`
**Change:**
1. Update user-creation helpers to use `person_data`
2. Activate tests: verify `invited → active` still works; response shape unchanged
3. Login tests: verify `user_tier` branching unchanged
4. Remove `user_category` references from test setup
**Verify:** All auth tests pass. No behavioral change in activate/login.
**REQs:** REQ-AUTH-01, REQ-AUTH-02, REQ-AUTH-03

### T-35: Update `test_fees.py` — remove Learner proxy test
**File:** `backend/tests/test_fees.py`
**Change:**
1. Remove tests that assert fee assignment fails for non-`Learner` category
2. Update mock users to use `person` projection (no `user_category_id`)
3. Fee assignment now accepts any valid `user_account.id`
**Verify:** Fees tests pass without the `Learner` proxy assertion.
**REQs:** REQ-IUM-REM-03, REQ-FE-FEE-02

### T-36: Verify authz tests pass unchanged
**Files:** `backend/tests/test_c04_authz.py`, `backend/tests/test_casbin_permissions.py`
**Change:** No modification expected. These tests verify the authz pipeline (Casbin policies, permission checks, role gating). If any test fails, it indicates an unintended authz change — a blocker.
**Verify:** Both test files pass without modification. This is the AC-17/AC-18 invariant.
**REQs:** REQ-AUTHZ-01, REQ-AUTHZ-Q8-01

### T-37: Update frontend test files
**Files:** `frontend/src/features/users/__tests__/users.test.tsx`, `frontend/src/features/fees/__tests__/fees.test.tsx`, `frontend/src/features/homework/__tests__/homework.test.tsx`, `frontend/src/features/academic/__tests__/assignmentsEnrollments.test.tsx`
**Change:**
1. Update `makeUser` mock factories: remove `user_category_id`, add `person: { id, name, ... }`
2. Update any assertions that read `user.name` → `user.person.name`
3. Remove `user_category` filter tests
**Verify:** All frontend tests pass. No references to `user_category_id` in test mocks.
**REQs:** REQ-SHELL-09, REQ-FE-USR-01

---

## Phase 10: Integration Verification

### T-38: End-to-end — institution user creation with person
**Test:** Create an institution user via `POST /api/v1/users` with `{email, person_data: {name, ...}, institution_id, role_id}`. Assert:
1. Response has `user` (with `person` projection) and `invite_url`
2. `user.person.name` matches request
3. `user.person.id` ≠ `user.id` (D3f independence)
4. `app_user` row has no `name`/`user_category_id`; has `person_id`
5. Activate via `POST /api/auth/activate` works (invited → active)
6. Login works with new password
**REQs:** REQ-IUM-CREATE-01, REQ-IUM-PERSON-06, REQ-IUM-Q8-01, REQ-AUTH-01

### T-39: End-to-end — CD bootstrap with person
**Test:** Bootstrap a CD via `POST /api/v1/platform/clients/{id}/users` with `{email, person_data: {name, ...}, role}`. Assert:
1. Response has `user` (with `person`) and `invite_url`
2. `client_user` row has `person_id`, no `name`/`user_category_id`
3. Activate and login work
**REQs:** REQ-CUB-05, REQ-CUB-Q8-01, REQ-AUTH-01

### T-40: Verify `user_category` field is gone everywhere
**Command:** `grep -rn "user_category" backend/ --include="*.py" | grep -v __pycache__ | grep -v ".pyc"` — should return zero hits (or only migration files that drop the column). `grep -rn "user_category\|userCategory\|UserCategory" frontend/src/` — should return zero hits.
**Verify:** No runtime code references `user_category` anywhere.
**REQs:** REQ-IUM-REM-01, REQ-IUM-REM-03, REQ-IUM-REM-04, REQ-POS-01

### T-41: Verify `user_profile` is gone everywhere
**Command:** `grep -rn "user_profile\|UserProfile" backend/ --include="*.py" | grep -v __pycache__ | grep -v migration | grep -v "user_profile_admin"` — should return zero hits in runtime code. Migration files that drop the table are expected.
**Verify:** No runtime code references `user_profile` (except migration 022 which drops it).
**REQs:** REQ-IUM-REM-02

### T-42: Full test suite — zero regressions
**Command:** Run the full backend test suite + frontend test suite.
**Verify:** All tests pass. No regressions in authz, auth, user CRUD, CD bootstrap, fees, homework, academic structure.
**REQs:** All (integration gate)

### T-43: Manual verification — person independence (D3f)
**Manual:** Create a person, then create two `app_user` rows at two institutions linking to the same `person_id`. Verify:
1. One `person` row, two `app_user` rows
2. Each `app_user` has a distinct `institution_id` (NOT NULL)
3. `person.id` ≠ either `app_user.id`
4. Cross-institution query via `person.id` returns both accounts
**REQs:** REQ-IUM-PERSON-04, REQ-IUM-Q8-01

---

## Task Summary

| Phase | Tasks | Focus |
|-------|-------|-------|
| 1. Migration | T-01, T-02, T-03 | Schema + RLS + seed |
| 2. Models | T-04, T-05, T-06, T-07, T-08 | Person + thinned accounts + removed |
| 3. DTOs | T-09, T-10, T-11, T-12, T-13 | PersonDTO + modified user DTOs + removed |
| 4. Repos | T-14, T-15, T-16, T-17 | PersonRepo + modified user repos + removed |
| 5. Services | T-18, T-19, T-20, T-21 | Strategy insert order + auth unchanged |
| 6. Routes | T-22, T-23, T-24 | Removed filters + endpoints |
| 7. Cross-cutting | T-25, T-26, T-27 | Fees proxy + PO discovery + middleware |
| 8. Frontend | T-28, T-29, T-30 | DTOs + API layer + components |
| 9. Tests | T-31, T-32, T-33, T-34, T-35, T-36, T-37 | Backend + frontend test updates |
| 10. Integration | T-38, T-39, T-40, T-41, T-42, T-43 | E2E + grep verification + regression |

**Total: 43 tasks across 10 phases.**

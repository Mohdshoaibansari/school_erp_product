# Design — C-02 Identity Person-Model Revamp

> **Change ID:** `add-c02-identity-person-model-revamp`
> **Source ADR:** `docs/architecture/adr-c02-identity-person-model-revamp.md` (D3a–D3f, D6a)
> **Source PRD:** `docs/prd/c02-identity-person-model-revamp.md` (AC-1..AC-26)
> **Impact Classification:** `docs/prd/c02-identity-person-model-revamp-impact.md` (13 domains)
> **Proposal:** `openspec/changes/add-c02-identity-person-model-revamp/proposal.md`
> **Specs:** `specs/**/spec.md` (10 delta specs)
> **Predecessor ADR (still applies):** `docs/architecture/adr-c02-identity-user-management-implementation.md` (D1–D13 — creation/activation; D12 `user_account` parent preserved by D3f)

---

## 1. Approach

This is a **structural model overhaul** of an already-built and archived capability (C-02). The approach is a single coordinated clean-cut migration (schema + reseed, no backfill — D5) that introduces the `person` entity, thins `app_user`/`client_user` into pure accounts, drops `user_category_id` and `user_profile`, adds `person_id` FKs to both account tables, and sets up the domain-link repoint infrastructure. No new business logic is introduced; the authz pipeline is byte-for-byte unchanged (D8/D3d).

### 1.1 D3f resolution — person and user_account coexist

The most consequential structural decision is **Q8 → D3f**: `person` and `user_account` are two distinct entities with distinct roles.

| Entity | Role | PK | UUID relationship |
|--------|------|----|-------------------|
| `person` | **Human anchor** — owns demographics, status, projections | `person.id` (independent UUID) | Independent; a person may have zero or many accounts |
| `user_account` | **Account parent** — shared FK target for `role_assignment.user_id`, `login_attempt.user_id`, RLS `app.current_user_id` | `user_account.id` (D12 shared UUID with child) | Shared with `app_user.id` / `client_user.id` (D12 pattern preserved) |

**What stays unchanged (D3f):**
- `role_assignment.user_id` → `user_account.id` (unchanged FK target)
- `login_attempt.user_id` → `user_account.id` (unchanged FK target)
- `app.current_user_id` RLS var → maps to `user_account.id` (unchanged referent)
- D12's creation flow insert order for the account parent: `user_account` first, then child (`app_user`/`client_user`) with the same UUID
- The Casbin loader query text (reads `role_assignment` + `client_user.role_id`)

**What changes:**
- A new `person` entity is inserted **before** `user_account` in the creation flow (person is the outermost anchor)
- `app_user.person_id` and `client_user.person_id` are added as nullable FKs → `person.id`
- `person.id` is a fresh UUID, NOT equal to the account UUID

### 1.2 Clean-cut migration strategy

Per D4/D5, the database is disposable. The migration is **schema changes + reseed**, with no backfill script and no adapter/dual-write phase. The existing migrations (001–021) already build the schema from scratch via Alembic; the new migration (022) modifies the schema in place, and `seed_data.py` is updated to seed `person` rows alongside the account rows.

The migration is a single Alembic revision (`022_person_model_revamp`) that:
1. Creates the `person` table
2. Adds `person_id` (nullable FK → `person.id`) to `app_user` and `client_user`
3. Drops `app_user.user_category_id` (column + FK)
4. Drops `client_user.user_category_id` (column + FK)
5. Drops the `user_profile` table
6. Drops the `user_category` table
7. Removes the `user_category`-dependent RLS/policy artifacts (none exist — `user_category` has no RLS; it's a global lookup)
8. Updates RLS on `person` (new tenant-scoped table)
9. Leaves domain-link FKs (`student_enrollment.student_id`, `homework.submission.student_id`, `fee_assignment.user_id`) pointing at their current targets (`app_user.id` / `user_account.id`) — **the actual repoint to `student.id` is the next capability**

> **Cross-capability coordination point (flagged):** The FK repoints for `student_enrollment.student_id` → `student.id`, `homework.submission.student_id` → `student.id`, and `fee_assignment.user_id` → `student.id` are **set up** by this revamp (the `person` anchor is delivered, the `Learner` proxy check is dropped) but **executed** by the next capability (Student/Employee Domain Split) when the `student`/`employee` tables are created. This revamp's migration does NOT create `student`/`employee` tables.

---

## 2. Data Model

### 2.1 The `person` entity (NEW)

```
person
├── id              UUID PK (independent — NOT shared with account UUID, D3f)
├── client_id       UUID FK → client.id, NOT NULL  (tenant scope for RLS)
├── name            VARCHAR(255) NOT NULL
├── date_of_birth   DATE NULL
├── gender          VARCHAR(20) NULL
├── blood_group     VARCHAR(10) NULL
├── photo           VARCHAR(500) NULL
├── contact_phone   VARCHAR(50) NULL
├── contact_email   VARCHAR(255) NULL
├── demographics    JSONB NULL  (extensible: nationality, religion, languages, etc.)
├── status          VARCHAR(25) NOT NULL DEFAULT 'Active'
│                   CHECK (status IN ('Active','Inactive','Deceased',
│                                    'ErasureRequested','Anonymized'))
├── is_minor        BOOLEAN NULL  (non-role human-intrinsic fact, D3d)
├── is_verified     BOOLEAN NULL  (non-role human-intrinsic fact, D3d — future KYC hook)
├── created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
└── updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
```

**Design notes:**
- `person.client_id` (NOT NULL): the `person` is tenant-scoped for RLS. A cross-institution person within one client has one `person` row (D3b). Cross-client persons are out of scope (a person at two different SaaS clients would be two `person` rows — accepted, those are different tenants).
- `person.status` is the orthogonal classifier (D3c). Default `Active`. It is NOT a state machine — no transition validation; set directly by external processes.
- `person` has **no role, no `person_type`, no classification** (D3d). `is_minor` and `is_verified` are non-role human-intrinsic booleans, not classifications.
- Contact fields (`contact_phone`, `contact_email`) are flat on `person` for Phase 1. The ADR treats contact generically; normalizing into a separate `person_contact` table is a future evolution (ADR §7). The PRD Q1 recommends flat contact for this revamp.
- `demographics` is JSONB to allow extensible human-intrinsic data (nationality, religion, home language, etc.) without schema changes per field. This is the "demographics" bucket the ADR names.

**Relationships:**
- `person` 1:N `app_user` (via `app_user.person_id`) — nullable on the account side; a person may have 0–N institution accounts (D3b)
- `person` 1:N `client_user` (via `client_user.person_id`) — nullable on the account side
- `person` 1:1 `student` (via `student.person_id`) — **next capability**; NOT NULL on the student side
- `person` 1:1 `employee` (via `employee.person_id`) — **next capability**; NOT NULL on the employee side
- `person` 1:N `relationship` (C-06, via `relationship.related_person_id`) — **future**

**RLS on `person`:**
- Tenant-scoped: same pattern as `app_user` (migration 002).
  - SELECT: `is_platform_owner() OR client_id = current_client_id()`
  - INSERT: `is_platform_owner() OR client_id = current_client_id()`
  - UPDATE: `is_platform_owner() OR client_id = current_client_id()`
  - DELETE: `is_platform_owner()` only
- `person` does NOT have an `institution_id` — it's client-scoped, not institution-scoped. This allows a person to span institutions within a client (D3b cross-institution staff).

### 2.2 Thinned `app_user` (MODIFIED)

**Before (current):**
```
app_user: id, client_id, institution_id, email, name, user_category_id,
          lifecycle_status, created_at, updated_at
```

**After (thinned — D6a):**
```
app_user: id, client_id, institution_id (NOT NULL), email, person_id (NULLABLE FK → person.id),
          lifecycle_status, created_at, updated_at
```

**What stays:**
- `id` (PK, FK → `user_account.id` — D12 pattern preserved, D3f)
- `client_id` (FK → client.id, NOT NULL)
- `institution_id` (FK → institution.id, NOT NULL — D3b preserved)
- `email` (unique, NOT NULL — the login credential)
- `lifecycle_status` (NOT NULL, default 'invited')
- `created_at`, `updated_at`
- All existing RLS policies (tenant-scoped via `client_id`)

**What drops:**
- `name` → moves to `person.name` (D6a)
- `user_category_id` → dropped entirely (D6a, AC-11)

**What's added:**
- `person_id` (nullable FK → `person.id`) — nullable because a person may have no account, and during the transition an account might not yet be linked (D3a)

**Relationships removed:**
- `User.user_category` relationship → removed (column dropped)
- `User.profile` relationship (`UserProfile`) → removed (table dropped)

### 2.3 Thinned `client_user` (MODIFIED)

**Before (current):**
```
client_user: id, client_id, email, name, user_category_id, role_id,
             lifecycle_status, created_at, updated_at
```

**After (thinned — D3e, D6a):**
```
client_user: id, client_id, email, person_id (NULLABLE FK → person.id), role_id,
             lifecycle_status, created_at, updated_at
```

**What stays:**
- `id` (PK, FK → `user_account.id` — D12 preserved)
- `client_id` (FK → client.id, NOT NULL)
- `email` (unique, NOT NULL)
- `role_id` (FK → role.id, NOT NULL — client-leadership role stored directly, no separate assignment table)
- `lifecycle_status` (NOT NULL, default 'invited')
- `created_at`, `updated_at`
- All existing RLS policies (PO bypass + CD own-row via `current_user_id`)

**What drops:**
- `name` → moves to `person.name` (D6a)
- `user_category_id` → dropped entirely (D6a, AC-11)

**What's added:**
- `person_id` (nullable FK → `person.id`)

### 2.4 `user_account` (UNCHANGED — D3f)

The `user_account` parent table (migration 015, D12) is **completely unchanged**. It remains a single-column table (`id UUID PK`) serving as the shared FK target for:
- `role_assignment.user_id` → `user_account.id`
- `login_attempt.user_id` → `user_account.id`
- `app_user.id` → `user_account.id` (FK)
- `client_user.id` → `user_account.id` (FK)
- `user_profile.user_id` → `user_account.id` (FK — **but `user_profile` is dropped**, so this FK is removed)

The RLS `app.current_user_id` session var continues to map to `user_account.id` (the acting account's UUID), NOT to `person.id` (D3f, REQ-AUTHINF-Q8-01).

### 2.5 Dropped artifacts (D6a)

| Artifact | Current location | Fate |
|----------|-----------------|------|
| `user_category` table | migration 002 | **Dropped** (table + seed data) |
| `user_category_id` column on `app_user` | migration 002 | **Dropped** (column + FK constraint) |
| `user_category_id` column on `client_user` | migration 011 | **Dropped** (column + FK constraint) |
| `user_profile` table | migration 002 | **Dropped** (table + FK to `user_account`) |
| `UserProfile` model | `kernel/user/models/user_profile.py` | **Removed** (columns move to `person`) |
| `UserCategory` model | `kernel/user/models/user_category.py` | **Removed** |
| `UserProfileRepository` | `kernel/user/repos/user_profile_repo.py` | **Removed** |
| `UserProfile` DTOs | `kernel/user/services/dtos.py` | **Removed** |
| `UserCategoryDTO` | `kernel/user/services/dtos.py` | **Removed** |
| `/api/v1/lookups/user-categories` endpoint | `kernel/user/routes/lookups.py` | **Removed** |
| `/api/v1/users/{id}/profile` endpoints | `kernel/user/routes/profiles.py` | **Removed** (human data now on `person`, accessed via user DTO's `person` projection) |
| `user_profile.admin` / `user_profile.*` permissions | migration 016/019 | **Removed** from Casbin policy + role-permission mappings |
| `user_category='Learner'` proxy check in fees | `business/fees/services/service.py` | **Removed** (AC-14) |
| PO discovery by `user_category='Executive Leadership'` | `kernel/auth/bootstrap.py` | **Removed** (AC-13; already uses `is_platform_owner` flag) |

### 2.6 FK repoint setup (cross-capability coordination)

This revamp delivers `person` as the anchor but does **NOT** create `student`/`employee` tables. The following FKs are **set up** for repointing but **not repointed** in this revamp:

| FK | Current target | Future target (next capability) | Action this revamp |
|----|---------------|-------------------------------|-------------------|
| `student_enrollment.student_id` | `app_user.id` | `student.id` | No change — `person` anchor delivered; repoint is next capability |
| `homework.submission.student_id` | `app_user.id` | `student.id` | No change — setup only |
| `fee_assignment.user_id` | `user_account.id` | `student.id` | No change — `Learner` proxy check dropped; FK repoint is next capability |

> **Design decision:** The FKs are NOT repointed in this revamp because the `student` table does not exist yet. Repointing to a non-existent table would break referential integrity. The revamp's contribution is: (1) `person` exists as the anchor, (2) the `Learner` proxy check is removed from fees, (3) the spec deltas declare the repoint for the next capability. The domain split will create `student`/`employee` and execute the actual FK changes.

---

## 3. Creation/Activation Flow Restructure

### 3.1 Institution user creation (POST /api/v1/users)

**Current flow (InstitutionUserStrategy.create_user):**
1. Insert `user_account` (shared UUID)
2. Insert `app_user` (with `name`, `user_category_id`, same UUID)
3. Optional: insert `role_assignment`
4. Mint invite JWT
5. Return `{user, invite_url}`

**New flow (D3f insert order):**
1. **Insert `person`** (independent UUID, human data: name, dob, gender, etc.) ← NEW
2. Insert `user_account` (D12 shared UUID) ← unchanged
3. Insert `app_user` (same UUID as `user_account`, **without** `name`/`user_category_id`, **with** `person_id` → step 1's `person.id`) ← modified
4. Optional: insert `role_assignment` (FK → `user_account.id`, unchanged)
5. Mint invite JWT (unchanged)
6. Return `{user: UserDTO (with person projection), invite_url}`

**Request body change (breaking — AC-20, AC-26):**
```
Before: {email, name, user_category_id, institution_id, role_id?}
After:  {email, person_data: {name, dob?, gender?, blood_group?, photo?, ...},
         institution_id, role_id?}
```

### 3.2 CD bootstrap (POST /api/v1/platform/clients/{id}/users)

**Current flow (CDStrategy.create_user):**
1. Insert `user_account` (shared UUID)
2. Insert `client_user` (with `name`, `user_category_id`, same UUID)
3. Insert `role_assignment`
4. Insert lifecycle event
5. Mint invite JWT
6. Return `{user, invite_url}`

**New flow (D3f insert order):**
1. **Insert `person`** (independent UUID, human data) ← NEW
2. Insert `user_account` (D12 shared UUID) ← unchanged
3. Insert `client_user` (same UUID, **without** `name`/`user_category_id`, **with** `person_id` → `person.id`) ← modified
4. Insert `role_assignment` (unchanged)
5. Insert lifecycle event (unchanged)
6. Mint invite JWT (unchanged)
7. Return `{user: ClientUserDTO (with person projection), invite_url}`

**Request body change (breaking — AC-20):**
```
Before: {email, name, role_id, user_category_id, client_id?}
After:  {email, person_data: {name, ...}, role_id, client_id?}
```

### 3.3 Person-only creation (pre-login / bulk-import scenario)

A `person` MAY be created with NO account (D3a, REQ-IUM-PERSON-01). This is the pre-login student record scenario (PRD §4.4). In this revamp, person-only creation is supported at the **model/repo level** (the `PersonRepository` can insert a `person` without any account). A dedicated `POST /api/v1/persons` endpoint is a **design clarification** — see §8.

> **Design decision (PRD Q2):** A standalone `POST /api/v1/persons` endpoint for person-only creation is **deferred to the domain-split capability**, not this revamp. This revamp delivers `person` as an entity + repo + DTO; person creation is always mediated through user creation (`POST /api/v1/users` / CD bootstrap). The domain split will add the standalone endpoint when it creates `student`/`employee` (which need person-only creation for bulk import). This keeps the revamp's scope to the model restructure.

### 3.4 Activate flow (unchanged behavior — REQ-AUTH-01)

The activate flow (`AuthService.activate`) is **behaviorally unchanged**. It:
1. Verifies the invite JWT → extracts `user_id` (the `user_account.id` / `app_user.id` / `client_user.id`)
2. Looks up the user in `app_user` then `client_user` (by PK, bypassing RLS)
3. Transitions `lifecycle_status: invited → active`
4. Creates the Supabase Auth user with password (D11)
5. Returns `{message, user_id, user_tier, client_slug}`

The only structural note: the account row now carries `person_id`, but activate does NOT need to join to `person` — it operates on the account. The response shape is unchanged (AC-21). No `person_id` is added to the activate response.

### 3.5 Login flow (unchanged behavior — REQ-CUB-03)

The login flow branches on `user_metadata.user_tier`:
- `client_leadership` → look up in `client_user`
- `institution` → look up in `app_user`

Both tables now carry `person_id` but login does NOT join to `person` — it reads the account for auth/tenant fields. Token minting is unchanged. The `user_tier` stamping at creation is unchanged.

---

## 4. DTO Changes (Breaking — AC-25, AC-26)

### 4.1 New `PersonDTO` and `PersonCreateDTO`

```python
class PersonCreateDTO(BaseModel):
    """Human data for person creation (nested in user creation DTOs)."""
    name: str
    date_of_birth: date | None = None
    gender: str | None = None
    blood_group: str | None = None
    photo: str | None = None
    contact_phone: str | None = None
    contact_email: str | None = None
    demographics: dict | None = None

class PersonDTO(BaseModel):
    """Response DTO for a Person."""
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    client_id: uuid.UUID
    name: str
    date_of_birth: date | None = None
    gender: str | None = None
    blood_group: str | None = None
    photo: str | None = None
    contact_phone: str | None = None
    contact_email: str | None = None
    demographics: dict | None = None
    status: str  # Active|Inactive|Deceased|ErasureRequested|Anonymized
    is_minor: bool | None = None
    is_verified: bool | None = None
    created_at: datetime
    updated_at: datetime
```

### 4.2 Modified `UserCreateDTO` (breaking)

```python
class UserCreateDTO(BaseModel):
    email: str
    person_data: PersonCreateDTO  # was: name + user_category_id
    institution_id: uuid.UUID
    role_id: uuid.UUID | None = None
```
- `name` → removed (now inside `person_data`)
- `user_category_id` → removed (D6a)

### 4.3 Modified `UserDTO` (breaking — AC-25, AC-26)

```python
class UserDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    client_id: uuid.UUID
    institution_id: uuid.UUID | None = None
    email: str
    person: PersonDTO  # NEW — person projection
    # name → removed (now person.name)
    # user_category_id → removed
    lifecycle_status: str
    created_at: datetime
    updated_at: datetime
```

The repo's `_to_dto` method must now join to `person` (via `app_user.person_id`) and embed the `PersonDTO`. This is a read-path change in `UserRepository._to_dto` and `ClientUserRepository._to_dto`.

### 4.4 Modified `ClientUserCreateDTO` (breaking)

```python
class ClientUserCreateDTO(BaseModel):
    email: str
    person_data: PersonCreateDTO  # was: name
    role_id: uuid.UUID
    # user_category_id → removed
    client_id: uuid.UUID | None = None
```

### 4.5 Modified `ClientUserDTO` (breaking)

```python
class ClientUserDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    client_id: uuid.UUID
    email: str
    person: PersonDTO  # NEW
    # name → removed (now person.name)
    # user_category_id → removed
    role_id: uuid.UUID
    lifecycle_status: str
    created_at: datetime
    updated_at: datetime
```

### 4.6 Removed DTOs

- `UserCategoryDTO` — removed (no `user_category` table)
- `UserProfileCreateDTO`, `UserProfileUpdateDTO`, `UserProfileDTO` — removed (no `user_profile` table; human data is on `person`)

---

## 5. Repository Layer Changes

### 5.1 New `PersonRepository`

```python
class PersonRepository(TenantAwareRepositoryBase[Person]):
    """Repository for the Person entity (D3a)."""
    
    def create(self, session, ctx, dto: PersonCreateDTO) -> PersonDTO:
        """Insert a person row. Returns PersonDTO."""
        # Generates an independent UUID (NOT shared with account)
        # client_id from ctx.client_id
    
    def get(self, session, ctx, person_id: uuid.UUID) -> PersonDTO | None:
        """Get a person by ID, tenant-filtered."""
    
    def get_by_id_unscoped(self, session, person_id: uuid.UUID) -> PersonDTO | None:
        """Get a person by ID, bypassing tenant filter (for internal lookups)."""
    
    def update(self, session, ctx, person_id, dto) -> PersonDTO:
        """Update person human data."""
    
    def link_account(self, session, account_table: str, account_id: uuid.UUID, person_id: uuid.UUID):
        """Set person_id on an account row (app_user or client_user)."""
```

### 5.2 `UserRepository` (modified)

- `create()`: no longer writes `name` or `user_category_id` to `app_user`; instead calls `PersonRepository.create()` first, then inserts `app_user` with `person_id`. Insert order: person → user_account → app_user.
- `_to_dto()`: now joins to `person` via `app_user.person_id` and embeds `PersonDTO`.
- `list()`: filter by `user_category_id` removed (AC-26); the route param is removed.

### 5.3 `ClientUserRepository` (modified)

- `create()`: no longer writes `name` or `user_category_id` to `client_user`; calls `PersonRepository.create()` first, then inserts `client_user` with `person_id`.
- `_to_dto()`: joins to `person` via `client_user.person_id`.
- `update()`: display-name update routes to `person.name` (REQ-CUB-04), not `client_user.name`.

### 5.4 Removed repos

- `UserProfileRepository` — removed (table dropped)

---

## 6. Service Layer Changes

### 6.1 `UserService` (modified)

- `create_user()`: delegates to strategy; strategy now creates `person` first. The service orchestration is unchanged — the strategy owns the insert order.
- `create_profile()`, `get_profile()`, `update_profile()`: **removed** (no `user_profile` table). Human data is now managed through the `person` projection on the user DTO. A future `update_person()` method may be added; for this revamp, person updates are handled within `update_user()` (if name/human data is in the update DTO, route it to `person`).
- Profile-related imports removed.

### 6.2 `InstitutionUserStrategy` (modified)

- `create_user()`: new insert order (person → user_account → app_user → role_assignment → invite JWT).
- `delete_user()`: the `DELETE FROM user_profile WHERE user_id = :uid` line is removed. The person row is NOT deleted (person is the enduring anchor — it survives account deletion; D3a).
- `update_user()`: if `UserUpdateDTO` includes name (or other human fields), route to `person` via `PersonRepository.update()`. The `app_user` row is updated only for account fields (email, lifecycle_status).

### 6.3 `CDStrategy` (modified)

- `create_user()`: new insert order (person → user_account → client_user → role_assignment → lifecycle event → invite JWT).
- `update_user()`: display-name update routes to `person.name` (REQ-CUB-04).
- `delete_user()`: person row is NOT deleted (enduring anchor).

### 6.4 `AuthService` (unchanged behavior)

- `activate()`: **behaviorally unchanged**. Looks up `app_user`/`client_user` by UUID (PK), transitions lifecycle, creates Supabase Auth user. The account row now carries `person_id` but activate does not need it.
- `login()`: **unchanged**. Branches on `user_tier`, reads account for auth/tenant fields.
- No `person` joins in auth.

### 6.5 `IdentityDomainLinkingService` (future — not in this revamp)

The ADR §3 mentions `IdentityDomainLinkingService` becoming more complex (resolves account↔domain through `person`, two links). This service is **not implemented in this revamp** — it belongs to the domain-split capability, where `student`/`employee` domain entities are created. This revamp delivers the `person` anchor it will resolve through.

---

## 7. Authorization Pipeline — Byte-for-Byte Unchanged (D8/D3d)

This is the most important invariant of the revamp. The design must show explicitly that the authz pipeline is untouched.

### 7.1 What does NOT change

| Component | File | Change |
|-----------|------|--------|
| Casbin enforcer setup | `kernel/authz/` | **None** |
| Casbin policy loader (dual source) | `kernel/authz/` loader | **None** — reads `role_assignment` (institution) + `client_user.role_id` (client-leadership); `role_assignment.user_id` → `user_account.id` (unchanged) |
| Middleware role resolution | `kernel/middleware.py` | **None** — reads roles from JWT or DB fallback (`role_assignment` join); the query `SELECT r.name FROM role r JOIN role_assignment ra ON r.id = ra.role_id WHERE ra.user_id = :uid` is unchanged |
| RLS session vars | `kernel/db.py` | **None** — `app.current_user_id` maps to `user_account.id` (unchanged, D3f) |
| RLS policies on `app_user` | migration 002 | **None** — tenant-scoped via `client_id` (unchanged) |
| RLS policies on `client_user` | migration 011 | **None** — PO bypass + CD own-row via `current_user_id` (unchanged) |
| Permission definitions | Casbin policy | **None** — no new permissions (except `user_profile.*` permissions are **removed**, but that's a removal, not an authz behavior change) |
| Role definitions | `role` table seed | **None** — the 10 roles are unchanged |
| `is_platform_owner` bypass | middleware + authz | **None** — defense-in-depth bypass unchanged |
| `check_permission()` / `require_permission()` | `kernel/authz/dependencies.py` | **None** |

### 7.2 What IS removed (but is NOT an authz behavior change)

- `user_profile.create`, `user_profile.read`, `user_profile.update`, `user_profile.admin` permissions are removed from the Casbin policy and role-permission mappings (migrations 016/019). These permissions governed the now-dropped `user_profile` routes. Removing them does not change any authz behavior for surviving resources — no role loses access to anything it still needs.

### 7.3 Verification

The authz invariant is verified by: **all existing authz tests pass without modification** (AC-17, AC-18). The test files `test_c04_authz.py`, `test_casbin_permissions.py` should pass unchanged. If any authz test fails, it indicates an unintended authz pipeline change — a blocker.

---

## 8. Design Clarifications (Resolving PRD Open Questions)

| Question | Resolution | Rationale |
|----------|-----------|-----------|
| **Q1: Person field shape** | Flat contact fields (`contact_phone`, `contact_email`) + JSONB `demographics`. Not normalized into a separate contact table. | Phase 1 simplicity; the ADR treats contact generically. Normalization is a future evolution (ADR §7). |
| **Q2: Person CRUD API surface** | **Deferred to domain-split capability.** This revamp delivers `person` as entity + repo + DTO; person creation is mediated through user creation. A standalone `POST /api/v1/persons` lands with the domain split (bulk import needs it). | Keeps revamp scope to the model restructure. The pre-login scenario (PRD §4.4) is fully enabled at the model level; the endpoint is the domain split's concern. |
| **Q3: Person deduplication** | **Not in scope.** No dedup/merge strategy for this revamp. Disposable DB reseed means no real duplicates to merge. Person-merge is a future feature. | Not blocking for a clean-cut migration (ADR constraint 11). |
| **Q4: person.status in admin UI** | **Backend-only in this revamp.** No admin UI for `person.status`. Set via backend processes (which don't exist yet). The `PersonDTO` includes `status` (readable), but no admin-facing set-status endpoint. | The processes that set `person.status` (GDPR, registrar) don't exist yet (PRD Q4 recommendation). |
| **Q5: Frontend update sequencing** | **Frontend update is in this revamp's blast radius** (constraint 4, AC-25, AC-26). The frontend's `UserDTO`, `ClientUserDTO`, user-display paths, and `user_category` filters MUST be updated in the same PR. The frontend is archived but its source is in-repo (`frontend/`). | Breaking contract change; in-repo consumers must be updated together. |
| **Q6: person.id vs account UUID** | **`person.id` is independent** (D3f). NOT equal to the account UUID. The `user_account` D12 shared-UUID pattern is preserved for the account parent; `person` gets its own UUID. | A person may have zero or many accounts; `person.id` cannot equal "the account UUID" (D3f rationale). |
| **Q8: person vs user_account** | **RESOLVED as D3f — coexist.** `user_account` is the account parent (FK target); `person` is the human anchor. See §1.1. | Do not re-open. |
| **PO ↔ person linkage** | **The PO gets a `person` row** (optional). The PO exists only in Supabase Auth (no `app_user`/`client_user`). A `person` row MAY be created for the PO's human data, linked via a nullable `person_id`... but the PO has no account row to carry `person_id`. **Decision: the PO does NOT get a `person` row in this revamp.** The PO is a single SaaS operator, not a domain entity. The PO's human data (if any) is not modeled until a use case demands it. | Minor — the PO is one person. Modeling PO↔person adds complexity for no current value. |

---

## 9. Migration Design

### 9.1 Migration 022: `person_model_revamp`

**Revision ID:** `022_person_model_revamp`
**Down revision:** `021_homework_fee_assignment_academic_fks`

**Upgrade steps:**

```sql
-- 1. Create person table
CREATE TABLE person (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id       UUID NOT NULL REFERENCES client(id),
    name            VARCHAR(255) NOT NULL,
    date_of_birth   DATE,
    gender          VARCHAR(20),
    blood_group     VARCHAR(10),
    photo           VARCHAR(500),
    contact_phone   VARCHAR(50),
    contact_email   VARCHAR(255),
    demographics    JSONB,
    status          VARCHAR(25) NOT NULL DEFAULT 'Active'
                    CHECK (status IN ('Active','Inactive','Deceased',
                                     'ErasureRequested','Anonymized')),
    is_minor        BOOLEAN,
    is_verified     BOOLEAN,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 2. Add person_id to app_user (nullable FK → person.id)
ALTER TABLE app_user ADD COLUMN person_id UUID REFERENCES person(id);
-- 3. Add person_id to client_user (nullable FK → person.id)
ALTER TABLE client_user ADD COLUMN person_id UUID REFERENCES person(id);

-- 4. Drop user_category_id from app_user
ALTER TABLE app_user DROP CONSTRAINT app_user_user_category_id_fkey;
ALTER TABLE app_user DROP COLUMN user_category_id;

-- 5. Drop user_category_id from client_user
ALTER TABLE client_user DROP CONSTRAINT client_user_user_category_id_fkey;
ALTER TABLE client_user DROP COLUMN user_category_id;

-- 6. Drop user_profile table (FK to user_account removed)
DROP TABLE user_profile;

-- 7. Drop user_category table
DROP TABLE user_category;

-- 8. RLS on person (tenant-scoped, same pattern as app_user)
ALTER TABLE person ENABLE ROW LEVEL SECURITY;
ALTER TABLE person FORCE ROW LEVEL SECURITY;
CREATE POLICY person_tenant_select ON person FOR SELECT
    USING (is_platform_owner() OR client_id = current_client_id());
CREATE POLICY person_tenant_insert ON person FOR INSERT
    WITH CHECK (is_platform_owner() OR client_id = current_client_id());
CREATE POLICY person_tenant_update ON person FOR UPDATE
    USING (is_platform_owner() OR client_id = current_client_id())
    WITH CHECK (is_platform_owner() OR client_id = current_client_id());
CREATE POLICY person_tenant_delete ON person FOR DELETE
    USING (is_platform_owner());

-- 9. Grant permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON person TO test_tenant_user;

-- 10. Index on person.client_id for RLS filter performance
CREATE INDEX ix_person_client_id ON person(client_id);
```

**What is NOT in this migration:**
- No backfill (D5 — disposable DB, reseed via `seed_data.py`)
- No `student`/`employee` table creation (next capability)
- No FK repoint for `student_enrollment.student_id`, `homework.submission.student_id`, `fee_assignment.user_id` (next capability)
- No changes to `role_assignment.user_id` or `login_attempt.user_id` FK targets (unchanged, D3f)

### 9.2 Seed data update (`seed_data.py`)

The seed script must be updated to:
1. Create `person` rows for every seeded user (CD + institution users)
2. Link `app_user.person_id` and `client_user.person_id` to the created `person` rows
3. Remove `user_category_id` from all seeded `app_user`/`client_user` inserts
4. Remove `user_category` seed data (the 5 categories)
5. Remove `user_profile` seed data (if any)

---

## 10. Frontend Contract Changes (Breaking — AC-25, AC-26)

### 10.1 TypeScript DTOs (`frontend/src/core/api/dto/users.ts`)

| DTO | Change |
|-----|--------|
| `UserDTO` | Add `person: PersonDTO`; remove `name`, `user_category_id` |
| `UserCreateDTO` | Replace `name` + `user_category_id` with `person_data: PersonCreateDTO` |
| `ClientUserDTO` | Add `person: PersonDTO`; remove `name`, `user_category_id` |
| `ClientUserCreateDTO` | Replace `name` + `user_category_id` with `person_data: PersonCreateDTO` |
| `UserProfileDTO` / `UserProfileCreateDTO` / `UserProfileUpdateDTO` | **Removed** |
| `UserCategoryDTO` | **Removed** |

New TypeScript interfaces:
```typescript
export interface PersonDTO {
  id: string;
  client_id: string;
  name: string;
  date_of_birth: string | null;
  gender: string | null;
  blood_group: string | null;
  photo: string | null;
  contact_phone: string | null;
  contact_email: string | null;
  demographics: Record<string, unknown> | null;
  status: string;
  is_minor: boolean | null;
  is_verified: boolean | null;
  created_at: string;
  updated_at: string;
}

export interface PersonCreateDTO {
  name: string;
  date_of_birth?: string | null;
  gender?: string | null;
  blood_group?: string | null;
  photo?: string | null;
  contact_phone?: string | null;
  contact_email?: string | null;
  demographics?: Record<string, unknown> | null;
}
```

### 10.2 API layer (`frontend/src/core/api/users.ts`, `lookups.ts`)

- `listUsers` filter: remove `user_category_id` param (AC-26)
- `getProfile` / `createProfile` / `updateProfile`: **removed** (human data via `user.person`)
- `listUserCategories` (lookups): **removed**
- `UserCategoryDTO` import in `lookups.ts`: **removed**

### 10.3 Feature components

- `frontend/src/features/users/Users.tsx`: remove `user_category_id` from form state, filters, and display; read `user.person.name` instead of `user.name`
- `frontend/src/features/platform/ClientUsers.tsx`: remove `user_category_id` from form; read `user.person.name`
- All test files that construct `makeUser({ ..., user_category_id: 'uc1' })`: remove `user_category_id`, add `person: { name: '...' }` or adjust mock

---

## 11. Fees Module Change (AC-14)

### 11.1 Remove `Learner` proxy check

**File:** `backend/business/fees/services/service.py` (lines ~81-92)

The current code checks `user_category_id NOT IN (SELECT id FROM user_category WHERE name = 'Learner')` to validate that fee assignments target students. This proxy check is **removed** (AC-14, D6a).

**After removal:** fee assignment validation will derive student status from the `student` domain entity (next capability) or `role_assignment`. Until the domain split lands, fee assignment validation is relaxed — it accepts any `user_account.id` without the `Learner` check. The next capability will add proper `student.id` validation.

### 11.2 `fee_assignment.user_id` FK (NOT repointed this revamp)

`fee_assignment.user_id` currently → `user_account.id`. This FK is **not changed** in this revamp. The repoint to `student.id` is the next capability (when `student` exists).

---

## 12. Cascade Behavior (D12 — domain-split, setup only)

Terminal domain transitions (Employee: Active→Resigned/Terminated; Student: Enrolled→Withdrawn) cascade to archive the linked `app_user` via `person`. This cascade is **not implemented in this revamp** — it belongs to the domain-split capability (where `student`/`employee` lifecycles exist). This revamp delivers the `person` link that the cascade will traverse (domain→person→account).

The config keys `identity.archiveGraduatedStudentLogin` and `identity.autoActivateStudentLoginOnEnroll` (domain-split ADR D12) are **not introduced by this revamp** — they belong to the domain-split capability.

---

## 13. Risk Points

| # | Risk | Impact | Mitigation |
|---|------|--------|------------|
| R1 | **`_to_dto` join to `person` adds a query per user serialization** | List endpoints (`GET /api/v1/users`) do N+1 queries if `person` is lazily loaded | Use SQLAlchemy `joinedload` or a JOIN in the list query to eager-load `person`. Test with `EXPLAIN` on the list query. |
| R2 | **Person row orphaned on account deletion** | If an `app_user` is deleted but `person` is not, orphaned `person` rows accumulate | By design — `person` is the enduring anchor (D3a). It survives account deletion. This is correct behavior, not a bug. A future GDPR/anonymization pipeline will handle person cleanup. |
| R3 | **`user_profile` permissions removal breaks Casbin policy load** | If the Casbin policy CSV/DB still references `user_profile.*` permissions after the migration, the enforcer may error | Migration 022 must remove `user_profile.*` from the Casbin policy table (or the policy seed). Test that the enforcer loads cleanly after migration. |
| R4 | **Frontend test breakage** | 6+ frontend test files reference `user_category_id` in mock user objects | Update all mock factories in the same PR. The frontend test suite must pass. |
| R5 | **`app_user.name` removal breaks audit payloads** | Audit events reference `result.name` in `InstitutionUserStrategy.create_user` | Update audit payload to use `person.name` (looked up from the created person). |
| R6 | **`client_user_repo.create` still writes `name`/`user_category_id`** | If repo is not updated, inserts fail (columns dropped) | Repo must be updated in the same migration PR. Integration test for CD bootstrap must pass. |
| R7 | **Fees validation gap after `Learner` proxy removal** | Until the domain split, fees can't validate "is this a student" | Accepted — the `Learner` proxy was an abuse (AC-14). The gap is temporary (until domain split). Document in the fees service that student validation is pending the domain split. |

---

## 14. Cross-Capability Coordination Points

| # | Coordination point | This revamp delivers | Next capability (domain split) delivers |
|---|-------------------|---------------------|----------------------------------------|
| X1 | `student`/`employee` tables | `person` anchor (exists, linkable) | `student`/`employee` tables with `person_id` NOT NULL FK → `person.id` |
| X2 | FK repoints (`student_enrollment.student_id`, `homework.submission.student_id`, `fee_assignment.user_id`) | Setup (anchor + spec declaration + `Learner` proxy dropped) | Actual FK repoint execution (`app_user.id`/`user_account.id` → `student.id`) |
| X3 | Cascade (domain→person→account) | `person` link exists | Cascade logic + config keys (`identity.archiveGraduatedStudentLogin`, etc.) |
| X4 | `IdentityDomainLinkingService` | `person` entity + repo | The linking service that resolves account↔domain through `person` |
| X5 | Standalone `POST /api/v1/persons` endpoint | `person` entity + repo + DTO (model-level ready) | The endpoint for person-only / bulk-import creation |
| X6 | C-06 Relationship Management | `person` as anchor (C-06 will link `relationship.related_person_id → person.id`) | N/A (C-06 is next-next) |

---

## 15. Test Strategy

### 15.1 Migration tests
- Apply migration 022 on a fresh DB → `person` table exists, `person_id` on both account tables, `user_category_id`/`user_profile`/`user_category` gone
- RLS on `person`: tenant-scoped SELECT/INSERT/UPDATE/DELETE policies work

### 15.2 Model/repo tests
- `PersonRepository.create()` → person row with independent UUID
- `UserRepository.create()` → person + user_account + app_user insert order (D3f)
- `UserRepository._to_dto()` → `UserDTO` contains `person` projection
- `ClientUserRepository._to_dto()` → `ClientUserDTO` contains `person` projection

### 15.3 Creation flow tests (D3f insert order)
- Institution user creation: verify insert order (person → user_account → app_user → role_assignment)
- CD bootstrap: verify insert order (person → user_account → client_user → role_assignment)
- `person.id` ≠ account UUID (independence, D3f)
- Person-only creation (no account): person row valid, no account rows

### 15.4 Authz pipeline tests (unchanged — AC-17, AC-18)
- `test_c04_authz.py` passes unchanged
- `test_casbin_permissions.py` passes unchanged
- Middleware role resolution: `role_assignment.user_id` → `user_account.id` (unchanged)

### 15.5 Breaking change tests
- `UserDTO` serialization: no `user_category_id`, has `person`
- `UserCreateDTO` validation: rejects `user_category_id`, accepts `person_data`
- `GET /api/v1/lookups/user-categories` → 404 (endpoint removed)
- `GET /api/v1/users/{id}/profile` → 404 (endpoint removed)

### 15.6 Regression tests
- Activate flow: `invited → active` still works (unchanged)
- Login flow: `user_tier` branching unchanged
- CD own-row access: RLS `current_user_id` still filters (unchanged)
- Fees: `Learner` proxy check removed; fee assignment accepts any `user_account.id`

### 15.7 Frontend tests
- All frontend test files updated: mock users use `person` projection, no `user_category_id`
- `users.test.tsx`, `ClientUsers.tsx`, `fees.test.tsx`, `homework.test.tsx`, `assignmentsEnrollments.test.tsx` — all pass

---

## 16. File Change Map

### Backend — new files
| File | Purpose |
|------|---------|
| `backend/kernel/user/models/person.py` | `Person` SQLAlchemy model |
| `backend/kernel/user/repos/person_repo.py` | `PersonRepository` |

### Backend — modified files
| File | Change |
|------|--------|
| `backend/kernel/user/models/user.py` | Drop `name`, `user_category_id`, `UserCategory` relationship, `UserProfile` relationship; add `person_id` FK + `Person` relationship |
| `backend/kernel/user/models/client_user.py` | Drop `name`, `user_category_id`; add `person_id` FK + `Person` relationship |
| `backend/kernel/user/models/__init__.py` | Add `Person`; remove `UserCategory`, `UserProfile` |
| `backend/kernel/user/models/user_account.py` | No change (D3f — unchanged) |
| `backend/kernel/user/services/dtos.py` | Add `PersonDTO`, `PersonCreateDTO`; modify `UserCreateDTO`, `UserDTO`, `ClientUserCreateDTO`, `ClientUserDTO`; remove `UserCategoryDTO`, `UserProfile*DTO`s |
| `backend/kernel/user/services/service.py` | Remove profile methods; adjust imports |
| `backend/kernel/user/services/strategies/institution_strategy.py` | New insert order (person first); remove `user_profile` delete; audit payload uses `person.name` |
| `backend/kernel/user/services/strategies/cd_strategy.py` | New insert order (person first); `user_category_id` removed from `ClientUserCreateDTO` construction |
| `backend/kernel/user/repos/user_repo.py` | `create()` inserts person first; `_to_dto()` joins person; remove `user_category_id` from create |
| `backend/kernel/user/repos/client_user_repo.py` | `create()` inserts person first; `_to_dto()` joins person; `update()` routes name to person |
| `backend/kernel/user/routes/users.py` | Remove `user_category_id` filter param from `list_users` |
| `backend/kernel/user/routes/lookups.py` | Remove `list_user_categories` endpoint + `UserCategoryDTO` import |
| `backend/kernel/user/routes/profiles.py` | Remove all profile endpoints (or convert to person endpoints — see §8 Q2: deferred) |
| `backend/kernel/auth/services/service.py` | No behavioral change; activate/login unchanged (person_id on account but not used) |
| `backend/kernel/auth/bootstrap.py` | Remove `user_category='Executive Leadership'` discovery (line ~64); already uses `is_platform_owner` |
| `backend/kernel/middleware.py` | No change (role lookup query unchanged; `user_account.id` referent unchanged) |
| `backend/business/fees/services/service.py` | Remove `Learner` proxy check (lines ~81-92) |
| `backend/migrations/versions/022_person_model_revamp.py` | New migration (schema + RLS) |
| `backend/scripts/seed_data.py` | Create person rows for seeded users; remove user_category/user_profile seed data |

### Backend — removed files
| File | Reason |
|------|--------|
| `backend/kernel/user/models/user_category.py` | `user_category` table dropped |
| `backend/kernel/user/models/user_profile.py` | `user_profile` table dropped |
| `backend/kernel/user/repos/user_profile_repo.py` | `user_profile` table dropped |

### Frontend — modified files
| File | Change |
|------|--------|
| `frontend/src/core/api/dto/users.ts` | Add `PersonDTO`/`PersonCreateDTO`; modify `UserDTO`/`UserCreateDTO`/`ClientUserDTO`/`ClientUserCreateDTO`; remove `UserProfile*DTO`s, `UserCategoryDTO` |
| `frontend/src/core/api/dto/lookups.ts` | Remove `UserCategoryDTO` |
| `frontend/src/core/api/users.ts` | Remove `user_category_id` filter; remove profile API methods |
| `frontend/src/core/api/lookups.ts` | Remove `listUserCategories` |
| `frontend/src/features/users/Users.tsx` | Remove `user_category` form/filter; read `user.person.name` |
| `frontend/src/features/platform/ClientUsers.tsx` | Remove `user_category` form; read `user.person.name` |
| `frontend/src/features/users/__tests__/users.test.tsx` | Update mock users |
| `frontend/src/features/fees/__tests__/fees.test.tsx` | Update mock users |
| `frontend/src/features/homework/__tests__/homework.test.tsx` | Update mock users |
| `frontend/src/features/academic/__tests__/assignmentsEnrollments.test.tsx` | Update mock users |

### Tests — modified
| File | Change |
|------|--------|
| `backend/tests/conftest.py` | Remove `user_category` fixtures; add `person` fixtures |
| `backend/tests/test_c02_user.py` | Update all user creation tests for new DTO + insert order |
| `backend/tests/test_c03_auth.py` | Update activate/login tests (person_id on account, no behavior change) |
| `backend/tests/test_client_user_bootstrap.py` | Update CD bootstrap tests for new DTO + insert order |
| `backend/tests/test_fees.py` | Remove `Learner` proxy test; update mock users |

---

> **End of design.** This design is the technical input to `tasks.md`. All spec requirement IDs (REQ-…) referenced in the spec deltas are mapped to tasks in the task list.

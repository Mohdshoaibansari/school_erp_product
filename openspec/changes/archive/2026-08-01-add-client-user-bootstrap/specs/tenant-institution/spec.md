## ADDED Requirements

### Requirement: Client one-to-many client_users relationship

The `client` entity SHALL have a one-to-many relationship with `client_user` (a client has zero or more client-leadership users, defined in the new `client_user` table owned by the `client-user-bootstrap` capability). The relationship is referenced via `client_user.client_id` FK → `client.id`.

#### Scenario: Client with multiple Client Directors
- **WHEN** the PO bootstraps two Client Directors for the same client
- **THEN** two distinct `client_user` rows SHALL exist with the same `client_id` and different `id`
- **AND** both SHALL be queryable via the PO's `GET /api/v1/platform/clients/$ID/users` endpoint

### Requirement: PO bootstrap journey through platform endpoint

The PO's documented bootstrap journey for a new client's first Client Director SHALL use `POST /api/v1/platform/clients/$ID/users` (owned by the `client-user-bootstrap` capability) instead of direct Supabase REST API calls. The direct Supabase REST API path to `app_user` and `role_assignment` SHALL NOT be the documented bootstrap procedure.

#### Scenario: Bootstrap documented as platform endpoint
- **WHEN** a new client's lifecycle is activated and the PO wishes to provision the first Client Director
- **THEN** the documented path SHALL be `POST /api/v1/platform/clients/$ID/users` with body `{email, name, role}`
- **AND** the response SHALL contain the invite URL to forward to the CD

## MODIFIED Requirements

### Requirement: Entity Identifiers — UUID v4

C-01 entities (`client`, `institution`, `org_unit`, `institution_type`) use UUID v4 primary keys generated on insert. **This requirement is widened to also cover `client_user` (owned by the `client-user-bootstrap` capability): every `client_user` row SHALL use a UUID v4 primary key.** The existing UUID v4 rule for the original C-01 entities is unchanged.

#### Scenario: client_user has UUID v4 primary key
- **WHEN** the PO bootstraps a CD via `POST /api/v1/platform/clients/$ID/users`
- **THEN** the resulting `client_user.id` SHALL be a UUID v4 value
- **AND** the same UUID SHALL be used as the Supabase Auth user's `id` (the bootstrap endpoint creates both with the same UUID)

## REMOVED Requirements

### Requirement: app_user.institution_id nullable

Migration `008_nullable_institution_id.py` made `app_user.institution_id` nullable to support client-leadership users without an institution (specifically the Client Director). With the two-tier user model (D1), the Client Director moves out of `app_user` into `client_user`, so the rationale for a nullable `institution_id` no longer applies. Migration 012 (owned by the `client-user-bootstrap` capability) ALTERs `app_user.institution_id` to NOT NULL.

**Reason:** The Client Director no longer lives in `app_user`. With all `app_user` rows now strictly institution-scoped (D1 of `client-user-bootstrap`), the `institution_id` column MUST mirror that invariant at the database level. A nullable `institution_id` allows "homeless" user rows that contradict the tier separation — only the PO can authorize writes through their middleware path, which has no `current_client_id`, and so the PO can never insert into `app_user` anyway. Tightening to NOT NULL surfaces bugs in `POST /api/v1/users` immediately at insert time rather than silently creating broken rows.

**Migration:**
1. Migration 011 (NEW — owned by `client-user-bootstrap`) moves every existing `app_user` row with `institution_id IS NULL` into `client_user` (with role resolved from existing `role_assignment` rows for those users) and backfills each user's `user_metadata.user_tier = "client_leadership"` via Supabase Admin API. Migration 011 is idempotent and asserts "0 NULL `institution_id` rows remaining in `app_user`" before completing.
2. Migration 012 (NEW — BREAKING) executes `ALTER TABLE app_user ALTER COLUMN institution_id SET NOT NULL`. Because migration 011 cleared NULL rows, this ALTER succeeds.
3. API layer: `UserCreateDTO.institution_id` is made a required field AFTER migration 012 is verified applied. Any client still posting without `institution_id` will receive a `422` symmetric to the DB constraint. The greenfield approach for existing test clients is to wipe and re-bootstrap rather than risk a constraint-inflight client.

**Operational note:** This is a BREAKING change. Migration 012 MUST run AFTER migration 011 has successfully completed AND after the operator has confirmed the post-011 assertion ("0 NULL `institution_id` rows") is true on the target database.

#### Scenario: Migration 011 moves NULL rows to client_user
- **WHEN** migration 011 runs on a database with `app_user` rows whose `institution_id IS NULL`
- **THEN** each such row SHALL be moved to `client_user`
- **AND** its Supabase Auth user's `user_metadata.user_tier` SHALL be backfilled to `"client_leadership"`
- **AND** the row SHALL be deleted from `app_user`

#### Scenario: Migration 011 idempotent
- **WHEN** migration 011 runs on a database that has already been migrated
- **THEN** migration 011 SHALL be a no-op
- **AND** the post-migration assertion ("0 NULL `institution_id` rows in `app_user`") SHALL hold

#### Scenario: Migration 012 enforces NOT NULL
- **WHEN** migration 012 runs and the post-011 assertion holds
- **THEN** the `ALTER TABLE app_user ALTER COLUMN institution_id SET NOT NULL` SHALL succeed
- **AND** any subsequent INSERT into `app_user` omitting `institution_id` SHALL be rejected by Postgres

#### Scenario: API requires institution_id post-migration
- **WHEN** a client calls `POST /api/v1/users` without `institution_id` after migration 012 is applied
- **THEN** the response SHALL be `422 Unprocessable Entity`
- **AND** the API error SHALL point at the `institution_id` field as required

#### Scenario: Migration 012 fails if 011 did not clean
- **WHEN** migration 012 runs but migration 011 left one or more NULL `institution_id` rows in `app_user`
- **THEN** the ALTER SHALL fail
- **AND** migration 012 SHALL rollback leaving the DB in a consistent pre-ALTER state
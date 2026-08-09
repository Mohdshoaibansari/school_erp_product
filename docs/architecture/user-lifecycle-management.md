# User Lifecycle Management — Design Decisions

> **Date:** 2026-08-09
> **Status:** Design — pending implementation
> **Source:** Conversation about `transition_user_lifecycle` vs `auth/activate` overlap

---

## 1. Problem

There are two endpoints that can set a user to `active` state:

| Endpoint | Purpose | Who calls it |
|---|---|---|
| `POST /api/auth/activate` | User self-activates via invite link | The user (unauthenticated, invite JWT only) |
| `POST /api/v1/users/{id}/transition` | Admin manually transitions lifecycle | An admin (authenticated) |

An admin can call `transition` with `new_state=active` and bypass the activate flow. The DB would show `lifecycle_status=active` but:
- No Supabase Auth user exists (D11 — created during activate)
- No password is set
- User can't log in

---

## 2. Lifecycle State Machine

```
                    ┌─────────────┐
                    │   invited   │
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              ▼            │            ▼
        ┌───────────┐      │      ┌───────────┐
        │  pending   │      │      │   active   │ ◄── auth/activate
        └─────┬─────┘      │      └─────┬─────┘     (sets password)
              │            │            │
              ▼            │            ▼
        ┌───────────┐      │      ┌───────────┐
        │   active   │      │      │ suspended  │
        └───────────┘      │      └─────┬─────┘
                           │            │
                           │            ▼
                           │      ┌───────────┐
                           │      │  archived  │ (terminal)
                           │      └───────────┘
                           │
                    admin can do:
                    invited → pending
                    pending → active
                    active → suspended
                    suspended → active
                    active → archived
                    suspended → archived
```

---

## 3. Two Paths to "Active"

### Path A: User Self-Activation (auth/activate)

```
User clicks invite link
    │
    ▼
POST /api/auth/activate {invite_token, password}
    │
    ├── 1. Verify invite JWT → extract user_id
    ├── 2. Elevated session → look up user identity
    ├── 3. Normal session → transition lifecycle invited → active
    ├── 4. COMMIT DB
    ├── 5. Create Supabase Auth user WITH password (D11)
    ├── 6. Emit audit (actor = user_id from token)
    └── 7. Return {message, user_id, user_tier, client_slug}

Result: User can log in (Supabase Auth user exists with password)
```

### Path B: Admin Manual Transition (transition endpoint)

```
Admin calls POST /api/v1/users/{id}/transition {new_state: "active"}
    │
    ├── 1. Check permission (admin role required)
    ├── 2. Validate transition arc
    ├── 3. Update lifecycle_status in DB
    ├── 4. Record lifecycle event
    ├── 5. COMMIT DB
    └── 6. Return UserDTO

Result: User CANNOT log in (no Supabase Auth user, no password)
```

---

## 4. The Bug

**Path B allows `invited → active` without setting a password.**

After Path B:
- DB says `lifecycle_status = "active"`
- Supabase Auth has no user for this UUID
- Login returns "Invalid email or password" (Supabase says user not found)
- Admin is confused: "I activated the user but they can't log in"

---

## 5. Recommended Fix

### Rule: `invited → active` must go through `auth/activate`

The admin transition endpoint should **block the `invited → active` arc**. The admin can do:
- `invited → pending` (acknowledge the invite, but user must still self-activate)
- `pending → active` (if the user was moved to pending first — but this still has the no-password problem)

**Better approach:** Only allow `invited → pending` from the admin endpoint. The `invited → active` path is exclusively through `auth/activate`.

### Guard to add

```python
# In transition_user_lifecycle route or service:
BLOCKED_ARCS = {
    ("invited", "active"): "Use auth/activate to set password. Admin can only do invited → pending.",
}

if (current_state, new_state) in BLOCKED_ARCS:
    raise HTTPException(400, detail=BLOCKED_ARCS[(current_state, new_state)])
```

### Full allowed transitions

| From | To | Who | Method |
|---|---|---|---|
| invited | pending | Admin | `POST /api/v1/users/{id}/transition` |
| invited | active | User | `POST /api/auth/activate` (sets password) |
| pending | active | Admin | `POST /api/v1/users/{id}/transition` (⚠️ no password — see §6) |
| active | suspended | Admin | `POST /api/v1/users/{id}/transition` |
| suspended | active | Admin | `POST /api/v1/users/{id}/transition` |
| active | archived | Admin | `POST /api/v1/users/{id}/transition` |
| suspended | archived | Admin | `POST /api/v1/users/{id}/transition` |

---

## 6. Open Question: `pending → active` without password

If an admin does `pending → active` via the transition endpoint, the user is active but has no password. This is the same problem as `invited → active`.

**Options:**

| Option | Behavior | Trade-off |
|---|---|---|
| **A: Block `pending → active` too** | Only `auth/activate` can set active | Cleanest. Admin can only move to `pending`, never to `active`. |
| **B: Allow `pending → active` but require password** | Transition endpoint accepts optional `password` param | Admin can set password on behalf of user. Security concern: admin knows user's password. |
| **C: Allow `pending → active` without password** | User must call `auth/activate` later to set password | Confusing: user is "active" but can't log in. |
| **D: Create Supabase Auth user on `pending → active`** | Transition endpoint calls Supabase create_user with a generated password | User gets a temp password via email. Requires C-09 notification framework. |

**Recommendation:** Option A — only `auth/activate` can transition to `active`. Admin can move users to `pending` but not to `active`.

---

## 7. Implementation Checklist

- [ ] Add guard to `transition_user_lifecycle` route: block `invited → active` arc
- [ ] Add guard to service layer: same block (defense in depth)
- [ ] Update allowed arcs documentation in route docstring
- [ ] Add test: admin calling `invited → active` gets 400
- [ ] Add test: admin calling `invited → pending` succeeds
- [ ] Add test: user calling `auth/activate` with valid token succeeds
- [ ] Consider: should `pending → active` also be blocked? (see §6)

---

## 8. Related Files

| File | Relevance |
|---|---|
| `backend/kernel/user/routes/users.py` | `transition_user_lifecycle` endpoint |
| `backend/kernel/auth/services/service.py` | `activate` method |
| `backend/kernel/user/services/service.py` | `transition_lifecycle` method |
| `backend/kernel/user/repos/user_repo.py` | Lifecycle transition logic |
| `backend/kernel/user/repos/client_user_repo.py` | CD lifecycle transition logic |
| `docs/architecture/adr-c02-identity-user-management-implementation.md` | D1, D11 decisions |

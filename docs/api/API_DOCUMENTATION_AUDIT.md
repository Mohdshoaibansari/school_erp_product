# API Documentation Audit

## Audit Methodology

1. **Module docstrings** — Does the file have a top-level docstring describing the routes it contains?
2. **Endpoint docstrings** — Does each `@router.*` decorated function have a `"""..."""` docstring?
3. **OpenAPI metadata** — Does each route have `summary=`, `description=`, `response_code` explanations?
4. **Response model docs** — Are DTOs documented with field descriptions?

## Current State

### Files WITH endpoint docstrings (good)
- `kernel/auth/routes/auth.py` — all 9 endpoints documented
- `business/tenant_institution/routes/platform.py` — all 11 endpoints documented

### Files MISSING endpoint docstrings (need work)
| File | Endpoints | Module docstring | Endpoint docstrings |
|---|---|---|---|
| `business/fees/routes/fee_types.py` | 5 | ✅ | ❌ |
| `business/fees/routes/fee_assignments.py` | 5 | ✅ | ❌ |
| `business/fees/routes/payments.py` | 2 | ✅ | ❌ |
| `business/homework/routes/homework_routes.py` | ~10 | ✅ | ❌ |
| `business/tenant_institution/routes/client_portal.py` | 13 | ✅ | ❌ |
| `kernel/user/routes/users.py` | 6 | ✅ | ✅ (partial) |
| `kernel/user/routes/identifiers.py` | 3 | ✅ | ❌ |
| `kernel/user/routes/lookups.py` | 3 | ✅ | ✅ (partial) |
| `kernel/user/routes/profiles.py` | 3 | ✅ | ❌ |
| `kernel/user/routes/roles.py` | 3 | ✅ | ❌ |
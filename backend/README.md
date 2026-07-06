# School ERP Backend

Python backend (FastAPI) for the School ERP platform.
Uses `uv` for dependency management.

## Structure

```
backend/
  kernel/              Kernel-tier modules (C-01 tenant, C-02 users, ...)
    app_factory.py     Module manifest composition + FastAPI app factory
    tenant_institution/  C-01 Tenant & Institution Management
  modules/             Business-tier modules (empty — future capabilities)
  migrations/          Single Alembic env (module-prefixed files)
  supabase/            Supabase CLI local config (tests only — Alembic owns schema)
  tests/               pytest test suite
```

## Development

```bash
uv sync                     # install dependencies
supabase start              # start local Supabase stack (Docker required)
alembic upgrade head        # apply migrations
pytest                      # run tests
```

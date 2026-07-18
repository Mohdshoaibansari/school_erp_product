# Homework Module — Design

## Structure
```
backend/business/homework/ — manifest, models, repos, services, routes, dependencies
```

## Schema (Migration 006)
3 tables: homework (RLS), submission (RLS), grade (RLS).
C-04 extension: 10 permissions + ~15 role_permissions.

## Key Patterns
Same as Fees: TenantAwareRepositoryBase, AuditEmitter, require_permission, ownership enforcement.

# ADR-0003: Supabase as backend platform

## Status

Accepted

## Context

The School ERP needs authentication (magic-link login), PostgreSQL persistence, file storage, and tenant data isolation. Building these from scratch is high effort and carries security risk. Alternatives: raw PostgreSQL with custom auth, Firebase, or AWS Cognito + RDS.

## Decision

Use Supabase as the backend platform for:

- **Auth**: Supabase Auth handles magic-link emails, session tokens, JWT verification. We store tenant membership in our `user_tenants` table linking `auth.users.id` to `tenants.id`. No password storage or custom auth code.
- **Database**: Supabase-managed PostgreSQL with Row Level Security policies for tenant isolation. RLS policies serve as a defense-in-depth layer even when kernel correctly filters by `tenant_id`.
- **Storage**: Supabase Storage for student documents and report cards.

The Fastify API server sits between clients and Supabase, using the Prisma client to query PostgreSQL and validating JWTs against Supabase Auth.

## Consequences

- **Easier**: Zero auth code to write and maintain. Battle-tested authentication. PostgreSQL is standard and migratable. RLS provides defense-in-depth against data leaks.
- **Harder**: Vendor lock-in to Supabase. Prisma abstracts Supabase-specific features (Realtime, PostgREST) — these are unavailable unless we bypass Prisma with raw SQL. Migration off Supabase would require replacing Auth flows but PostgreSQL and RLS policies are portable.
- **Mitigation**: Auth uses standard JWT — any OIDC provider can replace it. Storage uses S3-compatible API. Keep RLS policies in raw SQL migrations (not Prisma) for portability.

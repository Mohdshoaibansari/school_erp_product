# Homework Module — Impact Classification

> **Date:** 2026-07-18

## Summary

| Classification | Domain | What |
|---|---|---|
| **ADDED** | `homework` | New business module — 3 entities, ~12 endpoints, audit events |
| **MODIFIED** | `authorization` (C-04) | 10 new permission rows + ~15 role_permission rows |
| **NOT MODIFIED** | C-01, C-02, C-03, C-11 | No changes |

## ADDED: `homework` domain

- Module: `backend/business/homework/`
- Migration: `006_homework_module.py` (3 tables with RLS)
- Tests: `tests/test_homework.py`

## MODIFIED: `authorization` domain

- 10 permission rows (ON CONFLICT DO NOTHING)
- ~15 role_permission rows
- No C-04 code changes (DB-only)

## NOT MODIFIED

- C-01, C-02, C-03, C-11: consumed via existing interfaces, no endpoint changes
- Import-linter: no new contracts needed

## Test fixture impact

- Add `homework_manifest` to `create_app()` in conftest
- `AlwaysAllowEnforcer` override handles new permissions

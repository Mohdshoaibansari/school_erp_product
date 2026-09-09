# Tasks — C-06 Relationship Management Framework

> **Change:** add-c06-relationship-management
> **Date:** 2026-09-03

---

## 1. Database Schema (Alembic Migration)

- [x] 1.1 Create `relationship_type` table
- [x] 1.2 Create `contact_role` table
- [x] 1.3 Create `relationship_type_contact_role` table (compatibility matrix)
- [x] 1.4 Create `relationship` table (with normalized_pair)
- [x] 1.5 Create `contact_role_assignment` table
- [x] 1.6 Add RLS policies for all C-06 tables
- [x] 1.7 Seed default RelationshipTypes with inverse pairs
- [x] 1.8 Seed default ContactRoles
- [x] 1.9 Seed compatibility matrix
- [x] 1.10 Seed permissions in `permission` and `role_permission`

## 2. Models

- [x] 2.1 Create `RelationshipType` model
- [x] 2.2 Create `ContactRole` model
- [x] 2.3 Create `RelationshipTypeContactRole` model (compatibility)
- [x] 2.4 Create `Relationship` model
- [x] 2.5 Create `ContactRoleAssignment` model
- [x] 2.6 Update `__init__.py` exports

## 3. Repositories

- [x] 3.1 Create `RelationshipTypeRepo`
- [x] 3.2 Create `ContactRoleRepo`
- [x] 3.3 Create `RelationshipRepo`
- [x] 3.4 Create `ContactRoleAssignmentRepo`

## 4. Services

- [x] 4.1 Create `RelationshipTypeService` (create with inverse, list, validate)
- [x] 4.2 Create `ContactRoleService` (list, list compatible)
- [x] 4.3 Create `RelationshipService` (CRUD, temporal validation, symmetric normalization)
- [x] 4.4 Create `ContactRoleAssignmentService` (add, update, end, containment validation)
- [ ] 4.5 Integrate AuditEmitter

## 5. DTOs / Schemas

- [x] 5.1 Create DTOs for RelationshipType
- [x] 5.2 Create DTOs for ContactRole
- [x] 5.3 Create DTOs for Relationship
- [x] 5.4 Create DTOs for ContactRoleAssignment

## 6. Routes

- [x] 6.1 Create routes for RelationshipTypes
- [x] 6.2 Create routes for ContactRoles
- [x] 6.3 Create routes for Relationships
- [x] 6.4 Create routes for ContactRoleAssignments

## 7. Permissions

- [x] 7.1 Define new permissions (11 permissions)
- [x] 7.2 Seed permissions in database
- [x] 7.3 Update Casbin policies

## 8. Tests

- [x] 8.1 Unit tests for Relationship CRUD and temporal validation
- [x] 8.2 Unit tests for symmetric normalization
- [x] 8.3 Unit tests for ContactRole compatibility and containment
- [x] 8.4 Unit tests for RelationshipType change validation
- [x] 8.5 Integration tests for API/service/database interaction
- [x] 8.6 Concurrency tests for duplicate prevention

## 9. Documentation

- [x] 9.1 Update API documentation
- [x] 9.2 Run `openspec validate add-c06-relationship-management --type change --strict`

# Tasks — C-13 Address Management

> **Change:** add-c13-address-management
> **Date:** 2026-09-05

---

## 1. Database Schema (Alembic Migration)

- [x] 1.1 Create `entity_type` table
- [x] 1.2 Create `address_type` table
- [x] 1.3 Create `address_type_entity_type` table (compatibility matrix)
- [x] 1.4 Create `address` table
- [x] 1.5 Create `address_assignment` table
- [x] 1.6 Create `country` table
- [x] 1.7 Create `state` table
- [x] 1.8 Create `city` table
- [x] 1.9 Seed EntityTypes (INSTITUTION, PERSON)
- [x] 1.10 Seed AddressTypes (RESIDENTIAL, PERMANENT, CORRESPONDENCE, OFFICE, EMERGENCY)
- [x] 1.11 Seed compatibility matrix
- [x] 1.12 Seed geographic data (India)
- [x] 1.13 Seed permissions in `permission` and `role_permission`

## 2. Models

- [x] 2.1 Create `EntityType` model
- [x] 2.2 Create `AddressType` model
- [x] 2.3 Create `AddressTypeEntityType` model (compatibility)
- [x] 2.4 Create `Address` model
- [x] 2.5 Create `AddressAssignment` model
- [x] 2.6 Create `Country` model
- [x] 2.7 Create `State` model
- [x] 2.8 Create `City` model
- [x] 2.9 Update `__init__.py` exports

## 3. Repositories

- [x] 3.1 Create `EntityTypeRepo`
- [x] 3.2 Create `AddressTypeRepo`
- [x] 3.3 Create `AddressRepo`
- [x] 3.4 Create `AddressAssignmentRepo`
- [x] 3.5 Create `GeographicRepo`

## 4. Services

- [x] 4.1 Create `AddressService` (CRUD, correction, replacement)
- [x] 4.2 Create `AddressAssignmentService` (create, end, list)
- [x] 4.3 Create `AddressTypeService` (list, list compatible)
- [x] 4.4 Create `GeographicService` (list countries, states, cities)
- [x] 4.5 Integrate AuditEmitter

## 5. DTOs / Schemas

- [x] 5.1 Create DTOs for Address
- [x] 5.2 Create DTOs for AddressAssignment
- [x] 5.3 Create DTOs for AddressType
- [x] 5.4 Create DTOs for Geographic data

## 6. Routes

- [x] 6.1 Create routes for Address CRUD
- [x] 6.2 Create routes for Person addresses
- [x] 6.3 Create routes for Institution addresses
- [x] 6.4 Create routes for AddressTypes
- [x] 6.5 Create routes for Geographic reference data

## 7. Permissions

- [x] 7.1 Define new permissions (8 permissions)
- [x] 7.2 Seed permissions in database
- [x] 7.3 Update Casbin policies

## 8. Tests

- [x] 8.1 Unit tests for Address CRUD and validation
- [x] 8.2 Unit tests for geographic hierarchy validation
- [x] 8.3 Unit tests for AddressType compatibility
- [x] 8.4 Unit tests for temporal overlap prevention
- [x] 8.5 Unit tests for address replacement (transactional)
- [x] 8.6 Unit tests for address correction
- [x] 8.7 Integration tests for API/service/database interaction
- [x] 8.8 Authorization tests

## 9. Documentation

- [x] 9.1 Update API documentation
- [x] 9.2 Run `openspec validate add-c13-address-management --type change --strict`

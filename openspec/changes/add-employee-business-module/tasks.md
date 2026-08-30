## 1. Database migration

- [x] 1.1 Create Alembic migration (revision `024_add_employee_module`) creating the `employee` table with `id`, `client_id`, `institution_id`, `person_id`, `employee_no`, `joining_date`, `employment_type`, `employment_status`, `department`, `designation`, `created_at`, `updated_at`
- [x] 1.2 Add `CHECK` constraint on `employment_type` (`FULL_TIME`, `PART_TIME`, `CONTRACT`, `TEMPORARY`, `INTERN`, `CONSULTANT`) and on `employment_status` (`Hired`, `Active`, `On-Leave`, `Suspended`, `Retired`, `Resigned`, `Terminated`)
- [x] 1.3 Add `UNIQUE(person_id, institution_id)` and `UNIQUE(institution_id, employee_no)` constraints
- [x] 1.4 Add indexes on `institution_id`, `employee_no`, `person_id`, `employment_status`, `employment_type`, `department`
- [x] 1.5 Enable and force RLS on `employee` with tenant-scoped policies (`SELECT`/`INSERT`/`UPDATE`/`DELETE`) matching the `person` table pattern; grant table privileges to `test_tenant_user`
- [x] 1.6 Seed `employee.departments` and `employee.designations` config keys (C-08) with default value lists in the same migration
- [x] 1.7 Seed 7 `employee.*` permissions (`create`, `read`, `update`, `activate`, `suspend`, `deactivate`, `terminate`) and `role_permission` mappings (Admin/InstituteAdmin/Staff full set; HOD/Principal/Teacher `read`; no PlatformOwner)
- [x] 1.8 Provide `downgrade()` that drops policies → table → permissions → config keys in reverse order

## 2. Domain model

- [x] 2.1 Create `business/employee/models/employee.py` with the `Employee` SQLAlchemy model and `EmploymentType`/`EmploymentStatus` `StrEnum`s
- [x] 2.2 Add `EmploymentStatus` lifecycle transition rules (valid source→target map) as a pure domain helper with no framework imports
- [x] 2.3 Add `EmploymentStatus` `is_terminal` property (True for `Retired`/`Resigned`/`Terminated`)

## 3. Repository

- [x] 3.1 Create `business/employee/repos/employee_repo.py` with create/get/list/update persistence methods scoped by `client_id`/`institution_id`
- [x] 3.2 Implement `get_next_employee_number(session, institution_id)` using `SELECT … FOR UPDATE` (`with_for_update()`) and the `EMP-{inst_code}-{seq:06d}` format, mirroring the fees receipt-number generator

## 4. Application services

- [x] 4.1 Create `business/employee/services/dtos.py` with `EmployeeCreateRequest`, `EmployeeUpdateRequest`, `EmployeeResponse`, `EmployeeListResponse`, and `TerminateRequest(terminal_status)`
- [x] 4.2 Create `business/employee/services/service.py` with `CreateEmployee`, `GetEmployee`, `ListEmployees`, `UpdateEmployee`, `ActivateEmployee`, `SuspendEmployee`, `DeactivateEmployee`, `TerminateEmployee` use-cases
- [x] 4.3 Enforce department/designation validation against `employee.departments`/`employee.designations` config (via `config.get`) in create/update
- [x] 4.4 Enforce lifecycle transition rules (reject invalid transitions and terminal → non-terminal) in the transition use-cases
- [x] 4.5 Implement terminal cascade: on `Resigned`/`Terminated`/`Retired`, archive the `app_user` whose `institution_id` matches, via `person`, in the same transaction
- [x] 4.6 Generate `employee_no` on create and return DTOs (never ORM entities) from all use-cases

## 5. API routes

- [x] 5.1 Create `business/employee/routes/employees.py` with thin FastAPI routes: `POST /employees`, `GET /employees`, `GET /employees/{id}`, `PATCH /employees/{id}`
- [x] 5.2 Add transition routes: `POST /employees/{id}/activate`, `/suspend`, `/deactivate`, `/terminate`
- [x] 5.3 Guard every route with `Depends(require_permission("employee", "<action>"))` (no hardcoded role checks)

## 6. Module wiring

- [x] 6.1 Create `business/employee/dependencies.py` (service/repo wiring) and `business/employee/manifest.py` (register routes; document `employee.departments`/`employee.designations` config keys)
- [x] 6.2 Register the employee manifest in the app factory so routes load on startup
- [x] 6.3 Update `scripts/seed_data.py` to seed a sample employee linked to an existing `person` (disposable-DB; no backfill)

## 7. Tests

- [ ] 7.1 Domain tests: valid creation, invalid status transitions, terminal non-reactivation, `is_terminal`
- [ ] 7.2 Application tests: create/get/list/update + activate/suspend/deactivate/terminate, employee-number generation, department/designation validation, terminal cascade (including multi-account scoping)
- [ ] 7.3 API tests: each endpoint's happy path + 401/403/404 paths
- [ ] 7.4 AuthZ tests: authorized role allowed, unauthorized role denied, wrong institution denied, wrong client denied, PlatformOwner denied
- [ ] 7.5 RLS tests: Client A cannot read Client B employees; Institution A cannot read Institution B employees
- [ ] 7.6 Run full backend regression suite and confirm existing tests still pass
- [ ] 7.7 Run `openspec validate add-employee-business-module --type change --strict` before archive

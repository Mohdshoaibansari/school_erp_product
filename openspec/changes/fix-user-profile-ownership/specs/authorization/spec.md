# authorization — Delta Spec (UserProfile Permissions)

> **Change:** `fix-user-profile-ownership`
> **Domain:** C-04 Authorization
> **Delta type:** MODIFIED

---

## MODIFIED Requirements

### Requirement: user_profile permissions assigned to all roles (D13)

The `role_permission` table SHALL include:
- `user_profile.create` for Admin, client_director, institution_admin (institution scope)
- `user_profile.update` for ALL roles (institution scope)
- `user_profile.read` for ALL roles (institution scope)

#### Scenario: Teacher has user_profile.update
- WHEN querying `role_permission` for the Teacher role
- THEN the result includes `user_profile.update` with scope `institution`

#### Scenario: Student has user_profile.read
- WHEN querying `role_permission` for the Student role
- THEN the result includes `user_profile.read` with scope `institution`

#### Scenario: Admin has user_profile.create
- WHEN querying `role_permission` for the Admin role
- THEN the result includes `user_profile.create` with scope `institution`

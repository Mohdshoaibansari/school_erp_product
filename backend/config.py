"""Platform-wide configuration.

Centralized constants for middleware, auth, and platform operations.
"""

# Paths that do NOT require a tenant `client_id`.
# Platform owner accesses these without subdomain resolution.
# Update this list when adding new platform-level endpoints.
PLATFORM_PATHS = [
    "/api/v1/platform/",
    "/api/v1/config/",
    "/api/v1/lookups/",  # C-02 lookup tables: roles, user-categories, etc. Global read-only data needed for client/institution/user creation.
    "/api/auth/",
    "/health",
    "/docs",
    "/openapi.json",
]

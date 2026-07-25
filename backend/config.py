"""Platform-wide configuration.

Centralized constants for middleware, auth, and platform operations.
"""

# Paths that do NOT require a tenant `client_id`.
# Platform owner accesses these without subdomain resolution.
# Update this list when adding new platform-level endpoints.
PLATFORM_PATHS = [
    "/api/v1/platform/",
    "/api/v1/lookups/",
    "/api/v1/users/",
    "/api/v1/institutions/",
    "/api/auth/",
    "/health",
    "/docs",
    "/openapi.json",
]

"""C-08 Configuration Framework — kernel module.

Provides centralized runtime configuration for the platform:
- ConfigurationKey: registry of typed settings
- ConfigurationValue: scope-bound overrides
- ConfigurationAudit: change log
- config.get(key, institution_id=..., client_id=...): resolution API
- 12 REST endpoints under /api/v1/config/

C-08 is a kernel capability (per the platform capability roadmap §4).
Lives in backend/kernel/config/ — does not depend on any business module.
"""

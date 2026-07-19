"""Application entry point — creates FastAPI app with all modules registered."""

from kernel.app_factory import create_app

from business.tenant_institution.manifest import manifest as c01_manifest
from kernel.user.manifest import manifest as c02_manifest
from kernel.auth.manifest import manifest as c03_manifest
from kernel.authz.manifest import manifest as c04_manifest
from business.fees.manifest import manifest as fees_manifest
from business.homework.manifest import manifest as homework_manifest

app = create_app([
    c01_manifest,
    c02_manifest,
    c03_manifest,
    c04_manifest,
    fees_manifest,
    homework_manifest,
])

"""Test: app factory boots with zero modules registered (task 1.2 evidence)."""

from fastapi.testclient import TestClient

from kernel.app_factory import create_app
from business.tenant_institution.manifest import manifest as c01_manifest


def test_app_boots_with_zero_modules():
    """App factory creates a bootable app with an empty module list."""
    app = create_app(module_manifests=[])
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_app_boots_with_c01_manifest():
    """App factory composes the C-01 manifest without error."""
    app = create_app(module_manifests=[c01_manifest])
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200

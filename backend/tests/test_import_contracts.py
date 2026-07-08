"""Contract tests asserting C-01 import boundaries (A3, A4, 14b.2).

- ``test_kernel_imports_nothing_from_shared_or_business`` (A3): the kernel
  package imports nothing from ``shared`` / ``modules`` / ``business``.
- ``test_c01_services_is_published_interface`` (A4, 14b.2): cross-module imports
  of C-01 target the published ``services/`` interface only; ``repos/`` and
  ``models/`` are internal and not imported cross-module.
"""

import ast
import importlib
import pathlib
import pkgutil

import kernel
import business.tenant_institution


def test_kernel_imports_nothing_from_shared_or_business():
    """kernel package imports nothing from ``shared`` or ``modules`` (A3)."""
    kernel_pkg = importlib.import_module("kernel")
    forbidden_prefixes = ("shared", "modules", "business")

    for importer, modname, ispkg in pkgutil.walk_packages(
        kernel_pkg.__path__, prefix="kernel."
    ):
        try:
            mod = importlib.import_module(modname)
        except ImportError:
            continue

        # Check all module-level attributes for forbidden imports
        for attr_name in dir(mod):
            attr = getattr(mod, attr_name)
            mod_attr = getattr(attr, "__module__", None)
            if mod_attr:
                for prefix in forbidden_prefixes:
                    assert not mod_attr.startswith(prefix), (
                        f"kernel.{modname} imports from forbidden module '{mod_attr}' (A3 violation)"
                    )


def test_c01_services_is_published_interface():
    """14b.2, A4: ``services/`` is C-01's only published interface.

    Cross-module consumers must import from ``business.tenant_institution.services``
    only; ``repos/`` and ``models/`` are internal implementation packages and
    must not be imported from outside the ``business.tenant_institution`` package.
    ``services/`` MUST exist as a package (the published interface).
    """
    c01_root = pathlib.Path(business.tenant_institution.__file__).parent
    services_dir = c01_root / "services"
    repos_dir = c01_root / "repos"
    models_dir = c01_root / "models"
    # The published interface packages exist
    assert services_dir.is_dir(), (
        "business/tenant_institution/services/ must exist (published interface, A4)"
    )
    assert repos_dir.is_dir()
    assert models_dir.is_dir()

    internal_submodules = ("repos", "models")

    # Walk the kernel package OUTSIDE business.tenant_institution and assert no
    # import of ``business.tenant_institution.<internal_submodule>``.
    kernel_pkg = importlib.import_module("kernel")
    for importer, modname, ispkg in pkgutil.walk_packages(
        kernel_pkg.__path__, prefix="kernel."
    ):
        if modname.startswith("business.tenant_institution"):
            continue  # internal imports within C-01 are allowed (routes import repos/models)
        mod = importlib.import_module(modname)
        py_path = pathlib.Path(getattr(mod, "__file__", "") or "")
        if not py_path.exists():
            continue
        tree = ast.parse(py_path.read_text(encoding="utf-8"), filename=str(py_path))
        for node in ast.walk(tree):
            target = None
            if isinstance(node, ast.Import):
                target = node.names[0].name
            elif isinstance(node, ast.ImportFrom) and node.module:
                target = node.module
            if target and any(
                target == f"business.tenant_institution.{s}"
                or target.startswith(f"business.tenant_institution.{s}.")
                for s in internal_submodules
            ):
                raise AssertionError(
                    f"{modname} imports C-01 internal package '{target}' — "
                    "only business.tenant_institution.services is the published interface (A4, 14b.2)"
                )
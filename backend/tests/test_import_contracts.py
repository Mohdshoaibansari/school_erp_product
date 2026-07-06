"""Contract test asserting C-01 (kernel) imports nothing from shared/business (A3)."""

import importlib
import pkgutil

import kernel


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

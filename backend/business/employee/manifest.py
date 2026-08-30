"""Employee module — manifest (AGENTS.md §8).

Config keys consumed:
  - employee.departments  (JSON list of allowed department names)
  - employee.designations (JSON list of allowed designation names)
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI


class EmployeeManifest:
    """Employee business module manifest."""

    def __init__(self) -> None:
        self.name = "employee"
        self.tier = "business"

    def register_routes(self, app: FastAPI) -> None:
        from business.employee.routes.employees import router as employees_router
        app.include_router(employees_router)

    def register_casbin_policies(self, enforcer: Any) -> None:
        pass

    def on_startup(self) -> None:
        pass

    def on_shutdown(self) -> None:
        pass

    def register_cli(self, cli: Any) -> None:
        pass


manifest = EmployeeManifest()

"""Homework module — manifest (A5, D15)."""

from __future__ import annotations
from typing import Any
from fastapi import FastAPI


class HomeworkManifest:
    name = "homework"
    tier = "business"

    def register_routes(self, app: FastAPI) -> None:
        from business.homework.routes.homework_routes import hw_router, sub_router, grade_router
        app.include_router(hw_router)
        app.include_router(sub_router)
        app.include_router(grade_router)

    def register_casbin_policies(self, enforcer: Any) -> None:
        pass

    def on_startup(self) -> None:
        pass

    def on_shutdown(self) -> None:
        pass

    def register_cli(self, cli: Any) -> None:
        pass


manifest = HomeworkManifest()

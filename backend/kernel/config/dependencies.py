"""C-08 Configuration Framework — FastAPI dependencies (sync)."""

from __future__ import annotations

from fastapi import Depends
from sqlalchemy.orm import Session

from kernel.db import get_db
from kernel.config.services.configuration_service import ConfigurationService


def get_configuration_service(
    db: Session = Depends(get_db),
) -> ConfigurationService:
    """FastAPI dependency: build a ConfigurationService with the current DB session."""
    from kernel.config.resolver import config as cfg
    from kernel.config.notifier import get_notifier
    from kernel.config.repos.configuration_repo import ConfigurationRepository

    repo = ConfigurationRepository(db)
    notifier = get_notifier()
    return ConfigurationService(db=db, repo=repo, cache=cfg.cache, notifier=notifier)

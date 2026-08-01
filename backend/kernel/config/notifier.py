"""C-08 Configuration Framework — NOTIFY/LISTEN notifier (sync).

Multi-instance cache invalidation via PostgreSQL NOTIFY/LISTEN.
"""

from __future__ import annotations

import json
import logging
import os
import select
import threading
import time
from typing import Any

from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.orm import Session

from kernel.db import get_session_factory

logger = logging.getLogger(__name__)


class ConfigurationNotifier:
    """NOTIFY emit + LISTEN handler (background thread)."""

    def __init__(self) -> None:
        self._listener_thread: threading.Thread | None = None
        self._listen_conn = None
        self._running = False

    def notify(
        self,
        db: Session,
        op: str,
        table: str,
        key_id: str,
        row_id: str | None = None,
    ) -> None:
        """Emit a NOTIFY on the config_changes channel."""
        payload = json.dumps({"op": op, "table": table, "key_id": key_id, "id": row_id})
        try:
            db.execute(text(f"SELECT pg_notify('config_changes', :payload)"), {"payload": payload})
            # Don't commit here — let the calling service commit
        except Exception as e:
            logger.warning("[C-08 notifier] notify failed: %s", e)

    def start(self) -> None:
        """Start the LISTEN background thread."""
        if self._running:
            return
        self._running = True
        self._listener_thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._listener_thread.start()
        logger.info("[C-08 notifier] Started LISTEN thread on config_changes channel")

    def stop(self) -> None:
        """Stop the LISTEN background thread."""
        self._running = False
        # Wake up the poll() by cancelling the connection from this thread.
        # This causes poll() to raise an exception, the loop catches it and exits.
        if self._listen_conn is not None:
            try:
                self._listen_conn.cancel()  # interrupt any pending blocking call
            except Exception:
                pass
        if self._listener_thread is not None:
            self._listener_thread.join(timeout=3)
            if self._listener_thread.is_alive():
                logger.warning("[C-08 notifier] listener thread did not stop within 3s")
        if self._listen_conn is not None:
            try:
                self._listen_conn.close()
            except Exception:
                pass
        logger.info("[C-08 notifier] Stopped")

    def _listen_loop(self) -> None:
        """Background thread: poll for NOTIFY messages and patch the cache."""
        try:
            import psycopg2
            import psycopg2.extensions
        except ImportError:
            logger.warning("[C-08 notifier] psycopg2 not installed — NOTIFY/LISTEN disabled")
            return

        load_dotenv(".env")
        database_url = os.environ.get("DATABASE_URL")
        if not database_url:
            logger.warning("[C-08 notifier] DATABASE_URL not set — NOTIFY/LISTEN disabled")
            return

        try:
            if database_url.startswith("postgresql+asyncpg://"):
                database_url = database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
            self._listen_conn = psycopg2.connect(database_url)
            self._listen_conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
            cur = self._listen_conn.cursor()
            cur.execute("LISTEN config_changes;")
            logger.info("[C-08 notifier] LISTEN active on config_changes")
        except Exception as e:
            logger.warning("[C-08 notifier] LISTEN setup failed: %s", e)
            return

        import select

        from kernel.config.resolver import config as cfg

        while self._running:
            try:
                if self._listen_conn is None:
                    break
                # Use select() with timeout so we check self._running every second.
                # Without this, poll() blocks forever and stop() can't shut us down.
                if hasattr(select, 'select'):
                    ready = select.select([self._listen_conn], [], [], 1.0)
                    if not ready[0]:
                        continue  # timeout, loop back to check self._running
                self._listen_conn.poll()
                notifies = self._listen_conn.notifies
                if notifies:
                    for n in notifies:
                        try:
                            payload = json.loads(n.payload)
                            key_id = payload.get("key_id")
                            table = payload.get("table")
                            op = payload.get("op")
                            logger.debug(
                                "[C-08 notifier] NOTIFY op=%s table=%s key_id=%s",
                                op, table, key_id,
                            )
                            self._reload_and_patch(table, op, key_id, payload.get("id"))
                        except Exception as e:
                            logger.warning("[C-08 notifier] payload processing failed: %s", e)
                    self._listen_conn.notifies.clear()
            except Exception as e:
                logger.warning("[C-08 notifier] poll loop error: %s", e)
                time.sleep(1)
            time.sleep(0.1)

    def _reload_and_patch(
        self, table: str, op: str, key_id: str | None, row_id: str | None,
    ) -> None:
        """Reload the affected row from DB and patch the cache."""
        from kernel.config.models.configuration_models import (
            ConfigurationKey, ConfigurationValue,
        )
        from kernel.config.resolver import config as cfg

        session_factory = get_session_factory()
        with session_factory() as db:
            if table == "configuration_key" and key_id:
                k = db.get(ConfigurationKey, key_id)
                if k is not None:
                    if op == "DELETE":
                        cfg.cache.remove_key(str(k.id))
                    else:
                        cfg.cache.update_key(k)
                elif op == "DELETE":
                    cfg.cache.remove_key(key_id)

            elif table == "configuration_value" and row_id:
                v = db.get(ConfigurationValue, row_id)
                if v is not None:
                    if op == "DELETE":
                        cfg.cache.remove_value(
                            v.scope_type,
                            str(v.scope_id) if v.scope_id else None,
                            str(v.key_id),
                        )
                    else:
                        cfg.cache.add_value(v)


# Module-level singleton
_notifier_instance: ConfigurationNotifier | None = None


def get_notifier() -> ConfigurationNotifier:
    """Get the singleton notifier instance."""
    global _notifier_instance
    if _notifier_instance is None:
        _notifier_instance = ConfigurationNotifier()
    return _notifier_instance


def start_listener() -> None:
    """Convenience: start the notifier's LISTEN thread."""
    get_notifier().start()


def stop_listener() -> None:
    """Convenience: stop the notifier's LISTEN thread."""
    get_notifier().stop()

"""Run Alembic migrations (PostgreSQL) safely from application startup or the CLI.

Migrations use a dedicated owner engine (no `SET ROLE`), never the application engine, because DDL must run as the
table owner. A transaction-scoped advisory lock makes concurrent starts (several web/worker instances) safe: only one
migrates, the others wait and then find the schema at head. Render's free plan has no pre-deploy hook (ADR-0013), so
running at startup is the portable default; paid hosts can run `python -m app.database.migrate` as a pre-deploy step.
"""
from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy import create_engine, text

from app.core.config import settings

logger = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[2]
_LOCK_ID = 727_101  # arbitrary, constant advisory-lock key for MindDoc migrations


def alembic_config(url: str | None = None):
    from alembic.config import Config
    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(ROOT / "migrations"))
    cfg.set_main_option("sqlalchemy.url", (url or settings.database_url).replace("%", "%%"))
    return cfg


def upgrade_head(url: str | None = None) -> None:
    from alembic import command
    url = url or settings.database_url
    owner = create_engine(url, future=True)
    try:
        with owner.connect() as conn:
            conn.execute(text("SELECT pg_advisory_lock(:k)"), {"k": _LOCK_ID})
            try:
                cfg = alembic_config(url)
                cfg.attributes["connection"] = conn
                command.upgrade(cfg, "head")
                conn.commit()
            finally:
                conn.execute(text("SELECT pg_advisory_unlock(:k)"), {"k": _LOCK_ID})
                conn.commit()
        logger.info("migrations at head")
    finally:
        owner.dispose()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    upgrade_head()

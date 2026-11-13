"""Tenant context for every database transaction (ADR-0002, design G §4).

* `set_tenant(session, tenant_id)` records the tenant on the session and, on PostgreSQL, sets the transaction-local
  setting `app.tenant_id` that the row-level-security policies read. It is re-applied automatically at the start of
  every new transaction on that session (`after_begin`), so commits in the middle of a request keep the context.
* New rows of tenant-scoped models get `tenant_id` filled from the session when the caller did not set it, so child
  rows (chunks, messages, mentions, …) can never be written under the wrong tenant.
* Never use a session-level `SET`: on pooled connections it would leak into the next request. `set_config(…, true)`
  is transaction-local and is reset at commit/rollback.
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy import event, text
from sqlalchemy.orm import Session

TENANT_KEY = "tenant_id"


def _is_postgres(session_or_conn) -> bool:
    bind = session_or_conn.get_bind() if isinstance(session_or_conn, Session) else session_or_conn
    return bind.dialect.name == "postgresql"


def set_tenant(session: Session, tenant_id: Optional[int]) -> None:
    session.info[TENANT_KEY] = tenant_id
    if tenant_id is not None and _is_postgres(session):
        session.execute(text("SELECT set_config('app.tenant_id', :t, true)"), {"t": str(int(tenant_id))})


def current_tenant(session: Session) -> Optional[int]:
    return session.info.get(TENANT_KEY)


@event.listens_for(Session, "after_begin")
def _apply_tenant(session: Session, transaction, connection) -> None:
    tid = session.info.get(TENANT_KEY)
    if tid is not None and connection.dialect.name == "postgresql":
        connection.execute(text("SELECT set_config('app.tenant_id', :t, true)"), {"t": str(int(tid))})


@event.listens_for(Session, "before_flush")
def _fill_tenant(session: Session, flush_context, instances) -> None:
    tid = session.info.get(TENANT_KEY)
    if tid is None:
        return
    for obj in session.new:
        if hasattr(obj, "tenant_id") and getattr(obj, "tenant_id", None) is None and obj.__tablename__ not in (
                "users",):
            obj.tenant_id = tid

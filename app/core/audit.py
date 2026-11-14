"""Append-only, hash-chained audit trail per tenant (`audit_events`; the application role cannot change or delete
rows on PostgreSQL). Used for membership and disclosure actions: who invited whom, who joined a case with which role,
who issued a disclosure copy of a report."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.database.models import AuditEvent


def _digest(*parts: str) -> str:
    return hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()


def record(db: Session, tenant_id: int, actor_id: Optional[int], verb: str, object_type: str,
           object_id, payload: Optional[dict] = None) -> AuditEvent:
    payload_hash = hashlib.sha256(json.dumps(payload or {}, sort_keys=True, default=str).encode("utf-8")).hexdigest()
    prev = db.query(AuditEvent).filter(AuditEvent.tenant_id == tenant_id).order_by(AuditEvent.id.desc()).first()
    prev_hash = _digest(prev.prev_hash or "", prev.verb, prev.object_type, prev.object_id or "", prev.payload_hash) \
        if prev else None
    ev = AuditEvent(tenant_id=tenant_id, actor_id=actor_id, verb=verb, object_type=object_type,
                    object_id=None if object_id is None else str(object_id), payload_hash=payload_hash,
                    prev_hash=prev_hash, created_at=datetime.utcnow())
    db.add(ev)
    db.flush()
    return ev


def verify_chain(events: list[AuditEvent]) -> bool:
    """True when each event's `prev_hash` matches the event before it (events in id order)."""
    for a, b in zip(events, events[1:]):
        if b.prev_hash != _digest(a.prev_hash or "", a.verb, a.object_type, a.object_id or "", a.payload_hash):
            return False
    return True

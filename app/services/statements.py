"""Persisted bank-statement analysis (ADR-0011): run the engine on a stored original, keep one result per document.

The API reads the stored result; re-analysis (explicit refresh, a new engine version, or re-processing the document)
replaces it. Extracted values are stored exactly as read — reconciliation never edits them.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database.models import Document, ReconciliationCheck, Statement, StatementTxn

logger = logging.getLogger(__name__)

NOT_A_STATEMENT = "not_a_statement"
# Cheap pre-check before queueing a full analysis: a balance column plus debit/credit vocabulary.
_LIKELY = [re.compile(p, re.I) for p in (r"\bbalance\b", r"\b(debit|withdrawals?|dr)\b", r"\b(credit|deposits?|cr)\b")]


def engine_version() -> str:
    from app.finance.statements import ENGINE_VERSION
    return ENGINE_VERSION


def looks_like_statement(text: str) -> bool:
    head = (text or "")[:6000]
    return all(p.search(head) for p in _LIKELY)


def clear(db: Session, document_id: int) -> None:
    """Remove the stored analysis of a document (children first: works without database-level cascades)."""
    ids = [i for (i,) in db.query(Statement.id).filter(Statement.document_id == document_id).all()]
    if ids:
        db.query(StatementTxn).filter(StatementTxn.statement_id.in_(ids)).delete(synchronize_session=False)
        db.query(ReconciliationCheck).filter(ReconciliationCheck.statement_id.in_(ids)).delete(synchronize_session=False)
        db.query(Statement).filter(Statement.id.in_(ids)).delete(synchronize_session=False)


def _iso(d: Optional[str]) -> Optional[date]:
    return date.fromisoformat(d) if d else None


def analyse(db: Session, doc: Document) -> Statement:
    """Run the engine on the stored original and replace the stored result. Raises FileNotFoundError / ValueError."""
    from app.finance.statements import extract_statement
    if not (doc.filename or "").lower().endswith(".pdf"):
        raise ValueError("Statement analysis currently supports PDF statements")
    if not doc.source_path or not Path(doc.source_path).exists():
        raise FileNotFoundError("Original file is not available; upload it again")
    res = extract_statement(Path(doc.source_path).read_bytes())
    clear(db, doc.id)
    rows = res.rows
    stmt = Statement(
        tenant_id=doc.tenant_id, document_id=doc.id, engine_version=engine_version(),
        status=res.status if rows else NOT_A_STATEMENT, currency="INR",
        ifsc=(res.header or {}).get("ifsc"), account_masked=(res.header or {}).get("account"),
        opening_minor=res.opening if rows else None, closing_minor=res.closing if rows else None,
        period_start=_iso(rows[0].date) if rows else None, period_end=_iso(rows[-1].date) if rows else None,
        pages=res.pages, n_txns=len(rows),
        total_debit_minor=sum(r.debit for r in rows), total_credit_minor=sum(r.credit for r in rows),
        failed_checks=sum(c.status == "fail" for c in res.checks),
        inferred_directions=sum(r.direction_source == "inferred_from_balance" for r in rows),
        warnings=json.dumps(res.warnings or ([] if rows else ["no transactions found"])),
        created_at=datetime.utcnow())
    db.add(stmt)
    db.flush()
    for r in rows:
        box = res.row_boxes.get(r.seq)
        db.add(StatementTxn(
            tenant_id=doc.tenant_id, statement_id=stmt.id, seq=r.seq, txn_date=_iso(r.date), narration=r.narration,
            debit_minor=r.debit, credit_minor=r.credit, balance_minor=r.balance, page=r.page,
            box_x0=box[1] if box else None, box_top=box[2] if box else None,
            box_x1=box[3] if box else None, box_bottom=box[4] if box else None,
            direction_source=r.direction_source, amount_raw=r.amount_raw or None, balance_raw=r.balance_raw or None))
    for c in res.checks:
        if c.status == "pass" and not c.reason:
            continue  # plain passes are implied by the transactions; keep failures, flags and reversal pairs
        db.add(ReconciliationCheck(
            tenant_id=doc.tenant_id, statement_id=stmt.id, scope=c.scope, seq=c.seq, status=c.status,
            reason=c.reason or None, expected_minor=c.expected, observed_minor=c.observed,
            hypotheses=json.dumps(c.hypotheses) if c.hypotheses else None))
    if rows:
        doc.doc_type, doc.doc_type_confidence = "bank_statement", None  # set by the engine, not the classifier
    return stmt


def get_or_analyse(db: Session, doc: Document, refresh: bool = False) -> Statement:
    stmt = db.query(Statement).filter(Statement.document_id == doc.id).first()
    if stmt is not None and not refresh and stmt.engine_version == engine_version():
        return stmt
    stmt = analyse(db, doc)
    try:
        db.commit()
    except IntegrityError:  # a concurrent request stored it first
        db.rollback()
        stmt = db.query(Statement).filter(Statement.document_id == doc.id).one()
    return stmt


def payload(db: Session, stmt: Statement) -> dict:
    base = {"document_id": stmt.document_id, "engine_version": stmt.engine_version,
            "analysed_at": stmt.created_at, "warnings": json.loads(stmt.warnings or "[]")}
    if stmt.status == NOT_A_STATEMENT:
        return {**base, "is_statement": False}
    txns = (db.query(StatementTxn).filter(StatementTxn.statement_id == stmt.id).order_by(StatementTxn.seq).all())
    checks = (db.query(ReconciliationCheck).filter(ReconciliationCheck.statement_id == stmt.id)
              .order_by(ReconciliationCheck.id).all())
    return {
        **base, "is_statement": True, "status": stmt.status, "currency": stmt.currency,
        "header": {"ifsc": stmt.ifsc, "account": stmt.account_masked}, "pages": stmt.pages,
        "period": {"start": stmt.period_start, "end": stmt.period_end},
        "summary": {"opening_minor": stmt.opening_minor, "closing_minor": stmt.closing_minor,
                    "transactions": stmt.n_txns, "total_debit_minor": stmt.total_debit_minor,
                    "total_credit_minor": stmt.total_credit_minor, "failed_checks": stmt.failed_checks,
                    "inferred_directions": stmt.inferred_directions},
        "transactions": [{
            "seq": t.seq, "date": t.txn_date.isoformat(), "narration": t.narration or "",
            "debit_minor": t.debit_minor, "credit_minor": t.credit_minor, "balance_minor": t.balance_minor,
            "page": t.page, "direction_source": t.direction_source,
            "box": [t.box_x0, t.box_top, t.box_x1, t.box_bottom] if t.box_x0 is not None else None} for t in txns],
        "checks": [{
            "scope": c.scope, "seq": c.seq, "status": c.status, "reason": c.reason or "",
            "expected_minor": c.expected_minor, "observed_minor": c.observed_minor,
            "diff_minor": (c.observed_minor - c.expected_minor
                           if c.observed_minor is not None and c.expected_minor is not None else None),
            "hypotheses": json.loads(c.hypotheses) if c.hypotheses else []} for c in checks],
    }

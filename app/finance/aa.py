"""Import of Account Aggregator deposit data (ReBIT FI schema `deposit`, ADR-0015).

MindDoc does not act as an FIU or AA and requests no consent. It imports a *decrypted* deposit FI payload that the
customer already holds, validates it against the published schema's required structure, and maps it onto the same
transaction model and reconciliation as PDF statements.

Schema reference (checked 2026-11-11): https://specifications.rebit.org.in/api_schema/account_aggregator/documentation/deposit.html
namespace `http://api.rebit.org.in/FISchema/deposit`; Account(linkedAccRef, maskedAccNumber, type="deposit", version)
→ Summary(currentBalance, currency?, balanceDateTime, type, branch, facility, ifscCode, …) and
Transactions(startDate, endDate) → Transaction(type CREDIT|DEBIT, mode CASH|ATM|CARD|UPI|FT|OTHERS, amount,
currentBalance, transactionTimestamp, valueDate, txnId, narration, reference), all required.

The schema types `amount` as an XSD floating-point number; it is read from its decimal text (JSON numbers via
`Decimal`) and never converted to binary floating point (ADR-0010). Holder profile data (name, PAN, mobile, …) is not
read (an owner decision is open, docs/OWNER_ACTIONS.md §6); an analyst can set an account's holder by hand.
"""
from __future__ import annotations

import hashlib
import json
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Optional

from app.finance.money import Money, MoneyError
from app.finance.reconcile import TxnRow, reconcile

NS = "http://api.rebit.org.in/FISchema/deposit"
TXN_TYPES = {"CREDIT", "DEBIT"}
TXN_MODES = {"CASH", "ATM", "CARD", "UPI", "FT", "OTHERS"}
TXN_REQUIRED = ("type", "mode", "amount", "currentBalance", "transactionTimestamp", "valueDate", "txnId",
                "narration", "reference")
_FORBIDDEN_XML = re.compile(rb"<!\s*(DOCTYPE|ENTITY)", re.I)


class AAError(ValueError):
    """The payload is not a valid ReBIT deposit FI document (message is safe to show to the user)."""


@dataclass
class AAStatement:
    rows: list[TxnRow]
    status: str
    checks: list
    opening: Optional[int]
    closing: Optional[int]
    header: dict
    extras: dict                    # seq -> {"value_date", "reference", "external_id", "mode"}
    schema_version: str
    payload_sha256: str
    currency: str = "INR"
    warnings: list = field(default_factory=list)
    pages: int = 0
    row_boxes: dict = field(default_factory=dict)  # structured data has no page positions
    source: str = "aa_deposit"


def _norm(key: str) -> str:
    return key.lstrip("@_").lower()


def _get(d: dict, name: str):
    """Case-insensitive lookup tolerant of XML-to-JSON attribute prefixes (`@type`, `_type`)."""
    want = name.lower()
    for k, v in d.items():
        if _norm(k) == want:
            return v
    return None


def _from_json(data: bytes) -> tuple[dict, Optional[dict], Optional[dict], list]:
    try:
        obj = json.loads(data.decode("utf-8-sig"), parse_float=Decimal)
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        raise AAError(f"not valid JSON: {e}") from e
    if not isinstance(obj, dict):
        raise AAError("expected a JSON object with an Account")
    acc = _get(obj, "Account") if _get(obj, "maskedAccNumber") is None else obj
    if not isinstance(acc, dict):
        raise AAError("missing Account element")
    summary = _get(acc, "Summary")
    txns = _get(acc, "Transactions")
    if not isinstance(txns, dict):
        raise AAError("missing Transactions element")
    items = _get(txns, "Transaction")
    if isinstance(items, dict):
        items = [items]
    if not isinstance(items, list):
        raise AAError("missing Transaction entries")
    if not all(isinstance(t, dict) for t in items):
        raise AAError("each Transaction must be an object")
    flat = lambda d: {_norm(k): v for k, v in d.items() if not isinstance(v, (dict, list))}  # noqa: E731
    return flat(acc), (flat(summary) if isinstance(summary, dict) else None), flat(txns), [flat(t) for t in items]


def _from_xml(data: bytes) -> tuple[dict, Optional[dict], Optional[dict], list]:
    if _FORBIDDEN_XML.search(data[:4096]) or _FORBIDDEN_XML.search(data):
        raise AAError("XML with DOCTYPE or ENTITY declarations is not accepted")
    try:
        root = ET.fromstring(data)
    except ET.ParseError as e:
        raise AAError(f"not well-formed XML: {e}") from e

    def local(tag: str) -> str:
        return tag.split("}", 1)[1] if tag.startswith("{") else tag

    if local(root.tag) != "Account":
        raise AAError(f"root element must be Account, found {local(root.tag)}")
    if root.tag.startswith("{") and not root.tag.startswith("{" + NS + "}"):
        raise AAError(f"unexpected namespace {root.tag.split('}')[0][1:]} (expected {NS})")
    child = {local(c.tag): c for c in root}
    lower = lambda e: {k.lower(): v for k, v in e.attrib.items()}  # noqa: E731
    txns_el = child.get("Transactions")
    if txns_el is None:
        raise AAError("missing Transactions element")
    items = [lower(t) for t in txns_el if local(t.tag) == "Transaction"]
    summary = lower(child["Summary"]) if "Summary" in child else None
    return lower(root), summary, lower(txns_el), items


def _decimal(value, what: str) -> Decimal:
    if isinstance(value, bool) or value is None:
        raise AAError(f"{what}: missing or not a number")
    try:
        d = Decimal(str(value).replace(",", "").strip()) if not isinstance(value, Decimal) else value
    except InvalidOperation as e:
        raise AAError(f"{what}: {value!r} is not a number") from e
    if not d.is_finite():
        raise AAError(f"{what}: {value!r} is not a finite number")
    return d


def _minor(value, currency: str, what: str) -> int:
    try:
        return Money.from_decimal(_decimal(value, what), currency).minor
    except MoneyError as e:
        raise AAError(f"{what}: {e}") from e


def _timestamp(value, what: str) -> datetime:
    try:
        return datetime.fromisoformat(str(value).strip())
    except ValueError as e:
        raise AAError(f"{what}: {value!r} is not an ISO date-time") from e


def _date(value, what: str) -> date:
    try:
        return date.fromisoformat(str(value).strip()[:10])
    except ValueError as e:
        raise AAError(f"{what}: {value!r} is not an ISO date") from e


def parse_deposit(data: bytes, filename: str = "") -> AAStatement:
    """Validate and map a ReBIT deposit FI payload (JSON or XML). Raises AAError with a user-facing reason."""
    if not data or not data.strip():
        raise AAError("empty payload")
    is_xml = filename.lower().endswith(".xml") or data.lstrip()[:1] == b"<"
    acc, summary, txns_meta, items = (_from_xml if is_xml else _from_json)(data)

    if str(acc.get("type", "")).lower() != "deposit":
        raise AAError(f"Account type must be 'deposit' (got {acc.get('type')!r}); other FI types are not supported")
    for req in ("maskedaccnumber", "version", "linkedaccref"):
        if acc.get(req) in (None, ""):
            raise AAError(f"Account is missing required attribute {req}")
    version = str(acc["version"])
    try:
        v = Decimal(version)
    except InvalidOperation as e:
        raise AAError(f"Account version {version!r} is not a number") from e
    if not Decimal(0) <= v <= Decimal(2):
        raise AAError(f"Account version {version} is outside the schema range 0.0–2.0")
    for req in ("startdate", "enddate"):
        if not txns_meta.get(req):
            raise AAError(f"Transactions is missing required attribute {req}")
    start, end = _date(txns_meta["startdate"], "Transactions.startDate"), _date(txns_meta["enddate"], "Transactions.endDate")
    if not items:
        raise AAError("Transactions contains no Transaction entries")
    currency = str((summary or {}).get("currency") or "INR").upper()

    parsed = []
    for i, t in enumerate(items, 1):
        label = f"Transaction {i}" + (f" (txnId {t.get('txnid')})" if t.get("txnid") else "")
        for req in TXN_REQUIRED:
            if t.get(req.lower()) is None:
                raise AAError(f"{label}: missing required attribute {req}")
        kind, mode = str(t["type"]).upper(), str(t["mode"]).upper()
        if kind not in TXN_TYPES:
            raise AAError(f"{label}: type must be CREDIT or DEBIT (got {t['type']!r})")
        if mode not in TXN_MODES:
            raise AAError(f"{label}: mode must be one of {', '.join(sorted(TXN_MODES))} (got {t['mode']!r})")
        amount = _minor(t["amount"], currency, f"{label} amount")
        if amount < 0:
            raise AAError(f"{label}: amount must not be negative")
        parsed.append({"ts": _timestamp(t["transactiontimestamp"], f"{label} transactionTimestamp"),
                       "value_date": _date(t["valuedate"], f"{label} valueDate"), "kind": kind, "mode": mode,
                       "amount": amount, "amount_raw": str(t["amount"]),
                       "balance": _minor(t["currentbalance"], currency, f"{label} currentBalance"),
                       "balance_raw": str(t["currentbalance"]), "txn_id": str(t["txnid"]),
                       "narration": str(t["narration"]), "reference": str(t["reference"])})

    warnings = []
    ordered = sorted(parsed, key=lambda p: p["ts"])  # stable: equal timestamps keep their order
    if ordered != parsed:
        warnings.append("transactions were not in timestamp order; sorted by transactionTimestamp")
    outside = sum(not start <= p["ts"].date() <= end for p in ordered)
    if outside:
        warnings.append(f"{outside} transaction(s) fall outside the stated period {start}–{end}")

    rows, extras = [], {}
    for seq, p in enumerate(ordered, 1):
        rows.append(TxnRow(seq=seq, date=p["ts"].date().isoformat(),
                           debit=p["amount"] if p["kind"] == "DEBIT" else 0,
                           credit=p["amount"] if p["kind"] == "CREDIT" else 0,
                           balance=p["balance"], narration=p["narration"], page=0, direction_source="column",
                           amount_raw=p["amount_raw"], balance_raw=p["balance_raw"]))
        extras[seq] = {"value_date": p["value_date"].isoformat(), "reference": p["reference"],
                       "external_id": p["txn_id"], "mode": p["mode"]}

    closing = None
    if summary and summary.get("currentbalance") not in (None, "") and summary.get("balancedatetime"):
        at = _timestamp(summary["balancedatetime"], "Summary.balanceDateTime")
        if ordered[-1]["ts"] <= at and at.date() <= end:
            closing = _minor(summary["currentbalance"], currency, "Summary.currentBalance")
        else:
            warnings.append("summary balance is not dated within the period after the last transaction; "
                            "closing balance not checked")

    status, checks, opening = reconcile(rows, None, closing, source="text")
    header = {"ifsc": (summary or {}).get("ifsccode"), "account": acc.get("maskedaccnumber"),
              "account_type": (summary or {}).get("type"), "facility": (summary or {}).get("facility"),
              "period_start": start.isoformat(), "period_end": end.isoformat()}
    return AAStatement(rows=rows, status=status, checks=checks, opening=opening, closing=closing, header=header,
                       extras=extras, schema_version=version, payload_sha256=hashlib.sha256(data).hexdigest(),
                       currency=currency, warnings=warnings)


def render_text(st: AAStatement) -> str:
    """Plain-text rendering used for search and chat over imported data (amounts as exact decimals)."""
    def amt(minor: Optional[int]) -> str:
        return "" if minor is None else str(Money(minor, st.currency).to_decimal())
    lines = [f"Account Aggregator deposit statement (ReBIT schema version {st.schema_version})",
             f"Account {st.header.get('account')} · IFSC {st.header.get('ifsc') or '—'} · "
             f"{st.header.get('account_type') or ''} · period {st.header['period_start']} to {st.header['period_end']}",
             "Date | Type | Mode | Amount | Balance | Narration | Reference"]
    for r in st.rows:
        x = st.extras[r.seq]
        kind = "CREDIT" if r.credit else "DEBIT"
        lines.append(f"{r.date} | {kind} | {x['mode']} | {amt(r.credit or r.debit)} | {amt(r.balance)} | "
                     f"{r.narration} | {x['reference']}")
    return "\n".join(lines)

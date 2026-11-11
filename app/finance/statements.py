"""Layout-generic bank-statement extractor (ADR-0011; design E §S0–S4) + StatementBench adapter.

Pipeline for a text-layer PDF:
  words with boxes (pdfplumber) → lines → header line found with the lexicon (data file) → column model
  (text columns by left edges, amount columns anchored on right edges) → rows (a dated line starts a transaction;
  narration-only lines continue it; opening / brought-forward / carried-forward lines are special) → exact parsing
  (Money, paise) → reconciliation (app.finance.reconcile).
Coordinates are integers in tenths of a point; no floating point is used for money.
Scanned statements (OCR word boxes) feed the same functions from R4.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from app.finance.money import MoneyError, parse_amount, signed_balance
from app.finance.reconcile import TxnRow, reconcile

_LEX = json.loads(Path(__file__).with_name("statement_lexicon.json").read_text(encoding="utf-8"))
_AMOUNT_ROLES = ("debit", "credit", "amount", "balance")
_TEXT_ROLES = ("date", "value_date", "narration", "ref", "drcr")
_MONEY = re.compile(r"^\(?-?(?:₹|rs\.?|inr)?\d{1,3}(?:,\d{2,3})*(?:\.\d{2})\)?-?$|^\(?-?\d+\.\d{2}\)?-?$", re.I)
_SUFFIX = re.compile(r"^\(?(cr|dr)\.?\)?$", re.I)
_DATE_FORMATS = ["%d/%m/%y", "%d/%m/%Y", "%d-%m-%Y", "%d-%m-%y", "%d %b %Y", "%d %b %y", "%d-%b-%y", "%d-%b-%Y",
                 "%d.%m.%Y", "%d.%m.%y", "%Y-%m-%d", "%d %B %Y"]


def _tokens(text: str) -> list[str]:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).split()


_PHRASES = sorted(((tuple(_tokens(p)), role) for role, ps in _LEX["roles"].items() for p in ps),
                  key=lambda x: -len(x[0]))
_SPECIAL = {kind: [tuple(_tokens(p)) for p in ps] for kind, ps in _LEX["special_rows"].items()}


@dataclass
class Word:
    text: str
    x0: int
    x1: int
    top: int
    bottom: int
    page: int


@dataclass
class Column:
    role: str
    x0: int
    x1: int


@dataclass
class StatementResult:
    rows: list[TxnRow]
    status: str
    checks: list
    opening: Optional[int]
    closing: Optional[int]
    header: dict = field(default_factory=dict)
    column_source: str = "header"
    row_boxes: dict = field(default_factory=dict)   # seq -> (page, x0, top, x1, bottom) in tenths of a point
    pages: int = 0
    warnings: list = field(default_factory=list)


def parse_date(text: str) -> Optional[str]:
    t = " ".join(text.split())
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(t, fmt).date().isoformat()
        except ValueError:
            continue
    return None


# ------------------------------------------------------------------------------------------------- geometry
def _words_from_pdf(data: bytes) -> tuple[list[list[Word]], list[str]]:
    import io

    import pdfplumber
    pages, texts = [], []
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        for n, page in enumerate(pdf.pages, start=1):
            ws = page.extract_words(x_tolerance=1.5, y_tolerance=2, keep_blank_chars=False, use_text_flow=False)
            pages.append([Word(w["text"], int(round(w["x0"] * 10)), int(round(w["x1"] * 10)),
                               int(round(w["top"] * 10)), int(round(w["bottom"] * 10)), n) for w in ws])
            texts.append(page.extract_text() or "")
    return pages, texts


def _lines(words: list[Word], tol: int = 25) -> list[list[Word]]:
    out: list[list[Word]] = []
    for w in sorted(words, key=lambda w: (w.top, w.x0)):
        if out and abs(out[-1][0].top - w.top) <= tol:
            out[-1].append(w)
        else:
            out.append([w])
    return [sorted(line, key=lambda w: w.x0) for line in out]


def _header_columns(line: list[Word]) -> Optional[list[Column]]:
    stream = [(tok, i) for i, w in enumerate(line) for tok in _tokens(w.text)]
    cols, k = [], 0
    while k < len(stream):
        for phrase, role in _PHRASES:
            n = len(phrase)
            if tuple(t for t, _ in stream[k:k + n]) == phrase:
                first, last = line[stream[k][1]], line[stream[k + n - 1][1]]
                cols.append(Column(role, first.x0, last.x1))
                k += n
                break
        else:
            k += 1
    roles = {c.role for c in cols}
    if "date" in roles and "balance" in roles and len(roles) >= 3 and \
            (roles & {"debit", "credit", "amount"}):
        return cols
    return None


def _assign(line: list[Word], cols: list[Column]) -> dict[str, list[Word]]:
    """Put each word of a data line into a column. Money tokens go to the amount column whose header right edge is
    nearest; other tokens go to the text column whose left edge interval contains them."""
    cells: dict[str, list[Word]] = {}
    text_cols = sorted([c for c in cols if c.role in _TEXT_ROLES], key=lambda c: c.x0)
    amount_cols = [c for c in cols if c.role in _AMOUNT_ROLES]
    last_money: Optional[tuple[str, Word]] = None
    for w in line:
        if _MONEY.match(w.text) and amount_cols:
            best = min(amount_cols, key=lambda c: abs(c.x1 - w.x1))
            if abs(best.x1 - w.x1) <= 600 or w.x0 >= min(c.x0 for c in amount_cols) - 100:
                cells.setdefault(best.role, []).append(w)
                last_money = (best.role, w)
                continue
        if _SUFFIX.match(w.text) and last_money and 0 <= w.x0 - last_money[1].x1 <= 150:
            cells.setdefault(last_money[0], []).append(w)
            continue
        owner = None
        for i, c in enumerate(text_cols):
            right = text_cols[i + 1].x0 - 20 if i + 1 < len(text_cols) else (
                min((a.x0 for a in amount_cols if a.x0 > c.x0), default=10 ** 9) - 20)
            if c.x0 - 40 <= w.x0 < right:
                owner = c.role
                break
        if owner:
            cells.setdefault(owner, []).append(w)
            last_money = None
    return cells


def _cell_text(cells, role) -> str:
    return " ".join(w.text for w in cells.get(role, []))


def _money(cells, role) -> tuple[Optional[int], Optional[str], str]:
    """(minor units or None, printed side CR/DR or None, raw text)"""
    ws = cells.get(role, [])
    if not ws:
        return None, None, ""
    raw = " ".join(w.text for w in ws)
    nums = [w.text for w in ws if _MONEY.match(w.text)]
    side = next((_SUFFIX.match(w.text).group(1).upper() for w in ws if _SUFFIX.match(w.text)), None)
    if not nums:
        return None, side, raw
    try:
        p = parse_amount(nums[0])
    except MoneyError:
        return None, side, raw
    return abs(p.money.minor), side or p.side, raw


def _special(text: str) -> Optional[str]:
    toks = tuple(_tokens(text))
    for kind, phrases in _SPECIAL.items():
        for ph in phrases:
            n = len(ph)
            if any(toks[i:i + n] == ph for i in range(len(toks) - n + 1)):
                return kind
    return None


_HEADER_PATTERNS = {
    "opening": re.compile(r"opening balance\s*[:\-]?\s*(-?[\d,]+\.\d{2})\s*(cr|dr)?", re.I),
    "closing": re.compile(r"closing balance\s*[:\-]?\s*(-?[\d,]+\.\d{2})\s*(cr|dr)?", re.I),
    "ifsc": re.compile(r"\bIFSC\s*(?:code)?\s*[:\-]?\s*([A-Z]{4}0[A-Z0-9]{6})\b"),
    "account": re.compile(r"account\s*(?:no|number)\.?\s*[:\-]?\s*([X\d*]{6,20})", re.I),
}


def _header_value(texts: list[str], key: str) -> Optional[int]:
    for t in texts:
        m = _HEADER_PATTERNS[key].search(t)
        if m:
            try:
                p = parse_amount(m.group(1) + (" " + m.group(2) if m.group(2) else ""))
                return signed_balance(p).minor
            except MoneyError:
                return None
    return None


# ------------------------------------------------------------------------------------------------ extraction
def extract_statement(data: bytes) -> StatementResult:
    pages, texts = _words_from_pdf(data)
    rows: list[TxnRow] = []
    boxes: dict[int, tuple] = {}
    cols: Optional[list[Column]] = None
    warnings: list[str] = []
    opening_row: Optional[int] = None
    current: Optional[TxnRow] = None
    current_words: list[Word] = []

    def close_row():
        nonlocal current, current_words
        if current is not None:
            xs = current_words
            boxes[current.seq] = (current.page, min(w.x0 for w in xs), min(w.top for w in xs),
                                  max(w.x1 for w in xs), max(w.bottom for w in xs))
            rows.append(current)
        current, current_words = None, []

    for page_words in pages:
        lines = _lines(page_words)
        start = 0
        for i, line in enumerate(lines):
            hc = _header_columns(line)
            if hc:
                cols, start = hc, i + 1
                break
        if cols is None:
            continue
        for line in lines[start:]:
            cells = _assign(line, cols)
            date_iso = parse_date(_cell_text(cells, "date"))
            line_text = " ".join(w.text for w in line)
            kind = _special(_cell_text(cells, "narration") or line_text) if not date_iso else None
            if kind:
                close_row()
                bal, side, _ = _money(cells, "balance")
                if kind == "opening" and bal is not None and opening_row is None and not rows:
                    opening_row = -bal if side == "DR" else bal
                continue
            if date_iso:
                close_row()
                debit, _, draw = _money(cells, "debit")
                credit, _, craw = _money(cells, "credit")
                amount, aside, araw = _money(cells, "amount")
                bal, bside, braw = _money(cells, "balance")
                src = "column"
                if amount is not None and debit is None and credit is None:
                    drcr = _cell_text(cells, "drcr").strip().upper()
                    side = aside or ("DR" if drcr.startswith("D") else "CR" if drcr.startswith("C") else None)
                    if side == "DR":
                        debit, credit, src = amount, 0, "suffix"
                    elif side == "CR":
                        debit, credit, src = 0, amount, "suffix"
                    else:
                        debit, credit, src = amount, 0, "unknown"
                current = TxnRow(seq=len(rows) + 1, date=date_iso, debit=debit or 0, credit=credit or 0,
                                 balance=None if bal is None else (-bal if bside == "DR" else bal),
                                 narration=_cell_text(cells, "narration"), page=line[0].page,
                                 direction_source=src, amount_raw=draw or craw or araw, balance_raw=braw)
                current_words = list(line)
                continue
            if current is not None:
                narr = cells.get("narration", [])
                others = [w for r, ws in cells.items() if r not in ("narration", "ref") for w in ws]
                if narr and not others:
                    joiner = "" if current.narration.endswith("/") else " "
                    current.narration = (current.narration + joiner + " ".join(w.text for w in narr)).strip()
                    current_words.extend(line)
                    continue
                close_row()  # anything else ends the table region (footer, totals, page furniture)
        close_row()

    if cols is None:
        warnings.append("no transaction table header found")
    opening = _header_value(texts[:1], "opening")
    if opening is None:
        opening = opening_row
    closing = _header_value(texts[-1:], "closing")
    status, checks, opening_used = reconcile(rows, opening, closing, source="text")
    header = {"ifsc": None, "account": None}
    for key in ("ifsc", "account"):
        m = _HEADER_PATTERNS[key].search(texts[0] if texts else "")
        header[key] = m.group(1) if m else None
    return StatementResult(rows=rows, status=status, checks=checks, opening=opening_used, closing=closing,
                           header=header, row_boxes=boxes, pages=len(pages), warnings=warnings)


def extract_for_benchmark(pdf_path) -> dict:
    res = extract_statement(Path(pdf_path).read_bytes())
    return {"opening_minor": res.opening, "status": res.status,
            "rows": [{"date": r.date, "debit_minor": r.debit, "credit_minor": r.credit,
                      "balance_minor": r.balance, "narration": r.narration} for r in res.rows]}

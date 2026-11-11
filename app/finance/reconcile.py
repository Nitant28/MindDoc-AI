"""Deterministic running-balance reconciliation with diagnosis (design E §S5, ADR-0011).

Never changes an extracted value. Every check is recorded with expected, observed and difference (minor units), and a
failing check carries ranked, deterministic hypotheses for the reviewer.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

STATUS_RECONCILED = "reconciled"
STATUS_FLAGS = "reconciled_with_flags"
STATUS_REVIEW = "needs_review"
STATUS_NOT_CHECKABLE = "not_checkable"


@dataclass
class TxnRow:
    seq: int
    date: str                     # ISO date
    debit: int                    # minor units, >= 0
    credit: int                   # minor units, >= 0
    balance: Optional[int]        # signed minor units (overdraft negative), None if not printed
    narration: str = ""
    page: int = 1
    direction_source: str = "column"     # column | suffix | inferred_from_balance | unknown
    amount_raw: str = ""
    balance_raw: str = ""


@dataclass
class Check:
    scope: str                    # row | statement | opening
    seq: Optional[int]
    expected: Optional[int]
    observed: Optional[int]
    status: str                   # pass | fail | not_checkable
    reason: str = ""
    hypotheses: list = field(default_factory=list)

    @property
    def diff(self) -> Optional[int]:
        if self.expected is None or self.observed is None:
            return None
        return self.observed - self.expected


def _digit_variants(n: int) -> set:
    """Values one OCR-style edit away from n: one digit substituted, two adjacent digits swapped, one digit dropped
    or inserted, decimal point shifted by one place."""
    s = str(abs(n))
    out = set()
    for i in range(len(s)):
        for d in "0123456789":
            if d != s[i]:
                out.add(int(s[:i] + d + s[i + 1:]))
        if i + 1 < len(s):
            out.add(int(s[:i] + s[i + 1] + s[i] + s[i + 2:]))
        if len(s) > 1:
            out.add(int(s[:i] + s[i + 1:]))
    for i in range(len(s) + 1):
        for d in "0123456789":
            out.add(int(s[:i] + d + s[i:]))
    out |= {abs(n) * 10, abs(n) // 10}
    out.discard(abs(n))
    return out


def infer_directions(rows: list[TxnRow], opening: Optional[int]) -> None:
    """For rows whose direction is unknown, use the balance arithmetic to choose; never alter amounts."""
    prev = opening
    for r in rows:
        if r.direction_source == "unknown" and prev is not None and r.balance is not None:
            amount = r.debit or r.credit
            if prev + amount == r.balance and prev - amount != r.balance:
                r.credit, r.debit, r.direction_source = amount, 0, "inferred_from_balance"
            elif prev - amount == r.balance and prev + amount != r.balance:
                r.debit, r.credit, r.direction_source = amount, 0, "inferred_from_balance"
        if r.balance is not None:
            prev = r.balance
        elif prev is not None:
            prev = prev + r.credit - r.debit


# Hypothesis order shown to the reviewer. Corroborated explanations (other rows confirm them) come first. A one-edit
# amount misread and a missing transaction explain the same balances equally well; which is likelier depends on how
# the values were read: a PDF text layer carries exact characters (a dropped or merged row is the common failure),
# OCR misreads digits.
RANK = {
    "text": ["follows_previous_error", "amount_unreadable", "balance_ocr_suspect", "order_ambiguous", "direction_suspect", "missing_row_suspect", "amount_ocr_suspect"],
    "ocr": ["follows_previous_error", "amount_unreadable", "balance_ocr_suspect", "order_ambiguous", "direction_suspect", "amount_ocr_suspect", "missing_row_suspect"],
}


def reconcile(rows: list[TxnRow], opening: Optional[int], closing: Optional[int],
              source: str = "text") -> tuple[str, list[Check], Optional[int]]:
    """Return (status, checks, opening_used). Opening may be derived from the first row (then marked).

    `source` ("text" | "ocr") only orders the hypotheses of a failing check; it never changes a pass/fail result."""
    checks: list[Check] = []
    if not rows:
        return STATUS_NOT_CHECKABLE, checks, opening
    if all(r.balance is None for r in rows):
        return STATUS_NOT_CHECKABLE, [Check("statement", None, None, None, "not_checkable",
                                            "unreconcilable_no_balance")], opening
    infer_directions(rows, opening)
    derived = False
    if opening is None and rows[0].balance is not None:
        opening = rows[0].balance - rows[0].credit + rows[0].debit
        derived = True
        checks.append(Check("opening", rows[0].seq, None, opening, "not_checkable", "opening_derived"))

    prev, segment = opening, []
    for i, r in enumerate(rows):
        segment.append(r)
        if r.balance is None:
            continue
        expected = prev + sum(x.credit - x.debit for x in segment)
        if expected == r.balance:
            checks.append(Check("row", r.seq, expected, r.balance, "pass"))
        else:
            hyps = _diagnose(rows, i, prev, segment, expected, opening, source)
            follow = _follows_previous(checks, rows, segment, r)
            if follow:
                hyps.insert(0, follow)
            checks.append(Check("row", r.seq, expected, r.balance, "fail", "balance_mismatch", hyps))
        prev, segment = r.balance, []

    final = rows[-1].balance if rows[-1].balance is not None else prev
    if closing is not None:
        checks.append(Check("statement", None, closing, final, "pass" if closing == final else "fail",
                            "" if closing == final else "closing_mismatch"))
    for a, b in _reversal_pairs(rows):
        checks.append(Check("row", b.seq, None, None, "pass", "reversal_pair", [{"pairs_with": a.seq}]))

    fails = [c for c in checks if c.status == "fail"]
    if fails:
        status = STATUS_REVIEW
    elif derived or any(r.direction_source in ("inferred_from_balance", "unknown") for r in rows):
        status = STATUS_FLAGS
    else:
        status = STATUS_RECONCILED
    return status, checks, opening


def _diagnose(rows, i, prev, segment, expected, opening=None, source="text") -> list:
    r = rows[i]
    hyps = []
    amount = r.debit or r.credit
    # no amount could be read for this row: show what the balances imply (the stored value stays as read)
    if len(segment) == 1 and not amount and r.balance is not None:
        hyps.append({"code": "amount_unreadable", "detail": "no amount was read for this row; the balances imply "
                                                            "this amount", "implied": abs(r.balance - prev),
                     "direction": "credit" if r.balance > prev else "debit"})
    # direction swapped
    if len(segment) == 1 and amount and prev - (r.credit - r.debit) == r.balance:
        hyps.append({"code": "direction_suspect", "detail": "reconciles if the direction is reversed"})
    # one-edit amount error (OCR / transcription)
    if len(segment) == 1 and amount:
        implied = abs(r.balance - prev)
        if implied in _digit_variants(amount):
            hyps.append({"code": "amount_ocr_suspect", "detail": "amount differs from the implied amount by one edit",
                         "extracted": amount, "implied": implied})
    # balance misread: the next row reconciles from the expected value instead (corroborated by that row)
    if i + 1 < len(rows) and rows[i + 1].balance is not None and r.balance is not None:
        nxt = rows[i + 1]
        if expected + nxt.credit - nxt.debit == nxt.balance:
            hyps.append({"code": "balance_ocr_suspect", "detail": "the following row reconciles from the expected "
                                                               "balance", "observed": r.balance, "implied": expected})
    # same-date rows printed or read in a different order
    order = _same_date_order(rows, i, opening)
    if order:
        hyps.append({"code": "order_ambiguous", "detail": "rows reconcile in a different same-date order",
                     "order": order})
    # missing row: a constant offset after which the following rows reconcile again
    if r.balance is not None and not any(h["code"] in ("balance_ocr_suspect", "order_ambiguous") for h in hyps):
        offset = r.balance - expected
        run, checked, ok = r.balance, 0, True
        for x in rows[i + 1:i + 4]:
            run = run + x.credit - x.debit
            if x.balance is not None:
                if run != x.balance:
                    ok = False
                    break
                run, checked = x.balance, checked + 1
        if ok and checked:
            hyps.append({"code": "missing_row_suspect", "detail": "a transaction of net amount appears to be "
                                                                 "missing before this row; later rows reconcile",
                         "net": offset})
        elif ok and i == len(rows) - 1:
            hyps.append({"code": "missing_row_suspect", "detail": "a transaction of net amount may be missing before "
                                                                 "this row (last row: cannot be corroborated)",
                         "net": offset})
    rank = RANK.get(source, RANK["text"])
    hyps.sort(key=lambda h: rank.index(h["code"]) if h["code"] in rank else len(rank))
    return hyps


def _follows_previous(checks, rows, segment, r) -> Optional[dict]:
    """A failure that is only the knock-on effect of an earlier failing row's top hypothesis (a misread balance on the
    previous row, or same-date rows in another order) is labelled as such, so the reviewer is sent to the root cause."""
    row_checks = [c for c in checks if c.scope == "row"]
    fails = [c for c in row_checks if c.status == "fail" and c.hypotheses]
    if not fails:
        return None
    by_seq = {c.seq: c for c in row_checks}

    def root_of(c):
        while c.hypotheses and c.hypotheses[0]["code"] == "follows_previous_error":
            c = by_seq[c.hypotheses[0]["row"]]
        return c

    delta = sum(x.credit - x.debit for x in segment)
    # misread balance: only the very next balance row is affected
    if row_checks[-1] is fails[-1]:
        root = root_of(fails[-1])
        top = root.hypotheses[0] if root.hypotheses else None
        if top and top["code"] == "balance_ocr_suspect" and root is fails[-1] and top["implied"] + delta == r.balance:
            return {"code": "follows_previous_error", "row": root.seq,
                    "detail": f"reconciles if row {root.seq}'s printed balance is the misread one"}
    # same-date order: rows inside the flagged block, and the first row after it
    root = root_of(fails[-1])
    top = root.hypotheses[0] if root.hypotheses else None
    if top and top["code"] == "order_ambiguous":
        if r.seq in top["order"]:
            return {"code": "follows_previous_error", "row": root.seq,
                    "detail": f"part of the same-date block flagged at row {root.seq}"}
        pos = {x.seq: k for k, x in enumerate(rows)}
        block_end = max(pos[q] for q in top["order"])
        if pos.get(r.seq) == block_end + 1:
            last = rows[pos[top["order"][-1]]]
            if last.balance + delta == r.balance:
                return {"code": "follows_previous_error", "row": root.seq,
                        "detail": f"reconciles once the same-date rows flagged at row {root.seq} are reordered"}
    return None


def _same_date_order(rows, i, opening, limit: int = 12) -> Optional[list]:
    """If the contiguous block of rows sharing row i's date reconciles in another order (and the row after the block
    then reconciles too), return that order as a list of seqs. Depth-first search over the block, bounded by `limit`."""
    d = rows[i].date
    lo, hi = i, i
    while lo > 0 and rows[lo - 1].date == d:
        lo -= 1
    while hi + 1 < len(rows) and rows[hi + 1].date == d:
        hi += 1
    block = rows[lo:hi + 1]
    if not 2 <= len(block) <= limit or any(x.balance is None for x in block):
        return None
    base = rows[lo - 1].balance if lo > 0 else opening
    if base is None:
        return None
    after = rows[hi + 1] if hi + 1 < len(rows) and rows[hi + 1].balance is not None else None

    def dfs(run, remaining, path):
        if not remaining:
            if after is None or run + after.credit - after.debit == after.balance:
                return path
            return None
        for k, x in enumerate(remaining):
            if run + x.credit - x.debit == x.balance:
                got = dfs(x.balance, remaining[:k] + remaining[k + 1:], path + [x])
                if got:
                    return got
        return None

    found = dfs(base, list(block), [])
    if found and [x.seq for x in found] != [x.seq for x in block]:
        return [x.seq for x in found]
    return None


def _reversal_pairs(rows):
    markers = ("REV", "RTN", "RETURN", "REVERSAL")
    for j, b in enumerate(rows):
        if b.credit and any(m in b.narration.upper() for m in markers):
            for a in reversed(rows[max(0, j - 10):j]):
                if a.debit == b.credit:
                    yield a, b
                    break

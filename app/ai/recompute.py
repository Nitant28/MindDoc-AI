"""Recomputation and table reading for the claim verifier (R6).

The LLM never computes numbers (ADR-0007). When an answer states a figure that the cited passage does not print,
the verifier asks whether it can be computed from the passage's own figures with exact decimal arithmetic, and
records the derivation so a reviewer can check it:

  durations     36 months = 3 years; 16 quarterly instalments = 4 years
  periods       ₹1,50,000 per month × 12 = ₹18,00,000 a year (only when the claim itself says year/annual)
  sums          a + b, a − b (any two figures, as in v2); the total of a statement's debit or credit column
  percent-of    18% of ₹24,00,000 = ₹4,32,000; the base plus or minus that share (a total including tax)
  products      12 bales × ₹96,000 = ₹11,52,000 (a count times an amount); percent-of on that product
  shares        a ÷ b as a percentage, its complement, and the change between them — only between figures whose
                labels the claim names ("distress sale value ... of the fair market value")
  ratios        a ÷ b as a whole number ("the deposit equals six months' rent"), with the same label rule
  intervals     days / weeks / months / years between two full dates in the passage

Rounding: an exact claim must match to the paisa; a percentage may be rounded to the precision the claim states;
"about/roughly" allows 5% on amounts and counts and one percentage point on percentages.

Tables (pipe or Markdown) are read with the bank-statement header lexicon (app/finance/statement_lexicon.json), so
"Withdrawals (Dr)" is a debit column. Two value-level checks use the passage's figures:

  flow          an amount that sits only in a debit (credit) column, or that the passage says was debited/withdrawn
                (credited/deposited), must not be described as coming in (going out)
  from → to     "rose from A to B" with B below A contradicts itself; "increased to B" contradicts a passage in which
                the same figure went from A down to B
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Callable, Optional

from app.finance.statements import header_role

D = Decimal
HUNDRED = D(100)

# --------------------------------------------------------------------------------------------------- tables


@dataclass
class Table:
    header: list[str]
    roles: list[Optional[str]]
    rows: dict[int, list[str]] = field(default_factory=dict)  # line index -> cells
    leading_pipe: dict[int, bool] = field(default_factory=dict)  # "| a | b |" vs "a | b"


_SEP_CELL = re.compile(r"^:?-{2,}:?$")
_CELL_NUM = re.compile(r"^\(?(?:₹|rs\.?|inr)?\s*(\d{1,3}(?:,\d{2,3})+(?:\.\d+)?|\d+(?:\.\d+)?)\)?(?:\s*(?:cr|dr))?$", re.I)


def _cells(line: str) -> list[str]:
    body = line.strip()
    if body.startswith("|"):
        body = body[1:]
    if body.endswith("|"):
        body = body[:-1]
    return [c.strip() for c in body.split("|")]


def parse_tables(text: str) -> list[Table]:
    """Pipe-delimited tables ("a | b | c" or Markdown "| a | b |") whose first row is a header of words."""
    tables: list[Table] = []
    cur: Optional[Table] = None
    for i, line in enumerate(text.splitlines()):
        if line.count("|") < 2:
            cur = None
            continue
        cells = _cells(line)
        if all(not c or _SEP_CELL.match(c) for c in cells):
            continue  # Markdown separator row
        if cur is None:
            wordy = sum(bool(re.search(r"[A-Za-z]", c)) and not re.search(r"\d{2}", c) for c in cells)
            if len(cells) >= 3 and wordy >= len(cells) - 1:
                cur = Table(cells, [header_role(c) for c in cells])
                tables.append(cur)
            continue
        if len(cells) == len(cur.header):
            cur.rows[i] = cells
            cur.leading_pipe[i] = line.strip().startswith("|")
    return tables


def _cell_value(cell: str) -> Optional[Decimal]:
    m = _CELL_NUM.match(cell.strip())
    if not m:
        return None
    try:
        return D(m.group(1).replace(",", ""))
    except InvalidOperation:
        return None


def column_totals(tables: list[Table]) -> list[tuple[Decimal, str]]:
    out = []
    for t in tables:
        for k, role in enumerate(t.roles):
            if role in ("debit", "credit"):
                vals = [v for cells in t.rows.values() if (v := _cell_value(cells[k])) is not None]
                if len(vals) >= 2:
                    out.append((sum(vals), f"total of the {t.header[k]} column = {fmt(sum(vals), True)}"))
    return out


# -------------------------------------------------------------------------------------------------- figures

@dataclass
class Fig:
    value: Decimal
    pct: bool
    approx: bool
    text: str
    pos: int
    decimals: int
    money: bool
    unit: Optional[str] = None       # duration unit: day, week, month, quarter, half, year
    freq: Optional[str] = None       # frequency bound to the figure (monthly, annual, ...)
    label: frozenset = frozenset()   # content words that name the figure
    column: Optional[str] = None     # table column role (debit, credit, balance, ...)
    header: Optional[str] = None
    per_unit: bool = False           # a rate per item ("₹64,000 per tonne"), not per period
    ratio_phrase: bool = False       # a measure of something else ("six months' rent")


_MONEY_BEFORE = re.compile(r"(?:₹|\brs\.?|\binr)\s*$", re.I)
_SCALE_WORD = re.compile(r"lakh|lac|crore|\bcr\b|million|\bmn\b|billion|\bbn\b|thousand", re.I)
_UNIT_AFTER = re.compile(
    r"^[\s-]*(?:equal\s+)?(?:(quarterly|monthly|half-yearly|yearly|annual|weekly)\s+(?:instal{1,2}ments?|"
    r"repayments?|payments?)|(days?|weeks?|months?|quarters?|years?)\b)", re.I)
_UNIT_NAME = {"quarterly": "quarter", "monthly": "month", "half-yearly": "half", "yearly": "year", "annual": "year",
              "weekly": "week"}
_PER_UNIT = re.compile(r"^\s*(?:per|a|an|each|/)\s+(?!month|year|annum|quarter|week|day|fortnight)[a-z]+", re.I)
_RATIO_PHRASE = re.compile(r"^[\s-]*(?:days|weeks|months|years)'\s+(?:\w+\s+)?[a-z]+", re.I)
_IN_MONTHS = {"month": 1, "quarter": 3, "half": 6, "year": 12}
_IN_DAYS = {"day": 1, "week": 7}


def to_decimal(x: float) -> Decimal:
    return D(str(round(x, 6)))


def fmt(x: Decimal, money: bool) -> str:
    if money:
        q = x.quantize(D("0.01"))
        whole, frac = divmod(abs(q), 1)
        s = str(int(whole))
        if len(s) > 3:
            head, tail = s[:-3], s[-3:]
            parts = []
            while len(head) > 2:
                parts.insert(0, head[-2:])
                head = head[:-2]
            s = ",".join(([head] if head else []) + parts + [tail])
        return f"₹{s}" + (f".{int(frac * 100):02d}" if frac else "")
    s = format(x.normalize(), "f")
    return s.rstrip("0").rstrip(".") if "." in s else s


def figures(text: str, nums: list, words: Callable[[str], set], freq: Callable[[str, int], Optional[str]],
            tables: Optional[list[Table]] = None) -> list[Fig]:
    """Context for each extracted number (the verifier's _Num list over `text`)."""
    by_line = {i: (t, cells) for t in (tables or []) for i, cells in t.rows.items()}
    out = []
    for n in nums:
        pos, tx = n.pos, n.text
        line_no = text.count("\n", 0, pos)
        line_start = text.rfind("\n", 0, pos) + 1
        column = header = None
        label: set = set()
        if line_no in by_line:
            t, cells = by_line[line_no]
            line = text[line_start:text.find("\n", pos) if "\n" in text[pos:] else len(text)]
            k = line[:pos - line_start].count("|") - (1 if t.leading_pipe.get(line_no) else 0)
            if 0 <= k < len(t.roles):
                column, header = t.roles[k], t.header[k]
                label |= words(t.header[k])
            label |= words(cells[0])
            for j, role in enumerate(t.roles):
                if role == "narration":
                    label |= words(cells[j])
        else:
            seg = text[line_start:pos]
            cut = max(seg.rfind(". "), seg.rfind("; "), seg.rfind(": "))
            sentence = seg[cut + 2:] if cut >= 0 else seg
            last_digit = max((m.end() for m in re.finditer(r"\d", sentence)), default=0)
            window = " ".join(sentence[last_digit:].split()[-8:])
            clause = re.split(r",|;|\bwhile\b|\bwhereas\b", sentence)[-1]
            label = words(window) | set(list(_ordered_words(clause, words))[:4])
        after = text[pos + len(tx):]
        um = _UNIT_AFTER.match(after) if not n.pct else None
        unit = None
        if um:
            unit = _UNIT_NAME.get((um.group(1) or "").lower()) or (um.group(2) or "").lower().rstrip("s")
        digits = re.search(r"\d+(?:\.(\d+))?", tx)
        decimals = len(digits.group(1)) if digits and digits.group(1) else 0
        money = (bool(_MONEY_BEFORE.search(text[max(0, pos - 6):pos])) or bool(_SCALE_WORD.search(tx))
                 or bool(re.search(r"\d,\d", tx)) or column in ("debit", "credit", "balance", "amount"))
        value = to_decimal(n.value)
        out.append(Fig(value, n.pct, n.approx, tx, pos, decimals, money and not n.pct, unit, freq(text, pos),
                       frozenset(label), column, header, bool(money and _PER_UNIT.match(after)),
                       bool(_RATIO_PHRASE.match(after))))
    return out


def _ordered_words(text: str, words: Callable[[str], set]) -> list[str]:
    seen, out = set(), []
    for tok in re.findall(r"[A-Za-z][A-Za-z'\-]*", text):
        for w in words(tok):
            if w not in seen:
                seen.add(w)
                out.append(w)
    return out


# ---------------------------------------------------------------------------------------------- derivations

_CLAIM_PERIOD = [
    ("annual", re.compile(r"\b(?:first|1st|one|a|per|each|every)[\s-]+year\b|\bfirst-year\b|\bannual(?:ly)?\b|"
                          r"\byearly\b|\bper annum\b|\bp\.a\.", re.I)),
    ("quarterly", re.compile(r"\b(?:a|per|each|every)\s+quarter\b|\bquarterly\b", re.I)),
    ("monthly", re.compile(r"\b(?:a|per|each|every)\s+month\b|\bmonthly\b", re.I)),
]
_PERIOD_FACTOR = {("monthly", "annual"): D(12), ("quarterly", "annual"): D(4), ("monthly", "quarterly"): D(3),
                  ("annual", "monthly"): D(1) / D(12), ("annual", "quarterly"): D(1) / D(4),
                  ("quarterly", "monthly"): D(1) / D(3)}


def _same_duration(a: Decimal, ua: str, b: Decimal, ub: str) -> bool:
    if ua in _IN_MONTHS and ub in _IN_MONTHS:
        return a * _IN_MONTHS[ua] == b * _IN_MONTHS[ub]
    if ua in _IN_DAYS and ub in _IN_DAYS:
        return a * _IN_DAYS[ua] == b * _IN_DAYS[ub]
    return False


def date_intervals(full_dates: list[tuple[int, int, int]]) -> list[tuple[Decimal, str]]:
    """Intervals between full dates in the passage, in days, weeks, months and years (v2 behaviour)."""
    out = []
    for i, a in enumerate(full_dates):
        for b in full_dates[i + 1:]:
            try:
                days = abs((date(*b) - date(*a)).days)
            except ValueError:
                continue
            span = f"between {date(*a).isoformat()} and {date(*b).isoformat()}"
            out += [(D(days), f"{days} days {span}"),
                    (to_decimal(round(days / 30.44, 1)), f"about {round(days / 30.44, 1)} months {span}"),
                    (to_decimal(round(days / 7, 1)), f"about {round(days / 7, 1)} weeks {span}"),
                    (to_decimal(round(days / 365.25, 1)), f"about {round(days / 365.25, 1)} years {span}")]
    return out


def derive(c: Fig, src: list[Fig], claim: str, claim_words: set,
           extras: list[tuple[Decimal, str]] = ()) -> Optional[str]:
    """A derivation of claim figure `c` from the passage's figures, or None."""
    def close(x: Decimal) -> bool:
        tol = abs(c.value) * D("0.05") if c.approx else D("0.005")
        return abs(x - c.value) <= max(tol, D("1e-9") * abs(x))

    plain = [s for s in src if not s.pct][:60]
    money = [s for s in plain if s.money]

    if c.pct:
        tol = D("0.5") * D(10) ** -c.decimals
        if c.approx:
            tol = max(tol, D(1))
        cand = [s for s in plain if s.value > 0 and claim_words & s.label]
        for a in cand:
            for b in cand:
                if a is b or a.value == b.value:
                    continue
                share = a.value / b.value * HUNDRED
                forms = [(share, f"{a.text} is {fmt(share.quantize(D('0.01')), False)}% of {b.text}")]
                if a.value < b.value:
                    forms.append((HUNDRED - share, f"{a.text} is {fmt((HUNDRED - share).quantize(D('0.01')), False)}%"
                                                   f" below {b.text}"))
                change = abs(a.value - b.value) / b.value * HUNDRED
                forms.append((change, f"from {b.text} to {a.text} is a change of "
                                      f"{fmt(change.quantize(D('0.01')), False)}%"))
                for x, why in forms:
                    if abs(x - c.value) <= tol:
                        return why
        return None

    if c.ratio_phrase:  # "six months' rent" can only be a ratio of two amounts the claim names
        cand = [s for s in money if claim_words & s.label]
        for a in cand:
            for b in cand:
                if a.value > b.value > 0 and a.value == c.value * b.value:
                    return f"{a.text} ÷ {b.text} = {fmt(c.value, False)}"
        return None

    if c.unit:
        for s in src:
            if s.unit and s.unit != c.unit and _same_duration(c.value, c.unit, s.value, s.unit):
                return f"{c.text} {c.unit}s = {s.text} {s.unit}s"

    if len(plain) <= 25:  # any two figures (v2 behaviour)
        for i, a in enumerate(plain):
            for b in plain[i + 1:]:
                if close(a.value + b.value):
                    return f"{a.text} + {b.text} = {fmt(a.value + b.value, a.money or b.money)}"
                if close(abs(a.value - b.value)):
                    return f"{a.text} − {b.text} = {fmt(abs(a.value - b.value), a.money or b.money)}"

    for x, why in extras:
        if close(x):
            return why

    if c.money:
        pcts = [s for s in src if s.pct]
        # a count of items (not a duration) times a per-item rate: "12 bales at ₹96,000 per bale"
        counts = [s for s in plain if not s.money and not s.unit and s.value == s.value.to_integral_value()
                  and 0 < s.value < 100000]
        bases = [(m.value, m.text) for m in money]
        bases += [(k.value * m.value, f"{k.text} × {m.text}") for k in counts for m in money if m.per_unit][:300]
        for bv, bt in bases[len(money):]:
            if close(bv):
                return f"{bt} = {fmt(bv, True)}"
        for p in pcts:
            for bv, bt in bases:
                share = bv * p.value / HUNDRED
                if close(share):
                    return f"{p.text} of {bt} = {fmt(share, True)}"
                if close(bv + share):
                    return f"{bt} + {p.text} = {fmt(bv + share, True)}"
                if close(bv - share):
                    return f"{bt} − {p.text} = {fmt(bv - share, True)}"
        period = next((k for k, rx in _CLAIM_PERIOD if rx.search(claim)), None)
        if period:
            for s in money:
                factor = _PERIOD_FACTOR.get((s.freq, period))
                if factor and close(s.value * factor):
                    return f"{s.text} {s.freq} = {fmt(s.value * factor, True)} {period}"
        return None

    if c.value == c.value.to_integral_value() and c.value >= 2:
        cand = [s for s in money if claim_words & s.label]
        for a in cand:
            for b in cand:
                if a.value > b.value > 0 and a.value == c.value * b.value:
                    return f"{a.text} ÷ {b.text} = {fmt(c.value, False)}"
    return None


# --------------------------------------------------------------------------------------------- money flow

_ACCT = r"(?:the|this|its|their|his|her|our|my)\s+(?:bank\s+)?account"
_OUT_ACCT = re.compile(rf"\bfrom\s+{_ACCT}\b|\b{_ACCT}\s+(?:has\s+|had\s+)?(?:paid|sent|transferred|remitted|spent)\b",
                       re.I)
_IN_ACCT = re.compile(rf"\b(?:to|into|in)\s+{_ACCT}\b|\b{_ACCT}\s+(?:has\s+|had\s+)?(?:received|got)\b", re.I)
_STMT_IN = re.compile(r"\b(?:credited|deposited)\b", re.I)
_STMT_OUT = re.compile(r"\b(?:debited|withdrawn|withdrew|withdrawals?)\b", re.I)
_GEN_IN = re.compile(r"\b(?:received|receives|receipt|inflows?|came in)\b", re.I)
_GEN_OUT = re.compile(r"\b(?:paid|pays|payments?|sent|sends|transferred|transfers|remitted|outflows?|went out)\b", re.I)


def statement_direction(clause: str) -> Optional[str]:
    """Money in or out of the account, from account-perspective words only (credited, debited, 'to the account')."""
    if _OUT_ACCT.search(clause):
        return "out"
    if _IN_ACCT.search(clause):
        return "in"
    i, o = bool(_STMT_IN.search(clause)), bool(_STMT_OUT.search(clause))
    return "in" if i and not o else "out" if o and not i else None


def claim_direction(clause: str, counterparty_subject: bool) -> Optional[str]:
    """Direction a claim gives an amount. Generic verbs (paid, received) are read from the account's side unless a
    named counterparty is their subject ("Godavari paid ₹8 lakh" is money coming in)."""
    d = statement_direction(clause)
    if d:
        return d
    i, o = bool(_GEN_IN.search(clause)), bool(_GEN_OUT.search(clause))
    if i == o:
        return None
    d = "in" if i else "out"
    return ("out" if d == "in" else "in") if counterparty_subject else d


def clause_at(text: str, pos: int) -> str:
    start = max(text.rfind(". ", 0, pos), text.rfind("\n", 0, pos), text.rfind("; ", 0, pos)) + 1
    ends = [e for e in (text.find(". ", pos), text.find("\n", pos), text.find("; ", pos)) if e >= 0]
    return text[start:min(ends) if ends else len(text)]


def source_flow(c: Fig, src: list[Fig], source: str) -> Optional[tuple[str, str]]:
    """(direction, reason) the passage gives the amount `c`, if unambiguous."""
    def same(x: Decimal) -> bool:
        tol = abs(c.value) * D("0.05") if c.approx else D("0.005")
        return abs(x - c.value) <= tol

    hits = [s for s in src if not s.pct and same(s.value)]
    if not hits:
        return None
    cols = {s.column for s in hits if s.column}
    if cols:
        if cols == {"debit"}:
            h = next(s.header for s in hits if s.column == "debit")
            return "out", f"it is in the “{h}” column"
        if cols == {"credit"}:
            h = next(s.header for s in hits if s.column == "credit")
            return "in", f"it is in the “{h}” column"
        return None
    dirs = {statement_direction(clause_at(source, s.pos)) for s in hits} - {None}
    if len(dirs) == 1:
        d = dirs.pop()
        return d, "the passage says it was " + ("credited" if d == "in" else "debited")
    return None


# -------------------------------------------------------------------------------------------- from -> to

_UP = r"rose|risen|rises|grew|grown|grows|increased|increases|went up|jumped|climbed|improved"
_DOWN = r"fell|fallen|falls|declined|declines|decreased|decreases|dropped|drops|went down|slipped|slid|reduced"
_MOVE = re.compile(rf"\b(?:(?P<up>{_UP})|(?P<down>{_DOWN}))\b", re.I)


def _after(text: str, start: int, figs: list[Fig], word: str, max_words: int = 6) -> Optional[Fig]:
    """The first figure after `start` that is preceded (within max_words) by `word`."""
    for f in sorted(figs, key=lambda f: f.pos):
        if f.pos < start:
            continue
        gap = text[start:f.pos]
        if len(gap.split()) <= max_words + 1 and re.search(rf"\b{word}\b\s*(?:₹|rs\.?|inr)?\s*$", gap, re.I):
            return f
        if len(gap.split()) > max_words + 1:
            return None
    return None


def moves(text: str, figs: list[Fig]) -> list[tuple[str, Optional[Fig], Optional[Fig], Optional[Fig], int]]:
    """Each change verb with its 'from A', 'to B' and 'by X' figures: (direction, A, B, X, verb position)."""
    out = []
    for m in _MOVE.finditer(text):
        d = "up" if m.group("up") else "down"
        a = _after(text, m.end(), figs, "from")
        b = _after(text, (a.pos + len(a.text)) if a else m.end(), figs, "to", 8 if a else 4)
        x = _after(text, m.end(), figs, "by", 3)
        if a or b or x:
            out.append((d, a, b, x, m.start()))
    return out


def from_to_contradiction(claim: str, c_figs: list[Fig], source: str, s_figs: list[Fig]) -> Optional[str]:
    def same(f: Fig, g: Fig) -> bool:
        tol = abs(f.value) * D("0.05") if f.approx else D("0.005")
        return f.pct == g.pct and abs(f.value - g.value) <= tol

    src_pairs = [(a, b) for _, a, b, _, _ in moves(source, s_figs) if a and b and a.pct == b.pct]
    for d, a, b, x, _ in moves(claim, c_figs):
        word = "rose" if d == "up" else "fell"
        if a and b and a.pct == b.pct and a.value != b.value:
            if (d == "up") != (b.value > a.value):
                return f"the claim says it {word} from {a.text} to {b.text}, which is a " \
                       f"{'fall' if b.value < a.value else 'rise'}"
            continue
        for sa, sb in src_pairs:
            if sa.value == sb.value:
                continue
            src_up = sb.value > sa.value
            if b and same(b, sb) and (d == "up") != src_up:
                return f"the passage goes from {sa.text} to {sb.text} (a {'rise' if src_up else 'fall'}); " \
                       f"the claim says it {word} to {b.text}"
            if x and not b and abs(abs(sb.value - sa.value) - x.value) <= D("0.005") + (x.value * D("0.05") if x.approx else 0) \
                    and (d == "up") != src_up:
                return f"the passage goes from {sa.text} to {sb.text} (a {'rise' if src_up else 'fall'}); " \
                       f"the claim says it {word} by {x.text}"
    return None

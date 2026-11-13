# FROZEN copy of app/ai/verifier.py at commit 28d868a (verifier v3 baseline for HB-Synth v2). Do not edit.
"""Claim verifier v3: is an answer sentence supported by the source text it cites?

v1 only measured similarity, so "₹45,000" passed against a source saying "₹48,000", and "not secured" passed against
"secured" (its tokenizer even dropped "not"). v2 keeps similarity as a relevance gate and adds checks that each
return a human-readable reason:

  numbers      every amount/percentage in the claim must appear in the source (₹, Rs, INR, lakh/crore/million
               scales, Indian digit grouping, number words; sums/differences of two source numbers are accepted
               as derived; "about/approximately" allows 5%)
  identifiers  account numbers, DINs, invoice/PO/policy numbers must match exactly
  dates        full dates, day-month, month-year, FY ranges and years must appear in the source
  frequency    "per month" vs "per annum" etc., bound to the number they qualify
  polarity     negation / negative words (not, no, rejected, excludes…) must agree with the best-matching clause
  direction    credit/debit, rose/fell, above/below, before/after must agree with the best-matching clause
  parties      named parties must appear in the source, and must not swap roles (payer ↔ payee, by ↔ to)
  nli          optional: LettuceDetect token classifier (MIT weights) when the ML extras are installed

v3 (R6) adds, as value checks with a written reason or derivation (app/ai/recompute.py):
  recompute    a figure the passage does not print is accepted when it can be computed from the passage's figures
               (durations, monthly↔annual, percent-of, count × rate, shares, ratios, column totals, intervals);
               the derivation is returned so a reviewer can check it
  flow         an amount in a Debit/Withdrawals (Credit/Deposits) column, or one the passage calls debited
               (credited), must not be described as coming in (going out)
  arithmetic   "rose from A to B" with B < A, or "increased to B" when the passage goes from A down to B
and fixes in the wording heuristics: converse verbs (rents from / leases to), passive voice read only next to the
name, "declined" read as refused or decreased from what follows it, negated direction words ("not included" =
excluded), possessive name spans ("Traders' FY"), currency codes (INR, Rs) not taken as party names, and tables
read row by row with their headers.

These are deterministic heuristics with known blind spots (see docs/CONCEPTS.md and benchmarks/hallucination).
They make the checker *stricter*, not infallible: a claim that passes is "no inconsistency found", not "true".
"""
from __future__ import annotations

import logging
import re
import threading
from datetime import date
from dataclasses import dataclass, field
from typing import Optional

from benchmarks.hallucination.frozen_v3 import recompute
from app.ml.insights import split_sentences
from app.ml.retrieval import STOPWORDS, _stem

logger = logging.getLogger(__name__)

# ----------------------------------------------------------------------------------------------- text helpers

_EXTRA_STOP = {"either", "neither", "also", "both", "any", "all", "each", "every", "per", "a", "an", "same",
               "whole", "entire", "total", "ltd", "pvt", "llp", "inc", "limited", "private", "rs", "inr",
               "must", "shall", "may", "will", "can", "lakh", "lakhs", "crore", "crores", "million", "billion",
               "thousand", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
               "eleven", "twelve", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety",
               # generic nouns that name no fact ("after the transaction", "in the period")
               "transaction", "transactions", "period", "entry", "entries", "figure", "figures", "amount",
               "amounts"}
_MONTHS = {m: i for i, names in enumerate(
    [("jan", "january"), ("feb", "february"), ("mar", "march"), ("apr", "april"), ("may",), ("jun", "june"),
     ("jul", "july"), ("aug", "august"), ("sep", "sept", "september"), ("oct", "october"), ("nov", "november"),
     ("dec", "december")], start=1) for m in names}
_MONTH_RE = r"(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|sept?(?:ember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
_WORD_RE = re.compile(r"[a-z][a-z'\-]*[a-z]|[a-z]")


def _norm(text: str) -> str:
    return (text.replace("–", "-").replace("—", "-").replace(" ", " ").replace("’", "'")
            .replace("₹", " ₹"))


def content_words(text: str) -> set[str]:
    words = _WORD_RE.findall(text.lower())
    return {_stem(w.strip("'").removesuffix("'s")) for w in words
            if w not in STOPWORDS and w not in _EXTRA_STOP and w not in _MONTHS and len(w) > 2}


def _linearise(text: str) -> str:
    """Table rows as "Header: value; ..." so similarity and wording checks see what each cell means."""
    tables = recompute.parse_tables(text)
    if not tables:
        return text
    lines = text.splitlines()
    for t in tables:
        for i, cells in t.rows.items():
            lines[i] = "; ".join(f"{h}: {c}" for h, c in zip(t.header, cells) if c and h)
    return "\n".join(lines)


def _sentences(text: str) -> list[str]:
    """Sentences, with each line (e.g. a table row) treated as its own unit."""
    out = []
    for line in _linearise(_norm(text)).splitlines():
        out += [x.strip() for x in (split_sentences(line) or [line]) if len(x.strip()) > 2]
    return out


def _dice(a: set, b: set) -> float:
    return 2 * len(a & b) / (len(a) + len(b)) if a and b else 0.0


# ---------------------------------------------------------------------------------------------- dates

@dataclass(frozen=True)
class _Date:
    y: Optional[int]
    m: Optional[int]
    d: Optional[int]
    fy: Optional[tuple] = None

    def label(self) -> str:
        if self.fy:
            return f"FY {self.fy[0]}-{str(self.fy[1])[2:]}"
        parts = [str(self.d) if self.d else "", list(_MONTHS)[[*_MONTHS.values()].index(self.m)].title() if self.m else "",
                 str(self.y) if self.y else ""]
        return " ".join(p for p in parts if p)


def _month(name: str) -> int:
    return _MONTHS[name.lower()[:4].rstrip(".")] if name.lower()[:4] in _MONTHS else _MONTHS[name.lower()[:3]]


_DATE_PATTERNS = [
    ("fy", re.compile(r"\bFY\s?(\d{4})\s?[-/]\s?(\d{2,4})\b", re.I)),
    ("dmy", re.compile(rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s+{_MONTH_RE}\.?,?\s+(\d{{4}})\b", re.I)),
    ("mdy", re.compile(rf"\b{_MONTH_RE}\.?\s+(\d{{1,2}})(?:st|nd|rd|th)?,?\s+(\d{{4}})\b", re.I)),
    ("iso", re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")),
    ("num", re.compile(r"\b(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})\b")),
    ("my", re.compile(rf"\b{_MONTH_RE}\.?,?\s+(\d{{4}})\b", re.I)),
    ("dm", re.compile(rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s+{_MONTH_RE}\b", re.I)),
    ("y", re.compile(r"\b(19\d{2}|20\d{2})\b")),
]


def extract_dates(text: str) -> tuple[list[tuple[set, str]], str]:
    """Return ([(set of possible _Date readings, surface text)], text with dates blanked out)."""
    found, masked = [], text
    for kind, rx in _DATE_PATTERNS:
        for m in list(rx.finditer(masked)):
            g = m.groups()
            try:
                if kind == "fy":
                    a, b = int(g[0]), int(g[1])
                    b = b + (a // 100) * 100 if b < 100 else b
                    readings = {_Date(None, None, None, fy=(a, b))}
                elif kind == "dmy":
                    readings = {_Date(int(g[2]), _month(g[1]), int(g[0]))}
                elif kind == "mdy":
                    readings = {_Date(int(g[2]), _month(g[0]), int(g[1]))}
                elif kind == "iso":
                    readings = {_Date(int(g[0]), int(g[1]), int(g[2]))}
                elif kind == "num":  # Indian convention is D/M/Y; keep M/D/Y as a second reading when valid
                    a, b, y = int(g[0]), int(g[1]), int(g[2])
                    readings = {_Date(y, b, a)} if b <= 12 else set()
                    if a <= 12:
                        readings.add(_Date(y, a, b))
                    if not readings:
                        continue
                elif kind == "my":
                    readings = {_Date(int(g[1]), _month(g[0]), None)}
                elif kind == "dm":
                    readings = {_Date(None, _month(g[1]), int(g[0]))}
                else:
                    readings = {_Date(int(g[0]), None, None)}
            except (KeyError, ValueError):
                continue
            found.append((readings, m.group(0)))
            masked = masked[:m.start()] + " " * (m.end() - m.start()) + masked[m.end():]
    return found, masked


def _date_matches(c: _Date, e: _Date) -> bool:
    if c.fy or e.fy:
        return bool(c.fy and e.fy and c.fy == e.fy) or (c.fy is None and c.m is None and e.fy is not None
                                                        and c.y in e.fy)
    if c.y and e.y and c.y != e.y:
        return False
    if c.m and e.m and c.m != e.m:
        return False
    if c.d and e.d and c.d != e.d:
        return False
    # every component the claim states must be stated by the source
    return (not c.y or e.y) and (not c.m or e.m) and (not c.d or e.d)


# -------------------------------------------------------------------------------------------- numbers

_SCALE = {"crore": 1e7, "crores": 1e7, "cr": 1e7, "lakh": 1e5, "lakhs": 1e5, "lac": 1e5, "lacs": 1e5,
          "million": 1e6, "mn": 1e6, "billion": 1e9, "bn": 1e9, "thousand": 1e3, "k": 1e3}
_NUM_RE = re.compile(
    r"(?<![\w.,])(?P<num>\d{1,3}(?:,\d{2,3})+(?:\.\d+)?|\d+(?:\.\d+)?)"
    r"(?:\s?(?P<scale>crores?|cr\b|lakhs?|lacs?|million|mn\b|billion|bn\b|thousand|k\b))?"
    r"(?P<pct>\s?%|\s?per\s?cent\b|\s?percent\b)?", re.I)
_UNITS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
          "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16,
          "seventeen": 17, "eighteen": 18, "nineteen": 19}
_TENS = {"twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80,
         "ninety": 90}
_NUMWORD_RE = re.compile(r"\b(?:(" + "|".join(_TENS) + r")(?:[\s-](" + "|".join(_UNITS) + r"))?|("
                         + "|".join(_UNITS) + r"))\b(?=\s*(?:\(\d+\)\s*)?[a-z]+)", re.I)
_APPROX_RE = re.compile(r"\b(about|approximately|approx\.?|around|roughly|nearly|almost|close to|some|~)\s*$", re.I)
# identifiers: tokens mixing digits with letters or / - ( ), or long bare digit runs (account numbers, DINs)
_ID_RE = re.compile(r"(?<![\w/])(?=[\w/()\-]*\d)(?=[\w/()\-]*[A-Za-z/()\-])[A-Za-z0-9]+(?:[/()\-][A-Za-z0-9]+)+\)?"
                    r"|(?<!\d)(?<!\d[,.])\d{7,}(?!\d|[,.]\d)")
_NUM_UNIT_ID = re.compile(r"^\d+(\.\d+)?-(day|days|month|months|year|years|week|weeks|hour|hours)$", re.I)


@dataclass
class _Num:
    value: float
    pct: bool
    approx: bool
    text: str
    pos: int


def extract_identifiers(text: str) -> tuple[set[str], str]:
    ids, masked = set(), text
    for m in _ID_RE.finditer(text):
        tok = m.group(0)
        if _NUM_UNIT_ID.match(tok):
            continue
        ids.add(tok.lower().strip("()"))
        masked = masked[:m.start()] + " " * len(tok) + masked[m.end():]
    return ids, masked


def extract_numbers(text: str) -> list[_Num]:
    out = []
    for m in _NUM_RE.finditer(text):
        raw = m.group("num")
        try:
            value = float(raw.replace(",", ""))
        except ValueError:
            continue
        scale = (m.group("scale") or "").lower().rstrip("s") if m.group("scale") else ""
        scale = {"crore": "crore", "cr": "cr", "lakh": "lakh", "lac": "lac"}.get(scale, scale)
        value *= _SCALE.get(scale, _SCALE.get(scale + "s", 1.0)) if scale else 1.0
        approx = bool(_APPROX_RE.search(text[max(0, m.start() - 20):m.start()].replace("₹", "")))
        out.append(_Num(value, bool(m.group("pct")), approx, m.group(0).strip(), m.start()))
    for m in _NUMWORD_RE.finditer(text):
        tens, unit, alone = m.groups()
        value = (_TENS[tens.lower()] + (_UNITS[unit.lower()] if unit else 0)) if tens else _UNITS[alone.lower()]
        approx = bool(_APPROX_RE.search(text[max(0, m.start() - 20):m.start()]))
        out.append(_Num(float(value), False, approx, m.group(0), m.start()))
    return out


def _close(a: float, b: float, tol: float) -> bool:
    """Exact match (to the paisa) unless a relative tolerance is given for approximate claims."""
    if tol <= 1e-6:
        return abs(a - b) <= max(0.005, 1e-12 * max(abs(a), abs(b)))
    return abs(a - b) <= tol * max(abs(a), abs(b), 1e-9)


# ------------------------------------------------------------------------------------ frequency, polarity

_FREQ = {
    "annual": r"per annum|p\.a\.|per year|a year|each year|every year|annually|yearly|annual",
    "monthly": r"per month|a month|each month|every month|monthly|p\.m\.",
    "quarterly": r"per quarter|a quarter|each quarter|every quarter|quarterly",
    "weekly": r"per week|a week|each week|every week|weekly",
    "daily": r"per day|a day|each day|every day|daily",
}
_FREQ_RE = {k: re.compile(rf"\b(?:{v})", re.I) for k, v in _FREQ.items()}
_NEG_RE = re.compile(r"\b(not|no|never|none|nor|neither|cannot|can't|won't|isn't|aren't|wasn't|weren't|doesn't|"
                     r"don't|didn't|hasn't|haven't|hadn't|without|unable)\b|n't\b", re.I)
_NEG_WORDS_RE = re.compile(r"\b(reject(?:s|ed)?|declin(?:e|es|ed)|refus(?:e|es|ed)|denied|unsecured|unpaid|"
                           r"prohibit(?:s|ed)?|forbidden|disallow(?:s|ed)?|invalid|exclud(?:e|es|ed|ing)|abstain(?:s|ed|ing)?|"
                           r"omit(?:s|ted)?|left out)\b", re.I)
_DIRECTIONS = [
    (r"credit(?:s|ed)?", r"debit(?:s|ed)?"),
    (r"r(?:ose|ise|ises|isen)|grew|grow(?:s|n)?|increas(?:e|es|ed)|went up|up from", r"f(?:ell|all|alls|allen)|declin(?:e|es|ed)|decreas(?:e|es|ed)|dropp(?:ed)?|drop(?:s)?|went down|down from"),
    (r"above|over|higher than|more than|exceed(?:s|ed)?", r"below|under|lower than|less than"),
    (r"before|prior to|earlier than|ahead of", r"after|later than"),
    (r"includ(?:e|es|ed|ing)", r"exclud(?:e|es|ed|ing)"),
    (r"inflows?", r"outflows?"),
    (r"profits?", r"loss(?:es)?"),
    (r"surplus", r"deficit"),
]
_DIR_RE = [(re.compile(rf"\b(?:{a})\b", re.I), re.compile(rf"\b(?:{b})\b", re.I)) for a, b in _DIRECTIONS]


_DECLINE = re.compile(r"\bdeclin(?:e|es|ed|ing)\b", re.I)
_DECREASE_AFTER = re.compile(r"^\s+(?:sharply\s+|marginally\s+|slightly\s+|further\s+|steadily\s+)?"
                             r"(?:to|by|from)\s+(?:₹|rs\.?|inr|about|around|nearly)?\s*\d"
                             r"|^\s+(?:sharply|marginally|slightly|steadily)\b", re.I)


def _disambiguate(text: str) -> str:
    """'declined to 1.08' is a decrease; 'declined the request' is a refusal. Rewrite each so the negation and
    direction checks read the right sense."""
    return _DECLINE.sub(lambda m: "decreased" if _DECREASE_AFTER.match(text[m.end():]) else "refused", text)


_NEG_BEFORE = re.compile(r"\b(?:not|never)\b|n't\b", re.I)


def _direction_side(text: str, a_rx, b_rx) -> Optional[str]:
    """Which side of a direction pair the text takes; a negated word counts as the other side ("not included")."""
    sides = set()
    for side, rx in (("a", a_rx), ("b", b_rx)):
        for m in rx.finditer(text):
            before = " ".join(text[:m.start()].split()[-2:])
            negated = bool(_NEG_BEFORE.search(before))
            sides.add(side if not negated else ("b" if side == "a" else "a"))
    return sides.pop() if len(sides) == 1 else None


def _polarity(clause: str, other_words: set[str]) -> int:
    """Parity of negation cues whose scope (the next six words) touches the other text's content words.

    "Drawing power … excludes receivables" has a negative word, but it scopes over "receivables", so it does not
    make a claim about "margin on stock" negative.
    """
    count = 0
    for rx in (_NEG_RE, _NEG_WORDS_RE):
        for m in rx.finditer(clause):
            scope = " ".join(clause[m.end():].split()[:6])
            cue_word = m.group(0) if rx is _NEG_WORDS_RE else ""
            if content_words(scope + " " + cue_word) & other_words or not other_words:
                count += 1
    return count % 2


# --------------------------------------------------------------------------------------------- parties

_ENTITY_RE = re.compile(r"\b(?:[A-Z][\w'&.-]*|&)(?:\s+(?:[A-Z][\w'&.-]*|&))*")
_ENTITY_SKIP = {"the", "a", "an", "on", "in", "at", "if", "either", "neither", "each", "any", "under", "after",
                "before", "his", "her", "its", "their", "this", "that", "these", "those", "no", "all", "most", "it",
                "he", "she", "they", "we", "statement", "interest", "payment", "prepayment", "repayment",
                "services", "cover", "sales", "net", "tax", "monthly", "annual", "personal", "drawing", "cash",
                "there", "some", "date", "narration", "debit", "credit", "balance", "policy", "order", "rent",
                "purchase", "sum", "rate", "director", "directors", "board", "valuer", "auditor", "statutory",
                "fy", "most", "after", "receivables", "inr", "rs", "usd", "eur", "gbp"}
_ORG_SUFFIX = re.compile(r"\b(pvt|private|ltd|limited|llp|inc|co)\.?\b", re.I)
_PASSIVE_RE = re.compile(r"\b(is|are|was|were|be|been|being|get|got|gets)\s+(?:\w+ly\s+)?\w+(?:ed|en|wn|id|ld|lt|ht)\b",
                         re.I)
_LOCAL_PASSIVE = re.compile(r"^\s*(?:,[^,]{0,60},\s*)?(?:has\s+|have\s+|had\s+)?(?:is|are|was|were|be|been|being|"
                            r"get|got|gets)\s+(?:\w+ly\s+)?(?:been\s+)?\w+(?:ed|en|wn|id|ld|lt|ht)\b", re.I)
# Verbs whose active subject receives (rents, borrows, buys): "B rents the unit from A" = "A leases it to B".
_ACQUIRE = re.compile(r"^\s*(?:has\s+|have\s+|had\s+)?(?:\w+ly\s+)?(?:rents?|rented|borrow(?:s|ed)?|buys?|bought|"
                      r"purchas(?:e|es|ed)|receiv(?:e|es|ed)|avail(?:s|ed)?|obtain(?:s|ed)?|takes?|took|taken|"
                      r"accept(?:s|ed)?|gets?|got)\b", re.I)
_TWO_WAY = re.compile(r"^\s*(?:has\s+|have\s+|had\s+)?(?:leases?|leased|lets?|hires?|hired)\b", re.I)
_SUBJECT_PREFIX = re.compile(r"^(?:\W|\d|the\b|a\b|an\b|on\b|in\b|at\b|if\b|its\b|their\b|his\b|her\b|"
                             r"\d{1,2}\s+\w+\s+\d{4}\b)*$", re.I)


def _entity_key(name: str) -> str:
    return " ".join(_ORG_SUFFIX.sub(" ", name.lower().replace("'s", "")).replace(".", " ").split())


def extract_entities(text: str) -> list[tuple[str, int]]:
    """Capitalised name spans (organisations, people, places, defined parties, acronyms) with char offsets."""
    out = []
    for m in _ENTITY_RE.finditer(text):
        raw = m.group(0)
        pm = re.search(r"(?:s'|'s)(?=\s|$)", raw)  # possessive ends the name: "Sunrise Traders' FY" -> Sunrise Traders
        if pm:
            raw = raw[:pm.start() + 1] if raw[pm.start()] == "s" else raw[:pm.start()]
        words = raw.split()
        offset = 0
        while words and words[0].lower().rstrip(",.") in _ENTITY_SKIP | set(_MONTHS):
            offset = raw.index(words[0], offset) + len(words[0])
            words = words[1:]
        while words and words[-1].lower().rstrip(",.") in set(_MONTHS) | {"&"}:
            words = words[:-1]
        if not words or any(ch.isdigit() for ch in " ".join(words)):
            continue
        span = " ".join(words).rstrip(",.")
        key = _entity_key(span)
        if not key or key in _ENTITY_SKIP or len(key) < 2:
            continue
        pos = m.start() + raw.index(words[0], offset)
        sentence_start = pos == 0 or text[:pos].rstrip().endswith((".", "|", "\n", ":"))
        if len(words) == 1 and sentence_start and not span.isupper():
            continue  # a capitalised first word is usually just the start of a sentence
        out.append((span, pos))
    return out


def _roles(clause: str) -> tuple[dict[str, str], Optional[str]]:
    """Tiny role labeller: SOURCE (payer/issuer/agent) vs TARGET (payee/recipient).

    Only two signals are trusted: a preposition right before the name (by/from → SOURCE, to → TARGET), and the
    grammatical subject — a name that starts its comma-delimited segment (SOURCE in active voice, TARGET in
    passive). Everything else gets no role. Returns (roles, active-voice subject).
    """
    roles: dict[str, str] = {}
    subject = None
    for name, pos in extract_entities(clause):
        if name.isupper() and len(name) <= 5:
            continue  # channels and instruments (NEFT, RTGS, ATM, GST) are not parties
        rest = clause[pos + len(name):]
        if rest.startswith("'s") or (name.endswith("s") and rest.startswith("'")):
            continue  # possessive: not a participant
        key = _entity_key(name)
        prep = re.search(r"\b(by|from|to)\s+(?:the\s+)?$", clause[max(0, pos - 12):pos].lower())
        if prep:
            roles[key] = "SOURCE" if prep.group(1) in ("by", "from") else "TARGET"
            continue
        segment = clause[:pos].rsplit(",", 1)[-1]
        if _SUBJECT_PREFIX.match(segment.strip()) is not None:
            passive = bool(_LOCAL_PASSIVE.match(rest))
            receives = bool(_ACQUIRE.match(rest))
            if _TWO_WAY.match(rest):  # "leases X to B" gives, "leases X from A" receives
                tail = rest.lower()
                f, t = tail.find(" from "), tail.find(" to ")
                receives = f >= 0 and (t < 0 or f < t)
            roles[key] = "TARGET" if passive or receives else "SOURCE"
            if not passive and subject is None:
                subject = key
    return roles, subject


def _entity_in(key: str, source_keys: set[str], source_text: str) -> bool:
    if key in source_text:
        return True
    return any(key in k or k in key for k in source_keys if len(k) > 3)


# ---------------------------------------------------------------------------------------------- result

@dataclass
class Verdict:
    supported: bool
    issues: list[dict] = field(default_factory=list)
    coverage: float = 0.0
    similarity: Optional[float] = None
    nli: Optional[float] = None
    derivations: list[str] = field(default_factory=list)

    @property
    def needs_review(self) -> bool:
        return any(i["severity"] == "review" for i in self.issues)

    def add(self, kind: str, detail: str):
        severity = "review" if kind in REVIEW_KINDS else "contradiction"
        self.issues.append({"kind": kind, "detail": detail, "severity": severity})
        self.supported = not any(i["severity"] == "contradiction" for i in self.issues)


# Two tiers, by mechanism. Value checks compare concrete values with the source and decide "supported". Wording
# heuristics (negation scope, direction words, role labelling, the NLI model) only ask a human to check: on the
# held-out test split they found 12 real errors but also wrongly flagged 9 of 28 correct sentences.
REVIEW_KINDS = {"negation", "direction", "roles", "nli"}


def nearest_freq(text: str, pos: int, window: int = 40) -> Optional[str]:
    best, dist = None, window + 1
    for kind, rx in _FREQ_RE.items():
        for m in rx.finditer(text):
            d = min(abs(m.start() - pos), abs(m.end() - pos))
            if d < dist:
                best, dist = kind, d
    return best


def _counterparty_subject(claim: str) -> bool:
    """A named party (not 'the account') is the active subject: 'Godavari paid ₹8 lakh into ...'."""
    ents = extract_entities(claim)
    if not ents:
        return False
    name, pos = ents[0]
    return _SUBJECT_PREFIX.match(claim[:pos].strip()) is not None and not _LOCAL_PASSIVE.match(claim[pos + len(name):])


def _value_tokens(text: str) -> set[str]:
    found, masked = extract_dates(text)
    toks = {f"d:{r.y}-{r.m}-{r.d}" for rs, _ in found for r in rs if r.y and r.m and r.d}
    _, masked = extract_identifiers(masked)
    return toks | {f"n:{round(n.value, 2)}" for n in extract_numbers(masked) if n.value >= 10}


def _best_clause(claim_words: set[str], clauses: list[str], claim: str = "") -> tuple[Optional[str], float]:
    """The source sentence that best matches the claim: shared content words weighted by rarity across the
    passage (so "theft" outweighs "policy"), plus shared full dates and figures."""
    import math
    units = [content_words(c) | _value_tokens(c) for c in clauses]
    df: dict[str, int] = {}
    for u in units:
        for t in u:
            df[t] = df.get(t, 0) + 1
    n = len(units)
    w = lambda t: math.log(1 + n / df.get(t, 1))  # noqa: E731
    target = claim_words | (_value_tokens(claim) if claim else set())
    best, score = None, 0.0
    for c, u in zip(clauses, units):
        if not u or not target:
            continue
        shared = sum(w(t) for t in target & u)
        s = 2 * shared / (sum(w(t) for t in target) + sum(w(t) for t in u))
        if s > score:
            best, score = c, s
    return best, score


def check_claim(claim: str, sources: list[str], *, similarity: Optional[float] = None,
                sim_threshold: float = 0.5, embed_fn=None, question: str = "", use_nli: bool = False) -> Verdict:
    """Verify one claim against the source passages it cites (or all retrieved passages).

    similarity / embed_fn: optional semantic relevance signal. With embed_fn (texts -> L2-normalised matrix) the
    claim is compared with each source sentence and the best match is used.
    """
    claim = _norm(re.sub(r"\[\d{1,2}\]", "", claim)).strip()
    source = _norm("\n".join(sources))
    v = Verdict(supported=True)
    src_lower = source.lower()
    sentences = _sentences(source)
    if embed_fn is not None and sentences:
        try:
            vecs = embed_fn([claim] + sentences[:80])
            similarity = float((vecs[1:] @ vecs[0]).max())
        except Exception as e:  # relevance falls back to word coverage
            logger.debug("sentence similarity unavailable: %s", e)
    v.similarity = similarity

    # ---- relevance gate (v1 behaviour, kept): enough of the claim's content must come from the source
    cw, sw = content_words(claim), content_words(source)
    v.coverage = len(cw & sw) / max(1, len(cw))
    topical = v.coverage >= 0.6 or (similarity is not None and similarity >= sim_threshold)
    if cw and not topical:
        missing = sorted(cw - sw)[:4]
        v.add("unsupported_content", "most of this sentence is not in the source"
              + (f" (e.g. {', '.join(missing)})" if missing else ""))

    # ---- dates
    c_dates, c_masked = extract_dates(claim)
    s_dates, s_masked = extract_dates(source)
    s_readings = [r for rs, _ in s_dates for r in rs]
    for readings, surface in c_dates:
        if not any(_date_matches(c, e) for c in readings for e in s_readings):
            v.add("date", f"“{surface}” does not appear in the source")

    # ---- identifiers
    c_ids, c_masked = extract_identifiers(c_masked)
    s_ids, s_masked = extract_identifiers(s_masked)
    s_id_digits = {re.sub(r"\D", "", i) for i in s_ids}
    for ident in c_ids:
        if ident not in s_ids and not (ident.isdigit() and ident in s_id_digits):
            v.add("identifier", f"“{ident.upper() if not ident.isdigit() else ident}” does not match the source")

    # ---- numbers (amounts, percentages, counts): printed in the source, or recomputed from its figures
    c_nums, s_nums = extract_numbers(c_masked), extract_numbers(s_masked)
    tables = recompute.parse_tables(source)
    c_figs = recompute.figures(c_masked, c_nums, content_words, nearest_freq)
    s_figs = recompute.figures(s_masked, s_nums, content_words, nearest_freq, tables)
    full = sorted({(r.y, r.m, r.d) for r in s_readings if r.y and r.m and r.d})
    extras = recompute.column_totals(tables) + recompute.date_intervals(full)
    for n, f in zip(c_nums, c_figs):
        tol = 0.05 if n.approx else 1e-6
        if not f.ratio_phrase and any(_close(n.value, s.value, tol) for s in s_nums if s.pct == n.pct):
            continue
        why = recompute.derive(f, s_figs, claim, cw, extras)
        if why:
            v.derivations.append(f"“{n.text}”: {why}")
            continue
        v.add("number", f"“{n.text}” is not in the source" + (" (not within 5% either)" if n.approx else ""))

    # ---- money direction: an amount the source shows going out must not be described as coming in
    cp_subject = _counterparty_subject(claim)
    for n, f in zip(c_nums, c_figs):
        if f.pct:
            continue
        flow = recompute.source_flow(f, s_figs, s_masked)
        said = recompute.claim_direction(claim, cp_subject) if flow else None
        if flow and said and said != flow[0]:
            v.add("flow", f"“{n.text}” {'came in' if flow[0] == 'in' else 'went out'} ({flow[1]}); the claim says "
                          f"it {'came in' if said == 'in' else 'went out'}")
            break

    # ---- change arithmetic: rose/fell against the figures themselves
    why = recompute.from_to_contradiction(c_masked, c_figs, s_masked, s_figs)
    if why:
        v.add("arithmetic", why)

    # ---- frequency bound to a number ("₹3,25,000 per month" vs "per year")
    for n in c_nums:
        cf = nearest_freq(c_masked, n.pos)
        if not cf:
            continue
        occ = [s for s in s_nums if _close(s.value, n.value, 0.05 if n.approx else 1e-6)]
        sf = {nearest_freq(s_masked, s.pos) for s in occ} - {None}
        if sf and cf not in sf:
            v.add("frequency", f"the claim says {cf} for “{n.text}”, the source says {', '.join(sorted(sf))}")
    for kind, rx in _FREQ_RE.items():  # a frequency not tied to any number must still appear in the source
        if rx.search(c_masked) and not any(nearest_freq(c_masked, n.pos) == kind for n in c_nums) \
                and not rx.search(s_masked):
            v.add("frequency", f"the source never says {kind}")

    # ---- polarity and direction against the best-matching source sentence
    best, score = _best_clause(cw, sentences, claim)
    if best and score >= 0.3:
        bw = content_words(best)
        claim_d, best_d = _disambiguate(claim), _disambiguate(best)
        if _polarity(claim_d, bw) != _polarity(best_d, cw):
            v.add("negation", f"negation differs from the source: “{best[:140]}”")
        for a_rx, b_rx in _DIR_RE:
            cs, ss = _direction_side(claim_d, a_rx, b_rx), _direction_side(best_d, a_rx, b_rx)
            if cs and ss and cs != ss:
                word = (a_rx if cs == "a" else b_rx).search(claim_d) or (b_rx if cs == "a" else a_rx).search(claim_d)
                other = (a_rx if ss == "a" else b_rx).search(best_d) or (b_rx if ss == "a" else a_rx).search(best_d)
                v.add("direction", f"the claim says “{word.group(0)}”, the source says “{other.group(0)}”")

    # ---- parties: present in the source, and not in swapped roles
    s_entities = {_entity_key(n) for n, _ in extract_entities(source)}
    src_flat = " ".join(src_lower.replace("'s", "").split())
    for name, _ in extract_entities(claim):
        key = _entity_key(name)
        if not _entity_in(key, s_entities, src_flat):
            v.add("party", f"“{name}” is not mentioned in the source")
    if best and score >= 0.3:
        (c_roles, c_subj), (s_roles, s_subj) = _roles(claim), _roles(best)

        def same(a: str, b: str) -> bool:
            return a == b or (len(b) > 3 and len(a) > 3 and (a in b or b in a))

        swapped = next((k for k, r in c_roles.items()
                        if any(same(k, sk) and r != sr for sk, sr in s_roles.items())), None)
        if swapped:
            v.add("roles", f"“{swapped.title()}” has the opposite role in the source: “{best[:140]}”")
        elif (score >= 0.5 and c_subj and s_subj and not same(c_subj, s_subj)
              and not any(same(c_subj, k) for k in s_roles) and c_subj not in best.lower()):
            v.add("roles", f"the source says “{s_subj.title()}” does this, not “{c_subj.title()}”: “{best[:140]}”")

    # ---- optional learned check
    if use_nli:
        from app.core.config import settings
        prob = nli_unsupported_prob(question, sources, claim)
        if prob is not None:
            v.nli = round(prob, 3)
            if prob >= settings.verifier_nli_threshold:
                v.add("nli", f"the NLI model marks part of this sentence as unsupported (p={prob:.2f})")

    return v


# ------------------------------------------------------------------------------------------- NLI model

_NLI_LOCK = threading.Lock()
_NLI = {"state": "idle", "model": None, "tok": None, "name": None}
_QA_PROMPT = ("Briefly answer the following question:\n{question}\nBear in mind that your response should be "
              "strictly based on the following {n} passages:\n{context}\nIn case the passages do not contain the "
              "necessary information to answer the question, please reply with: \"Unable to answer based on given "
              "passages.\"\noutput:")


def _load_nli(model_name: str, allow_download: bool = False):
    with _NLI_LOCK:
        if _NLI["state"] == "ready" and _NLI["name"] == model_name:
            return _NLI
        if _NLI["state"] == "failed" and _NLI["name"] == model_name:
            return None
        try:
            from transformers import AutoModelForTokenClassification, AutoTokenizer
            kw = {} if allow_download else {"local_files_only": True}
            _NLI["tok"] = AutoTokenizer.from_pretrained(model_name, **kw)
            _NLI["model"] = AutoModelForTokenClassification.from_pretrained(model_name, **kw).eval()
            _NLI.update(state="ready", name=model_name)
            logger.info("NLI verifier loaded: %s", model_name)
            return _NLI
        except Exception as e:  # not installed / not cached: rules-only verification
            _NLI.update(state="failed", name=model_name)
            logger.info("NLI verifier unavailable (%s): %s", model_name, e)
            return None


def nli_unsupported_prob(question: str, passages: list[str], claim: str, model_name: Optional[str] = None,
                         allow_download: bool = False) -> Optional[float]:
    """Max per-token 'hallucinated' probability over the claim (LettuceDetect input format)."""
    from app.core.config import settings
    nli = _load_nli(model_name or settings.verifier_nli_model, allow_download)
    if not nli:
        return None
    import torch
    tok, model = nli["tok"], nli["model"]
    ctx = "\n".join(f"passage {i + 1}: {p}" for i, p in enumerate(passages))
    prompt = _QA_PROMPT.format(question=question or "Answer the question.", n=len(passages), context=ctx)
    enc = tok(prompt, claim, truncation="only_first", max_length=4096, return_tensors="pt")
    n_answer = len(tok(claim, add_special_tokens=False)["input_ids"])
    start = enc["input_ids"].shape[1] - n_answer - 1
    with torch.no_grad():
        probs = torch.softmax(model(**enc).logits, dim=-1)[0, :, 1]
    return float(probs[start:start + n_answer].max()) if n_answer else 0.0


def nli_sentence_probs(question: str, passages: list[str], answer: str, sentences: list[str]
                       ) -> Optional[list[Optional[float]]]:
    """One NLI pass over the whole answer; returns the max 'unsupported' token probability per sentence.

    None when the model isn't available (slim install or not downloaded yet) — callers fall back to rules only.
    """
    from app.core.config import settings
    nli = _load_nli(settings.verifier_nli_model)
    if not nli or not answer.strip():
        return None
    try:
        import torch
        tok, model = nli["tok"], nli["model"]
        ctx = "\n".join(f"passage {i + 1}: {p}" for i, p in enumerate(passages))
        prompt = _QA_PROMPT.format(question=question or "Answer the question.", n=len(passages), context=ctx)
        enc = tok(prompt, answer, truncation="only_first", max_length=4096, return_tensors="pt",
                  return_offsets_mapping=True)
        offsets = enc.pop("offset_mapping")[0].tolist()
        n_answer = len(tok(answer, add_special_tokens=False)["input_ids"])
        start = enc["input_ids"].shape[1] - n_answer - 1
        with torch.no_grad():
            probs = torch.softmax(model(**enc).logits, dim=-1)[0, :, 1].tolist()
        tokens = [(offsets[i][0], offsets[i][1], probs[i]) for i in range(start, start + n_answer)]
        out, cursor = [], 0
        for s in sentences:
            lo = answer.find(s, cursor)
            if lo < 0:
                out.append(None)
                continue
            hi, cursor = lo + len(s), lo + len(s)
            inside = [p for a, b, p in tokens if a < hi and b > lo and b > a]
            out.append(max(inside) if inside else None)
        return out
    except Exception as e:
        logger.warning("NLI verification failed, using rules only: %s", e)
        return None


def download_nli_model_in_background() -> None:
    """Fetch the NLI weights once (ML installs only), so later answers get the learned check."""
    from app.core.config import settings
    if not settings.enable_nli_verifier:
        return
    try:
        import importlib.util
        if importlib.util.find_spec("transformers") is None or importlib.util.find_spec("torch") is None:
            return
    except Exception:
        return

    def run():
        name = settings.verifier_nli_model
        if _load_nli(name) is not None:
            return  # already cached and now loaded
        try:  # download without holding the lock: answers keep using rules-only checks meanwhile
            from huggingface_hub import snapshot_download
            snapshot_download(name)
        except Exception as e:
            logger.info("NLI model download failed (%s); claim checks stay rules-only", e)
            return
        with _NLI_LOCK:
            _NLI.update(state="idle", name=None)
        _load_nli(name)

    threading.Thread(target=run, daemon=True, name="nli-download").start()

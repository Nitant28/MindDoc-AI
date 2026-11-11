"""FROZEN copy of claim verifier v2 (app/ai/verifier.py at commit 5c1df06), the baseline for HB-Synth v1 (R6).

Do not edit. The shipped verifier keeps evolving in app/ai/verifier.py; this file lets the benchmark score v2 and the
current verifier side by side on the same cases. The NLI helpers are dropped (the baseline is rules-only).
"""
from __future__ import annotations

import logging
import re
import threading
from datetime import date
from dataclasses import dataclass, field
from typing import Optional

from app.ml.insights import split_sentences
from app.ml.retrieval import STOPWORDS, _stem

logger = logging.getLogger(__name__)

# ----------------------------------------------------------------------------------------------- text helpers

_EXTRA_STOP = {"either", "neither", "also", "both", "any", "all", "each", "every", "per", "a", "an", "same",
               "whole", "entire", "total", "ltd", "pvt", "llp", "inc", "limited", "private", "rs", "inr",
               "must", "shall", "may", "will", "can", "lakh", "lakhs", "crore", "crores", "million", "billion",
               "thousand", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
               "eleven", "twelve", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"}
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


def _sentences(text: str) -> list[str]:
    """Sentences, with each line (e.g. a table row) treated as its own unit."""
    out = []
    for line in _norm(text).splitlines():
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
                           r"prohibit(?:s|ed)?|forbidden|disallow(?:s|ed)?|invalid|exclud(?:e|es|ed|ing)|"
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
                "fy", "most", "after", "receivables"}
_ORG_SUFFIX = re.compile(r"\b(pvt|private|ltd|limited|llp|inc|co)\.?\b", re.I)
_PASSIVE_RE = re.compile(r"\b(is|are|was|were|be|been|being|get|got|gets)\s+(?:\w+ly\s+)?\w+(?:ed|en|wn|id|ld|lt|ht)\b",
                         re.I)
_SUBJECT_PREFIX = re.compile(r"^(?:\W|\d|the\b|a\b|an\b|on\b|in\b|at\b|if\b|its\b|their\b|his\b|her\b|"
                             r"\d{1,2}\s+\w+\s+\d{4}\b)*$", re.I)


def _entity_key(name: str) -> str:
    return " ".join(_ORG_SUFFIX.sub(" ", name.lower().replace("'s", "")).replace(".", " ").split())


def extract_entities(text: str) -> list[tuple[str, int]]:
    """Capitalised name spans (organisations, people, places, defined parties, acronyms) with char offsets."""
    out = []
    for m in _ENTITY_RE.finditer(text):
        raw = m.group(0)
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
        if clause[pos + len(name):pos + len(name) + 2] == "'s":
            continue  # possessive: not a participant
        key = _entity_key(name)
        prep = re.search(r"\b(by|from|to)\s+(?:the\s+)?$", clause[max(0, pos - 12):pos].lower())
        if prep:
            roles[key] = "SOURCE" if prep.group(1) in ("by", "from") else "TARGET"
            continue
        segment = clause[:pos].rsplit(",", 1)[-1]
        if _SUBJECT_PREFIX.match(segment.strip()) is not None:
            passive = bool(_PASSIVE_RE.search(clause[pos:]))
            roles[key] = "TARGET" if passive else "SOURCE"
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


def _best_clause(claim_words: set[str], clauses: list[str]) -> tuple[Optional[str], float]:
    best, score = None, 0.0
    for c in clauses:
        s = _dice(claim_words, content_words(c))
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

    # ---- numbers (amounts, percentages, counts)
    c_nums, s_nums = extract_numbers(c_masked), extract_numbers(s_masked)
    plain = [n.value for n in s_nums if not n.pct]
    derived = {a + b for i, a in enumerate(plain) for b in plain[i + 1:]} | \
              {abs(a - b) for i, a in enumerate(plain) for b in plain[i + 1:]} if len(plain) <= 25 else set()
    full = sorted({(r.y, r.m, r.d) for r in s_readings if r.y and r.m and r.d})
    for i, a in enumerate(full):  # intervals between source dates: "two days later", "about 20 months"
        for b in full[i + 1:]:
            try:
                days = abs((date(*b) - date(*a)).days)
            except ValueError:
                continue
            derived |= {float(days), round(days / 30.44, 1), round(days / 7, 1), round(days / 365.25, 1)}
    for n in c_nums:
        tol = 0.05 if n.approx else 1e-6
        pool = [s.value for s in s_nums if s.pct == n.pct]
        if any(_close(n.value, s, tol) for s in pool):
            continue
        if not n.pct and any(_close(n.value, d, max(tol, 1e-6)) for d in derived):
            continue  # e.g. a total of two figures in the source
        v.add("number", f"“{n.text}” is not in the source" + (" (not within 5% either)" if n.approx else ""))

    # ---- frequency bound to a number ("₹3,25,000 per month" vs "per year")
    def nearest_freq(text: str, pos: int, window: int = 40) -> Optional[str]:
        best, dist = None, window + 1
        for kind, rx in _FREQ_RE.items():
            for m in rx.finditer(text):
                d = min(abs(m.start() - pos), abs(m.end() - pos))
                if d < dist:
                    best, dist = kind, d
        return best

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
    best, score = _best_clause(cw, sentences)
    if best and score >= 0.3:
        bw = content_words(best)
        if _polarity(claim, bw) != _polarity(best, cw):
            v.add("negation", f"negation differs from the source: “{best[:140]}”")
        for a_rx, b_rx in _DIR_RE:
            ca, cb, sa, sb = a_rx.search(claim), b_rx.search(claim), a_rx.search(best), b_rx.search(best)
            if (ca and not cb and sb and not sa) or (cb and not ca and sa and not sb):
                word = (ca or cb).group(0)
                other = (sb or sa).group(0)
                v.add("direction", f"the claim says “{word}”, the source says “{other}”")

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

    return v

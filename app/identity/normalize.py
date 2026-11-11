"""Name and identifier normalisation for entity resolution (ADR-0009).

Normalisation only canonicalises spelling variants of the *same* words (case, punctuation, legal-form spellings,
honorifics). It never drops distinguishing words, so "Sunrise Traders" and "Sunrise Trading Co" stay different.
"""
from __future__ import annotations

import re

# Legal-form spellings -> one canonical token sequence. Order matters: longest first.
_LEGAL_FORMS = [
    (r"\bprivate\s+limited\b", "pvt ltd"), (r"\bpvt\.?\s*ltd\.?\b", "pvt ltd"), (r"\bp\.?\s*ltd\.?\b", "pvt ltd"),
    (r"\bpvt\b\.?", "pvt"), (r"\blimited\b", "ltd"), (r"\bltd\b\.?", "ltd"),
    (r"\blimited\s+liability\s+partnership\b", "llp"), (r"\bl\.?\s*l\.?\s*p\.?\b", "llp"),
    (r"\bcompany\b", "co"), (r"\bco\b\.?", "co"), (r"\bcorporation\b", "corp"), (r"\bcorp\b\.?", "corp"),
    (r"\bincorporated\b", "inc"), (r"\b(and|&)\b", "and"),
]
LEGAL_TOKENS = {"pvt", "ltd", "llp", "co", "corp", "inc", "and"}
_PREFIXES = re.compile(r"^(m\s*/\s*s\.?|messrs\.?|mr\.?|mrs\.?|ms\.?|shri\.?|smt\.?|dr\.?)\s+", re.I)


def normalize_name(name: str) -> str:
    """Lower-case, punctuation-free, legal forms canonicalised, honorifics removed, whitespace collapsed."""
    s = (name or "").strip()
    s = _PREFIXES.sub("", s)
    s = s.lower().replace("&", " and ")
    s = re.sub(r"(?<=\b[a-z])\.(?=[a-z]\b)", "", s)     # A.B.C. -> ABC (initialisms)
    s = re.sub(r"\b([a-z])\.\s*(?=[a-z]\.)", r"\1", s)
    for pat, rep in _LEGAL_FORMS:
        s = re.sub(pat, rep, s)
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


# Standard business abbreviations, canonicalised to one spelling (both directions map to the short form).
_ABBREV = {"infrastructure": "infra", "engineering": "engg", "industries": "inds", "international": "intl",
           "electricals": "elec", "electrical": "elec", "pharmaceuticals": "pharma", "components": "comp",
           "brothers": "bros", "manufacturing": "mfg", "services": "svcs", "enterprises": "ent"}


def core_name(name_norm: str) -> str:
    """The normalised name without legal-form tokens: 'sunrise traders pvt ltd' -> 'sunrise traders'."""
    toks = [_ABBREV.get(t, t) for t in name_norm.split() if t not in LEGAL_TOKENS]
    return " ".join(toks) or name_norm


def legal_form(name_norm: str) -> str | None:
    """The legal form printed in a normalised name, if any: pvt ltd | ltd | llp | co."""
    toks = name_norm.split()
    if "llp" in toks:
        return "llp"
    if "ltd" in toks:
        return "pvt ltd" if "pvt" in toks else "ltd"
    if toks and toks[-1] == "co":
        return "co"
    return None


def sorted_key(core: str) -> str:
    return " ".join(sorted(core.split()))


def initial_key(core: str) -> str | None:
    """First initial + last token ("geeta mehta" and "g mehta" -> "g mehta"); None for one-word names."""
    toks = core.split()
    return f"{toks[0][0]} {toks[-1]}" if len(toks) >= 2 else None


def name_kind(name: str) -> str:
    """org | person | unknown, from legal-form and business words only (no guessing from given names)."""
    n = normalize_name(name)
    toks = set(n.split())
    if toks & {"pvt", "ltd", "llp", "corp", "inc", "co", "and"} or toks & _BUSINESS_WORDS:
        return "org"
    if 2 <= len(toks) <= 4 and all(t.isalpha() for t in toks):
        return "person"
    return "unknown"


_BUSINESS_WORDS = {
    "traders", "trading", "enterprises", "industries", "logistics", "polymers", "exports", "imports", "agro", "foods",
    "steel", "works", "packaging", "warehousing", "storage", "realty", "textiles", "pharma", "engineering", "infra",
    "infrastructure", "services", "solutions", "systems", "motors", "auto", "components", "mills", "fisheries",
    "bank", "finance", "capital", "holdings", "builders", "developers", "constructions", "chemicals", "electricals",
    "hospital", "clinic", "school", "trust", "foundation", "society", "store", "stores", "mart", "agencies", "agency",
    # standard abbreviations of the above (see _ABBREV)
    "infra", "engg", "inds", "intl", "elec", "comp", "mfg", "svcs", "ent", "bros", "pharmaceuticals", "group",
}


def normalize_vpa(vpa: str) -> str:
    return (vpa or "").strip().lower()


def normalize_account(account: str) -> str:
    return re.sub(r"[^0-9X]", "", (account or "").upper())

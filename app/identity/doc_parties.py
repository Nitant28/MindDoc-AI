"""Party candidates from documents: a printed name paired with a PAN or GSTIN on the same or the previous line.

Invoices, KYC pages and agreements print identifiers next to the party they belong to, e.g.
`Supplier: Sunrise Traders Pvt Ltd  GSTIN: 27AAACS1234K1Z5` or a name line followed by `PAN: AAACS1234K`.
Pairing is deliberately conservative: an identifier is attached only when a plausible name sits in front of it on
the same line, or on the line just above when that line is a labelled name (`Supplier:`, `Buyer:`, `Bill to:` …).
Unpaired identifiers stay document-level (`GET /documents/{id}/identifiers`). Only structurally valid identifiers
are used (app/finance/identifiers.py). A PAN's holder-status letter (official) sets the party kind.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.finance.identifiers import PAN_HOLDER_STATUS, check_gstin, check_pan
from app.identity.normalize import name_kind

_ID = re.compile(r"\b(\d{2}[A-Z]{5}\d{4}[A-Z][A-Z0-9]{3}|[A-Z]{5}\d{4}[A-Z])\b")
_ID_LABEL = re.compile(r"(?:\b(?:gstin|gst\s*(?:in|no|number|reg(?:istration)?)?|pan(?:\s*(?:no|number))?|"
                       r"uin)\b\.?\s*[:#\-]?\s*)+$", re.I)
_NAME_LABEL = re.compile(r"^\s*(?:supplier|seller|vendor|buyer|purchaser|customer|consignee|consignor|bill(?:ed)?\s*to|"
                         r"ship(?:ped)?\s*to|party|name(?:\s+of\s+(?:the\s+)?(?:party|company|firm|borrower))?|"
                         r"borrower|guarantor|payee|payer|lessor|lessee|landlord|tenant|employer|employee)\b\s*[:\-]\s*",
                         re.I)
_TRAIL = re.compile(r"[\s,;:|\-–(]+$")


@dataclass
class DocParty:
    name: str
    kind: str
    pan: str | None = None
    gstin: str | None = None
    line: str = ""
    identifiers: list = field(default_factory=list)


def _plausible(name: str) -> bool:
    toks = name.split()
    if not 1 <= len(toks) <= 8 or len(name) < 4:
        return False
    if sum(ch.isdigit() for ch in name) > 2:
        return False
    return name_kind(name) in ("org", "person")


def _clean(name: str) -> str:
    name = _NAME_LABEL.sub("", name)
    name = re.split(r"\s{3,}|\t|\|", name)[-1]  # take the last column of a wide line
    return _TRAIL.sub("", name).strip(" .,:")


def find_doc_parties(text: str) -> list[DocParty]:
    out: dict[tuple, DocParty] = {}
    lines = (text or "").splitlines()
    for i, line in enumerate(lines):
        for m in _ID.finditer(line):
            value = m.group(1)
            is_gstin = len(value) == 15
            chk = check_gstin(value) if is_gstin else check_pan(value)
            if not chk.valid_structure:
                continue
            before = _ID_LABEL.sub("", line[: m.start()]).rstrip()
            name = _clean(before)
            if not _plausible(name):
                name = ""
                prev = next((lines[j] for j in range(i - 1, max(-1, i - 3), -1) if lines[j].strip()), "")
                if prev and _NAME_LABEL.match(prev) and not _ID.search(prev):
                    cand = _clean(prev)
                    name = cand if _plausible(cand) else ""
            if not name:
                continue
            pan = value[2:12] if is_gstin else value
            kind = "person" if pan[3] == "P" else ("org" if pan[3] in PAN_HOLDER_STATUS else name_kind(name))
            key = (name.lower(), pan)
            dp = out.setdefault(key, DocParty(name=name, kind=kind, pan=pan, line=line.strip()[:300]))
            if is_gstin:
                dp.gstin = value
            dp.identifiers.append({"scheme": "GSTIN" if is_gstin else "PAN", "value": value})
    return list(out.values())

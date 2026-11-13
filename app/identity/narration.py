"""Counterparty candidates from bank-statement narrations (design E §S7, ADR-0009).

Indian narrations commonly follow channel-prefixed layouts: `UPI/<rrn>/<name>/<vpa>/<note>`, `NEFT/<utr>/<name>`,
`RTGS/<utr>/<name>`, `IMPS/P2A/<rrn>/<name>`, `NACH/<umrn>/<name>`, `CHQ PAID <no> <name>`, `CHQ DEP <no> <name>`.
Real banks vary these (separators, order, truncation), so extraction returns a *candidate* with the fields it could
read and the pattern used; it never invents a name. Cash, ATM, interest and charges have no counterparty.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from app.finance.identifiers import check_ifsc

_VPA = re.compile(r"\b([a-z0-9][a-z0-9._\-]{1,63}@[a-z][a-z0-9]{1,31})\b", re.I)
_IFSC = re.compile(r"\b([A-Z]{4}0[A-Z0-9]{6})\b")
_NO_PARTY = re.compile(r"^(cash|atm|int(erest)?\b|sms|chq\s*book|chgs?|charges|gst\b|tds\b|min\s*bal|by\s+cash|"
                       r"cash\s+deposit\s+by\s+self|self\b)", re.I)
_REF_TOKEN = re.compile(r"^(?=(?:[A-Z]*\d){6})[A-Z0-9]+$")  # UTR/RRN/cheque-like: upper-case run with >= 6 digits
_TRAILING_NOTES = re.compile(r"\b(emi|collect|payment|pay|transfer|trf|salary|rent|refund|reversal)\b\.?$", re.I)


@dataclass
class Counterparty:
    name: str                       # as printed (cleaned of channel/reference tokens), may be truncated
    channel: str                    # UPI | NEFT | RTGS | IMPS | NACH | CHQ | OTHER
    vpa: Optional[str] = None
    ifsc: Optional[str] = None
    reference: Optional[str] = None
    pattern: str = ""
    notes: list = field(default_factory=list)


def _clean_name(parts: list[str]) -> str:
    words = [p for p in parts if p and not _REF_TOKEN.match(p) and not _VPA.fullmatch(p)]
    name = " ".join(" ".join(words).split())
    prev = None
    while prev != name:                       # strip trailing purpose notes ("EMI", "Collect")
        prev, name = name, _TRAILING_NOTES.sub("", name).strip(" -/.")
    return name


def extract_counterparty(narration: str) -> Optional[Counterparty]:
    text = " ".join((narration or "").split())
    if not text or _NO_PARTY.match(text):
        return None
    vpa_m = _VPA.search(text)
    vpa = vpa_m.group(1).lower() if vpa_m else None
    ifsc_m = _IFSC.search(text)
    ifsc = ifsc_m.group(1) if ifsc_m and check_ifsc(ifsc_m.group(1)).valid_structure else None
    head = re.split(r"[/:\-]", text, maxsplit=1)[0].strip().upper()

    if "/" in text and head in ("UPI", "NEFT", "RTGS", "IMPS", "NACH", "ACH", "ECS", "MMT"):
        segs = [s.strip() for s in text.split("/")]
        channel = {"MMT": "IMPS", "ACH": "NACH", "ECS": "NACH"}.get(head, head)
        rest = segs[1:]
        if channel == "IMPS" and rest and rest[0].upper() in ("P2A", "P2P", "P2M"):
            rest = rest[1:]
        ref = rest[0] if rest and _REF_TOKEN.match(rest[0].replace(" ", "")) else None
        if ref:
            rest = rest[1:]
        # the name is the first segment that is not a reference, VPA, IFSC or bank code
        name_segs = []
        for seg in rest:
            if _VPA.fullmatch(seg) or _IFSC.fullmatch(seg) or _REF_TOKEN.match(seg.replace(" ", "")):
                if name_segs:
                    break
                continue
            name_segs.append(seg)
            break                      # later segments are VPAs, notes ("INV 22", "Collect") or bank codes
        name = _clean_name(" ".join(name_segs).split())
        return Counterparty(name, channel, vpa, ifsc, ref, f"{channel.lower()}_slash") if name or vpa else None

    m = re.match(r"^(?:CHQ|CHEQUE|CLG)\s*(?:PAID|DEP(?:OSIT)?|ISSUED|RETURN(?:ED)?)?\s*(?:NO\.?\s*)?(\d{4,})?\s*(.*)$",
                 text, re.I)
    if m and text[:3].upper() in ("CHQ", "CHE", "CLG"):
        name = _clean_name(m.group(2).split())
        return Counterparty(name, "CHQ", vpa, ifsc, m.group(1), "cheque") if name else None
    if vpa:
        name = _clean_name(_VPA.sub(" ", text).split())
        return Counterparty(name, "UPI", vpa, ifsc, None, "vpa_only")
    return None

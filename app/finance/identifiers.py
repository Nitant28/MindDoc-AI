"""Structural validation of Indian financial identifiers (PAN, GSTIN, IFSC) from official specifications only.

Every rule below comes from a primary source (read 2026-11-11); nothing is taken from informal examples. Where the
official source does not publish an algorithm (the PAN check digit, the GSTIN checksum), the check is reported as
*not verified* rather than guessed. A structurally valid identifier is not proof that it was issued or belongs to
the named party, and an invalid one is a data-quality signal for review — never a finding of fraud.

Sources
- PAN: Income Tax Department FAQ "How PAN is formed and how it gets its unique identity?"
  https://wm.incometaxindia.gov.in/w/how-pan-is-formed-and-how-it-gets-its-unique-identity-
  (10 characters; 1–3 alphabetic series AAA–ZZZ; 4th = holder status A/B/C/F/G/H/J/L/P/T; 5th = first letter of
  surname or name; 6–9 sequential number 0001–9999; 10th = alphabetic check digit, algorithm not published)
- IFSC: Reserve Bank of India, NEFT FAQ "What is Indian Financial System Code?"
  https://www.rbi.org.in/scripts/FS_FAQs.aspx?Id=60
  (11 characters; first 4 alphabetic = bank; 5th = 0; last 6 = branch)
- GSTIN: CBIC GST Registration Rules, format of the GSTIN https://cbic-gst.gov.in/gst-registration-rules.html
  (2 characters State code; 10 characters PAN or TAN; 2 characters entity code; 1 checksum character, algorithm not
  described) and the GST e-invoice master State codes https://einvoice1.gst.gov.in/Others/MasterCodes (version 1.01)
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

SOURCES = {
    "PAN": "https://wm.incometaxindia.gov.in/w/how-pan-is-formed-and-how-it-gets-its-unique-identity-",
    "IFSC": "https://www.rbi.org.in/scripts/FS_FAQs.aspx?Id=60",
    "GSTIN": "https://cbic-gst.gov.in/gst-registration-rules.html ; "
             "state codes: https://einvoice1.gst.gov.in/Others/MasterCodes",
}

PAN_HOLDER_STATUS = {
    "A": "Association of Persons", "B": "Body of Individuals", "C": "Company", "F": "Firm / Limited Liability Partnership",
    "G": "Government Agency", "H": "Hindu Undivided Family", "J": "Artificial Juridical Person", "L": "Local Authority",
    "P": "Individual", "T": "Trust",
}

GST_STATE_CODES = {
    "01": "Jammu and Kashmir", "02": "Himachal Pradesh", "03": "Punjab", "04": "Chandigarh", "05": "Uttarakhand",
    "06": "Haryana", "07": "Delhi", "08": "Rajasthan", "09": "Uttar Pradesh", "10": "Bihar", "11": "Sikkim",
    "12": "Arunachal Pradesh", "13": "Nagaland", "14": "Manipur", "15": "Mizoram", "16": "Tripura", "17": "Meghalaya",
    "18": "Assam", "19": "West Bengal", "20": "Jharkhand", "21": "Odisha", "22": "Chhattisgarh", "23": "Madhya Pradesh",
    "24": "Gujarat", "25": "Daman and Diu", "26": "Dadra and Nagar Haveli", "27": "Maharashtra", "29": "Karnataka",
    "30": "Goa", "31": "Lakshadweep", "32": "Kerala", "33": "Tamil Nadu", "34": "Puducherry",
    "35": "Andaman and Nicobar", "36": "Telangana", "37": "Andhra Pradesh", "38": "Ladakh", "96": "Other countries",
    "97": "Other territory", "99": "Other countries",
}


@dataclass
class IdentifierCheck:
    kind: str                       # PAN | GSTIN | IFSC
    value: str                      # normalised (upper case, no spaces)
    valid_structure: bool
    issues: list = field(default_factory=list)       # structural problems found
    not_verified: list = field(default_factory=list)  # parts the official sources give no way to check
    details: dict = field(default_factory=dict)
    source: str = ""

    def as_dict(self) -> dict:
        return {"kind": self.kind, "value": self.value, "valid_structure": self.valid_structure,
                "issues": self.issues, "not_verified": self.not_verified, "details": self.details,
                "source": self.source}


def _norm(value: str) -> str:
    return re.sub(r"[\s-]", "", str(value or "")).upper()


def _pan_issues(v: str) -> list:
    issues = []
    if len(v) != 10:
        return [f"must be 10 characters (got {len(v)})"]
    if not v[:5].isalpha() or not v[:5].isascii():
        issues.append("characters 1-5 must be letters")
    if not v[5:9].isdigit():
        issues.append("characters 6-9 must be digits")
    elif v[5:9] == "0000":
        issues.append("characters 6-9 run from 0001 to 9999")
    if not (v[9].isalpha() and v[9].isascii()):
        issues.append("character 10 (check digit) must be a letter")
    if v[3:4].isalpha() and v[3] not in PAN_HOLDER_STATUS:
        issues.append(f"character 4 '{v[3]}' is not a listed holder status ({''.join(sorted(PAN_HOLDER_STATUS))})")
    return issues


def check_pan(value: str) -> IdentifierCheck:
    v = _norm(value)
    issues = _pan_issues(v)
    details = {"holder_status": PAN_HOLDER_STATUS.get(v[3])} if len(v) == 10 and v[3] in PAN_HOLDER_STATUS else {}
    return IdentifierCheck("PAN", v, not issues, issues,
                           ["check digit (character 10): the Income Tax Department does not publish the algorithm"],
                           details, SOURCES["PAN"])


def check_ifsc(value: str) -> IdentifierCheck:
    v = _norm(value)
    issues = []
    if len(v) != 11:
        issues.append(f"must be 11 characters (got {len(v)})")
    else:
        if not (v[:4].isalpha() and v[:4].isascii()):
            issues.append("characters 1-4 (bank) must be letters")
        if v[4] != "0":
            issues.append("character 5 must be 0 (zero)")
        if not (v[5:].isalnum() and v[5:].isascii()):
            issues.append("characters 6-11 (branch) must be letters or digits")
    return IdentifierCheck("IFSC", v, not issues, issues,
                           ["whether the bank and branch codes are allotted (needs RBI's published IFSC lists)"],
                           {"bank_code": v[:4]} if not issues else {}, SOURCES["IFSC"])


def check_gstin(value: str) -> IdentifierCheck:
    v = _norm(value)
    issues, details = [], {}
    not_verified = ["checksum character (15): the CBIC/GSTN sources consulted do not describe the algorithm"]
    if len(v) != 15:
        issues.append(f"must be 15 characters (got {len(v)})")
    elif not v.isascii() or not v.isalnum():
        issues.append("must contain only letters and digits")
    else:
        state, pan_or_tan, entity, checksum = v[:2], v[2:12], v[12:14], v[14]
        if state not in GST_STATE_CODES:
            issues.append(f"state code '{state}' is not in the GST state code list")
        else:
            details["state"] = GST_STATE_CODES[state]
        pan_problems = _pan_issues(pan_or_tan)
        if pan_problems:
            # the rule allows a PAN or a TAN here; the TAN layout is not in the sources consulted
            not_verified.append("characters 3-12 do not follow the PAN layout; they may be a TAN, which is not checked")
        else:
            details["pan"] = pan_or_tan
            details["holder_status"] = PAN_HOLDER_STATUS.get(pan_or_tan[3])
        details["entity_code"] = entity
    return IdentifierCheck("GSTIN", v, not issues, issues, not_verified, details, SOURCES["GSTIN"])


# Candidate patterns for finding identifiers in text (validation is done by the checkers above).
_CANDIDATES = {
    "GSTIN": re.compile(r"\b\d{2}[A-Z]{5}\d{4}[A-Z][A-Z0-9]{3}\b"),
    "PAN": re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b"),
    "IFSC": re.compile(r"\b[A-Z]{4}0[A-Z0-9]{6}\b"),
}
_CHECKERS = {"PAN": check_pan, "GSTIN": check_gstin, "IFSC": check_ifsc}


def find_identifiers(text: str) -> list[dict]:
    """Identifier candidates in text with their structural check. A PAN embedded in a GSTIN is reported once, as part
    of the GSTIN. Results are ordered by position and de-duplicated by (kind, value)."""
    hits, seen, gst_spans = [], set(), []
    for kind in ("GSTIN", "PAN", "IFSC"):
        for m in _CANDIDATES[kind].finditer(text or ""):
            if kind == "PAN" and any(a <= m.start() and m.end() <= b for a, b in gst_spans):
                continue
            if kind == "GSTIN":
                gst_spans.append((m.start(), m.end()))
            key = (kind, m.group(0))
            if key in seen:
                continue
            seen.add(key)
            hits.append((m.start(), _CHECKERS[kind](m.group(0)).as_dict()))
    return [h for _, h in sorted(hits, key=lambda x: x[0])]

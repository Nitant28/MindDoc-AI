"""Disclosure copies of frozen reports: third-party personal data withheld, with reasons recorded (R8).

Why: in *SBI v. Amit Iron* (Supreme Court, 7 Apr 2026, 2026 INSC 323, para 126(e)) a forensic report the bank
relies on must be given to the borrower; only parts that affect third-party privacy may be withheld, with reasons
recorded (docs/review/D_MARKET_RESEARCH.md §1.2). MindDoc does not decide what the law requires in a given case; it
produces a reviewable copy and logs every item it withheld.

Rules (deterministic, conservative):
* **Subjects** are the parties the report is about. By default: the holders of the statement accounts in the case;
  the reviewer can change the list. Their data is not withheld.
* **Third-party personal data** = names of parties that are not subjects and are people, or whose kind is unknown
  (treated as people, to be safe). Organisations are not personal data and stay visible.
  Each withheld party gets a stable label ("Third party 1") so a reader can still follow the money.
* **Identifiers in free text** (narrations, the analyst's wording, file names): UPI VPAs, email addresses, PANs and
  digit runs of 9 or more (account and phone numbers) are masked wherever they appear, because MindDoc cannot always
  tell whose they are. Account numbers keep their last four digits.
* The copy is canonical JSON with its own SHA-256 and the SHA-256 of the frozen report it came from. The internal
  log (what was withheld, with the original values) stays with the bank; the disclosed copy lists only labels,
  kinds, reasons and counts.
"""
from __future__ import annotations

import copy
import hashlib
import re
from dataclasses import dataclass, field
from typing import Optional

from app.findings.service import canonical

METHOD = "disclosure-redaction v1"
LEGAL_BASIS = ("Third-party privacy: SBI v. Amit Iron Pvt Ltd, Supreme Court of India, 7 Apr 2026, 2026 INSC 323, "
               "para 126(e)")

_VPA = re.compile(r"\b[\w.\-]{2,64}@[A-Za-z][A-Za-z0-9]{1,30}\b")
_EMAIL = re.compile(r"\b[\w.+\-]+@[\w\-]+(?:\.[\w\-]+)+\b")
_PAN = re.compile(r"\b[A-Z]{3}[ABCFGHLJPT][A-Z]\d{4}[A-Z]\b")
_DIGITS = re.compile(r"(?<!\d)\d{9,18}(?!\d)")


@dataclass
class Withheld:
    label: str
    kind: str                  # person | unknown | identifier
    reason: str
    values: set = field(default_factory=set)   # internal only
    count: int = 0


@dataclass
class Redactor:
    """Replaces withheld names and identifiers in text, counting what it did. `found` keeps the exact substrings
    that were replaced (to black them out on page images)."""
    parties: list[tuple[str, re.Pattern]]                     # (label, pattern over every printed name)
    log: dict[str, Withheld]
    found: set = field(default_factory=set)

    def text(self, value: Optional[str]) -> Optional[str]:
        if not value:
            return value
        out = value
        # identifiers first (an email or VPA can contain a name), then names
        for name, pat, repl in (("email address", _EMAIL, None), ("UPI address", _VPA, None),
                                ("PAN", _PAN, None), ("account or phone number", _DIGITS, "digits")):
            def sub(m, name=name, repl=repl):
                raw = m.group(0)
                self.found.add(raw)
                w = self.log.setdefault(f"identifier:{name}", Withheld(
                    label=name, kind="identifier",
                    reason="identifier in free text that cannot always be attributed to a subject"))
                w.values.add(raw)
                w.count += 1
                return ("X" * (len(raw) - 4) + raw[-4:]) if repl == "digits" else f"[{name} withheld]"
            out = pat.sub(sub, out)
        for label, pat in self.parties:
            def sub_name(m, label=label):
                self.found.add(m.group(0))
                self.log[label].count += 1
                return f"[{label}]"
            out = pat.sub(sub_name, out)
        return out


def _name_pattern(names: set[str]) -> Optional[re.Pattern]:
    alts = []
    for n in sorted(names, key=len, reverse=True):
        tokens = [re.escape(t) for t in re.split(r"[\W_]+", n) if t]
        if not tokens or sum(len(t) for t in tokens) < 3:
            continue
        alts.append(r"[\W_]+".join(tokens))
    return re.compile(r"(?<![A-Za-z0-9])(?:" + "|".join(alts) + r")(?![A-Za-z0-9])", re.IGNORECASE) if alts else None


def build_redactor(parties: list[dict], subjects: set[int]) -> Redactor:
    """`parties`: canonical parties of the case, each {"id", "kind", "names": set of printed names}."""
    log: dict[str, Withheld] = {}
    pats: list[tuple[str, re.Pattern]] = []
    third = [p for p in parties if p["id"] not in subjects and p["kind"] in ("person", "unknown")]
    for i, p in enumerate(sorted(third, key=lambda p: p["id"]), start=1):
        pat = _name_pattern(p["names"])
        if pat is None:
            continue
        label = f"Third party {i}"
        log[label] = Withheld(label=label, kind=p["kind"], values=set(p["names"]),
                              reason="name of a third party who is a natural person" if p["kind"] == "person" else
                              "name of a third party whose kind is unknown (treated as a natural person)")
        pats.append((label, pat))
    return Redactor(pats, log)


def redact_snapshot(snapshot: dict, red: Redactor) -> dict:
    out = copy.deepcopy(snapshot)
    for f in out.get("findings", []):
        f["title"] = red.text(f.get("title"))
        f["statement"] = red.text(f.get("statement"))
        f.pop("created_by", None)
        for s in f.get("support", []):
            c = s.get("claim", {})
            c["party"] = red.text(c.get("party"))
            c["subject"] = red.text(c.get("subject"))
            for e in s.get("evidence", []):
                e["quote"] = red.text(e.get("quote"))
                e["filename"] = red.text(e.get("filename"))
        rob = f.get("robustness") or {}
        for docs in (rob.get("sources") or {}).values():
            for d in docs:
                d["filename"] = red.text(d.get("filename"))
    return out


def make(snapshot: dict, base_hash: str, parties: list[dict], subjects: set[int], recipient: str,
         created_at: str) -> tuple[dict, str, list[dict]]:
    """Returns (disclosed copy, its SHA-256, internal log with the withheld values)."""
    red = build_redactor(parties, subjects)
    body = redact_snapshot(snapshot, red)
    withheld = [w for w in red.log.values() if w.count]
    body["disclosure"] = {
        "method": METHOD, "legal_basis": LEGAL_BASIS, "recipient": recipient, "created_at": created_at,
        "base_report_sha256": base_hash,
        "subjects": sorted(p["display"] for p in parties if p["id"] in subjects),
        "withheld": [{"label": w.label, "kind": w.kind, "reason": w.reason, "occurrences": w.count}
                     for w in withheld],
        "notice": "Parts of this report were withheld only to protect third parties' personal data; each withheld "
                  "item is listed with its reason. Organisations are not withheld. The full report is kept by the "
                  "issuer and is identified by base_report_sha256."}
    text = canonical(body)
    internal = [{"label": w.label, "kind": w.kind, "reason": w.reason, "occurrences": w.count,
                 "values": sorted(w.values)} for w in withheld]
    return body, hashlib.sha256(text.encode("utf-8")).hexdigest(), internal


# ------------------------------------------------------------------------------------------------ database

def case_parties(db, case_id: int) -> tuple[list[dict], set[int]]:
    """Canonical parties of the case with every printed name, and the default subjects (account holders)."""
    from app.database.models import BankAccount, CaseDocument, Party, PartyMention, Statement
    from app.identity.service import canonical_map
    cmap = canonical_map(db, case_id)
    records = db.query(Party).filter(Party.case_id == case_id).all()
    by_canon: dict[int, dict] = {}
    for r in records:
        cid = cmap.get(r.id, r.id)
        p = by_canon.setdefault(cid, {"id": cid, "kinds": set(), "names": set(), "display": r.name})
        p["kinds"].add(r.kind or "unknown")
        p["names"].add(r.name)
    for p in by_canon.values():
        kinds = p.pop("kinds")
        p["kind"] = "org" if kinds == {"org"} else "person" if "person" in kinds else \
            "unknown" if "unknown" in kinds else "org"
    holders = {cmap.get(m.party_id, m.party_id) for m in db.query(PartyMention).filter(
        PartyMention.source_type == "account_holder",
        PartyMention.party_id.in_([r.id for r in records] or [-1]))}
    # holder names typed by an analyst may not be party records yet: match them by name
    holder_names = {(name or "").strip().lower() for (name,) in db.query(BankAccount.holder_name)
                    .join(Statement, Statement.bank_account_id == BankAccount.id)
                    .join(CaseDocument, CaseDocument.document_id == Statement.document_id)
                    .filter(CaseDocument.case_id == case_id, BankAccount.holder_name.isnot(None))}
    holders |= {p["id"] for p in by_canon.values() if any(n.strip().lower() in holder_names for n in p["names"])}
    return sorted(by_canon.values(), key=lambda p: p["id"]), holders

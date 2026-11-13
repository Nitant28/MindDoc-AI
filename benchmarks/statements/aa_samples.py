"""Synthetic ReBIT deposit FI payloads (ADR-0015 acceptance samples), built from the published schema's structure with
fictional values from the StatementBench history generator. No real account, holder or consent data.

    python -m benchmarks.statements.aa_samples --out benchmarks/statements/data/aa --n 3
"""
from __future__ import annotations

import argparse
import json
import random
import re
from datetime import date, datetime, time, timedelta
from pathlib import Path
from xml.sax.saxutils import quoteattr

from benchmarks.statements.generator import make_history

NS = "http://api.rebit.org.in/FISchema/deposit"


def _mode(narration: str) -> str:
    head = narration.split("/")[0].split(" ")[0].upper()
    return {"UPI": "UPI", "NEFT": "FT", "RTGS": "FT", "IMPS": "FT", "ATM": "ATM", "CASH": "CASH"}.get(head, "OTHERS")


def build(txns, *, start: date, end: date, masked: str = "XXXXXXXX4321", fmt: str = "json",
          numeric_amounts: bool = False, summary_balance=None, summary_at: datetime | None = None) -> bytes:
    """Serialise generator transactions as a deposit payload. Amounts are written from exact paise."""
    def dec(minor: int) -> str:
        sign = "-" if minor < 0 else ""
        return f"{sign}{abs(minor) // 100}.{abs(minor) % 100:02d}"

    items, clock = [], {}
    for i, t in enumerate(txns, 1):
        n = clock.get(t.date, 0)
        clock[t.date] = n + 1
        ts = datetime.combine(t.date, time(9, 0)) + timedelta(minutes=7 * n)
        items.append({"type": "CREDIT" if t.credit.minor else "DEBIT", "mode": _mode(t.narration),
                      "amount": dec(t.credit.minor or t.debit.minor), "currentBalance": dec(t.balance.minor),
                      "transactionTimestamp": ts.isoformat() + "+05:30", "valueDate": t.value_date.isoformat(),
                      "txnId": f"S{i:08d}", "narration": t.narration, "reference": t.ref or ""})
    last = txns[-1]
    summary = {"currentBalance": dec(summary_balance if summary_balance is not None else last.balance.minor),
               "currency": "INR",
               "balanceDateTime": (summary_at or datetime.combine(end, time(23, 59))).isoformat() + "+05:30",
               "type": "CURRENT", "branch": "Andheri", "facility": "OD", "ifscCode": "MERI0123456",
               "micrCode": "400999001", "openingDate": "2019-04-01", "currentODLimit": "500000.00",
               "drawingLimit": "500000.00", "status": "ACTIVE"}
    account = {"linkedAccRef": "SYNTH-LINK-0001", "maskedAccNumber": masked, "type": "deposit", "version": "1.1"}
    if fmt == "json":
        body = {"Account": {**account, "Summary": {**summary, "Pending": {"amount": "0.00"}},
                            "Transactions": {"startDate": start.isoformat(), "endDate": end.isoformat(),
                                             "Transaction": items}}}
        s = json.dumps(body, indent=1)
        if numeric_amounts:
            s = re.sub(r'"amount": "(-?[0-9]+\.[0-9]+)"', r'"amount": \1', s)
        return s.encode("utf-8")
    attrs = lambda d: " ".join(f"{k}={quoteattr(str(v))}" for k, v in d.items())  # noqa: E731
    xml = [f'<?xml version="1.0" encoding="UTF-8"?>', f'<Account xmlns="{NS}" {attrs(account)}>',
           f'  <Summary {attrs(summary)}><Pending amount="0.00"/></Summary>',
           f'  <Transactions startDate="{start.isoformat()}" endDate="{end.isoformat()}">']
    xml += [f"    <Transaction {attrs(t)}/>" for t in items]
    xml += ["  </Transactions>", "</Account>"]
    return "\n".join(xml).encode("utf-8")


def sample(seed: int = 7, n: int = 30, od: bool = True, **kw):
    """(payload_bytes, opening Money, txns) for a seeded synthetic history."""
    rng = random.Random(seed)
    opening, txns = make_history(rng, od, n, date(2024, 4, 1))
    return build(txns, start=date(2024, 4, 1), end=max(t.date for t in txns), **kw), opening, txns


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", default="benchmarks/statements/data/aa")
    ap.add_argument("--n", type=int, default=3)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for i in range(a.n):
        for fmt in ("json", "xml"):
            data, _, _ = sample(seed=100 + i, fmt=fmt)
            (out / f"aa-deposit-{i + 1}.{fmt}").write_bytes(data)
    print("wrote", a.n * 2, "payloads to", out)


if __name__ == "__main__":
    main()

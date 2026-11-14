"""R7: detectors on real statement PDFs through the API; ledger behaviour (stable keys, kept dispositions)."""
import random
from datetime import date, timedelta

import pytest

from app.discovery import detectors
from app.discovery.detectors import CaseData, Txn


def _t(key, d, amount, direction, cp=None, channel="NEFT", narration="", account="a", holder="p:S"):
    return Txn(key, 1, account, holder, d, amount, direction, cp, None, channel, narration, 1, 1)


def test_detectors_are_deterministic_and_never_name_fraud():
    d0 = date(2024, 5, 2)
    txns = [_t("1", d0, 1_00_00_000_00, "credit", "p:L", narration="NEFT/LN1/LOAN DISB/BANK"),
            _t("2", d0 + timedelta(days=3), 40_00_000_00, "debit", "p:G", "RTGS"),
            _t("3", d0 + timedelta(days=9), 39_50_000_00, "credit", "p:G", "RTGS")]
    txns += [_t(f"c{i}", d0 + timedelta(days=i), (48_000 + 400 * i) * 100, "credit", channel="CASH",
                narration="CASH DEPOSIT") for i in range(4)]
    case = CaseData(txns=txns, names={"p:S": "Subject", "p:G": "Group Co", "p:L": "Lender"}, group={"p:S", "p:G"})
    a, b = detectors.run_all(case), detectors.run_all(case)
    assert [x.key for x in a] == [x.key for x in b]
    assert {x.detector for x in a} == {"end_use", "round_trip", "structuring"}
    for lead in a:
        text = (lead.title + " " + lead.summary).lower()
        assert "fraud" not in text and "launder" not in text
        assert lead.rule_out and lead.txns


def _history(rng, start, rows):
    """Generator transactions with running balances from (day offset, narration, debit, credit) rows."""
    from app.finance.money import Money
    from benchmarks.statements.generator import Txn as GTxn
    opening = Money(25_00_000_00)
    bal, out = opening, []
    for off, narration, debit, credit in sorted(rows, key=lambda r: r[0]):
        d = start + timedelta(days=off)
        bal = bal - Money(debit) + Money(credit)
        out.append(GTxn(date=d, value_date=d, narration=narration, ref=str(rng.randint(10**5, 10**6)),
                        debit=Money(debit), credit=Money(credit), balance=bal))
    return opening, out


def _statement(tmp_path, name, holder, account, rows):
    pytest.importorskip("reportlab")
    from benchmarks.statements.generator import LAYOUTS, render
    opening, txns = _history(random.Random(name), date(2024, 5, 1), rows)
    meta = {"bank": "Meridian Bank Ltd", "branch": "Fort", "ifsc": "MERI0123456", "holder": holder,
            "account_masked": account, "account_type": "CURRENT", "period": ["01-05-2024", "30-06-2024"]}
    pdf = tmp_path / name
    render(pdf, meta, opening, txns, LAYOUTS["A"])
    return pdf.read_bytes()


def test_discovery_ledger_end_to_end(client, tmp_path):
    from tests.test_findings import _upload, _user
    h = _user(client, "r7-owner@example.com")
    a_rows = [(1, "NEFT/LN4471002/LOAN DISB/UNION CREDIT BANK", 0, 1_00_00_000_00),
              (4, "RTGS/UTRA0000017734/ORION HOLDINGS PVT LTD", 40_00_000_00, 0),
              (10, "RTGS/UTRB0000019921/ORION HOLDINGS PVT LTD", 0, 39_50_000_00),
              (12, "NEFT/N66120001/ZENITH SUPPLIES/INV 81", 1_25_000_00, 0),
              (14, "NEFT/N66120077/ZENITH SUPPLIES/INV 81", 1_25_000_00, 0)]
    a_rows += [(16 + i, "CASH DEPOSIT BY SELF", 0, amt) for i, amt in
               enumerate([48_500_00, 49_200_00, 47_800_00, 49_900_00])]
    a_rows += [(20 + i, f"UPI/40{i}1122334/STERLING FOODS/sterling@okbank/Payment", 0, (12_000 + 900 * i) * 100)
               for i in range(6)]
    b_rows = [(4, "RTGS/UTRA0000017734/KESTREL INDUSTRIES PVT LTD", 0, 40_00_000_00),
              (10, "RTGS/UTRB0000019921/KESTREL INDUSTRIES PVT LTD", 39_50_000_00, 0),
              (15, "NEFT/N55120044/APEX LOGISTICS/FREIGHT", 2_10_000_00, 0)]
    _upload(client, h, "kestrel.pdf", _statement(tmp_path, "kestrel.pdf", "Kestrel Industries Pvt Ltd",
                                                 "XXXXXXXX1001", a_rows))
    _upload(client, h, "orion.pdf", _statement(tmp_path, "orion.pdf", "Orion Holdings Pvt Ltd", "XXXXXXXX2002", b_rows))

    run = client.post("/api/discoveries/run", headers=h)
    assert run.status_code == 200, run.text
    # join same-name records the reviewer would accept (holder of one statement = counterparty in the other)
    for r in client.get("/api/parties/reviews", headers=h).json()["reviews"]:
        names = {(r["a"] or {}).get("name", "").lower(), (r["b"] or {}).get("name", "").lower()}
        if all("orion" in n for n in names) or all("kestrel" in n for n in names):
            client.post(f"/api/parties/reviews/{r['id']}", headers=h,
                        json={"decision": "merge", "reason": "holder and counterparty are the same company"})
    run = client.post("/api/discoveries/run", headers=h).json()
    listing = client.get("/api/discoveries", headers=h).json()
    found = {d["detector"] for d in listing["discoveries"]}
    assert {"end_use", "round_trip", "structuring", "duplicate_payment"} <= found, listing["discoveries"]
    assert listing["last_run"]["transactions"] == run["transactions"] >= 18

    rt = next(d for d in listing["discoveries"] if d["detector"] == "round_trip")
    detail = client.get(f"/api/discoveries/{rt['id']}", headers=h).json()
    assert detail["rule_out"] and detail["details"]["path"]
    tx = detail["transactions"]
    assert all(t["page"] and t["seq"] and t["box"] for t in tx)        # every row opens on its page
    assert any(t["claim_id"] for t in tx)                              # usable as finding support

    # dispositions need a reason, survive re-runs, and keys are stable
    assert client.post(f"/api/discoveries/{rt['id']}/disposition", headers=h,
                       json={"status": "dismissed", "reason": ""}).status_code == 422
    assert client.post(f"/api/discoveries/{rt['id']}/disposition", headers=h,
                       json={"status": "confirmed", "reason": "same amount back within six days"}).status_code == 200
    again = client.post("/api/discoveries/run", headers=h).json()
    assert again["new"] == 0
    after = client.get(f"/api/discoveries/{rt['id']}", headers=h).json()
    assert after["status"] == "confirmed" and after["still_detected"]

    # tagging a party as related is recorded and shown; other tenants see nothing
    party = next(p for p in client.get("/api/parties", headers=h).json()["parties"] if "apex" in p["name"].lower())
    assert client.put(f"/api/parties/{party['party_id']}/tags", headers=h,
                      json={"related": True, "reason": "director's relative"}).status_code == 200
    tagged = next(p for p in client.get("/api/parties", headers=h).json()["parties"] if p["party_id"] == party["party_id"])
    assert tagged["tags"].get("related") == "director's relative"
    other = _user(client, "r7-other@example.com")
    assert client.get(f"/api/discoveries/{rt['id']}", headers=other).status_code == 404

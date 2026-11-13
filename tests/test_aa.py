"""Account Aggregator deposit import (ADR-0015): schema validation, exact mapping, reconciliation, provenance.

Samples are synthetic, built from the published ReBIT deposit schema structure (benchmarks/statements/aa_samples.py).
"""
import json
from datetime import date, datetime

import pytest

from app.finance.aa import AAError, parse_deposit

pytest.importorskip("reportlab", reason="the sample builder reuses the StatementBench generator")
from benchmarks.statements.aa_samples import build, sample  # noqa: E402


@pytest.mark.parametrize("fmt", ["json", "xml"])
def test_payload_maps_exactly_and_reconciles(fmt):
    data, opening, txns = sample(seed=11, n=40, fmt=fmt)
    st = parse_deposit(data, f"x.{fmt}")
    assert [(r.date, r.debit, r.credit, r.balance) for r in st.rows] == \
        [(t.date.isoformat(), t.debit.minor, t.credit.minor, t.balance.minor) for t in txns]
    # the schema carries no opening balance: it is derived from the first row and flagged, never assumed
    assert st.opening == opening.minor and st.status == "reconciled_with_flags"
    assert any(c.reason == "opening_derived" for c in st.checks)
    assert st.closing == txns[-1].balance.minor
    assert next(c for c in st.checks if c.scope == "statement").status == "pass"
    assert st.extras[1]["external_id"] == "S00000001" and st.extras[1]["mode"] in {"CASH", "ATM", "CARD", "UPI", "FT", "OTHERS"}
    assert st.schema_version == "1.1" and len(st.payload_sha256) == 64 and st.header["ifsc"] == "MERI0123456"


def test_numeric_json_amounts_are_exact():
    data, _, txns = sample(seed=12, n=30, numeric_amounts=True)
    assert b'"amount": "' not in data  # amounts really are JSON numbers here
    st = parse_deposit(data, "x.json")
    assert [r.debit or r.credit for r in st.rows] == [t.debit.minor or t.credit.minor for t in txns]


def test_misstated_balance_is_flagged_not_fixed():
    data, _, txns = sample(seed=13, n=25)
    obj = json.loads(data)
    obj["Account"]["Transactions"]["Transaction"][9]["currentBalance"] = "1.00"
    st = parse_deposit(json.dumps(obj).encode(), "x.json")
    assert st.status == "needs_review" and st.rows[9].balance == 100
    fail = next(c for c in st.checks if c.status == "fail")
    assert fail.seq == 10 and fail.hypotheses[0]["code"] == "balance_ocr_suspect"


def test_summary_balance_outside_period_is_not_used_as_closing():
    data, _, txns = sample(seed=14, n=20, summary_at=datetime(2030, 1, 1))
    st = parse_deposit(data, "x.json")
    assert st.closing is None and any("closing balance not checked" in w for w in st.warnings)


def test_unsorted_transactions_are_sorted_with_a_warning():
    data, _, txns = sample(seed=15, n=20)
    obj = json.loads(data)
    obj["Account"]["Transactions"]["Transaction"].reverse()
    st = parse_deposit(json.dumps(obj).encode(), "x.json")
    assert [r.balance for r in st.rows] == [t.balance.minor for t in txns]
    assert any("sorted" in w for w in st.warnings)


def _mutate(fn):
    data, _, _ = sample(seed=16, n=10)
    obj = json.loads(data)
    fn(obj["Account"])
    return json.dumps(obj).encode()


@pytest.mark.parametrize("mutate, message", [
    (lambda a: a.update(type="term-deposit"), "must be 'deposit'"),
    (lambda a: a["Transactions"]["Transaction"][3].pop("txnId"), "Transaction 4: missing required attribute txnId"),
    (lambda a: a["Transactions"]["Transaction"][0].update(mode="CHEQUE"), "mode must be one of"),
    (lambda a: a["Transactions"]["Transaction"][0].update(type="REFUND"), "type must be CREDIT or DEBIT"),
    (lambda a: a["Transactions"]["Transaction"][0].update(amount="10.005"), "more than 2 decimal places"),
    (lambda a: a["Transactions"]["Transaction"][0].update(amount="-5.00"), "must not be negative"),
    (lambda a: a["Transactions"]["Transaction"][0].update(transactionTimestamp="yesterday"), "not an ISO date-time"),
    (lambda a: a.update(version="3.0"), "outside the schema range"),
    (lambda a: a.pop("Transactions"), "missing Transactions"),
])
def test_invalid_payloads_are_rejected_with_a_reason(mutate, message):
    with pytest.raises(AAError, match=message):
        parse_deposit(_mutate(mutate), "x.json")


def test_unsafe_or_foreign_xml_is_rejected():
    data, _, _ = sample(seed=17, n=5, fmt="xml")
    evil = data.replace(b'<?xml version="1.0" encoding="UTF-8"?>',
                        b'<?xml version="1.0"?><!DOCTYPE a [<!ENTITY x "y">]>')
    with pytest.raises(AAError, match="DOCTYPE"):
        parse_deposit(evil, "x.xml")
    with pytest.raises(AAError, match="unexpected namespace"):
        parse_deposit(data.replace(b"FISchema/deposit", b"FISchema/term_deposit"), "x.xml")
    with pytest.raises(AAError, match="not valid JSON"):
        parse_deposit(b"{not json", "x.json")


def _user(client, email):
    r = client.post("/api/auth/register", json={"email": email, "password": "correct-horse-1"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_import_api_creates_document_statement_and_provenance(client):
    alice, bob = _user(client, "aa-owner@example.com"), _user(client, "aa-other@example.com")
    data, opening, txns = sample(seed=21, n=35)
    r = client.post("/api/documents/import-aa", headers=alice, data={"consent_ref": "CONSENT-SYNTH-0001"},
                    files={"file": ("aa-sample.json", data, "application/json")})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["created"] and body["transactions"] == len(txns) and body["status"] == "reconciled_with_flags"
    doc_id = body["document_id"]

    st = client.get(f"/api/documents/{doc_id}/statement", headers=alice).json()
    assert st["source"]["type"] == "aa_deposit" and st["source"]["consent_ref"] == "CONSENT-SYNTH-0001"
    assert st["source"]["schema_version"] == "1.1" and len(st["source"]["payload_sha256"]) == 64
    assert st["summary"]["opening_minor"] == opening.minor
    first = st["transactions"][0]
    assert first["box"] is None and first["external_id"] == "S00000001" and first["value_date"]
    # refresh re-parses the stored payload and keeps the consent reference
    again = client.get(f"/api/documents/{doc_id}/statement?refresh=true", headers=alice).json()
    assert again["source"]["consent_ref"] == "CONSENT-SYNTH-0001" and again["transactions"] == st["transactions"]
    assert client.get(f"/api/documents/{doc_id}", headers=alice).json()["doc_type"] == "bank_statement"
    # same payload again: no duplicate
    dup = client.post("/api/documents/import-aa", headers=alice,
                      files={"file": ("aa-sample.json", data, "application/json")}).json()
    assert dup["created"] is False and dup["document_id"] == doc_id
    # another tenant cannot see it; re-parsing an import as a document is refused
    assert client.get(f"/api/documents/{doc_id}/statement", headers=bob).status_code == 404
    assert client.post(f"/api/documents/{doc_id}/reprocess", headers=alice).status_code == 422


def test_import_api_rejects_invalid_payloads_without_storing(client):
    alice = _user(client, "aa-invalid@example.com")
    before = len(client.get("/api/documents/list", headers=alice).json())
    r = client.post("/api/documents/import-aa", headers=alice,
                    files={"file": ("bad.json", b'{"Account": {"type": "deposit"}}', "application/json")})
    assert r.status_code == 400 and "Not a valid ReBIT deposit payload" in r.json()["detail"]
    r = client.post("/api/documents/import-aa", headers=alice,
                    files={"file": ("bad.csv", b"a,b", "text/csv")})
    assert r.status_code == 400
    assert len(client.get("/api/documents/list", headers=alice).json()) == before

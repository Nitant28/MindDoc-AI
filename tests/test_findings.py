"""R5 leftovers: bank accounts and holders, co-mentions out of relationships, findings and frozen reports."""
import hashlib
import json
import random
import re
from datetime import date

import pytest
from sqlalchemy import text

from app.database.models import IS_POSTGRES, BankAccount, SessionLocal, Statement, StatementTxn, User
from app.database.tenancy import set_tenant


def _user(client, email):
    r = client.post("/api/auth/register", json={"email": email, "password": "correct-horse-1"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _pdf(tmp_path, name, holder, account, seed=77, start=date(2024, 4, 1)):
    pytest.importorskip("reportlab")
    from benchmarks.statements.generator import LAYOUTS, make_history, render
    opening, txns = make_history(random.Random(seed), LAYOUTS["A"]["od"], 40, start)
    meta = {"bank": "Meridian Bank Ltd", "branch": "Andheri", "ifsc": "MERI0123456", "holder": holder,
            "account_masked": account, "account_type": "CURRENT", "period": ["01-04-2024", "30-06-2024"]}
    pdf = tmp_path / name
    render(pdf, meta, opening, txns, LAYOUTS["A"])
    return pdf.read_bytes()


def _upload(client, h, name, data, mime="application/pdf"):
    r = client.post("/api/documents/upload?wait=true", headers=h, files={"file": (name, data, mime)})
    assert r.status_code == 200, r.text
    doc = r.json()["document_id"]
    if mime == "application/pdf":
        assert client.get(f"/api/documents/{doc}/statement", headers=h).json()["is_statement"]
    return doc


def _tenant_session(email):
    db = SessionLocal()
    tid = db.query(User).filter(User.email == email).one().tenant_id
    set_tenant(db, tid)
    return db


# ------------------------------------------------------------------------------------------- accounts

def test_accounts_are_masked_hashed_shared_and_their_holders_link_statements(client, tmp_path):
    email = "accounts-owner@example.com"
    h = _user(client, email)
    a = _upload(client, h, "a.pdf", _pdf(tmp_path, "a.pdf", "Identity Test", "50200014567892"))
    st = client.get(f"/api/documents/{a}/statement", headers=h).json()
    assert st["header"]["account"] == "XXXXXXXXXX7892"          # never the full number
    assert st["header"]["holder"] == "Identity Test" and st["header"]["holder_source"] == "statement_header"
    db = _tenant_session(email)
    try:
        tid = db.info["tenant_id"]  # explicit: SQLite has no row-level security
        stored = [s.account_masked for s in db.query(Statement).filter(Statement.tenant_id == tid)] +                  [b.account_masked for b in db.query(BankAccount).filter(BankAccount.tenant_id == tid)]
        assert stored and all(not re.search(r"\d{5,}", s) for s in stored)
        assert db.query(BankAccount).filter(BankAccount.tenant_id == tid).one().hash_basis == "full"
    finally:
        db.close()

    # a second statement of the same account shares the account; its holder is a counterparty of the first
    client.post("/api/parties/resolve", headers=h)
    cp = next(p for p in client.get("/api/parties", headers=h).json()["parties"]
              if p["kind"] == "org" and p["transactions"] >= 2)
    b = _upload(client, h, "b.pdf", _pdf(tmp_path, "b.pdf", cp["name"], "XXXXXXXX4321", seed=5, start=date(2024, 7, 1)))
    a2 = _upload(client, h, "a2.pdf", _pdf(tmp_path, "a2.pdf", "Identity Test", "50200014567892", seed=9,
                                           start=date(2024, 7, 1)))
    accounts = client.get("/api/accounts", headers=h).json()["accounts"]
    by_masked = {x["account_masked"]: x for x in accounts}
    assert sorted(by_masked["XXXXXXXXXX7892"]["documents"]) == sorted([a, a2])
    assert by_masked["XXXXXXXX4321"]["hash_basis"] == "masked"

    run = client.post("/api/parties/resolve", headers=h).json()
    assert run["holder_parties_created"] == 1  # account 7892's holder came with the first run
    cmap_party = next(p for p in client.get("/api/parties", headers=h).json()["parties"] if cp["party_id"] in p["member_ids"])
    if not cmap_party["accounts"]:  # not joined automatically: a reviewer joins the same-name records
        review = next(r for r in client.get("/api/parties/reviews", headers=h).json()["reviews"]
                      if cp["party_id"] in (r["a"] or {}).get("member_ids", []) + (r["b"] or {}).get("member_ids", []))
        assert client.post(f"/api/parties/reviews/{review['id']}", headers=h,
                           json={"decision": "merge", "reason": "same company holds account 4321"}).status_code == 200
        cmap_party = next(p for p in client.get("/api/parties", headers=h).json()["parties"]
                          if cp["party_id"] in p["member_ids"])
    assert cmap_party["accounts"] and cmap_party["accounts"][0]["masked"] == "XXXXXXXX4321"

    g = client.get("/api/parties/graph", headers=h).json()
    accts = [n for n in g["nodes"] if n["type"] == "account"]
    assert len(accts) == 2 and any(sorted(n["document_ids"]) == sorted([a, a2]) for n in accts)
    holds = [e for e in g["edges"] if e["kind"] == "holds"]
    assert any(e["source"] == f"party:{cmap_party['party_id']}" for e in holds)
    assert all(e["evidence"] for e in holds)
    # money paid by account 7892 to the party can be followed into the account it holds
    assert any(e["kind"] == "flow" and e["target"] == f"party:{cmap_party['party_id']}" for e in g["edges"])

    # an analyst corrects a holder; headers never overwrite it, and the party follows after resolution
    acct_b = by_masked["XXXXXXXX4321"]["id"]
    r = client.put(f"/api/accounts/{acct_b}/holder", headers=h, json={"name": "Corrected Holder Pvt Ltd",
                                                                     "reason": "per account opening form"})
    assert r.status_code == 200 and r.json()["holder_source"] == "analyst"
    client.get(f"/api/documents/{b}/statement?refresh=true", headers=h)
    # re-analysis clears the statement's mentions until the next resolution: the graph must not dangle meanwhile
    g2 = client.get("/api/parties/graph", headers=h).json()
    listed = {n["id"] for n in g2["nodes"]}
    assert all(e["source"] in listed and e["target"] in listed for e in g2["edges"])
    assert client.get("/api/accounts", headers=h).json()["accounts"][-1]["holder"] in ("Corrected Holder Pvt Ltd",
                                                                                       "Identity Test")
    run = client.post("/api/parties/resolve", headers=h).json()
    assert run["holder_mentions_moved"] >= 1
    names = {p["name"] for p in client.get("/api/parties", headers=h).json()["parties"] if p["accounts"]}
    assert "Corrected Holder Pvt Ltd" in names
    other = _user(client, "accounts-other@example.com")
    assert client.put(f"/api/accounts/{acct_b}/holder", headers=other,
                      json={"name": "Intruder", "reason": "should fail"}).status_code == 404


# ----------------------------------------------------------------------------------------- co-mentions

def test_co_mentions_are_a_weak_signal_not_relationships(client):
    email = "comention-owner@example.com"
    h = _user(client, email)
    body = ("Meridian Bank Ltd sanctioned a loan to Shreeji Polymers Pvt Ltd. Anil Mehta is a director of Shreeji "
            "Polymers Pvt Ltd. Meridian Bank Ltd holds a charge over the stock of Shreeji Polymers Pvt Ltd.")
    doc = _upload(client, h, "co.txt", body.encode(), "text/plain")
    g = client.get(f"/api/intel/graph?document_id={doc}", headers=h).json()
    assert g["edges"] and all(e["weak"] and e["relation"] == "mentioned_together" for e in g["edges"])
    db = _tenant_session(email)
    try:
        assert db.execute(text("SELECT count(*) FROM relations WHERE relation = 'co_occurs'")).scalar() == 0
        assert db.execute(text("SELECT count(*) FROM co_mentions WHERE document_id = :d"), {"d": doc}).scalar() > 0
    finally:
        db.close()
    assert client.delete(f"/api/documents/delete/{doc}", headers=h).status_code == 200
    db = _tenant_session(email)
    try:
        assert db.execute(text("SELECT count(*) FROM co_mentions WHERE document_id = :d"), {"d": doc}).scalar() == 0
    finally:
        db.close()


# ------------------------------------------------------------------------------------ findings, reports

def test_findings_are_versioned_explainable_and_frozen_into_reports(client, tmp_path):
    email = "findings-owner@example.com"
    h = _user(client, email)
    doc = _upload(client, h, "f.pdf", _pdf(tmp_path, "f.pdf", "Findings Test", "XXXX9876"))
    client.post("/api/parties/resolve", headers=h)
    claims = client.get("/api/parties/claims", headers=h).json()["claims"]
    picked = [c for c in claims if c["kind"] == "TRANSFERRED_TO"][:2]
    assert len(picked) == 2

    r = client.post("/api/findings", headers=h, json={
        "title": "Payments to two suppliers",
        "statement": "Two payments to suppliers were made in the period; both are shown on the statement.",
        "support": [{"claim_id": c["id"]} for c in picked]})
    assert r.status_code == 200, r.text
    f1 = r.json()
    assert f1["status"] == "draft" and f1["version"] == 1 and not f1["stale"]
    ev = f1["support"][0]["evidence"][0]
    assert ev["document_id"] == doc and ev["page"] and ev["seq"] and ev["box"] and len(ev["source_sha256"]) == 64

    # a report needs approved findings; approval goes draft -> proposed -> approved, one version each
    assert client.post("/api/reports", headers=h, json={"title": "R", "finding_ids": [f1["id"]]}).status_code == 422
    assert client.post(f"/api/findings/{f1['id']}/revise", headers=h, json={"status": "approved"}).status_code == 422
    f2 = client.post(f"/api/findings/{f1['id']}/revise", headers=h, json={"status": "proposed"}).json()
    assert client.post(f"/api/findings/{f1['id']}/revise", headers=h, json={"status": "proposed"}).status_code == 409
    f3 = client.post(f"/api/findings/{f2['id']}/revise", headers=h, json={"status": "approved", "note": "checked"}).json()
    assert f3["version"] == 3 and f3["status"] == "approved"
    rep = client.post("/api/reports", headers=h, json={"title": "Interim report", "finding_ids": [f3["id"]]}).json()
    assert rep["intact"] and len(rep["content_hash"]) == 64 and not rep["new_evidence_since_report"]
    exported = client.get(f"/api/reports/{rep['id']}/export", headers=h)
    assert hashlib.sha256(exported.content).hexdigest() == rep["content_hash"] == exported.headers["x-content-sha256"]
    assert json.loads(exported.content)["findings"][0]["support"][0]["claim"]["id"] == picked[0]["id"]

    # the evidence changes: a corrected row supersedes its claim
    db = _tenant_session(email)
    try:
        st = db.query(Statement).filter(Statement.document_id == doc).one()
        t = db.query(StatementTxn).filter(StatementTxn.statement_id == st.id, StatementTxn.seq ==
                                          f1["support"][0]["evidence"][0]["seq"]).one()
        t.debit_minor += 100
        db.commit()
    finally:
        db.close()
    client.post("/api/parties/resolve", headers=h)
    now = client.get(f"/api/findings/{f3['id']}", headers=h).json()
    assert now["stale"] and now["support"][0]["changed_since"]["current_claim_id"] not in (None, picked[0]["id"])
    rep_now = client.get(f"/api/reports/{rep['id']}", headers=h).json()
    assert rep_now["intact"] and rep_now["new_evidence_since_report"]
    assert rep_now["snapshot"]["findings"][0]["support"][0]["claim"]["amount_minor"] == picked[0]["amount_minor"]

    f4 = client.post(f"/api/findings/{f3['id']}/refresh", headers=h).json()
    assert f4["version"] == 4 and f4["status"] == "draft" and not f4["stale"]
    assert f4["support"][0]["claim"]["amount_minor"] == picked[0]["amount_minor"] + 100
    old = client.get(f"/api/findings/{f1['id']}", headers=h).json()       # the first version still resolves
    assert old["support"][0]["claim"]["id"] == picked[0]["id"] and [v["version"] for v in old["history"]] == [1, 2, 3, 4]
    assert client.post(f"/api/findings/{f3['id']}/refresh", headers=h).status_code == 409   # superseded version

    other = _user(client, "findings-other@example.com")
    assert client.get(f"/api/findings/{f1['id']}", headers=other).status_code == 404
    assert client.get(f"/api/reports/{rep['id']}", headers=other).status_code == 404
    assert client.post("/api/findings", headers=other, json={
        "title": "Not mine", "statement": "Trying to cite another tenant's claim.",
        "support": [{"claim_id": picked[0]["id"]}]}).status_code == 422

    if IS_POSTGRES:  # issued reports and finding versions are protected from the application role
        db = _tenant_session(email)
        try:
            for sql in ("UPDATE reports SET title = 'changed'", "DELETE FROM reports", "DELETE FROM findings",
                        "UPDATE report_findings SET finding_id = finding_id"):
                with pytest.raises(Exception):
                    db.execute(text(sql))
                db.rollback()
                set_tenant(db, db.info["tenant_id"])
        finally:
            db.close()

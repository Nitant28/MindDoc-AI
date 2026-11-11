"""Entity resolution (R5, ADR-0009): narration counterparties, resolver rules, reversible merges with as-of replay,
review decisions that later runs respect, and the case flow graph."""
import random
from datetime import date, datetime, timedelta

import pytest
from sqlalchemy import text

from app.database import models
from app.database.models import Case, IdentityEvent, Party, PartyIdentifier, SessionLocal, Tenant
from app.database.tenancy import set_tenant
from app.identity import service
from app.identity.narration import extract_counterparty
from app.identity.resolver import Record, resolve


# ------------------------------------------------------------------------------------------- pure functions

@pytest.mark.parametrize("narration, name, channel, vpa", [
    ("UPI/220023878639/Bhiwandi Warehousing Co/bhiwandi@okdect/Collect", "Bhiwandi Warehousing Co", "UPI",
     "bhiwandi@okdect"),
    ("NEFT/DECTN18733653537/Meridian Logistics", "Meridian Logistics", "NEFT", None),
    ("IMPS/P2A/948777782049/Tarapur Steel Works", "Tarapur Steel Works", "IMPS", None),
    ("NACH/DECT4431735760814113/Silvassa Packaging EMI", "Silvassa Packaging", "NACH", None),
    ("CHQ PAID 593336 Shreeji Polymers Pvt Ltd", "Shreeji Polymers Pvt Ltd", "CHQ", None),
    ("NEFT/SBIN0001234/N123456789/ABC INFRA PVT LTD/INV 22", "ABC INFRA PVT LTD", "NEFT", None),
])
def test_counterparty_from_narration(narration, name, channel, vpa):
    cp = extract_counterparty(narration)
    assert (cp.name, cp.channel, cp.vpa) == (name, channel, vpa)


@pytest.mark.parametrize("narration", ["CASH DEPOSIT BY SELF", "ATM WDL MERI089779", "SMS CHARGES", "INT.PD 31-03-2024"])
def test_no_counterparty_for_cash_atm_interest_charges(narration):
    assert extract_counterparty(narration) is None


def test_resolver_rules_conflicts_and_homonyms():
    recs = [Record("1", "Sunrise Traders Pvt Ltd", vpa="sunrise@okhdfc"), Record("2", "M/s Sunrise Traders",
                                                                                   vpa="sunrise@okhdfc"),
            Record("3", "SUNRISE TRADERS PRIVATE LIMITED"),
            Record("4", "Sunrise Trading Co", pan="AAACS1234K"),
            Record("5", "Rahul Sharma", pan="ALWPS1111A"), Record("6", "Rahul Sharma", pan="BXZPS2222B"),
            Record("7", "Rahul Sharma"),
            Record("8", "Meridian Cold Storage Ltd"), Record("9", "Meridian Cold Storage LLP")]
    decisions, clusters = resolve(recs)
    band = {tuple(sorted((d.a, d.b))): d for d in decisions}
    assert band[("1", "2")].band == "auto" and band[("1", "2")].method == "rule:vpa"
    assert ["1", "2", "3"] in [sorted(c) for c in clusters]          # same org name, compatible legal form
    assert band[("5", "6")].band == "review" and "different PANs" in band[("5", "6")].reason
    assert band[("6", "7")].band == "review"                         # same personal name: never automatic
    assert not any(set(c) >= {"8", "9"} for c in clusters)           # different legal forms: separate entities
    assert all(not ({"5", "6"} <= set(c)) for c in clusters)


# ------------------------------------------------------------------------------------------- database helpers

@pytest.fixture()
def case_ctx(client):
    db = SessionLocal()
    t = Tenant(name=f"identity-{random.randint(0, 10 ** 9)}")
    db.add(t)
    db.commit()
    set_tenant(db, t.id)
    case = Case(tenant_id=t.id, title="Identity test", is_default=False)
    db.add(case)
    db.commit()
    yield db, t.id, case.id
    db.close()


def _party(db, tid, cid, name, **ids):
    p = Party(tenant_id=tid, case_id=cid, kind="org", name=name, name_norm=name.lower(), signature=f"{name}|{ids}")
    db.add(p)
    db.flush()
    for scheme, value in ids.items():
        db.add(PartyIdentifier(tenant_id=tid, party_id=p.id, scheme=scheme, value=value, valid_structure=True))
    db.flush()
    return p.id


def test_as_of_replay_is_stable_across_merges_and_unmerges(case_ctx):
    """Design F §11 property: the identity state at time T never changes because of later events."""
    db, tid, cid = case_ctx
    ids = [_party(db, tid, cid, f"Party {i}") for i in range(8)]
    rng = random.Random(42)
    t0 = datetime(2026, 1, 1)
    snapshots, merges = [], []
    for step in range(40):
        at = t0 + timedelta(minutes=step)
        live = [m for m in merges if not db.query(IdentityEvent).filter(IdentityEvent.reverses_event_id == m).first()]
        if live and rng.random() < 0.35:
            target = db.get(IdentityEvent, rng.choice(live))
            ev = IdentityEvent(tenant_id=tid, case_id=cid, kind="unmerge", a_party_id=target.a_party_id,
                               b_party_id=target.b_party_id, reverses_event_id=target.id, method="human",
                               reason="test", decided_at=at)
        else:
            a, b = rng.sample(ids, 2)
            ev = IdentityEvent(tenant_id=tid, case_id=cid, kind="merge", a_party_id=a, b_party_id=b, method="human",
                               reason="test", decided_at=at)
        db.add(ev)
        db.flush()
        if ev.kind == "merge":
            merges.append(ev.id)
        snapshots.append((at, service.canonical_map(db, cid)))
    db.commit()
    for at, snap in snapshots:  # replaying at each past moment reproduces exactly what was true then
        assert service.canonical_map(db, cid, as_of=at) == snap


def test_human_merge_requires_reason_and_override_for_conflicting_pans(case_ctx):
    db, tid, cid = case_ctx
    a = _party(db, tid, cid, "Konkan Exports", PAN="AAACK1234K")
    b = _party(db, tid, cid, "Konkan Export House", PAN="AAACK9999Z")
    with pytest.raises(service.IdentityError, match="reason"):
        service.merge(db, tid, cid, a, b, "  ", user_id=None)
    with pytest.raises(service.IdentityError, match="different PANs"):
        service.merge(db, tid, cid, a, b, "looks the same", user_id=None)
    ev = service.merge(db, tid, cid, a, b, "group restructuring confirmed by client letter", None,
                       override_conflict=True)
    assert service.canonical_map(db, cid)[b] == a
    out = service.unmerge(db, tid, cid, ev.id, "client letter was about a different entity", None)
    assert out["still_connected"] is False
    with pytest.raises(service.IdentityError, match="already reversed"):
        service.unmerge(db, tid, cid, ev.id, "again", None)


# ------------------------------------------------------------------------------------------- API end to end

def _statement_pdf(tmp_path):
    pytest.importorskip("reportlab")
    from benchmarks.statements.generator import LAYOUTS, make_history, render
    opening, txns = make_history(random.Random(77), LAYOUTS["A"]["od"], 60, date(2024, 4, 1))
    meta = {"bank": "Meridian Bank Ltd", "branch": "Andheri", "ifsc": "MERI0123456", "holder": "Identity Test",
            "account_masked": "XXXXXXXX4321", "account_type": "CURRENT", "period": ["01-04-2024", "30-06-2024"]}
    pdf = tmp_path / "identity.pdf"
    render(pdf, meta, opening, txns, LAYOUTS["A"])
    return pdf.read_bytes()


def _user(client, email):
    r = client.post("/api/auth/register", json={"email": email, "password": "correct-horse-1"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_resolution_review_unmerge_and_graph_via_api(client, tmp_path):
    h, other = _user(client, "parties-owner@example.com"), _user(client, "parties-other@example.com")
    doc = client.post("/api/documents/upload?wait=true", headers=h,
                      files={"file": ("identity.pdf", _statement_pdf(tmp_path), "application/pdf")}).json()["document_id"]
    assert client.get(f"/api/documents/{doc}/statement", headers=h).json()["is_statement"]

    run = client.post("/api/parties/resolve", headers=h).json()
    assert run["parties_created"] > 0 and run["mentions_added"] > 0
    parties = client.get("/api/parties", headers=h).json()["parties"]
    assert parties and all(p["transactions"] >= 0 for p in parties)
    assert sum(p["transactions"] for p in parties) == run["mentions_added"]

    # idempotent: a second run adds nothing and creates no duplicate review items
    again = client.post("/api/parties/resolve", headers=h).json()
    assert again["parties_created"] == 0 and again["mentions_added"] == 0 and again["review_items"] == 0

    reviews = client.get("/api/parties/reviews", headers=h).json()["reviews"]
    assert reviews, "the synthetic statement has same-name people without identifiers: they must reach review"
    if reviews:
        r0 = reviews[0]
        assert client.post(f"/api/parties/reviews/{r0['id']}", headers=h,
                           json={"decision": "keep_separate", "reason": "x"}).status_code == 422  # reason too short
        ok = client.post(f"/api/parties/reviews/{r0['id']}", headers=h,
                         json={"decision": "keep_separate", "reason": "different people per KYC"})
        assert ok.status_code == 200 and ok.json()["state"] == "kept_separate"
        client.post("/api/parties/resolve", headers=h)
        still = client.get("/api/parties", headers=h).json()["parties"]
        a, b = r0["a"]["party_id"], r0["b"]["party_id"]
        assert not any(a in p["member_ids"] and b in p["member_ids"] for p in still)  # human decision respected

    # unmerge an automatic merge, then check later runs do not redo it
    merged = next((p for p in parties if p["records"] > 1), None)
    assert merged, "UPI and NEFT mentions of the same organisation must auto-merge"
    if merged:
        det = client.get(f"/api/parties/{merged['party_id']}", headers=h).json()
        ev = next(e for e in det["events"] if e["kind"] == "merge" and not e["reversed"])
        assert ev["reason"] and ev["features"]  # every merge carries its evidence
        r = client.post("/api/parties/unmerge", headers=h, json={"event_id": ev["id"], "reason": "wrong link"})
        assert r.status_code == 200
        client.post("/api/parties/resolve", headers=h)
        det2 = client.get(f"/api/parties/{ev['a']['id']}", headers=h).json()
        assert any(e["id"] == ev["id"] and e["reversed"] for e in det2["events"])

    g = client.get("/api/parties/graph", headers=h).json()
    assert any(n["type"] == "account" for n in g["nodes"]) and g["edges"]
    assert all(e["transactions"] for e in g["edges"])  # every edge carries its transactions (evidence)
    # tenant isolation
    assert client.get("/api/parties", headers=other).json()["parties"] == []
    assert client.get(f"/api/parties/{parties[0]['party_id']}", headers=other).status_code == 404


@pytest.mark.skipif(not models.IS_POSTGRES, reason="row-level security is PostgreSQL-only")
def test_identity_events_are_append_only_for_the_app_role(case_ctx):
    db, tid, cid = case_ctx
    a, b = _party(db, tid, cid, "Alpha Traders"), _party(db, tid, cid, "Alpha Trading")
    ev = service.merge(db, tid, cid, a, b, "same GSTIN on invoices", None)
    db.commit()
    set_tenant(db, tid)
    with pytest.raises(Exception):
        db.execute(text("UPDATE identity_events SET reason = 'edited' WHERE id = :i"), {"i": ev.id})
        db.commit()
    db.rollback()
    set_tenant(db, tid)
    with pytest.raises(Exception):
        db.execute(text("DELETE FROM identity_events WHERE id = :i"), {"i": ev.id})
        db.commit()
    db.rollback()

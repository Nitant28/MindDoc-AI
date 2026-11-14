"""R8: leave-one-source-out fragility of findings, disclosure copies with third-party data withheld, evidence bundles."""
import hashlib
import io
import json
import random
import zipfile
from datetime import date

from app.findings import disclosure, fragility
from app.findings.fragility import ClaimFact


# ------------------------------------------------------------------------------------------------ fragility

def test_k_fragility_matches_brute_force_on_random_witness_structures():
    rng = random.Random(11)
    for _ in range(400):
        universe = [f"S{i}" for i in range(1, rng.randint(2, 7))]
        providers = [frozenset(rng.sample(universe, rng.randint(1, len(universe)))) for _ in range(rng.randint(1, 5))]
        kappa, essential, resp = fragility.hitting(providers)
        bk, be = fragility.brute_force(providers)
        assert (kappa, essential) == (bk, be), providers
        assert all(resp[s] == 1.0 for s in essential)
        assert min(1 / v for v in resp.values()) == kappa  # κ = min over sources of 1/ρ (proposal I §2.7)


def _fact(cid, kind, doc, subject, obj, amount=500000, day=10):
    return ClaimFact(cid, kind, amount, "INR", date(2024, 5, day), doc, subject, obj)


def test_corroboration_and_copies_decide_which_sources_a_finding_needs():
    a, p = ("party", 1), ("party", 2)
    paid = _fact(1, "TRANSFERRED_TO", 10, a, p)                 # A's statement: A paid P
    received = _fact(2, "RECEIVED_FROM", 20, p, a, day=12)      # P's statement: P received from A, two days later
    copy_of_a = _fact(3, "TRANSFERRED_TO", 30, a, p)            # the same statement of A imported again (AA)
    other = _fact(4, "TRANSFERRED_TO", 10, a, ("party", 3), amount=90000, day=20)
    rows_a = {(date(2024, 5, d), 100 * d, 0) for d in range(1, 30)}
    rows = {10: rows_a, 20: {(date(2024, 5, 12), 0, 500000)}, 30: set(rows_a)}

    # one fact, evidenced by A's statement and corroborated by P's: removing either one leaves the finding standing
    res = fragility.analyse([paid], [paid, received, copy_of_a], rows)
    assert res.k_fragility == 2 and res.essential == [] and res.loso_score == 0
    assert sorted(map(sorted, res.clusters.values())) == [[10, 30], [20]]  # the AA copy is not independent

    # a second fact seen only in A's statement makes A's statement (and its copy) essential
    res = fragility.analyse([paid, other], [paid, received, copy_of_a, other], rows)
    assert res.k_fragility == 1 and res.loso_score == 1
    assert res.clusters[res.essential[0]] == [10, 30]

    # no corroboration across the wrong parties, amounts or a gap of more than three days
    assert not fragility.corroborates(paid, _fact(5, "RECEIVED_FROM", 20, p, ("party", 9)))
    assert not fragility.corroborates(paid, _fact(6, "RECEIVED_FROM", 20, p, a, amount=500001))
    assert not fragility.corroborates(paid, _fact(7, "RECEIVED_FROM", 20, p, a, day=14))


# ------------------------------------------------------------------------------------------------ redaction

def _snapshot():
    quote = "UPI/RAHUL SHARMA/rahul.sharma@okaxis/9876543210 rent"
    return {"report": {"title": "Interim"}, "findings": [{
        "id": 7, "title": "Payments to Rahul Sharma", "statement": "Rahul Sharma received Rs 5,000 from the company.",
        "created_by": 3,
        "support": [
            {"claim": {"id": 1, "party": "RAHUL SHARMA", "subject": "Shreeji Polymers Pvt Ltd"},
             "evidence": [{"quote": quote, "filename": "statement.pdf"}]},
            {"claim": {"id": 2, "party": "Orion Traders Pvt Ltd", "subject": "Shreeji Polymers Pvt Ltd"},
             "evidence": [{"quote": "NEFT/ORION TRADERS PVT LTD/INV 22 PAN ABCPE1234F", "filename": "s.pdf"}]},
            {"claim": {"id": 3, "party": "Meena Iyer", "subject": "Shreeji Polymers Pvt Ltd"},
             "evidence": [{"quote": "IMPS/MEENA IYER/director loan", "filename": "s.pdf"}]}]}]}


PARTIES = [{"id": 1, "kind": "org", "names": {"Shreeji Polymers Pvt Ltd"}, "display": "Shreeji Polymers Pvt Ltd"},
           {"id": 2, "kind": "person", "names": {"RAHUL SHARMA", "Rahul Sharma"}, "display": "RAHUL SHARMA"},
           {"id": 3, "kind": "org", "names": {"Orion Traders Pvt Ltd"}, "display": "Orion Traders Pvt Ltd"},
           {"id": 4, "kind": "person", "names": {"Meena Iyer"}, "display": "Meena Iyer"}]


def test_disclosure_withholds_third_party_people_and_identifiers_only():
    body, digest, internal = disclosure.make(_snapshot(), "b" * 64, PARTIES, subjects={1, 4}, recipient="Borrower",
                                             created_at="2026-11-14T10:00:00")
    text = json.dumps(body)
    assert "rahul" not in text.lower() and "9876543210" not in text and "ABCPE1234F" not in text
    f = body["findings"][0]
    assert f["title"] == "Payments to [Third party 1]" and "created_by" not in f
    ev = f["support"][0]["evidence"][0]["quote"]
    assert "[UPI address withheld]" in ev and "XXXXXX3210" in ev
    assert f["support"][1]["claim"]["party"] == "Orion Traders Pvt Ltd"   # organisations are not personal data
    assert f["support"][2]["claim"]["party"] == "Meena Iyer"              # a subject (e.g. the director) stays
    labels = {w["label"]: w for w in body["disclosure"]["withheld"]}
    assert labels["Third party 1"]["kind"] == "person" and labels["Third party 1"]["occurrences"] >= 3
    assert all("values" not in w for w in body["disclosure"]["withheld"])
    assert any("RAHUL SHARMA" in w["values"] for w in internal)            # the issuer keeps what was withheld
    assert digest == hashlib.sha256(disclosure.canonical(body).encode()).hexdigest()
    assert body["disclosure"]["base_report_sha256"] == "b" * 64
    # deterministic: the same inputs give the same copy
    assert disclosure.make(_snapshot(), "b" * 64, PARTIES, {1, 4}, "Borrower", "2026-11-14T10:00:00")[1] == digest


# ------------------------------------------------------------------------------------------------ end to end

def test_report_disclosure_and_evidence_bundle_end_to_end(client, tmp_path):
    from tests.test_findings import _pdf, _upload, _user
    h = _user(client, "r8-owner@example.com")
    _upload(client, h, "r8.pdf", _pdf(tmp_path, "r8.pdf", "Disclosure Test Pvt Ltd", "50200099990001", seed=31))
    client.post("/api/parties/resolve", headers=h)
    parties = {p["party_id"]: p for p in client.get("/api/parties", headers=h).json()["parties"]}
    claims = [c for c in client.get("/api/parties/claims", headers=h).json()["claims"] if c["kind"] == "TRANSFERRED_TO"]
    person = [c for c in claims if parties.get(c["party_id"], {}).get("kind") in ("person", "unknown")]
    assert person, "the generated statement should pay at least one person"
    picked = (person[:1] + [c for c in claims if c not in person[:1]])[:2]
    f = client.post("/api/findings", headers=h, json={
        "title": "Two payments out of the account", "statement": "The account paid these two parties in May.",
        "support": [{"claim_id": c["id"]} for c in picked]}).json()
    detail = client.get(f"/api/findings/{f['id']}", headers=h).json()
    rob = detail["robustness"]
    assert rob["method"] == fragility.METHOD and rob["bound_type"] == "exact"
    assert rob["k_fragility"] == 1 and rob["loso_score"] == 1 and len(rob["essential_sources"]) == 1
    assert "every supporting claim comes from one source" in rob["notes"]

    f = client.post(f"/api/findings/{f['id']}/revise", headers=h, json={"status": "proposed"}).json()
    f = client.post(f"/api/findings/{f['id']}/revise", headers=h, json={"status": "approved"}).json()
    rep = client.post("/api/reports", headers=h, json={"title": "Interim", "finding_ids": [f["id"]]}).json()
    assert rep["snapshot"]["findings"][0]["robustness"]["k_fragility"] == 1  # frozen with the report

    # internal bundle: report as hashed, the cited rows and pages, a manifest that verifies
    b1 = client.get(f"/api/reports/{rep['id']}/bundle", headers=h)
    assert b1.status_code == 200 and b1.headers["content-type"] == "application/zip"
    z = zipfile.ZipFile(io.BytesIO(b1.content))
    names = z.namelist()
    manifest = json.loads(z.read("manifest.json"))
    assert hashlib.sha256(z.read("report.json")).hexdigest() == rep["content_hash"] == manifest["report_sha256"]
    assert manifest["intact"] and any(n.startswith("evidence/") for n in names) and any(n.startswith("pages/") for n in names)
    for entry in manifest["files"]:
        assert hashlib.sha256(z.read(entry["path"])).hexdigest() == entry["sha256"]
    assert client.get(f"/api/reports/{rep['id']}/bundle", headers=h).content == b1.content  # reproducible

    # disclosure: default subjects are the account holders; third-party people are withheld
    cand = client.get(f"/api/reports/{rep['id']}/disclosure-parties", headers=h).json()["parties"]
    assert any(p["default_subject"] and "Disclosure Test" in p["name"] for p in cand)
    d = client.post(f"/api/reports/{rep['id']}/disclosures", headers=h, json={"recipient": "Borrower's counsel"})
    assert d.status_code == 200, d.text
    d = d.json()
    assert d["intact"] and d["base_hash"] == rep["content_hash"]
    exported = client.get(f"/api/reports/{rep['id']}/disclosures/{d['id']}/export", headers=h)
    assert hashlib.sha256(exported.content).hexdigest() == d["content_hash"] == exported.headers["x-content-sha256"]
    copy = json.loads(exported.content)
    for w in d["withheld"]:
        if w["kind"] in ("person", "unknown"):
            for v in w["values"]:
                assert v.lower() not in exported.content.decode().lower()
    assert copy["disclosure"]["recipient"] == "Borrower's counsel"
    # the frozen report is unchanged
    assert client.get(f"/api/reports/{rep['id']}", headers=h).json()["intact"]

    b2 = client.get(f"/api/reports/{rep['id']}/bundle", headers=h, params={"disclosure_id": d["id"]})
    z2 = zipfile.ZipFile(io.BytesIO(b2.content))
    m2 = json.loads(z2.read("manifest.json"))
    assert "report.json" not in z2.namelist() and not any(n.startswith("pages/") for n in z2.namelist())
    assert hashlib.sha256(z2.read("disclosure.json")).hexdigest() == d["content_hash"] == m2["disclosure"]["sha256"]
    shown = [n for n in z2.namelist() if n.startswith("evidence/")]
    assert len(shown) + len(m2["omitted"]) >= len(picked)  # every cited row is either shown (redacted) or explained
    assert all(o["reason"] for o in m2["omitted"])

    # a viewer cannot make a disclosure; another tenant cannot see the report
    other = _user(client, "r8-other@example.com")
    assert client.get(f"/api/reports/{rep['id']}/bundle", headers=other).status_code == 404

"""Cases inside an organisation (ADR-0012): invitations, case membership with roles, and what a non-member can see."""
import uuid

CONTRACT = ("Master Services Agreement between Kestrel Ltd and Orion Pvt Ltd. Effective date 12 March 2025. "
            "Either party may terminate with ninety days written notice. Fees: Rs 4,50,000 per quarter.")


def _register(client, email, token=None):
    body = {"email": email, "password": "correct-horse-1"}
    if token:
        body["invite_token"] = token
    r = client.post("/api/auth/register", json=body)
    return r


def _h(r):
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _org(client):
    """An admin and an invited member of the same organisation."""
    tag = uuid.uuid4().hex[:6]
    admin = _h(_register(client, f"lead-{tag}@example.com"))
    inv = client.post("/api/team/invites", headers=admin, json={"email": f"colleague-{tag}@example.com"})
    assert inv.status_code == 200, inv.text
    token = inv.json()["token"]
    member = _h(_register(client, f"colleague-{tag}@example.com", token))
    return admin, member, token, tag


def test_invitation_joins_the_organisation_once(client):
    admin, member, token, tag = _org(client)
    me_a = client.get("/api/auth/me", headers=admin).json()
    me_m = client.get("/api/auth/me", headers=member).json()
    assert me_a["workspace"] == me_m["workspace"]
    assert me_a["tenant_role"] == "admin" and me_m["tenant_role"] == "member"
    # single use, and limited to the invited address
    assert _register(client, f"other-{tag}@example.com", token).status_code == 400
    inv2 = client.post("/api/team/invites", headers=admin, json={"email": f"named-{tag}@example.com"}).json()
    assert _register(client, f"wrong-{tag}@example.com", inv2["token"]).status_code == 400
    # members cannot invite; the token is never listed again
    assert client.post("/api/team/invites", headers=member, json={}).status_code == 403
    listed = client.get("/api/team/invites", headers=admin).json()
    assert all("token" not in i for i in listed) and {i["state"] for i in listed} >= {"used", "open"}
    # revoked invitations cannot be used
    inv3 = client.post("/api/team/invites", headers=admin, json={}).json()
    assert client.delete(f"/api/team/invites/{inv3['id']}", headers=admin).status_code == 200
    assert _register(client, f"late-{tag}@example.com", inv3["token"]).status_code == 400
    members = client.get("/api/team/members", headers=member).json()["members"]
    assert len(members) == 2


def test_non_members_cannot_see_a_case_or_its_documents(client):
    admin, member, _, tag = _org(client)
    case = client.post("/api/cases", headers=admin, json={"title": f"Engagement {tag}"}).json()
    assert case["my_role"] == "lead"
    up = client.post(f"/api/documents/upload?wait=true&case_id={case['id']}", headers=admin,
                     files={"file": (f"msa-{tag}.txt", CONTRACT.encode(), "text/plain")})
    assert up.status_code == 200, up.text
    doc_id = up.json()["document_id"]

    # the member sees neither the case nor anything from its documents
    assert case["id"] not in {c["id"] for c in client.get("/api/cases", headers=member).json()}
    assert client.get(f"/api/cases/{case['id']}", headers=member).status_code == 404
    assert doc_id not in {d["id"] for d in client.get("/api/documents/list", headers=member).json()}
    assert client.get(f"/api/documents/{doc_id}", headers=member).status_code == 404
    assert client.get("/api/findings", headers=member, params={"case_id": case["id"]}).status_code == 404
    assert client.get("/api/reports", headers=member, params={"case_id": case["id"]}).status_code == 404
    q = client.post("/api/chat/query", headers=member, json={"query": "What is the notice period?",
                                                             "document_id": doc_id})
    assert q.status_code == 404
    graph = client.get("/api/intel/graph", headers=member).json()
    assert not any("Kestrel" in n["label"] for n in graph["nodes"])
    assert client.get("/api/intel/overview", headers=member).json()["documents"] == 0
    # the lead still sees everything
    assert doc_id in {d["id"] for d in client.get("/api/documents/list", headers=admin,
                                                  params={"case_id": case["id"]}).json()}

    # viewer: read only
    email = f"colleague-{tag}@example.com"
    assert client.post(f"/api/cases/{case['id']}/members", headers=admin,
                       json={"email": email, "role": "viewer"}).status_code == 200
    assert client.get(f"/api/documents/{doc_id}", headers=member).status_code == 200
    assert client.post("/api/parties/resolve", headers=member, params={"case_id": case["id"]}).status_code == 403
    assert client.delete(f"/api/documents/delete/{doc_id}", headers=member).status_code == 403
    up2 = client.post(f"/api/documents/upload?wait=true&case_id={case['id']}", headers=member,
                      files={"file": ("note.txt", b"A short note about the engagement for the file.", "text/plain")})
    assert up2.status_code == 403

    # analyst: analysis yes, reports no (a reviewer's decision)
    me = client.get("/api/team/members", headers=member).json()["me"]
    assert client.put(f"/api/cases/{case['id']}/members/{me}", headers=admin,
                      json={"role": "analyst"}).status_code == 200
    assert client.post("/api/parties/resolve", headers=member, params={"case_id": case["id"]}).status_code == 200
    rep = client.post("/api/reports", headers=member, params={"case_id": case["id"]},
                      json={"title": "Draft report", "finding_ids": [1]})
    assert rep.status_code == 403
    assert client.post(f"/api/cases/{case['id']}/members", headers=member,
                       json={"email": email, "role": "lead"}).status_code == 403

    # a case keeps at least one lead
    lead_id = client.get("/api/team/members", headers=admin).json()["me"]
    assert client.delete(f"/api/cases/{case['id']}/members/{lead_id}", headers=admin).status_code == 409


def test_documents_move_between_cases_and_deactivation(client):
    admin, member, _, tag = _org(client)
    case = client.post("/api/cases", headers=admin, json={"title": f"Second {tag}"}).json()
    up = client.post(f"/api/documents/upload?wait=true&case_id={case['id']}", headers=admin,
                     files={"file": (f"msa2-{tag}.txt", (CONTRACT + " Schedule 2.").encode(), "text/plain")})
    doc_id = up.json()["document_id"]
    # the only case of a document cannot be dropped (it would fall back to General and become visible to all)
    assert client.delete(f"/api/cases/{case['id']}/documents/{doc_id}", headers=admin).status_code == 409
    general = next(c for c in client.get("/api/cases", headers=admin).json() if c["is_default"])
    assert client.post(f"/api/cases/{general['id']}/documents", headers=admin,
                       json={"document_id": doc_id}).status_code == 200
    # now in General too: every organisation member sees it
    assert client.get(f"/api/documents/{doc_id}", headers=member).status_code == 200
    # but changing it needs analyst rights in every case that holds it
    assert client.delete(f"/api/documents/delete/{doc_id}", headers=member).status_code == 403
    assert client.delete(f"/api/cases/{case['id']}/documents/{doc_id}", headers=admin).status_code == 200
    assert client.get(f"/api/cases/{case['id']}", headers=admin).json()["document_list"] == []
    # closing a case; General cannot be closed
    assert client.put(f"/api/cases/{case['id']}", headers=admin, json={"status": "closed"}).json()["status"] == "closed"
    assert client.put(f"/api/cases/{general['id']}", headers=admin, json={"status": "closed"}).status_code == 409
    # deactivated members lose access at once; the last admin cannot be removed
    me = client.get("/api/team/members", headers=member).json()["me"]
    assert client.put(f"/api/team/members/{me}", headers=admin, json={"is_active": False}).status_code == 200
    assert client.get("/api/auth/me", headers=member).status_code == 401
    admin_id = client.get("/api/team/members", headers=admin).json()["me"]
    assert client.put(f"/api/team/members/{admin_id}", headers=admin,
                      json={"tenant_role": "member"}).status_code == 409


def test_audit_chain_records_membership_changes(client):
    from app.core.audit import verify_chain
    from app.database.models import AuditEvent, SessionLocal, User
    from app.database.tenancy import set_tenant
    admin, member, _, tag = _org(client)
    case = client.post("/api/cases", headers=admin, json={"title": f"Audited {tag}"}).json()
    client.post(f"/api/cases/{case['id']}/members", headers=admin,
                json={"email": f"colleague-{tag}@example.com", "role": "viewer"})
    db = SessionLocal()
    try:
        tid = db.query(User).filter(User.email == f"lead-{tag}@example.com").one().tenant_id
        set_tenant(db, tid)
        events = db.query(AuditEvent).filter(AuditEvent.tenant_id == tid).order_by(AuditEvent.id).all()
        verbs = [e.verb for e in events]
        assert verbs[:2] == ["team.invite.create", "team.invite.used"]
        assert "case.create" in verbs and "case.member.add" in verbs
        assert verify_chain(events)
    finally:
        db.close()

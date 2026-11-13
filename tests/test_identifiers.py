"""Identifier structure checks (PAN, GSTIN, IFSC) per official sources cited in app/finance/identifiers.py.

Values are the Income Tax Department's own published example PAN (ALWPG5809L) and synthetic codes built from the
documented layouts; no real taxpayer data. Check digits / checksums are never claimed as verified.
"""
from app.finance.identifiers import check_gstin, check_ifsc, check_pan, find_identifiers


def test_pan_official_example_and_holder_status():
    c = check_pan("alwpg 5809l")
    assert c.valid_structure and c.value == "ALWPG5809L" and c.details["holder_status"] == "Individual"
    assert any("check digit" in n for n in c.not_verified)  # never claimed as verified


def test_pan_structural_failures_are_named():
    assert "character 4 'X' is not a listed holder status" in check_pan("ALWXG5809L").issues[0]
    assert any("0001 to 9999" in i for i in check_pan("ALWPG0000L").issues)
    assert check_pan("ALWPG5809").issues == ["must be 10 characters (got 9)"]
    assert any("character 10" in i for i in check_pan("ALWPG58091").issues)


def test_ifsc_layout():
    assert check_ifsc("MERI0123456").valid_structure
    assert check_ifsc("MERI1123456").issues == ["character 5 must be 0 (zero)"]
    assert "characters 1-4 (bank) must be letters" in check_ifsc("ME1I0123456").issues
    assert check_ifsc("MERI012345").issues == ["must be 11 characters (got 10)"]


def test_gstin_layout_state_code_and_embedded_pan():
    c = check_gstin("27ALWPG5809L1Z5")
    assert c.valid_structure and c.details["state"] == "Maharashtra" and c.details["pan"] == "ALWPG5809L"
    assert any("checksum" in n for n in c.not_verified)
    assert check_gstin("28ALWPG5809L1Z5").issues == ["state code '28' is not in the GST state code list"]
    assert check_gstin("27ALWPG5809L1Z").issues == ["must be 15 characters (got 14)"]
    # characters 3-12 may be a TAN, whose layout is not in the consulted sources: not an error, but not verified
    t = check_gstin("27MUMA12345B1D7")
    assert t.valid_structure and any("TAN" in n for n in t.not_verified)


def test_find_identifiers_reports_embedded_pan_once():
    text = ("Supplier GSTIN 27ALWPG5809L1Z5, proprietor PAN ALWPG5809L. Bank IFSC MERI0123456. "
            "Another PAN ALWXG5809L is malformed.")
    found = find_identifiers(text)
    kinds = [(f["kind"], f["value"], f["valid_structure"]) for f in found]
    assert kinds == [("GSTIN", "27ALWPG5809L1Z5", True), ("PAN", "ALWPG5809L", True),
                     ("IFSC", "MERI0123456", True), ("PAN", "ALWXG5809L", False)]


def test_document_identifiers_endpoint(client):
    r = client.post("/api/auth/register", json={"email": "ids@example.com", "password": "correct-horse-1"})
    h = {"Authorization": f"Bearer {r.json()['access_token']}"}
    body = ("Tax invoice. Supplier GSTIN 27ALWPG5809L1Z5. Payment to IFSC MERI0123456. "
            "Reference PAN ALWXG5809L appears on the covering letter.").encode()
    doc = client.post("/api/documents/upload?wait=true", headers=h,
                      files={"file": ("ids.txt", body, "text/plain")}).json()["document_id"]
    out = client.get(f"/api/documents/{doc}/identifiers", headers=h).json()
    assert [(i["kind"], i["valid_structure"]) for i in out["identifiers"]] == \
        [("GSTIN", True), ("IFSC", True), ("PAN", False)]
    assert "not proof" in out["note"]

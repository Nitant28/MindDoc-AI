"""Bank-statement engine (ADR-0011) and reconciliation (design E §S5).

Uses the StatementBench generator for dev layout families only (A–D); held-out families E–F are never touched by
tests or development.
"""
import copy
import random
from datetime import date

import pytest

from app.finance.reconcile import TxnRow, reconcile

reportlab = pytest.importorskip("reportlab", reason="StatementBench generator needs reportlab (requirements-dev.txt)")


@pytest.mark.parametrize("family", ["A", "B", "C", "D"])
def test_engine_reproduces_gold_rows_and_reconciles(tmp_path, family):
    from app.finance.statements import extract_statement
    from benchmarks.statements.generator import LAYOUTS, make_history, render

    rng = random.Random(1000 + ord(family))
    opening, txns = make_history(rng, LAYOUTS[family]["od"], 45, date(2024, 4, 1))
    meta = {"bank": "Meridian Bank Ltd", "branch": "Andheri", "ifsc": "MERI0123456", "holder": "Test Holder",
            "account_masked": "XXXXXXXX1234", "account_type": "CURRENT", "period": ["01-04-2024", "30-06-2024"]}
    pdf = tmp_path / f"{family}.pdf"
    render(pdf, meta, opening, txns, LAYOUTS[family])
    res = extract_statement(pdf.read_bytes())
    got = [(r.date, r.debit, r.credit, r.balance) for r in res.rows]
    want = [(t.date.isoformat(), t.debit.minor, t.credit.minor, t.balance.minor) for t in txns]
    assert got == want
    assert res.status == "reconciled", [c for c in res.checks if c.status == "fail"][:3]
    assert res.opening == opening.minor and res.header["ifsc"] == "MERI0123456"
    assert all(res.row_boxes[r.seq][0] == r.page for r in res.rows)  # every row knows its page and box


def _rows(spec):
    """spec: list of (debit, credit, balance) in paise."""
    return [TxnRow(seq=i + 1, date="2024-04-0%d" % (1 + i // 3), debit=d, credit=c, balance=b, narration=n)
            for i, (d, c, b, n) in enumerate(spec)]


def test_clean_statement_reconciles():
    rows = _rows([(0, 50000, 150000, "NEFT"), (20000, 0, 130000, "UPI"), (0, 1000, 131000, "INT")])
    status, checks, opening = reconcile(rows, 100000, 131000)
    assert status == "reconciled" and opening == 100000
    assert all(c.status == "pass" for c in checks if c.scope in ("row", "statement"))


def test_failure_is_diagnosed_and_values_are_never_modified():
    # row 2's amount was misread: printed 2,000.00 but balances imply 20,000.00 (one dropped digit)
    rows = _rows([(0, 50000, 150000, "NEFT"), (200000, 0, 130000, "UPI"), (0, 1000, 131000, "INT")])
    before = copy.deepcopy(rows)
    status, checks, _ = reconcile(rows, 100000, 131000)
    assert status == "needs_review"
    fail = next(c for c in checks if c.status == "fail")
    assert fail.seq == 2 and fail.expected == -50000 and fail.observed == 130000 and fail.diff == 180000
    assert any(h["code"] == "amount_ocr_suspect" and h["implied"] == 20000 for h in fail.hypotheses)
    assert [(r.debit, r.credit, r.balance) for r in rows] == [(r.debit, r.credit, r.balance) for r in before]


def test_direction_swap_is_diagnosed():
    rows = _rows([(0, 50000, 150000, "NEFT"), (0, 20000, 130000, "UPI")])  # printed as credit, balance fell
    status, checks, _ = reconcile(rows, 100000, None)
    fail = next(c for c in checks if c.status == "fail")
    assert status == "needs_review" and any(h["code"] == "direction_suspect" for h in fail.hypotheses)


def test_missing_row_is_diagnosed():
    # a 5,000.00 debit between rows 1 and 2 is missing; later rows are internally consistent
    rows = _rows([(0, 50000, 150000, "A"), (10000, 0, 135000, "B"), (0, 2000, 137000, "C"), (1000, 0, 136000, "D")])
    status, checks, _ = reconcile(rows, 100000, None)
    fail = next(c for c in checks if c.status == "fail")
    assert fail.seq == 2 and any(h["code"] == "missing_row_suspect" and h["net"] == -5000 for h in fail.hypotheses)


def test_reversal_pair_detected_and_unknown_direction_inferred():
    rows = _rows([(30000, 0, 70000, "UPI/123/Sunrise"), (0, 30000, 100000, "REV:UPI/123/Sunrise")])
    status, checks, _ = reconcile(rows, 100000, 100000)
    assert status == "reconciled"
    assert any(c.reason == "reversal_pair" for c in checks)
    r = TxnRow(seq=1, date="2024-04-01", debit=25000, credit=0, balance=125000, direction_source="unknown")
    status, _, _ = reconcile([r], 100000, None)
    assert r.credit == 25000 and r.debit == 0 and r.direction_source == "inferred_from_balance"
    assert status == "reconciled_with_flags"


def test_no_balances_is_not_checkable():
    rows = [TxnRow(seq=1, date="2024-04-01", debit=100, credit=0, balance=None)]
    status, checks, _ = reconcile(rows, None, None)
    assert status == "not_checkable" and checks[0].reason == "unreconcilable_no_balance"


def _statement_pdf(tmp_path, family="A", seed=77, n=30):
    from benchmarks.statements.generator import LAYOUTS, make_history, render
    rng = random.Random(seed)
    opening, txns = make_history(rng, LAYOUTS[family]["od"], n, date(2024, 4, 1))
    meta = {"bank": "Meridian Bank Ltd", "branch": "Andheri", "ifsc": "MERI0123456", "holder": "Test Holder",
            "account_masked": "XXXXXXXX1234", "account_type": "CURRENT", "period": ["01-04-2024", "30-06-2024"]}
    pdf = tmp_path / f"api-{family}-{seed}.pdf"
    render(pdf, meta, opening, txns, LAYOUTS[family])
    return pdf.read_bytes(), opening, txns


def test_statement_endpoint_and_row_highlight(client, alice, bob, tmp_path):
    data, opening, txns = _statement_pdf(tmp_path)
    r = client.post("/api/documents/upload?wait=true", headers=alice,
                    files={"file": ("statement-api.pdf", data, "application/pdf")})
    assert r.status_code == 200, r.text
    doc_id = r.json()["document_id"]

    r = client.get(f"/api/documents/{doc_id}/statement", headers=alice)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["is_statement"] and body["status"] == "reconciled"
    assert body["summary"]["opening_minor"] == opening.minor and body["summary"]["transactions"] == len(txns)
    assert body["summary"]["failed_checks"] == 0
    got = [(t["date"], t["debit_minor"], t["credit_minor"], t["balance_minor"]) for t in body["transactions"]]
    assert got == [(t.date.isoformat(), t.debit.minor, t.credit.minor, t.balance.minor) for t in txns]
    first = body["transactions"][0]
    assert first["box"] and len(first["box"]) == 4 and all(isinstance(v, int) for v in first["box"])

    box = ",".join(map(str, first["box"]))
    r = client.get(f"/api/documents/{doc_id}/page/{first['page']}/image", params={"box": box}, headers=alice)
    assert r.status_code == 200 and r.headers["content-type"] == "image/png" and r.content[:4] == b"\x89PNG"
    assert r.headers["x-highlight-boxes"] == "1"
    assert client.get(f"/api/documents/{doc_id}/page/1/image", params={"box": "1,2,x"},
                      headers=alice).status_code == 422
    assert client.get(f"/api/documents/{doc_id}/page/99/image", params={"box": box},
                      headers=alice).status_code == 404
    # tenant isolation: another tenant cannot read the statement or its page
    assert client.get(f"/api/documents/{doc_id}/statement", headers=bob).status_code == 404
    assert client.get(f"/api/documents/{doc_id}/page/1/image", params={"box": box}, headers=bob).status_code == 404


def test_statement_endpoint_on_non_statement_pdf(client, alice):
    from reportlab.pdfgen import canvas
    import io
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.drawString(72, 720, "Master services agreement between Acme Ltd and Beta LLP, effective 1 April 2024.")
    c.drawString(72, 700, "This agreement has no transaction table or running balance of any kind.")
    c.save()
    r = client.post("/api/documents/upload?wait=true", headers=alice,
                    files={"file": ("not-a-statement.pdf", buf.getvalue(), "application/pdf")})
    assert r.status_code == 200, r.text
    r = client.get(f"/api/documents/{r.json()['document_id']}/statement", headers=alice)
    assert r.status_code == 200 and r.json()["is_statement"] is False


def test_same_date_reorder_found_in_a_large_block():
    # six rows on one date; rows 3 and 4 were read in the wrong order (each keeps its printed balance)
    deltas = [5000, -2000, 700, -300, 1200, -900]
    bal, spec = 100000, []
    for dlt in deltas:
        bal += dlt
        spec.append((max(-dlt, 0), max(dlt, 0), bal))
    spec[2], spec[3] = spec[3], spec[2]
    rows = [TxnRow(seq=i + 1, date="2024-04-05", debit=d, credit=c, balance=b) for i, (d, c, b) in enumerate(spec)]
    status, checks, _ = reconcile(rows, 100000, bal)
    fail = next(c for c in checks if c.status == "fail")
    assert status == "needs_review" and fail.seq == 3
    assert fail.hypotheses[0]["code"] == "order_ambiguous" and fail.hypotheses[0]["order"] == [1, 2, 4, 3, 5, 6]


def test_ranking_follows_source_but_never_changes_the_result():
    # row 2: printed 2,000.00 but balances imply 20,000.00 — a misread digit *or* a missing 18,000.00 row
    spec = [(0, 50000, 150000, "NEFT"), (200000, 0, 130000, "UPI"), (0, 1000, 131000, "INT")]
    text = reconcile(_rows(spec), 100000, 131000, source="text")
    ocr = reconcile(_rows(spec), 100000, 131000, source="ocr")
    assert text[0] == ocr[0] == "needs_review"
    t = next(c for c in text[1] if c.status == "fail")
    o = next(c for c in ocr[1] if c.status == "fail")
    assert {h["code"] for h in t.hypotheses} == {h["code"] for h in o.hypotheses} == {"amount_ocr_suspect",
                                                                                    "missing_row_suspect"}
    assert t.hypotheses[0]["code"] == "missing_row_suspect" and o.hypotheses[0]["code"] == "amount_ocr_suspect"


def test_misread_balance_ranked_first_when_next_row_corroborates():
    # row 2's balance printed 1,38,000.00 but the arithmetic (and row 3) say 1,30,000.00
    rows = _rows([(0, 50000, 150000, "A"), (20000, 0, 138000, "B"), (0, 1000, 131000, "C")])
    _, checks, _ = reconcile(rows, 100000, 131000)
    first = next(c for c in checks if c.status == "fail")
    assert first.seq == 2 and first.hypotheses[0]["code"] == "balance_ocr_suspect"
    assert first.hypotheses[0]["implied"] == 130000


def test_fault_benchmark_smoke():
    from benchmarks.statements.faults import evaluate
    res = evaluate("dev", 8)
    assert res["clean"]["false_alarm_rate"]["k"] == 0
    for m in res["faults"].values():
        assert m["detected"]["k"] == m["injected"]


def test_knock_on_failures_point_to_the_root_cause():
    # misread balance on row 2 also breaks row 3; row 3 must point back to row 2
    rows = _rows([(0, 50000, 150000, "A"), (20000, 0, 138000, "B"), (0, 1000, 131000, "C"), (500, 0, 130500, "D")])
    _, checks, _ = reconcile(rows, 100000, 130500)
    fails = [c for c in checks if c.status == "fail"]
    assert [c.seq for c in fails] == [2, 3]
    assert fails[1].hypotheses[0]["code"] == "follows_previous_error" and fails[1].hypotheses[0]["row"] == 2
    # same-date swap: the second swapped row and the row after the block both point back to the first failure
    deltas = [5000, -2000, 700, -300, 1200]
    bal, spec = 100000, []
    for dlt in deltas:
        bal += dlt
        spec.append((max(-dlt, 0), max(dlt, 0), bal))
    spec[1], spec[2] = spec[2], spec[1]
    rows = [TxnRow(seq=i + 1, date="2024-04-05" if i in (1, 2) else f"2024-04-0{i + 1}", debit=d, credit=c,
                   balance=b) for i, (d, c, b) in enumerate(spec)]
    _, checks, _ = reconcile(rows, 100000, bal)
    fails = [c for c in checks if c.status == "fail"]
    assert fails[0].seq == 2 and fails[0].hypotheses[0]["code"] == "order_ambiguous"
    assert all(c.hypotheses[0]["code"] == "follows_previous_error" and c.hypotheses[0]["row"] == 2 for c in fails[1:])

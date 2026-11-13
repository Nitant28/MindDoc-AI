"""Scanned statements (R4): OCR word boxes feed the same engine; recognition errors must never pass silently.

Uses dev layout families only (A-D). Tesseract-dependent tests skip when the binary is absent.
"""
import random
from datetime import date

import pytest

from app.finance.statements import Word, _merge_number_fragments, _ocr_clean, extract_statement
from app.vision import ocr_words

reportlab = pytest.importorskip("reportlab", reason="StatementBench generator needs reportlab (requirements-dev.txt)")
needs_tesseract = pytest.mark.skipif(not ocr_words.available(), reason="Tesseract OCR not installed")


def test_token_repair_only_when_result_is_a_valid_amount_or_date():
    assert _ocr_clean("1,23,4S6.78") == "1,23,456.78"
    assert _ocr_clean("§,87,325.72") == "5,87,325.72"
    assert _ocr_clean("2,000.OO(Cr)") == "2,000.00(Cr)"
    assert _ocr_clean("O1/04/2024") == "01/04/2024"
    for untouched in ("01-Oct-2024", "NEFT", "SBIN0001234", "Balance", "12,345.00Dr"):
        assert _ocr_clean(untouched) == untouched


def test_split_amount_fragments_are_joined_only_into_valid_amounts():
    def w(t, x0, x1):
        return Word(t, x0, x1, 0, 80, 1, ocr=True)
    assert [x.text for x in _merge_number_fragments([w("7,31", 0, 100), w(",830.60", 130, 260)])] == ["7,31,830.60"]
    assert [x.text for x in _merge_number_fragments([w("94,44", 0, 100), w("488.80", 140, 260)])] == ["94,44,488.80"]
    # far apart, or two complete amounts: never joined
    assert len(_merge_number_fragments([w("7,31", 0, 100), w(",830.60", 400, 520)])) == 2
    assert len(_merge_number_fragments([w("5,000.00", 0, 100), w("6,051,599.92", 130, 260)])) == 2


@needs_tesseract
def test_deskew_estimate_recovers_a_small_rotation():
    from PIL import Image, ImageDraw
    img = Image.new("L", (1600, 2000), 255)
    d = ImageDraw.Draw(img)
    for y in range(150, 1850, 40):  # rows of "text"
        for x in range(120, 1480, 90):
            d.rectangle([x, y, x + 60, y + 14], fill=0)
    tilted = img.rotate(-0.8, resample=Image.BICUBIC, fillcolor=255)
    assert abs(ocr_words.estimate_rotation(tilted) - 0.8) <= 0.1


@needs_tesseract
@pytest.mark.parametrize("family", ["A", "C"])
def test_scanned_statement_is_read_and_errors_are_never_silent(tmp_path, family):
    from benchmarks.statements.generator import LAYOUTS, make_history, render
    from benchmarks.statements.scan import degrade_pdf
    rng = random.Random(4100 + ord(family))
    opening, txns = make_history(rng, LAYOUTS[family]["od"], 18, date(2024, 4, 1))
    meta = {"bank": "Meridian Bank Ltd", "branch": "Andheri", "ifsc": "MERI0123456", "holder": "Scan Test",
            "account_masked": "XXXXXXXX1234", "account_type": "CURRENT", "period": ["01-04-2024", "30-06-2024"]}
    clean, scanned = tmp_path / "clean.pdf", tmp_path / "scan.pdf"
    render(clean, meta, opening, txns, LAYOUTS[family])
    degrade_pdf(clean, scanned, "mild", seed=7)

    res = extract_statement(scanned.read_bytes())
    assert res.ocr_pages and any("OCR" in w for w in res.warnings)
    want = [(t.date.isoformat(), t.debit.minor, t.credit.minor, t.balance.minor) for t in txns]
    got = [(r.date, r.debit, r.credit, r.balance) for r in res.rows]
    assert len(got) == len(want)
    exact = sum(g == w for g, w in zip(got, want))
    assert exact >= 0.9 * len(want)
    if got != want:  # any recognition error must surface for review, never as a clean reconciliation
        assert res.status != "reconciled"
    # row boxes are mapped back onto the page and stay inside it (A4: 5954 x 8420 tenths of a point)
    for page, x0, top, x1, bottom in res.row_boxes.values():
        assert 0 <= x0 < x1 <= 5960 and 0 <= top < bottom <= 8430


def test_text_layer_pdfs_do_not_use_ocr(tmp_path):
    from benchmarks.statements.generator import LAYOUTS, make_history, render
    opening, txns = make_history(random.Random(5), LAYOUTS["B"]["od"], 10, date(2024, 4, 1))
    meta = {"bank": "Meridian Bank Ltd", "branch": "Andheri", "ifsc": "MERI0123456", "holder": "Text Test",
            "account_masked": "XXXXXXXX1234", "account_type": "CURRENT", "period": ["01-04-2024", "30-06-2024"]}
    pdf = tmp_path / "t.pdf"
    render(pdf, meta, opening, txns, LAYOUTS["B"])
    res = extract_statement(pdf.read_bytes())
    assert res.ocr_pages == [] and res.status == "reconciled"

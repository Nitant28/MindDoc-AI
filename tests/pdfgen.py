"""Tiny text-PDF builder for tests (reportlab, BSD; dev only). Replaces the PyMuPDF-based helpers (ADR-0006)."""
import io

import pytest


def make_pdf(pages: list[list[str]], fontsize: int = 10) -> bytes:
    canvas = pytest.importorskip("reportlab.pdfgen.canvas", reason="reportlab is in requirements-dev.txt")
    from reportlab.lib.pagesizes import A4

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    _, height = A4
    for lines in pages:
        c.setFont("Helvetica", fontsize)
        y = height - 72
        for line in lines:
            c.drawString(72, y, line)
            y -= fontsize + 4
        c.showPage()
    c.save()
    return buf.getvalue()

"""Evidence bundle for a frozen report ("material relied upon", R8): one zip a reader can check offline.

Contents:
* `report.json` — the frozen snapshot exactly as hashed (or `disclosure.json`, the redacted copy, for a disclosure);
* `evidence/…png` — the page region of every evidence row cited by the findings;
* `pages/…png` — whole cited pages with the row boxed (internal bundles only; a whole page shows other people's
  transactions, so disclosure bundles never include it);
* `sources.json` — each source document with its SHA-256 and the pages cited;
* `manifest.json` — SHA-256 and size of every file, and the hashes of the report (and disclosure) it belongs to;
* `README.txt` — how to verify it.

Disclosure bundles black out, on each region image, every withheld name and identifier found in the page's text
layer. When the text layer cannot confirm that (a scanned page, or a withheld value the page search does not find),
the image is left out and the manifest says why: an unredacted image is never included.
"""
from __future__ import annotations

import hashlib
import io
import json
import re
import zipfile
from pathlib import Path

from PIL import Image, ImageDraw

GENERATOR = "minddoc evidence-bundle v1"
ZOOM = 2.0
MARGIN_PT = 3.0


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _png(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def _withheld_in(quote: str, values: list[str]) -> list[str]:
    """Exact substrings of `quote` that a withheld value matches (names tolerate punctuation between words)."""
    found = []
    for v in values:
        tokens = [re.escape(t) for t in re.split(r"[\W_]+", v) if t]
        if not tokens:
            continue
        pat = re.compile(r"(?<![A-Za-z0-9])" + r"[\W_]+".join(tokens) + r"(?![A-Za-z0-9])", re.IGNORECASE)
        found += [m.group(0) for m in pat.finditer(quote or "")]
    return found


def _render(path: str, page_no: int, box_pt: tuple, search: list[str], whole_page: bool):
    """(region image, whole page image or None, search strings not found inside the region)."""
    import pypdfium2 as pdfium

    from app.vision.highlight import find_text_boxes
    pdf = pdfium.PdfDocument(path)
    try:
        page = pdf[page_no - 1]
        try:
            img = page.render(scale=ZOOM).to_pil().convert("RGB")
            x0, top, x1, bottom = box_pt
            missing, rects = [], []
            for s in search:
                hits = find_text_boxes(page, [s])
                inside = [r for r in hits if r[0] < x1 + MARGIN_PT and r[2] > x0 - MARGIN_PT
                          and r[1] < bottom + MARGIN_PT and r[3] > top - MARGIN_PT]
                if not inside:  # must be found inside this row, or the image cannot be shown safely
                    missing.append(s)
                rects += hits
        finally:
            page.close()
    finally:
        pdf.close()
    full = None
    if whole_page:
        full = img.copy()
        ImageDraw.Draw(full).rectangle([x0 * ZOOM - 3, top * ZOOM - 3, x1 * ZOOM + 3, bottom * ZOOM + 3],
                                       outline=(217, 119, 6), width=3)
    if rects:
        draw = ImageDraw.Draw(img)
        for rx0, rtop, rx1, rbottom in rects:
            draw.rectangle([rx0 * ZOOM - 1, rtop * ZOOM - 1, rx1 * ZOOM + 1, rbottom * ZOOM + 1], fill=(0, 0, 0))
    # exactly the row's height: a margin would show slivers of the neighbouring rows (other people's transactions)
    crop = img.crop((max(0, int((x0 - MARGIN_PT) * ZOOM)), max(0, int(top * ZOOM)),
                     min(img.width, int((x1 + MARGIN_PT) * ZOOM)), min(img.height, int(bottom * ZOOM + 1))))
    return crop, full, missing


def build(db, report, disclosure=None) -> tuple[bytes, str]:
    """The zip bytes and a file name. `disclosure`: a ReportDisclosure row, or None for the internal bundle."""
    from app.database.models import Document, Statement
    original = json.loads(report.snapshot)
    shown_text = disclosure.content if disclosure is not None else report.snapshot
    shown = json.loads(shown_text)
    withheld_values: list[str] = []
    if disclosure is not None:
        for w in json.loads(disclosure.withheld_internal or "[]"):
            withheld_values += w.get("values", [])

    files: dict[str, bytes] = {("disclosure.json" if disclosure is not None else "report.json"):
                               shown_text.encode("utf-8")}
    omitted: list[dict] = []
    sources: dict[int, dict] = {}
    pages_done: set = set()
    for fi, (f_orig, f_shown) in enumerate(zip(original.get("findings", []), shown.get("findings", []))):
        for si, (s_orig, s_shown) in enumerate(zip(f_orig.get("support", []), f_shown.get("support", []))):
            for ei, (e_orig, e_shown) in enumerate(zip(s_orig.get("evidence", []), s_shown.get("evidence", []))):
                doc_id = e_orig.get("document_id")
                where = {"finding_id": f_orig.get("id"), "claim_id": s_orig.get("claim", {}).get("id"),
                         "page": e_orig.get("page"), "row": e_orig.get("seq")}
                if doc_id is None:
                    continue
                src = sources.setdefault(doc_id, {"document_id": doc_id, "filename": e_shown.get("filename"),
                                                  "sha256": e_orig.get("source_sha256"), "pages": set()})
                if e_orig.get("page"):
                    src["pages"].add(e_orig["page"])
                doc = db.get(Document, doc_id)
                path = Path(doc.source_path) if doc is not None and doc.source_path else None
                if path is None or not path.is_file() or path.suffix.lower() != ".pdf" or not e_orig.get("box") \
                        or not e_orig.get("page"):
                    omitted.append({**where, "reason": "no page image for this evidence (not a stored PDF page)"})
                    continue
                if doc.content_hash and e_orig.get("source_sha256") and doc.content_hash != e_orig["source_sha256"]:
                    omitted.append({**where, "reason": "the stored file no longer matches the SHA-256 in the report"})
                    continue
                st = db.query(Statement).filter(Statement.document_id == doc_id).first()
                search = _withheld_in(e_orig.get("quote") or "", withheld_values) if disclosure is not None else []
                if disclosure is not None and search and st is not None and st.source == "pdf_ocr":
                    omitted.append({**where, "reason": "scanned page: withheld text cannot be located for blacking "
                                                       "out, so the image is not included"})
                    continue
                box = tuple(v / 10 for v in e_orig["box"])
                key = (doc_id, e_orig["page"])
                crop, full, missing = _render(str(path), e_orig["page"], box, search,
                                              whole_page=disclosure is None and key not in pages_done)
                if missing:
                    omitted.append({**where, "reason": f"{len(missing)} withheld value(s) not found in the page's "
                                                       "text layer, so the image is not included"})
                    continue
                files[f"evidence/F{f_orig.get('id')}-C{where['claim_id']}-{fi + 1}.{si + 1}.{ei + 1}.png"] = _png(crop)
                if full is not None:
                    pages_done.add(key)
                    files[f"pages/D{doc_id}-p{e_orig['page']}.png"] = _png(full)
    files["sources.json"] = json.dumps(
        [{**v, "pages": sorted(v["pages"])} for _, v in sorted(sources.items())], indent=2,
        ensure_ascii=False).encode("utf-8")
    manifest = {
        "generator": GENERATOR, "report_id": report.id, "report_title": shown.get("report", {}).get("title"),
        "frozen_at": report.frozen_at.isoformat(), "report_sha256": report.content_hash,
        "intact": _sha(report.snapshot.encode("utf-8")) == report.content_hash,
        "disclosure": None if disclosure is None else {
            "id": disclosure.id, "sha256": disclosure.content_hash, "recipient": disclosure.recipient,
            "intact": _sha(disclosure.content.encode("utf-8")) == disclosure.content_hash},
        "files": [{"path": p, "sha256": _sha(b), "bytes": len(b)} for p, b in sorted(files.items())],
        "omitted": omitted,
        "notice": "Findings are statements by the named analysts, each tied to the claim versions and page regions "
                  "listed. MindDoc does not determine fraud or intent."}
    files["manifest.json"] = json.dumps(manifest, indent=2, ensure_ascii=False).encode("utf-8")
    main = "disclosure.json" if disclosure is not None else "report.json"
    files["README.txt"] = (
        f"MindDoc evidence bundle ({GENERATOR})\n\n"
        f"{main}: the {'disclosure copy' if disclosure is not None else 'frozen report'} exactly as hashed.\n"
        f"  SHA-256 should equal {disclosure.content_hash if disclosure is not None else report.content_hash}\n"
        + (f"  It was derived from the frozen report with SHA-256 {report.content_hash}.\n"
           "  Third-party personal data was withheld; disclosure.json lists each withheld item and its reason.\n"
           if disclosure is not None else "")
        + "evidence/: the page region of each cited row (finding F, claim C).\n"
        + ("pages/: each cited page with the row boxed.\n" if disclosure is None else "")
        + "sources.json: the source documents with their SHA-256 and the pages cited.\n"
          "manifest.json: SHA-256 of every file in this bundle, and any evidence image that was left out and why.\n\n"
          "Verify: compute SHA-256 of each file (e.g. `sha256sum` or `Get-FileHash`) and compare with manifest.json.\n"
          "MindDoc does not determine fraud or intent.\n").encode("utf-8")

    stamp = report.frozen_at.timetuple()[:6]
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(files):
            info = zipfile.ZipInfo(p, date_time=stamp)  # fixed timestamps: the same bundle gives the same bytes
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, files[p])
    name = f"minddoc-report-{report.id}" + (f"-disclosure-{disclosure.id}" if disclosure is not None else "") + ".zip"
    return buf.getvalue(), name

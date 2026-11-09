# ADR-0006 — Document parsing: Docling + PaddleOCR + Tesseract; licence-clean models

**Status:** Proposed

**Context.** v2 uses PyMuPDF + EasyOCR + OpenCV heuristics. Research (`docs/research/TECHNOLOGY_EVALUATION.md`) found
EasyOCR stagnant and slow on CPU, Table Transformer archived (Sep 2026), LayoutLMv3 weights non-commercial,
Ultralytics / DocLayout-YOLO AGPL, Surya weights revenue-restricted and Qwen2.5-VL-3B non-commercial.

**Licence finding (audit, verified):** PyMuPDF — used by v2 for PDF text, rendering and the page highlighter — is
**AGPL-3.0** (commercial licence from Artifex). It must leave the default build or be licensed.

**Decision.** Replace PyMuPDF with pypdfium2 (Apache-2.0/BSD) for rendering and the highlighter, and pdfplumber/pdfminer
(MIT) or Docling's parser for text and word boxes. Docling for conversion, layout and TableFormer; PaddleOCR PP-OCRv5 (Apache-2.0) as primary OCR with
Tesseract fallback; keep v2's OpenCV quality/deskew stage as preprocessing; choose the table engine between TableFormer
and PP-StructureV3 by TEDS on DocBench-50. Policy: no non-commercial, AGPL or revenue-restricted weights in the default
build; such models may appear only in clearly separated research experiments.

**Alternatives.** Azure AI Document Intelligence / Google Document AI as optional adapters for customers who allow data
egress; VLM-only parsing (ungrounded and costly on CPU).

**Consequences.** Better speed and grounding on CPU; a dependency swap with regression risk, so it is gated by
DocBench metrics ≥ the current baseline.

**Revisit when.** A GPU is available (Granite-Docling, local VLMs) or Docling fails >10% of DocBench pages.

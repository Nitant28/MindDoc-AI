# ADR-0014 — Build profiles: slim (default) and ML (optional)

**Status:** Accepted (owner mandate 2026-11-10)

**Context.** The demo host has 512 MB; torch alone exceeds that. Several useful components (Docling, PaddleOCR,
sentence-transformers, graspologic) are heavy. The product must stay usable without them.

**Decision.** Two profiles. **slim** (`requirements.txt`, default Docker build): no torch, no paddle; hashing
embeddings, Tesseract and RapidOCR (ONNX), pdfplumber/pypdfium2, rule-based everything. **ml**
(`requirements-ml.txt`, `INSTALL_ML=true`): MiniLM embeddings, cross-encoder reranker, optional NLI verifier, Docling and
other models as they pass their benchmarks. Every new dependency declares its profile in `docs/LICENSES.md`. Features
detect optional components at runtime and degrade with a visible capability flag, never an error.

**Acceptance.** CI builds and boots the slim image within 512 MB and runs the smoke test; CI runs the test suite with the
ML profile; `GET /api/intel/capabilities` reports which optional components are active.

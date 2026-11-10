# StatementBench results

| Date | Commit | Split | Extractor | Row F1 | Row recall (95% CI) | Balance acc. | Statement exact | Reconciled | s/page |
|---|---|---|---|---|---|---|---|---|---|
| 2026-11-10 | R1 baseline (code = `ee814b0`) | dev (40 stmts, 2,602 rows) | `current` (2.1.0 pipeline) | 0.000 | 0.000 (0.000–0.001) | — | 0.000 | 0.000 | 0.55 |

**Reading.** MindDoc 2.1.0 has no transaction extractor. Its generic parser (`document_service.parse_pdf`) emits
Markdown tables only when PyMuPDF's `find_tables` detects a ruled table; statement tables are usually borderless, so no
rows are produced. This is the baseline every later number is compared with. The test split (E–F) is not scored for the
baseline, to keep it unseen until the engine is frozen.

Raw: `statementbench-dev-2026-11-10.json`.

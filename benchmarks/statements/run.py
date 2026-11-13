"""StatementBench scorer.

    python -m benchmarks.statements.generator --out benchmarks/statements/data
    python -m benchmarks.statements.run --data benchmarks/statements/data --split dev --extractors current --report

Extractors return {"rows": [{"date": "YYYY-MM-DD", "debit_minor": int, "credit_minor": int, "balance_minor": int|None,
"narration": str}], "opening_minor": int|None}. Metrics (H §3.3):
  row precision / recall / F1   a predicted row matches an unused gold row with the same date, debit and credit
  balance accuracy              matched rows whose balance equals gold exactly
  narration accuracy            matched rows whose whitespace/case-normalised narration equals gold
  statement exact match         every gold row matched, no extra rows, every balance exact
  reconciliation pass rate      statements whose *extracted* rows satisfy prev + credit − debit = balance for every row
  seconds per page              wall time / pages
Rates come with Wilson 95% intervals; row-level intervals treat rows as independent (optimistic — rows within a
statement are correlated; statement-level metrics are the conservative view).
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
import time
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

REPORTS = Path(__file__).resolve().parents[1] / "reports"


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if not n:
        return (0.0, 0.0)
    p, d = k / n, 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0.0, c - h), min(1.0, c + h)


# ----------------------------------------------------------------------------------------------- extractors
_DATE_FORMATS = ["%d/%m/%y", "%d/%m/%Y", "%d-%m-%Y", "%d-%m-%y", "%d %b %Y", "%d-%b-%y", "%d-%b-%Y", "%d.%m.%Y",
                 "%Y-%m-%d"]


def parse_date(text: str) -> date | None:
    text = (text or "").strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def extract_current(pdf_path: Path) -> dict:
    """Baseline: today's pipeline (document_service.parse_pdf, tables via find_tables → Markdown) read naively.

    This is what MindDoc 2.1.0 can do with a statement: it has no transaction extractor, so the only structured
    signal is whatever Markdown tables the generic parser emits.
    """
    from app.finance.money import MoneyError, parse_amount, signed_balance
    from app.services.document_service import parse_pdf

    doc = parse_pdf(pdf_path.read_bytes())
    rows: list[dict] = []
    for page in doc.pages:
        header = None
        for line in page.text.splitlines():
            if not line.strip().startswith("|"):
                header = None if not line.strip() else header
                continue
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if set("".join(cells)) <= set("-: "):
                continue
            if header is None:
                header = [c.lower() for c in cells]
                continue
            rec = dict(zip(header, cells))

            def pick(*keys):
                return next((v for k, v in rec.items() if any(x in k for x in keys) and v), "")

            d = parse_date(pick("date"))
            if not d:
                continue
            try:
                debit = parse_amount(pick("withdrawal", "debit")).money.minor if pick("withdrawal", "debit") else 0
                credit = parse_amount(pick("deposit", "credit")).money.minor if pick("deposit", "credit") else 0
                bal_txt = pick("balance")
                bal = signed_balance(parse_amount(bal_txt)).minor if bal_txt else None
            except MoneyError:
                continue
            rows.append({"date": d.isoformat(), "debit_minor": debit, "credit_minor": credit, "balance_minor": bal,
                         "narration": pick("narration", "particular", "description", "detail", "remark")})
    return {"rows": rows, "opening_minor": None}


EXTRACTORS = {"current": extract_current}


def _register_engine() -> None:
    """The R3 statement engine registers itself here once it exists (app.finance.statements)."""
    try:
        from app.finance import statements  # noqa: F401
        EXTRACTORS["engine"] = statements.extract_for_benchmark
    except Exception:
        pass


# --------------------------------------------------------------------------------------------------- scoring
def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").replace("/ ", "/")).strip().casefold()


def score_statement(gold: dict, pred: dict) -> dict:
    unused = list(range(len(gold["rows"])))
    matched = []
    for p in pred["rows"]:
        for j in unused:
            g = gold["rows"][j]
            if (p["date"], p["debit_minor"], p["credit_minor"]) == (g["date"], g["debit_minor"], g["credit_minor"]):
                matched.append((p, g))
                unused.remove(j)
                break
    bal_ok = sum(p.get("balance_minor") == g["balance_minor"] for p, g in matched)
    narr_ok = sum(_norm(p.get("narration", "")) == _norm(g["narration"]) for p, g in matched)
    # reconciliation of the *extracted* rows
    rows = pred["rows"]
    recon = bool(rows) and all(r.get("balance_minor") is not None for r in rows)
    if recon:
        prev = pred.get("opening_minor")
        if prev is None:
            prev = rows[0]["balance_minor"] - rows[0]["credit_minor"] + rows[0]["debit_minor"]
        for r in rows:
            if prev + r["credit_minor"] - r["debit_minor"] != r["balance_minor"]:
                recon = False
                break
            prev = r["balance_minor"]
    exact = len(matched) == len(gold["rows"]) == len(rows) and bal_ok == len(matched)
    return {"gold_rows": len(gold["rows"]), "pred_rows": len(rows), "matched": len(matched), "balance_ok": bal_ok,
            "narration_ok": narr_ok, "exact": exact, "reconciled": recon}


def aggregate(results: list[dict]) -> dict:
    g = sum(r["gold_rows"] for r in results)
    p = sum(r["pred_rows"] for r in results)
    m = sum(r["matched"] for r in results)
    prec, rec = (m / p if p else 0.0), (m / g if g else 0.0)
    n = len(results)
    ex = sum(r["exact"] for r in results)
    rc = sum(r["reconciled"] for r in results)
    return {"statements": n, "gold_rows": g, "pred_rows": p, "matched": m,
            "row_precision": prec, "row_recall": rec, "row_recall_ci": wilson(m, g),
            "row_f1": 2 * prec * rec / (prec + rec) if prec + rec else 0.0,
            "balance_acc": sum(r["balance_ok"] for r in results) / m if m else 0.0,
            "narration_acc": sum(r["narration_ok"] for r in results) / m if m else 0.0,
            "statement_exact": ex / n if n else 0.0, "statement_exact_ci": wilson(ex, n),
            "reconciled": rc / n if n else 0.0, "reconciled_ci": wilson(rc, n)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="benchmarks/statements/data")
    ap.add_argument("--split", default="dev", choices=["dev", "test", "all"])
    ap.add_argument("--extractors", nargs="+", default=["current"])
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--tag", default="", help="report name prefix, e.g. scan-mild")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    _register_engine()
    data = Path(a.data)
    golds = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(data.glob("*.gold.json"))]
    golds = [g for g in golds if a.split == "all" or g["split"] == a.split]
    out = {}
    for name in a.extractors:
        fn = EXTRACTORS[name]
        per, pages, t0 = [], 0, time.perf_counter()
        by_layout = defaultdict(list)
        for g in golds:
            try:
                pred = fn(data / f"{g['id']}.pdf")
            except Exception as e:  # an extractor crash is a scored failure, not a skipped case
                pred = {"rows": [], "opening_minor": None, "error": repr(e)}
            s = score_statement(g, pred)
            s.update(id=g["id"], layout=g["layout"])
            per.append(s)
            by_layout[g["layout"]].append(s)
            pages += g["pages"]
        secs = time.perf_counter() - t0
        agg = aggregate(per)
        agg["seconds_per_page"] = secs / pages if pages else 0.0
        agg["by_layout"] = {k: aggregate(v) for k, v in sorted(by_layout.items())}
        out[name] = {"summary": agg, "statements": per}
        print(f"\n== {name} [{a.split}: {agg['statements']} statements, {agg['gold_rows']} rows, {pages} pages]")
        print(f"   rows: precision {agg['row_precision']:.3f} recall {agg['row_recall']:.3f} "
              f"(95% CI {agg['row_recall_ci'][0]:.3f}-{agg['row_recall_ci'][1]:.3f}) F1 {agg['row_f1']:.3f}")
        print(f"   matched rows: balance {agg['balance_acc']:.3f} narration {agg['narration_acc']:.3f}")
        print(f"   statements: exact {agg['statement_exact']:.3f} reconciled {agg['reconciled']:.3f}; "
              f"{agg['seconds_per_page']:.3f} s/page")
        print("   by layout: " + ", ".join(f"{k} F1={v['row_f1']:.2f} exact={v['statement_exact']:.2f}"
                                          for k, v in agg["by_layout"].items()))
    if a.report:
        REPORTS.mkdir(parents=True, exist_ok=True)
        prefix = f"{a.tag}-" if a.tag else ""
        path = REPORTS / f"statementbench-{prefix}{a.split}-{date.today()}.json"
        path.write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
        print(f"\nwrote {path}")


if __name__ == "__main__":
    main()

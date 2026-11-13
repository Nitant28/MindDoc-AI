"""StatementBench v1 — fault injection for the reconciliation and diagnosis layer (ADR-0011, design E §S5).

Measures what the reviewer is shown when an extraction is wrong: is the fault detected, is it localised to the right
row, and does the right hypothesis appear (anywhere / ranked first)? Also measures false alarms on clean statements.

Faults are injected at the *row* level into synthetic histories (the same generator as StatementBench v0), so this
isolates reconciliation from PDF parsing: it says nothing about how often the extractor makes these errors.

Splits are by seed range. `dev` is used for development; `test` is scored with frozen code and reported, never tuned on.

    python -m benchmarks.statements.faults --split dev [--n 300] [--report]
"""
from __future__ import annotations

import argparse
import copy
import json
import random
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.finance.reconcile import TxnRow, _digit_variants, reconcile  # noqa: E402
from benchmarks.statements.generator import make_history  # noqa: E402
from benchmarks.statements.run import wilson  # noqa: E402

SEEDS = {"dev": 10_000, "test": 90_000}
FAULTS = ["amount_digit", "direction_swap", "balance_digit", "dropped_row", "same_day_swap"]
EXPECTED_CODE = {"amount_digit": "amount_ocr_suspect", "direction_swap": "direction_suspect",
                 "balance_digit": "balance_ocr_suspect", "dropped_row": "missing_row_suspect",
                 "same_day_swap": "order_ambiguous"}


def _rows(txns) -> list[TxnRow]:
    return [TxnRow(seq=i + 1, date=t.date.isoformat(), debit=t.debit.minor, credit=t.credit.minor,
                   balance=t.balance.minor, narration=t.narration) for i, t in enumerate(txns)]


def _one_edit(rng: random.Random, n: int) -> int:
    """A realistic one-edit misreading of a positive amount (substitution, transposition, dropped digit)."""
    s = str(n)
    for _ in range(50):
        kind = rng.choice(["sub", "swap", "drop"])
        i = rng.randrange(len(s))
        if kind == "sub":
            v = s[:i] + rng.choice([d for d in "0123456789" if d != s[i]]) + s[i + 1:]
        elif kind == "swap" and i + 1 < len(s) and s[i] != s[i + 1]:
            v = s[:i] + s[i + 1] + s[i] + s[i + 2:]
        elif kind == "drop" and len(s) > 3:
            v = s[:i] + s[i + 1:]
        else:
            continue
        val = int(v)
        if val > 0 and val != n and val in _digit_variants(n):
            return val
    raise ValueError("no edit found")


def inject(rng: random.Random, rows: list[TxnRow], fault: str):
    """Return (faulty_rows, target_seq) or None if this history cannot host the fault. target_seq is the seq of the
    row a reviewer should be sent to (the faulty row, or the row after a dropped one)."""
    rows = copy.deepcopy(rows)
    n = len(rows)
    if fault == "amount_digit":
        k = rng.randrange(n)
        r = rows[k]
        amt = r.debit or r.credit
        if amt < 1000:
            return None
        new = _one_edit(rng, amt)
        if r.debit:
            r.debit = new
        else:
            r.credit = new
        return rows, r.seq
    if fault == "direction_swap":
        r = rows[rng.randrange(n)]
        r.debit, r.credit = r.credit, r.debit
        return rows, r.seq
    if fault == "balance_digit":
        k = rng.randrange(n - 1)            # not the last row: its error is only visible through the closing check
        r = rows[k]
        if abs(r.balance) < 1000:
            return None
        sign = -1 if r.balance < 0 else 1
        r.balance = sign * _one_edit(rng, abs(r.balance))
        return rows, r.seq
    if fault == "dropped_row":
        k = rng.randrange(1, n - 1)
        del rows[k]
        for i, r in enumerate(rows):
            r.seq = i + 1                    # an extractor that missed a row numbers the rest consecutively
        return rows, rows[k].seq
    if fault == "same_day_swap":
        pairs = [i for i in range(1, n - 1) if rows[i].date == rows[i + 1].date
                 and (rows[i].credit - rows[i].debit) != (rows[i + 1].credit - rows[i + 1].debit)]
        if not pairs:
            return None
        i = rng.choice(pairs)
        rows[i], rows[i + 1] = rows[i + 1], rows[i]
        rows[i].seq, rows[i + 1].seq = i + 1, i + 2
        return rows, rows[i].seq
    raise ValueError(fault)


def evaluate(split: str, n: int, source: str = "text") -> dict:
    base = SEEDS[split]
    tally = defaultdict(lambda: defaultdict(int))
    clean = {"n": 0, "false_alarm": 0, "rows": 0}
    for s in range(n):
        rng = random.Random(base + s)
        opening, txns = make_history(rng, od=rng.random() < 0.3, n=rng.randint(20, 60), start=date(2024, 4, 1))
        gold = _rows(txns)
        closing = gold[-1].balance

        rows = copy.deepcopy(gold)
        status, checks, _ = reconcile(rows, opening.minor, closing, source)
        clean["n"] += 1
        clean["rows"] += len(rows)
        clean["false_alarm"] += any(c.status == "fail" for c in checks)

        for fault in FAULTS:
            got = inject(random.Random(f"{base + s}:{fault}"), gold, fault)
            if got is None:
                continue
            faulty, target = got
            snapshot = [(r.debit, r.credit, r.balance) for r in faulty]
            status, checks, _ = reconcile(faulty, opening.minor, closing, source)
            assert snapshot == [(r.debit, r.credit, r.balance) for r in faulty], "reconcile modified a value"
            fails = [c for c in checks if c.status == "fail"]
            row_fails = [c for c in fails if c.scope == "row"]
            t = tally[fault]
            t["n"] += 1
            t["detected"] += bool(fails)
            first = row_fails[0] if row_fails else None
            localised = first is not None and first.seq == target
            t["localised"] += localised
            at_target = next((c for c in row_fails if c.seq == target), None)
            codes = [h["code"] for h in at_target.hypotheses] if at_target else []
            want = EXPECTED_CODE[fault]
            t["diagnosed_any"] += want in codes
            t["diagnosed_top1"] += bool(codes) and codes[0] == want
            t["no_hypothesis"] += at_target is not None and not codes
            t["failed_rows"] += len(row_fails)
            follow = [c for c in row_fails if c.seq != target]
            t["follow_on"] += len(follow)
            t["follow_on_labelled"] += sum(bool(c.hypotheses) and c.hypotheses[0]["code"] == "follows_previous_error"
                                           for c in follow)

    def rate(k, m):
        lo, hi = wilson(k, m)
        return {"k": k, "n": m, "rate": round(k / m, 4) if m else None, "ci95": [round(lo, 4), round(hi, 4)]}

    out = {"split": split, "source_prior": source, "histories": n, "seed_base": base,
           "clean": {"statements": clean["n"], "rows": clean["rows"],
                     "false_alarm_rate": rate(clean["false_alarm"], clean["n"])},
           "faults": {}}
    for fault in FAULTS:
        t = tally[fault]
        out["faults"][fault] = {
            "injected": t["n"],
            "detected": rate(t["detected"], t["n"]),
            "localised_first_failure": rate(t["localised"], t["n"]),
            "diagnosis_in_hypotheses": rate(t["diagnosed_any"], t["n"]),
            "diagnosis_ranked_first": rate(t["diagnosed_top1"], t["n"]),
            "failing_row_with_no_hypothesis": t["no_hypothesis"],
            "mean_failed_rows": round(t["failed_rows"] / t["n"], 2) if t["n"] else None,
            "follow_on_failures_pointing_to_root": rate(t["follow_on_labelled"], t["follow_on"]),
        }
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--split", choices=sorted(SEEDS), default="dev")
    ap.add_argument("--n", type=int, default=300, help="number of synthetic histories")
    ap.add_argument("--report", action="store_true", help="write benchmarks/reports/statementbench-faults-<split>-<date>.json")
    args = ap.parse_args()
    results = {src: evaluate(args.split, args.n, src) for src in ("text", "ocr")}
    for src, res in results.items():
        print(f"\n[{args.split} - ranking prior: {src}] clean statements: false-alarm "
              f"{res['clean']['false_alarm_rate']['rate']} over {res['clean']['statements']}")
        print(f"{'fault':16} {'n':>5} {'detect':>7} {'locate':>7} {'diag':>7} {'top1':>7} {'knock-on->root':>14}")
        for f, m in res["faults"].items():
            print(f"{f:16} {m['injected']:>5} {m['detected']['rate']:>7} {m['localised_first_failure']['rate']:>7} "
                  f"{m['diagnosis_in_hypotheses']['rate']:>7} {m['diagnosis_ranked_first']['rate']:>7} "
                  f"{str(m['follow_on_failures_pointing_to_root']['k']) + '/' + str(m['follow_on_failures_pointing_to_root']['n']):>14}")
    if args.report:
        p = ROOT / "benchmarks" / "reports" / f"statementbench-faults-{args.split}-{date.today().isoformat()}.json"
        p.write_text(json.dumps(results, indent=2), encoding="utf-8")
        print("wrote", p.relative_to(ROOT))


if __name__ == "__main__":
    main()

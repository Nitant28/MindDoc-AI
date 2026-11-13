"""Score entity resolution on EntityBench (EB) v0.

    python -m benchmarks.entities.run --split dev --n 30 [--report]

Metrics (pairs of records):
- auto band: pairwise precision/recall of the clusters formed by automatic links;
- wrong auto merges, and the high-risk subset: records whose true parties carry different PANs that were nonetheless
  auto-merged (must be 0), and homonym/sibling merges;
- review band: pairs sent to review, the share that are true matches, and recall if every review pair were accepted.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from datetime import date
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.identity.resolver import Record, resolve  # noqa: E402
from benchmarks.entities.generator import cases  # noqa: E402
from benchmarks.statements.run import wilson  # noqa: E402


def score_case(case: dict, **kw) -> dict:
    recs = case["records"]
    truth = {r["id"]: r["truth"] for r in recs}
    records = [Record(r["id"], r["name"], pan=r["pan"], gstin=r["gstin"], vpa=r["vpa"], account=r["account"])
               for r in recs]
    decisions, clusters = resolve(records, **kw)
    pred_pairs = {tuple(sorted(p)) for c in clusters for p in combinations(c, 2)}
    by_truth: dict = {}
    for rid, t in truth.items():
        by_truth.setdefault(t, []).append(rid)
    true_pairs = {tuple(sorted(p)) for ids in by_truth.values() for p in combinations(ids, 2)}
    review = {tuple(sorted((d.a, d.b))) for d in decisions if d.band == "review"}
    wrong = pred_pairs - true_pairs
    pans = {}
    for r in recs:
        if r["pan"] or r["gstin"]:
            pans.setdefault(r["truth"], set()).add(r["pan"] or r["gstin"][2:12])
    high_risk = [p for p in wrong if pans.get(truth[p[0]]) and pans.get(truth[p[1]])]
    cluster_of = {rid: i for i, c in enumerate(clusters) for rid in c}
    review_clusters = {tuple(sorted((cluster_of[a], cluster_of[b]))) for a, b in review
                       if cluster_of[a] != cluster_of[b]}
    return {"tp": len(pred_pairs & true_pairs), "fp": len(wrong), "fn": len(true_pairs - pred_pairs),
            "review_cluster_pairs": len(review_clusters),
            "true_pairs": len(true_pairs), "high_risk": len(high_risk),
            "review": len(review), "review_true": len(review & true_pairs),
            "recall_if_review_accepted": len((pred_pairs | review) & true_pairs)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", choices=["dev", "test"], default="dev")
    ap.add_argument("--n", type=int, default=30)
    ap.add_argument("--report", action="store_true")
    a = ap.parse_args()
    t0 = time.perf_counter()
    tot = Counter()
    n_records = 0
    for case in cases(a.split, a.n):
        n_records += len(case["records"])
        tot.update(score_case(case))
    secs = time.perf_counter() - t0
    prec = tot["tp"] / (tot["tp"] + tot["fp"]) if tot["tp"] + tot["fp"] else 1.0
    rec = tot["tp"] / tot["true_pairs"] if tot["true_pairs"] else 1.0
    res = {
        "split": a.split, "cases": a.n, "records": n_records, "true_pairs": tot["true_pairs"],
        "auto": {"precision": round(prec, 4), "precision_ci95": [round(x, 4) for x in wilson(tot["tp"], tot["tp"] + tot["fp"])],
                 "recall": round(rec, 4), "recall_ci95": [round(x, 4) for x in wilson(tot["tp"], tot["true_pairs"])],
                 "wrong_pairs": tot["fp"], "high_risk_wrong_pairs": tot["high_risk"]},
        "review": {"pairs": tot["review"], "per_case": round(tot["review"] / a.n, 1),
                   "cluster_pairs_per_case": round(tot["review_cluster_pairs"] / a.n, 1),
                   "true_match_share": round(tot["review_true"] / tot["review"], 4) if tot["review"] else None,
                   "recall_if_all_accepted": round(tot["recall_if_review_accepted"] / tot["true_pairs"], 4)},
        "seconds_per_case": round(secs / a.n, 2),
    }
    print(json.dumps(res, indent=1))
    if a.report:
        p = ROOT / "benchmarks" / "reports" / f"entitybench-{a.split}-{date.today().isoformat()}.json"
        p.write_text(json.dumps(res, indent=2), encoding="utf-8")
        print("wrote", p.relative_to(ROOT))


if __name__ == "__main__":
    main()

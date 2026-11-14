"""FB-Synth runner: scheme recall, false flags on benign look-alikes and on background activity, evidence completeness.

    python -m benchmarks.discovery.run --split dev
    python -m benchmarks.discovery.run --split test --final     # once, from a committed tree

Matching (pre-registered in README.md):
* a scheme instance is **found** when a lead from its detector cites at least half of its transactions;
* a benign look-alike is **falsely flagged** when any lead cites any of its transactions;
* a **background false flag** is a lead citing only background transactions (no planted instance);
* evidence completeness = share of a found scheme's transactions cited by the matching lead.
"""
from __future__ import annotations

import argparse
import json
import math
import subprocess
from collections import defaultdict
from datetime import date
from pathlib import Path

from app.discovery import detectors
from benchmarks.discovery import synth

ROOT = Path(__file__).resolve().parents[2]
REPORTS = ROOT / "benchmarks" / "reports"


def wilson(k: int, n: int, z: float = 1.96) -> list[float]:
    if n == 0:
        return [0.0, 0.0]
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(max(0.0, c - h), 3), round(min(1.0, c + h), 3)]


def evaluate(split: str, n: int) -> dict:
    found = defaultdict(lambda: [0, 0])
    benign = defaultdict(lambda: [0, 0])
    completeness, bg_flags, bg_txns, misses, flagged_examples = [], 0, 0, [], []
    for data, inst in synth.cases(split, n):
        leads = detectors.run_all(data)
        planted = {k for i in inst for k in i.keys}
        bg_txns += sum(1 for t in data.txns if t.key not in planted)
        for i in inst:
            gold = set(i.keys)
            if i.kind == "scheme":
                best = max((len(gold & {t.key for t in lead.txns}) / len(gold) for lead in leads
                            if lead.detector == i.detector), default=0.0)
                found[i.family][1] += 1
                if best >= 0.5:
                    found[i.family][0] += 1
                    completeness.append(best)
                elif len(misses) < 12:
                    misses.append({"family": i.family, "best_overlap": round(best, 2)})
            else:
                benign[i.family][1] += 1
                hit = [lead for lead in leads if gold & {t.key for t in lead.txns}]
                if hit:
                    benign[i.family][0] += 1
                    if len(flagged_examples) < 12:
                        flagged_examples.append({"family": i.family, "by": sorted({h.detector for h in hit})})
        bg_flags += sum(1 for lead in leads if not ({t.key for t in lead.txns} & planted))
    k_s, n_s = sum(v[0] for v in found.values()), sum(v[1] for v in found.values())
    k_b, n_b = sum(v[0] for v in benign.values()), sum(v[1] for v in benign.values())
    return {
        "benchmark": synth.VERSION, "split": split, "cases": n, "detectors_version": detectors.VERSION,
        "scheme_recall": round(k_s / n_s, 3), "scheme_recall_ci95": wilson(k_s, n_s), "schemes": n_s,
        "recall_by_family": {f: {"found": v[0], "of": v[1]} for f, v in sorted(found.items())},
        "false_flags_per_10_benign": round(10 * k_b / n_b, 2), "benign_flagged_share_ci95": wilson(k_b, n_b),
        "benign": n_b, "benign_flagged_by_family": {f: {"flagged": v[0], "of": v[1]} for f, v in sorted(benign.items())},
        "background_false_flags": bg_flags, "background_txns": bg_txns,
        "background_false_flags_per_1000_txns": round(1000 * bg_flags / max(1, bg_txns), 2),
        "evidence_completeness_mean": round(sum(completeness) / max(1, len(completeness)), 3),
        "misses": misses, "benign_flagged_examples": flagged_examples,
    }


def git_state() -> tuple[str, bool]:
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    dirty = bool(subprocess.run(["git", "status", "--porcelain", "app/discovery", "benchmarks/discovery"], cwd=ROOT,
                                capture_output=True, text=True).stdout.strip())
    return commit, dirty


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", choices=["dev", "test"], default="dev")
    ap.add_argument("--cases", type=int, default=40)
    ap.add_argument("--final", action="store_true", help="required to score the held-out test split")
    args = ap.parse_args()
    commit, dirty = git_state()
    if args.split == "test":
        if not args.final:
            raise SystemExit("the test split is held out: pass --final to score it (once)")
        if dirty:
            raise SystemExit("commit the detectors and the benchmark before scoring the test split")
    res = evaluate(args.split, args.cases)
    res["meta"] = {"commit": commit, "dirty": dirty, "date": date.today().isoformat()}
    print(json.dumps(res, indent=2, ensure_ascii=False))
    if args.final or args.split == "dev":
        REPORTS.mkdir(parents=True, exist_ok=True)
        out = REPORTS / f"fbsynth-{args.split}-{date.today().isoformat()}.json"
        out.write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()

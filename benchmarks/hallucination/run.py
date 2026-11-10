"""Score claim verifiers on the MindDoc hallucination test set.

    python -m benchmarks.hallucination.run --split dev
    python -m benchmarks.hallucination.run --split test --configs legacy value rules rules+nli --report

Configs: legacy = v1 similarity check; value = v2 value checks only (what marks a sentence "not supported");
rules = value checks + wording heuristics (everything the UI flags, red or amber); rules+nli / nli = with the
optional LettuceDetect model.

Metrics (positive class = "unsupported"):
  catch rate  = unsupported claims flagged / unsupported claims          (recall)
  false flags = supported claims flagged / supported claims              (false-positive rate)
Both with Wilson 95% intervals — the set is small, so read the intervals, not just the point estimates.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from collections import defaultdict
from datetime import date
from pathlib import Path

if "--hashing" in sys.argv:  # force the offline hashing embedder (what the slim Render image runs)
    os.environ["EMBEDDING_MODEL"] = "none/hashing-only"
    os.environ["HF_HUB_OFFLINE"] = "1"

from benchmarks.hallucination.cases import cases  # noqa: E402
from benchmarks.hallucination.legacy import legacy_supported  # noqa: E402
from app.ai import verifier  # noqa: E402
from app.ml import embeddings as emb  # noqa: E402

REPORT_DIR = Path(__file__).resolve().parents[1] / "reports"
NLI_THRESHOLD = 0.5


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def similarity(claim: str, passage: str) -> tuple[float, float]:
    vecs, model = emb.embed([passage, claim])
    return float(vecs[0] @ vecs[1]), (0.5 if model != emb.HASHING_MODEL_NAME else 0.35)


def predict(config: str, case: dict, nli_model: str | None) -> tuple[bool, dict]:
    """Return (flagged_as_unsupported, detail)."""
    if config == "legacy":
        return (not legacy_supported(case["claim"], case["passage"])), {}
    if config == "nli":
        p = verifier.nli_unsupported_prob(case["question"], [case["passage"]], case["claim"], nli_model,
                                          allow_download=True)
        return (p is not None and p >= 0.5), {"nli": p}
    sim, thr = similarity(case["claim"], case["passage"])
    v = verifier.check_claim(case["claim"], [case["passage"]], sim_threshold=thr, embed_fn=lambda t: emb.embed(t)[0],
                             question=case["question"], use_nli=False)
    issues, p = list(v.issues), None
    if config == "value":  # red tier only: value checks decide "unsupported"; wording heuristics don't count
        return (not v.supported), {"issues": issues, "coverage": round(v.coverage, 2), "sim": round(sim, 3)}
    if config == "rules+nli":
        p = verifier.nli_unsupported_prob(case["question"], [case["passage"]], case["claim"], nli_model,
                                          allow_download=True)
        if p is not None and p >= NLI_THRESHOLD:
            issues.append({"kind": "nli", "detail": f"p={p:.2f}"})
    return bool(issues), {"issues": issues, "coverage": round(v.coverage, 2), "sim": round(sim, 3),
                          "rules_flagged": bool(v.issues), "nli": p}


def score(rows: list[dict]) -> dict:
    unsup = [r for r in rows if r["label"] == "unsupported"]
    sup = [r for r in rows if r["label"] == "supported"]
    caught = sum(r["flagged"] for r in unsup)
    false_flags = sum(r["flagged"] for r in sup)
    precision = caught / max(1, caught + false_flags)
    recall = caught / max(1, len(unsup))
    by_type = defaultdict(lambda: [0, 0])
    for r in rows:
        by_type[r["type"]][0] += r["flagged"]
        by_type[r["type"]][1] += 1
    return {"n": len(rows), "caught": caught, "n_unsupported": len(unsup), "catch_rate": recall,
            "catch_ci": wilson(caught, len(unsup)), "false_flags": false_flags, "n_supported": len(sup),
            "false_flag_rate": false_flags / max(1, len(sup)), "false_flag_ci": wilson(false_flags, len(sup)),
            "f1": 2 * precision * recall / max(1e-9, precision + recall), "by_type": dict(by_type)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="dev", choices=["dev", "test", "all"])
    ap.add_argument("--configs", nargs="+", default=["legacy", "rules"])
    ap.add_argument("--nli-model", default="KRLabsOrg/tinylettuce-ettin-68m-en")
    ap.add_argument("--hashing", action="store_true", help="use the offline hashing embedder")
    ap.add_argument("--report", action="store_true", help="write benchmarks/reports/hallucination-*.md/json")
    ap.add_argument("--show-errors", action="store_true")
    ap.add_argument("--nli-threshold", type=float, default=0.5)
    ap.add_argument("--sweep", action="store_true", help="print rules+nli results for NLI thresholds 0.5–0.99")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    global NLI_THRESHOLD
    NLI_THRESHOLD = args.nli_threshold

    data = cases(None if args.split == "all" else args.split)
    emb_name = emb.active_model_name()
    results = {}
    for config in args.configs:
        t0 = time.perf_counter()
        rows = []
        for c in data:
            flagged, detail = predict(config, c, args.nli_model)
            rows.append({**c, "flagged": flagged, **detail})
        s = score(rows)
        s["seconds"] = round(time.perf_counter() - t0, 1)
        results[config] = {"summary": s, "rows": rows}
        print(f"\n== {config}  [{args.split}, n={s['n']}, embeddings={emb_name}"
              + (f", nli={args.nli_model}" if "nli" in config else "") + f", {s['seconds']}s]")
        print(f"   catch rate  {s['caught']}/{s['n_unsupported']} = {s['catch_rate']:.0%} "
              f"(95% CI {s['catch_ci'][0]:.0%}–{s['catch_ci'][1]:.0%})")
        print(f"   false flags {s['false_flags']}/{s['n_supported']} = {s['false_flag_rate']:.0%} "
              f"(95% CI {s['false_flag_ci'][0]:.0%}–{s['false_flag_ci'][1]:.0%})   F1 {s['f1']:.2f}")
        print("   by type: " + ", ".join(f"{t} {k}/{n}" for t, (k, n) in sorted(s["by_type"].items())))
        if args.sweep and config == "rules+nli":
            for t in (0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.98, 0.99):
                swept = [{**r, "flagged": r["rules_flagged"] or (r["nli"] is not None and r["nli"] >= t)} for r in rows]
                ss = score(swept)
                print(f"   sweep t={t:.2f}: catch {ss['caught']}/{ss['n_unsupported']} = {ss['catch_rate']:.0%}, "
                      f"false flags {ss['false_flags']}/{ss['n_supported']} = {ss['false_flag_rate']:.0%}, F1 {ss['f1']:.2f}")
        if args.show_errors:
            for r in rows:
                wrong = r["flagged"] != (r["label"] == "unsupported")
                if wrong:
                    tag = "MISS " if r["label"] == "unsupported" else "FALSE"
                    print(f"   {tag} {r['id']} [{r['type']}] {r['claim']}")
                    for i in r.get("issues", []):
                        print(f"          - {i['kind']}: {i['detail']}")
    if args.report:
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        stem = REPORT_DIR / f"hallucination-{args.split}-{'hashing' if args.hashing else 'minilm'}-{date.today()}"
        meta = {"split": args.split, "embeddings": emb_name, "nli_model": args.nli_model, "date": str(date.today())}
        stem.with_suffix(".json").write_text(json.dumps({"meta": meta, "results": results}, indent=1,
                                                        ensure_ascii=False, default=str), encoding="utf-8")
        print(f"\nwrote {stem.with_suffix('.json')}")


if __name__ == "__main__":
    main()

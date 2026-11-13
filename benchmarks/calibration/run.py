"""CB: can the claim verifier's output be turned into a calibrated probability that a sentence is supported?

    python -m benchmarks.calibration.run fit  benchmarks/reports/hbsynth-dev-minilm-<date>.json \
                                              benchmarks/reports/hallucination-all-minilm-<date>.json
    python -m benchmarks.calibration.run eval benchmarks/reports/hbsynth-test-minilm-<date>.json

Inputs are hallucination-runner reports (config "rules": every issue with its severity, coverage, similarity,
derivations). `fit` estimates an L2-regularised logistic model of P(supported) on non-held-out reports only and freezes it in
model.json (commit it before scoring the test split). `eval` applies the frozen model to a held-out report and
reports ECE (10 equal-width bins), adaptive ECE (10 equal-mass bins), Brier score and log loss, with 95% intervals
from a bootstrap over documents (1,000 resamples, seed 0), plus the reliability table.

Rule (H_BENCHMARK_STRATEGY §4, J_ROADMAP R6): no score is shown as a probability unless held-out ECE ≤ 0.1.
"""
from __future__ import annotations

import json
import math
import random
import subprocess
import sys
from datetime import date
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
MODEL = HERE / "model.json"
REPORTS = HERE.parents[0] / "reports"
FEATURES = ["red", "amber", "coverage", "similarity", "recomputed"]
L2 = 1.0


def features(row: dict) -> list[float]:
    issues = row.get("issues") or []
    red = any(i.get("severity") == "contradiction" for i in issues)
    amber = any(i.get("severity") == "review" for i in issues)
    sim = row.get("sim")
    return [float(red), float(amber), float(row.get("coverage") or 0.0), float(sim if sim is not None else 0.0),
            float(bool(row.get("derivations")))]


def load_rows(paths: list[str], config: str = "rules") -> list[dict]:
    rows = []
    for p in paths:
        data = json.loads(Path(p).read_text(encoding="utf-8"))
        if config not in data["results"]:
            raise SystemExit(f"{p}: no '{config}' results (run the hallucination runner with --configs {config})")
        for r in data["results"][config]["rows"]:
            rows.append({**r, "_report": Path(p).name})
    return rows


def fit_logistic(x: np.ndarray, y: np.ndarray, l2: float = L2, iters: int = 50) -> np.ndarray:
    """Newton–Raphson for an L2-penalised logistic regression (intercept not penalised)."""
    xb = np.hstack([np.ones((len(x), 1)), x])
    w = np.zeros(xb.shape[1])
    pen = np.full(xb.shape[1], l2)
    pen[0] = 0.0
    for _ in range(iters):
        p = 1 / (1 + np.exp(-xb @ w))
        grad = xb.T @ (p - y) + pen * w
        hess = (xb * (p * (1 - p))[:, None]).T @ xb + np.diag(pen)
        step = np.linalg.solve(hess, grad)
        w -= step
        if np.abs(step).max() < 1e-9:
            break
    return w


def predict(w: np.ndarray, x: np.ndarray) -> np.ndarray:
    return 1 / (1 + np.exp(-(w[0] + x @ w[1:])))


def ece(p: np.ndarray, y: np.ndarray, bins: int = 10, adaptive: bool = False) -> float:
    if adaptive:
        order = np.argsort(p)
        groups = [g for g in np.array_split(order, bins) if len(g)]
    else:
        idx = np.minimum((p * bins).astype(int), bins - 1)
        groups = [np.where(idx == b)[0] for b in range(bins)]
        groups = [g for g in groups if len(g)]
    return float(sum(len(g) / len(p) * abs(p[g].mean() - y[g].mean()) for g in groups))


def metrics(p: np.ndarray, y: np.ndarray) -> dict:
    eps = 1e-12
    return {"ece": ece(p, y), "ece_adaptive": ece(p, y, adaptive=True), "brier": float(np.mean((p - y) ** 2)),
            "log_loss": float(-np.mean(y * np.log(p + eps) + (1 - y) * np.log(1 - p + eps)))}


def reliability(p: np.ndarray, y: np.ndarray, bins: int = 10) -> list[dict]:
    idx = np.minimum((p * bins).astype(int), bins - 1)
    out = []
    for b in range(bins):
        g = np.where(idx == b)[0]
        if len(g):
            out.append({"bin": f"{b / bins:.1f}–{(b + 1) / bins:.1f}", "n": int(len(g)),
                        "mean_predicted": round(float(p[g].mean()), 3), "observed_supported": round(float(y[g].mean()), 3)})
    return out


def bootstrap(p: np.ndarray, y: np.ndarray, groups: list[str], n: int = 1000, seed: int = 0) -> dict:
    """95% intervals from resampling whole documents (claims of one passage are not independent)."""
    rng = random.Random(seed)
    by = {}
    for i, g in enumerate(groups):
        by.setdefault(g, []).append(i)
    keys = list(by)
    draws = {k: [] for k in ("ece", "ece_adaptive", "brier", "log_loss")}
    for _ in range(n):
        idx = np.array([i for k in (rng.choice(keys) for _ in keys) for i in by[k]])
        m = metrics(p[idx], y[idx])
        for k in draws:
            draws[k].append(m[k])
    return {k: [round(float(np.percentile(v, 2.5)), 4), round(float(np.percentile(v, 97.5)), 4)]
            for k, v in draws.items()}


def commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=HERE, capture_output=True, text=True).stdout.strip()
    except OSError:
        return "unknown"


def cmd_fit(paths: list[str]) -> None:
    rows = load_rows(paths)
    x = np.array([features(r) for r in rows])
    y = np.array([1.0 if r["label"] == "supported" else 0.0 for r in rows])
    w = fit_logistic(x, y)
    p = predict(w, x)
    model = {"features": FEATURES, "intercept": float(w[0]), "coef": dict(zip(FEATURES, map(float, w[1:]))),
             "l2": L2, "target": "P(sentence supported)",
             "fit": {"reports": [Path(q).name for q in paths], "n": len(rows), "supported_rate": float(y.mean()),
                     **{k: round(v, 4) for k, v in metrics(p, y).items()}},
             "fitted": str(date.today()), "commit": commit()}
    MODEL.write_text(json.dumps(model, indent=1), encoding="utf-8")
    print(json.dumps(model, indent=1))


def cmd_eval(path: str) -> None:
    model = json.loads(MODEL.read_text(encoding="utf-8"))
    w = np.array([model["intercept"]] + [model["coef"][f] for f in model["features"]])
    rows = load_rows([path])
    x = np.array([features(r) for r in rows])
    y = np.array([1.0 if r["label"] == "supported" else 0.0 for r in rows])
    p = predict(w, x)
    m = metrics(p, y)
    ci = bootstrap(p, y, [r.get("source_id", r["id"]) for r in rows])
    out = {"model": model, "eval_report": Path(path).name, "n": len(rows), "supported_rate": float(y.mean()),
           "metrics": {k: round(v, 4) for k, v in m.items()}, "ci95": ci, "reliability": reliability(p, y),
           "display_allowed": bool(ci["ece"][1] <= 0.1), "date": str(date.today()), "commit": commit()}
    target = REPORTS / f"calibration-{Path(path).stem}.json"
    target.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"n={len(rows)} supported rate {y.mean():.2f}")
    for k, v in m.items():
        print(f"  {k:<13} {v:.4f}  (95% CI {ci[k][0]:.4f}–{ci[k][1]:.4f})")
    for b in out["reliability"]:
        print(f"  {b['bin']}: n={b['n']:<4} predicted {b['mean_predicted']:.3f} observed {b['observed_supported']:.3f}")
    print(f"wrote {target}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) < 3 or sys.argv[1] not in ("fit", "eval"):
        raise SystemExit(__doc__)
    if sys.argv[1] == "fit":
        cmd_fit(sys.argv[2:])
    else:
        cmd_eval(sys.argv[2])

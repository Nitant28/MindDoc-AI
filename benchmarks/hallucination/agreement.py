"""Inter-annotator agreement for claim labels (Cohen's kappa).

    python -m benchmarks.hallucination.agreement annotator_a.jsonl annotator_b.jsonl

Each file is JSONL with at least passage, claim, label. Rows are matched on (passage, claim). Rows labelled
"ambiguous" by either annotator are counted and left out of kappa. Disagreements are printed for adjudication.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path


def load(path: str) -> dict[tuple[str, str], str]:
    out = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            out[(r["passage"].strip(), r["claim"].strip())] = r["label"].strip().lower()
    return out


def cohen_kappa(pairs: list[tuple[str, str]]) -> float:
    n = len(pairs)
    if n == 0:
        return float("nan")
    observed = sum(a == b for a, b in pairs) / n
    ca, cb = Counter(a for a, _ in pairs), Counter(b for _, b in pairs)
    expected = sum(ca[k] * cb[k] for k in set(ca) | set(cb)) / (n * n)
    return 1.0 if expected == 1 else (observed - expected) / (1 - expected)


def main(a_path: str, b_path: str) -> None:
    a, b = load(a_path), load(b_path)
    common = sorted(set(a) & set(b))
    ambiguous = [k for k in common if "ambiguous" in (a[k], b[k])]
    pairs = [(a[k], b[k]) for k in common if k not in ambiguous]
    print(f"matched {len(common)} claims ({len(set(a) - set(b))} only in A, {len(set(b) - set(a))} only in B); "
          f"{len(ambiguous)} marked ambiguous")
    if pairs:
        agree = sum(x == y for x, y in pairs)
        print(f"raw agreement {agree}/{len(pairs)} = {agree / len(pairs):.1%}; Cohen's kappa {cohen_kappa(pairs):.3f}")
    for k in common:
        if k not in ambiguous and a[k] != b[k]:
            print(f"  DISAGREE A={a[k]} B={b[k]}: {k[1]}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    sys.stdout.reconfigure(encoding="utf-8")
    main(sys.argv[1], sys.argv[2])

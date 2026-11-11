"""Entity resolution: deterministic identifier rules, Splink (Fellegi-Sunter, DuckDB) scoring, conservative bands.

ADR-0009. Steps:
1. **Rules.** Records sharing a validated strong identifier (PAN, a GSTIN's PAN, UPI VPA, account+IFSC) link
   deterministically, unless they carry conflicting PANs.
2. **Cannot-link.** Two different valid PANs never auto-merge, directly or through a chain of links (checked when
   clusters are joined). Such pairs go to review with the conflict named.
3. **Splink.** Remaining pairs (blocked on first name token, VPA local part, PAN, account) are scored with a fixed
   Fellegi-Sunter model: the m/u probabilities below are documented priors tuned on the EB dev split only, not
   re-estimated per case (cases are too small for stable EM).
4. **Bands.** auto (merge), review (human decision), separate. Auto from Splink also needs corroboration beyond the
   name for people (homonyms are common), or an exact core name for organisations.
Every pair decision keeps its evidence ("why linked") for the identity event that records it.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

from app.identity.normalize import core_name, initial_key, legal_form, name_kind, normalize_name, sorted_key

logger = logging.getLogger(__name__)

MODEL_VERSION = "splink-5.0.0/fs-v1"
AUTO_THRESHOLD = 0.99
REVIEW_THRESHOLD = 0.3
PRIOR_MATCH = 0.02

# (comparison, levels, m, u) — m: P(level | same party), u: P(level | different parties); non-null levels only.
_PRIORS = {
    "name": {"levels": ["exact", "same tokens", "truncated prefix", "jw>=0.95", "initial+surname", "jw>=0.88", "other"],
             "m": [0.62, 0.04, 0.08, 0.12, 0.04, 0.06, 0.04],
             "u": [0.002, 0.0005, 0.002, 0.004, 0.003, 0.03, 0.9585]},
    "pan": {"levels": ["exact", "other"], "m": [0.98, 0.02], "u": [0.0001, 0.9999]},
    "vpa": {"levels": ["exact", "other"], "m": [0.60, 0.40], "u": [0.0005, 0.9995]},
    "vpa_local": {"levels": ["exact", "other"], "m": [0.50, 0.50], "u": [0.02, 0.98]},
    "account": {"levels": ["exact", "other"], "m": [0.70, 0.30], "u": [0.0001, 0.9999]},
}
STRONG = ("pan", "vpa", "account")  # agreement on these corroborates a name match; a VPA local part does not


@dataclass
class Record:
    id: str
    name: str = ""
    pan: Optional[str] = None
    gstin: Optional[str] = None
    vpa: Optional[str] = None
    account: Optional[str] = None      # "<account>|<IFSC>"
    kind: str = ""

    def __post_init__(self):
        self.name_norm = normalize_name(self.name)
        self.name_core = core_name(self.name_norm)
        self.kind = self.kind or name_kind(self.name)
        if self.gstin and not self.pan and len(self.gstin) == 15:
            self.pan = self.gstin[2:12]
        self.vpa_local = self.vpa.split("@")[0] if self.vpa and "@" in self.vpa else None
        self.legal_form = legal_form(self.name_norm)
        self.name_sorted = sorted_key(self.name_core)
        self.initial_key = initial_key(self.name_core)


@dataclass
class PairDecision:
    a: str
    b: str
    band: str                          # auto | review | separate
    method: str                        # rule:pan | rule:gstin | rule:vpa | rule:account | splink
    probability: Optional[float] = None
    reason: str = ""
    features: dict = field(default_factory=dict)


def _mask(value: Optional[str]) -> Optional[str]:
    if not value:
        return value
    return ("X" * max(0, len(value) - 4)) + value[-4:]


def _rule_pairs(records: list[Record]) -> list[PairDecision]:
    out, seen = [], set()
    for scheme in ("pan", "gstin", "vpa", "account"):
        groups: dict[str, list[Record]] = {}
        for r in records:
            v = getattr(r, scheme)
            if v:
                groups.setdefault(v, []).append(r)
        for value, rs in groups.items():
            for i in range(len(rs)):
                for j in range(i + 1, len(rs)):
                    a, b = rs[i], rs[j]
                    key = tuple(sorted((a.id, b.id)))
                    if key in seen:
                        continue
                    seen.add(key)
                    conflict = a.pan and b.pan and a.pan != b.pan
                    out.append(PairDecision(
                        key[0], key[1], "review" if conflict else "auto", f"rule:{scheme}", None,
                        "same identifier but different PANs" if conflict else f"same {scheme.upper()}",
                        {"identifier": scheme, "value": _mask(value),
                         **({"conflict": "pan", "pans": [_mask(a.pan), _mask(b.pan)]} if conflict else {})}))
    return out


def _splink_settings():
    import splink.comparison_level_library as cll
    import splink.comparison_library as cl
    from splink import SettingsCreator, block_on

    def conf(comp, key):
        p = _PRIORS[key]
        return comp.configure(m_probabilities=p["m"], u_probabilities=p["u"])

    prefix = ("(length(name_core_l) >= 10 AND starts_with(name_core_r, name_core_l)) OR "
              "(length(name_core_r) >= 10 AND starts_with(name_core_l, name_core_r))")
    name = cl.CustomComparison([
        cll.NullLevel("name_core"),
        cll.ExactMatchLevel("name_core"),
        cll.ExactMatchLevel("name_sorted"),
        cll.CustomLevel(prefix, label_for_charts="truncated prefix"),
        cll.JaroWinklerLevel("name_core", 0.95),
        cll.ExactMatchLevel("initial_key"),
        cll.JaroWinklerLevel("name_core", 0.88),
        cll.ElseLevel(),
    ], output_column_name="name")
    return SettingsCreator(
        link_type="dedupe_only",
        probability_two_random_records_match=PRIOR_MATCH,
        comparisons=[
            conf(name, "name"),
            conf(cl.ExactMatch("pan"), "pan"),
            conf(cl.ExactMatch("vpa"), "vpa"),
            conf(cl.ExactMatch("vpa_local"), "vpa_local"),
            conf(cl.ExactMatch("account"), "account"),
        ],
        blocking_rules_to_generate_predictions=[
            block_on("first_token"), block_on("last_token"), block_on("vpa_local"), block_on("pan"),
            block_on("account"),
        ],
        retain_intermediate_calculation_columns=True,
    )


def splink_scores(records: list[Record]) -> dict[tuple, dict]:
    """Pairwise Splink match probabilities with per-comparison levels and match weights."""
    if len(records) < 2:
        return {}
    import pyarrow as pa
    from splink import DuckDBAPI, Linker
    rows = [{"unique_id": r.id, "name_core": r.name_core or None, "name_sorted": r.name_sorted or None,
             "initial_key": r.initial_key, "first_token": (r.name_core.split() or [None])[0],
             "last_token": (r.name_core.split() or [None])[-1], "pan": r.pan, "vpa": r.vpa,
             "vpa_local": r.vpa_local, "account": r.account} for r in records]
    db = DuckDBAPI()
    sdf = db.register(pa.Table.from_pylist(rows))
    linker = Linker(sdf, _splink_settings(), log_level=40)
    pred = linker.inference.predict(threshold_match_probability=0.001).as_record_list()
    out = {}
    for p in pred:
        key = tuple(sorted((str(p["unique_id_l"]), str(p["unique_id_r"]))))
        levels = {c: p.get(f"gamma_{c}") for c in _PRIORS}
        weights = {c: round(p[f"mw_{c}"], 2) for c in _PRIORS if p.get(f"mw_{c}") is not None}
        out[key] = {"probability": float(p["match_probability"]), "match_weight": round(p["match_weight"], 2),
                    "levels": {c: _level_label(c, g) for c, g in levels.items()}, "weights": weights}
    return out


def _level_label(comparison: str, gamma) -> str:
    if gamma is None or gamma == -1:
        return "missing"
    labels = _PRIORS[comparison]["levels"]
    # Splink numbers non-null levels from the most similar (highest gamma) down to 0
    idx = len(labels) - 1 - int(gamma)
    return labels[idx] if 0 <= idx < len(labels) else str(gamma)


def resolve(records: list[Record], auto_threshold: float = AUTO_THRESHOLD,
            review_threshold: float = REVIEW_THRESHOLD,
            person_exact_auto: bool = False) -> tuple[list[PairDecision], list[list[str]]]:
    """Return (pair decisions, clusters). Clusters are connected components of auto links that never join two
    different PANs; any link that would is demoted to review."""
    by_id = {r.id: r for r in records}
    forms_by_core: dict[str, set] = {}
    for r in records:
        if r.legal_form:
            forms_by_core.setdefault(r.name_core, set()).add(r.legal_form)
    decisions = {(d.a, d.b): d for d in _rule_pairs(records)}
    for key, s in splink_scores(records).items():
        if key in decisions:
            decisions[key].features["splink"] = s
            continue
        a, b = by_id[key[0]], by_id[key[1]]
        p = s["probability"]
        conflict = bool(a.pan and b.pan and a.pan != b.pan)
        corroborated = any(s["levels"][c] == "exact" for c in STRONG)
        name_level = s["levels"]["name"]
        forms_ok = not (a.legal_form and b.legal_form and a.legal_form != b.legal_form)
        # a name printed with two legal forms in one case is likely a group (e.g. "X Ltd" and "X LLP"): only an
        # explicit, identical form links automatically
        ambiguous = len(forms_by_core.get(a.name_core, ())) > 1 and not (a.legal_form and a.legal_form == b.legal_form)
        exact_org = (a.kind == b.kind == "org" and name_level in ("exact", "same tokens") and forms_ok
                     and not ambiguous)
        if conflict:
            band = "review" if name_level in ("exact", "same tokens", "truncated prefix", "jw>=0.95") else "separate"
            reason = "similar names but different PANs"
        elif corroborated and p >= auto_threshold:
            band, reason = "auto", "name match corroborated by an identifier"
        elif exact_org:
            band, reason = "auto", "same organisation name and compatible legal form"
        elif person_exact_auto and a.kind == b.kind == "person" and name_level in ("exact", "same tokens"):
            band, reason = "auto", "same personal name (policy: person_exact_auto)"
        elif not forms_ok and name_level in ("exact", "same tokens"):
            band, reason = "separate", "same name, different legal forms (separate legal entities)"
        elif p >= review_threshold or (a.name_core == b.name_core and a.name_core):
            band = "review"
            reason = ("name used by more than one legal form in this case" if ambiguous and a.kind == "org"
                      else "same name, no shared identifier" if name_level in ("exact", "same tokens")
                      else "probable match" if corroborated else "similar name, no shared identifier")
        else:
            band, reason = "separate", "low match probability"
        if band != "separate":
            decisions[key] = PairDecision(key[0], key[1], band, "splink", p, reason, {"splink": s})

    # union-find over auto links, strongest first, never joining two different PANs
    parent = {r.id: r.id for r in records}
    pans = {r.id: ({r.pan} if r.pan else set()) for r in records}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    order = sorted((d for d in decisions.values() if d.band == "auto"),
                   key=lambda d: (not d.method.startswith("rule"), -(d.probability or 1.0)))
    for d in order:
        ra, rb = find(d.a), find(d.b)
        if ra == rb:
            continue
        if len(pans[ra] | pans[rb]) > 1:
            d.band, d.reason = "review", "would join records with different PANs"
            d.features["conflict"] = "pan_cluster"
            continue
        parent[rb] = ra
        pans[ra] |= pans.pop(rb)
    clusters: dict[str, list[str]] = {}
    for r in records:
        clusters.setdefault(find(r.id), []).append(r.id)
    return list(decisions.values()), sorted(clusters.values(), key=lambda c: (-len(c), c))

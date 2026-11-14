"""Deterministic detectors over one case's bank transactions (R7; INVESTIGATION_ENGINE §5, MARKET_SELECTION §7.2).

Each detector is a pure function `detect(case, params) -> list[Lead]`: the same transactions and parameters always
give the same leads. A lead names the pattern in neutral words, lists every transaction behind it (with its page
region) and the ordinary explanations a reviewer should rule out first. Nothing here labels fraud or intent.

| id               | pattern (lead for review)                                                    | source of the idea |
|------------------|-------------------------------------------------------------------------------|--------------------|
| end_use          | a loan disbursement followed, within N days, by outflows to group or related parties | RBI wilful-defaulter direction 2024 (diversion to group companies); D1 |
| round_trip       | money leaves an account and returns to the same party through 1–3 other parties | D2 round-tripping |
| structuring      | cash deposits clustered just below a reporting threshold, or split within a day | threshold avoidance (Pack 2) |
| pass_through     | repeated credits passed on, almost the same amount, to someone else within 2 days | layering |
| duplicate_payment| the same amount paid to the same party twice within a few days | duplicate payments (Pack 2) |
| window_dressing  | a large credit in the last days of a quarter paid back to the same party soon after | D6 period-end anomalies |

Thresholds are parameters, stored with every run. Defaults for `structuring`: ₹50,000 (PAN needed for a cash
deposit above this in a day, Income-tax Rule 114B; checked against secondary summaries only) and ₹10,00,000 (cash
transaction reports under PML Rules rule 3, per FIU-IND and RBI material). Verify both against the current rules
before relying on them.
"""
from __future__ import annotations

import hashlib
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Callable, Optional

VERSION = "r7.1"

# narrations that explain a movement as ordinary banking, not a transfer between parties
_SWEEP = re.compile(r"\b(sweep|auto\s*sweep|f\.?d\.?|fixed\s*deposit|term\s*deposit|t\.?d\.?\s*(open|clos|matur)|"
                    r"reverse\s*sweep|flexi)\b", re.I)
_REVERSAL = re.compile(r"\b(rev(ersal)?|rvsl|refund|return(ed)?|rtn|chargeback)\b", re.I)
_STANDING = re.compile(r"\b(nach|ecs|emi|si\b|standing\s*instr|autopay|mandate)", re.I)
_DISBURSEMENT = re.compile(r"\b(disb(ursement|ursal|\.)?|loan\s*(a/?c|account)?\s*(cr|credit)|term\s*loan|"
                           r"tl\s*disb|drawdown|draw\s*down)\b", re.I)


@dataclass(frozen=True)
class Txn:
    key: str                         # stable across re-analysis: source document hash + row
    document_id: int
    account: str                     # the statement account
    holder: Optional[str]            # party key of the account holder ("p:12"), if resolved
    date: date
    amount_minor: int                # always positive
    direction: str                   # debit | credit
    counterparty: Optional[str]      # party key of the other side, if resolved
    counterparty_name: Optional[str]
    channel: str                     # CASH | UPI | NEFT | RTGS | IMPS | CHQ | NACH | OTHER
    narration: str
    page: Optional[int] = None
    seq: Optional[int] = None
    box: Optional[tuple] = None
    claim_id: Optional[int] = None   # the transfer claim built from this row, when there is one
    txn_id: Optional[int] = None


@dataclass
class CaseData:
    txns: list[Txn]
    names: dict[str, str] = field(default_factory=dict)        # party key -> display name
    related: set = field(default_factory=set)                  # party keys tagged "related" by an analyst
    group: set = field(default_factory=set)                    # holders of the case's statement accounts


@dataclass
class Lead:
    detector: str
    key: str                         # stable identity of the pattern (detector + its transactions)
    title: str
    summary: str
    amount_minor: int
    txns: list[Txn]
    details: dict
    rule_out: list[str]              # ordinary explanations to check first


DEFAULTS: dict[str, dict] = {
    "end_use": {"window_days": 30, "min_disbursement_minor": 10_00_000_00, "min_share": 0.25,
                "min_amount_minor": 5_00_000_00},
    "round_trip": {"window_days": 30, "max_hops": 4, "min_ratio": 0.8, "max_ratio": 1.05,
                   "min_amount_minor": 1_00_000_00, "two_hop_min_amount_minor": 5_00_000_00,
                   "two_hop_window_days": 15, "two_hop_min_ratio": 0.9, "two_hop_max_ratio": 1.0,
                   "hop_min_ratio": 0.85, "hop_max_ratio": 1.05, "max_gap_days": 10},
    "structuring": {"thresholds_minor": [50_000_00, 10_00_000_00], "band": 0.10, "min_count": 3,
                    "window_days": 30, "max_p_value": 0.01, "split_min_days": 2},
    "pass_through": {"max_lag_days": 2, "tolerance": 0.02, "min_amount_minor": 1_00_000_00, "min_events": 3,
                     "window_days": 60},
    "duplicate_payment": {"window_days": 7, "min_amount_minor": 10_000_00},
    "window_dressing": {"last_days": 5, "return_days": 15, "min_amount_minor": 5_00_000_00, "min_ratio": 0.9},
}

_TITLES = {
    "end_use": "Loan disbursement followed by payments to group or related parties",
    "round_trip": "Money returned to the same party through a circular path",
    "structuring": "Cash deposits clustered just below a reporting threshold",
    "pass_through": "Credits passed on almost unchanged within two days",
    "duplicate_payment": "Same amount paid to the same party twice within days",
    "window_dressing": "Quarter-end credit paid back to the same party soon after",
}

RULE_OUT = {
    "end_use": ["the sanction letter allows payments to these parties (e.g. a group supplier or a takeover of debt)",
                "the payment settles a genuine invoice for goods or services",
                "the 'group' account is the borrower's own account (an internal transfer)"],
    "round_trip": ["a refund or a cancelled order", "a short-term loan given and repaid",
                   "a sweep or fixed-deposit movement not marked as such in the narration"],
    "structuring": ["daily cash takings of a retail business", "deposits by different branches or people",
                    "a business whose sales are naturally just below the threshold"],
    "pass_through": ["a trading business that buys and sells at near cost", "an escrow or collection account",
                     "a payment agent acting on documented instructions"],
    "duplicate_payment": ["two separate invoices for the same amount", "an instalment schedule",
                          "a payment that failed and was re-sent (check for a reversal)"],
    "window_dressing": ["an advance returned because an order was cancelled", "a genuine quarter-end collection "
                        "and a later, unrelated purchase from the same party", "an inter-company settlement cycle"],
}


def _key(detector: str, txns: list[Txn]) -> str:
    return hashlib.sha256((detector + "|" + "|".join(sorted(t.key for t in txns))).encode()).hexdigest()[:40]


def _inr(minor: int) -> str:
    rupees = minor // 100
    s = str(rupees)
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        head = ",".join([head[max(0, i - 2):i] for i in range(len(head), 0, -2)][::-1])
        s = head + "," + tail
    return f"₹{s}"


def _name(case: CaseData, party: Optional[str]) -> str:
    return case.names.get(party, party or "an unidentified party") if party else "an unidentified party"


def _lead(detector: str, txns: list[Txn], summary: str, amount: int, details: dict) -> Lead:
    return Lead(detector, _key(detector, txns), _TITLES[detector], summary, amount,
                sorted(txns, key=lambda t: (t.date, t.key)), details, RULE_OUT[detector])


# --------------------------------------------------------------------------------------------- end_use (D1)

def end_use(case: CaseData, p: dict) -> list[Lead]:
    """For each disbursement-like credit, the payments from the same account to group or related parties in the next
    N days, up to the disbursed amount. A payment counts only against the latest disbursement before it (stated in
    every lead). A lead when that total reaches `min_share` of the disbursement and `min_amount_minor`."""
    out = []
    by_account: dict[str, list[Txn]] = defaultdict(list)
    for t in case.txns:
        by_account[t.account].append(t)
    for acct, txns in by_account.items():
        txns.sort(key=lambda t: (t.date, t.seq or 0))
        disb = [t for t in txns if t.direction == "credit" and t.amount_minor >= p["min_disbursement_minor"]
                and _DISBURSEMENT.search(t.narration or "")]
        for i, d in enumerate(disb):
            nxt = disb[i + 1] if i + 1 < len(disb) else None
            end = d.date + timedelta(days=p["window_days"])
            linked = []
            for t in txns:
                if t.direction != "debit" or (t.date, t.seq or 0) <= (d.date, d.seq or 0) or t.date > end:
                    continue
                if nxt is not None and (t.date, t.seq or 0) > (nxt.date, nxt.seq or 0):
                    continue  # belongs to the next disbursement
                if t.counterparty and t.counterparty != d.holder and \
                        (t.counterparty in case.related or t.counterparty in case.group):
                    linked.append(t)
            to_linked = min(d.amount_minor, sum(t.amount_minor for t in linked))
            if to_linked >= p["min_amount_minor"] and to_linked >= p["min_share"] * d.amount_minor:
                parties = sorted({t.counterparty for t in linked})
                summary = (f"{_inr(d.amount_minor)} credited on {d.date.isoformat()} as a loan disbursement; within "
                           f"{p['window_days']} days {_inr(to_linked)} ({to_linked / d.amount_minor:.0%}) went to "
                           f"{', '.join(_name(case, x) for x in parties)}, marked as group or related.")
                out.append(_lead("end_use", [d] + linked, summary, to_linked, {
                    "disbursement": d.key, "attribution": "payments to group or related parties within the window "
                    "after the disbursement and before the next one, up to the disbursed amount",
                    "to_group_or_related_minor": to_linked,
                    "parties": [{"party": x, "name": _name(case, x), "related": x in case.related,
                                 "group_account_holder": x in case.group} for x in parties]}))
    return out


# ------------------------------------------------------------------------------------------- round_trip (D2)

@dataclass(frozen=True)
class _Edge:
    src: str
    dst: str
    amount_minor: int
    date: date
    txns: tuple


def _edges(case: CaseData) -> list[_Edge]:
    """Transfers between parties. The same transfer seen in both parties' statements becomes one edge."""
    raw = []
    for t in case.txns:
        if not t.holder or not t.counterparty or t.holder == t.counterparty:
            continue
        if _SWEEP.search(t.narration or "") or _REVERSAL.search(t.narration or ""):
            continue
        src, dst = (t.holder, t.counterparty) if t.direction == "debit" else (t.counterparty, t.holder)
        raw.append((src, dst, t))
    raw.sort(key=lambda x: (x[2].date, x[2].key))
    merged: list[list] = []
    for src, dst, t in raw:
        for m in merged:
            if m[0] == src and m[1] == dst and m[2] == t.amount_minor and abs((m[3] - t.date).days) <= 3 \
                    and all(x.account != t.account for x in m[4]):
                m[4].append(t)
                break
        else:
            merged.append([src, dst, t.amount_minor, t.date, [t]])
    return [_Edge(s, d, a, dt, tuple(ts)) for s, d, a, dt, ts in merged]


def round_trip(case: CaseData, p: dict) -> list[Lead]:
    edges = _edges(case)
    out_by: dict[str, list[_Edge]] = defaultdict(list)
    for e in edges:
        out_by[e.src].append(e)
    seen, out = set(), []

    def search(path: list[_Edge]):
        first, last = path[0], path[-1]
        two_hop = len(path) == 1
        window = p["two_hop_window_days"] if two_hop else p["window_days"]
        for e in out_by.get(last.dst, []):
            if e.date < last.date or e.date > first.date + timedelta(days=p["window_days"]):
                continue
            # money passed on through intermediaries keeps roughly its size and moves on quickly
            if not two_hop and ((e.date - last.date).days > p["max_gap_days"] or not (
                    p["hop_min_ratio"] * last.amount_minor <= e.amount_minor <= p["hop_max_ratio"] * last.amount_minor)):
                continue
            closes = e.dst == first.src
            lo, hi = (p["two_hop_min_ratio"], p["two_hop_max_ratio"]) if (two_hop and closes) else \
                (p["min_ratio"], p["max_ratio"])
            if not (lo * first.amount_minor <= e.amount_minor <= hi * first.amount_minor):
                continue
            if e in path:
                continue
            nodes = [x.src for x in path]
            if e.dst == first.src:
                cycle = path + [e]
                if len(cycle) == 2:
                    if first.amount_minor < p["two_hop_min_amount_minor"] or (e.date - first.date).days > window:
                        continue
                elif first.amount_minor < p["min_amount_minor"]:
                    continue
                if len({x.src for x in cycle}) < 2:
                    continue
                txns = [t for x in cycle for t in x.txns]
                k = _key("round_trip", txns)
                if k in seen:
                    continue
                seen.add(k)
                hops = " → ".join([_name(case, cycle[0].src)] + [_name(case, x.dst) for x in cycle])
                returned = cycle[-1].amount_minor
                summary = (f"{_inr(first.amount_minor)} left {_name(case, first.src)} on {first.date.isoformat()} and "
                           f"{_inr(returned)} came back on {cycle[-1].date.isoformat()} via {hops} "
                           f"({len(cycle)} transfers, {(cycle[-1].date - first.date).days} days).")
                out.append(_lead("round_trip", txns, summary, first.amount_minor, {
                    "path": [{"from": x.src, "from_name": _name(case, x.src), "to": x.dst, "to_name": _name(case, x.dst),
                              "amount_minor": x.amount_minor, "date": x.date.isoformat(),
                              "seen_in_statements": len(x.txns)} for x in cycle],
                    "returned_share": round(returned / first.amount_minor, 4),
                    "days": (cycle[-1].date - first.date).days}))
            elif len(path) + 1 < p["max_hops"] and e.dst not in nodes:
                search(path + [e])

    for e in sorted(edges, key=lambda x: (x.date, x.src)):
        search([e])
    # keep the shortest cycle when one cycle's transfers contain another's
    out.sort(key=lambda lead: len(lead.txns))
    kept: list[Lead] = []
    for lead in out:
        ks = {t.key for t in lead.txns}
        if not any({t.key for t in k.txns} <= ks for k in kept):
            kept.append(lead)
    return kept


# ------------------------------------------------------------------------------------------- structuring (T1)

def structuring(case: CaseData, p: dict) -> list[Lead]:
    out = []
    by_account: dict[str, list[Txn]] = defaultdict(list)
    for t in case.txns:
        if t.direction == "credit" and t.channel == "CASH":
            by_account[t.account].append(t)
    for acct, deps in by_account.items():
        deps.sort(key=lambda t: (t.date, t.seq or 0))
        for thr in p["thresholds_minor"]:
            lo = int(thr * (1 - p["band"]))
            band = [t for t in deps if lo <= t.amount_minor <= thr]
            # (a) clustering just below the threshold, compared with deposits in the wider half below it
            best: list[Txn] = []
            for i, t in enumerate(band):
                win = [x for x in band[i:] if x.date <= t.date + timedelta(days=p["window_days"])]
                if len(win) > len(best):
                    best = win
            if len(best) >= p["min_count"]:
                start, end = best[0].date, best[-1].date
                wider = [x for x in deps if thr // 2 <= x.amount_minor <= thr and start <= x.date <= end]
                share = len(best) / max(1, len(wider))
                # under an even spread of amounts between half the threshold and the threshold, the band holds
                # band / 0.5 of them; how unlikely is a cluster this large?
                p_value = _binom_tail(len(best), len(wider), p["band"] / 0.5)
                if p_value <= p["max_p_value"]:
                    summary = (f"{len(best)} cash deposits between {_inr(lo)} and {_inr(thr)} from {start.isoformat()} "
                               f"to {end.isoformat()}: {share:.0%} of deposits between {_inr(thr // 2)} and {_inr(thr)} "
                               f"in that period sit in the top {p['band']:.0%} just below {_inr(thr)}.")
                    out.append(_lead("structuring", best, summary, sum(x.amount_minor for x in best), {
                        "pattern": "cluster_below_threshold", "threshold_minor": thr, "band": p["band"],
                        "count": len(best), "cluster_share": round(share, 3), "p_value": float(f"{p_value:.3g}"),
                        "test": "binomial tail against an even spread between half the threshold and the threshold"}))
            # (b) the same day split into several deposits each below the threshold that together exceed it
            by_day: dict[date, list[Txn]] = defaultdict(list)
            for t in deps:
                if thr // 2 <= t.amount_minor < thr:
                    by_day[t.date].append(t)
            split_days = sorted(d for d, ts in by_day.items() if len(ts) >= 2 and sum(x.amount_minor for x in ts) > thr)
            if len(split_days) >= p["split_min_days"]:
                ts = [t for d in split_days for t in by_day[d]]
                summary = (f"On {len(split_days)} days cash was deposited in two or more amounts each below "
                           f"{_inr(thr)} that together exceed it ({', '.join(d.isoformat() for d in split_days[:5])}"
                           f"{'…' if len(split_days) > 5 else ''}).")
                out.append(_lead("structuring", ts, summary, sum(x.amount_minor for x in ts), {
                    "pattern": "same_day_split", "threshold_minor": thr, "days": [d.isoformat() for d in split_days]}))
    return out


# ------------------------------------------------------------------------------------------ pass_through (T2)

def pass_through(case: CaseData, p: dict) -> list[Lead]:
    out = []
    by_account: dict[str, list[Txn]] = defaultdict(list)
    for t in case.txns:
        by_account[t.account].append(t)
    for acct, txns in by_account.items():
        txns.sort(key=lambda t: (t.date, t.seq or 0))
        used, events = set(), []
        for c in txns:
            if c.direction != "credit" or c.amount_minor < p["min_amount_minor"] or c.channel == "CASH":
                continue
            for d in txns:
                if d.direction != "debit" or d.key in used or d.date < c.date or \
                        (d.date - c.date).days > p["max_lag_days"] or (d.date, d.seq or 0) <= (c.date, c.seq or 0):
                    continue
                if abs(d.amount_minor - c.amount_minor) > p["tolerance"] * c.amount_minor:
                    continue
                if d.counterparty and c.counterparty and d.counterparty == c.counterparty:
                    continue  # paid back to the payer: a reversal or a refund, not a pass-through
                if _REVERSAL.search(d.narration or "") or _SWEEP.search(d.narration or ""):
                    continue
                used.add(d.key)
                events.append((c, d))
                break
        events.sort(key=lambda e: e[0].date)
        best: list = []
        for i, (c, _) in enumerate(events):
            win = [e for e in events[i:] if e[0].date <= c.date + timedelta(days=p["window_days"])]
            if len(win) > len(best):
                best = win
        if len(best) >= p["min_events"]:
            txns_ = [t for e in best for t in e]
            total = sum(c.amount_minor for c, _ in best)
            summary = (f"{len(best)} times between {best[0][0].date.isoformat()} and {best[-1][0].date.isoformat()} a "
                       f"credit was paid on to someone else within {p['max_lag_days']} days at almost the same amount "
                       f"(total {_inr(total)}).")
            out.append(_lead("pass_through", txns_, summary, total, {
                "events": [{"in": c.key, "in_from": _name(case, c.counterparty), "out": d.key,
                            "out_to": _name(case, d.counterparty), "amount_in_minor": c.amount_minor,
                            "amount_out_minor": d.amount_minor, "lag_days": (d.date - c.date).days} for c, d in best]}))
    return out


# ------------------------------------------------------------------------------------- duplicate_payment (T3)

def duplicate_payment(case: CaseData, p: dict) -> list[Lead]:
    out = []
    groups: dict[tuple, list[Txn]] = defaultdict(list)
    for t in case.txns:
        if t.direction == "debit" and t.counterparty and t.amount_minor >= p["min_amount_minor"] \
                and not _STANDING.search(t.narration or ""):
            groups[(t.account, t.counterparty, t.amount_minor)].append(t)
    for (acct, cp, amount), ts in groups.items():
        ts.sort(key=lambda t: (t.date, t.seq or 0))
        for a, b in zip(ts, ts[1:]):
            if (b.date - a.date).days <= p["window_days"]:
                summary = (f"{_inr(amount)} paid to {_name(case, cp)} on {a.date.isoformat()} and again on "
                           f"{b.date.isoformat()} ({(b.date - a.date).days} days apart).")
                out.append(_lead("duplicate_payment", [a, b], summary, amount, {
                    "counterparty": cp, "days_apart": (b.date - a.date).days}))
    return out


# ------------------------------------------------------------------------------------- window_dressing (D6)

def _binom_tail(k: int, n: int, p0: float) -> float:
    """P(X >= k) for X ~ Binomial(n, p0)."""
    from math import comb
    return sum(comb(n, i) * p0 ** i * (1 - p0) ** (n - i) for i in range(k, n + 1))


def _quarter_end(d: date) -> date:
    q_month = ((d.month - 1) // 3 + 1) * 3
    nxt = date(d.year + (q_month == 12), 1 if q_month == 12 else q_month + 1, 1)
    return nxt - timedelta(days=1)


def window_dressing(case: CaseData, p: dict) -> list[Lead]:
    out = []
    by_account: dict[str, list[Txn]] = defaultdict(list)
    for t in case.txns:
        by_account[t.account].append(t)
    for acct, txns in by_account.items():
        for c in txns:
            if c.direction != "credit" or not c.counterparty or c.amount_minor < p["min_amount_minor"]:
                continue
            qe = _quarter_end(c.date)
            if (qe - c.date).days >= p["last_days"]:
                continue
            for d in txns:
                if d.direction == "debit" and d.counterparty == c.counterparty and qe < d.date <= \
                        qe + timedelta(days=p["return_days"]) and d.amount_minor >= p["min_ratio"] * c.amount_minor \
                        and d.amount_minor <= c.amount_minor * 1.1:
                    summary = (f"{_inr(c.amount_minor)} received from {_name(case, c.counterparty)} on "
                               f"{c.date.isoformat()}, {(qe - c.date).days} days before the quarter end "
                               f"({qe.isoformat()}), and {_inr(d.amount_minor)} paid back to them on "
                               f"{d.date.isoformat()}.")
                    out.append(_lead("window_dressing", [c, d], summary, c.amount_minor, {
                        "quarter_end": qe.isoformat(), "counterparty": c.counterparty,
                        "returned_share": round(d.amount_minor / c.amount_minor, 4)}))
                    break
    return out


DETECTORS: dict[str, Callable[[CaseData, dict], list[Lead]]] = {
    "end_use": end_use, "round_trip": round_trip, "structuring": structuring, "pass_through": pass_through,
    "duplicate_payment": duplicate_payment, "window_dressing": window_dressing,
}

DESCRIPTIONS = {
    "end_use": "Loan disbursement followed within N days by payments to parties marked as related or to holders of "
               "other accounts in the case (RBI wilful-defaulter direction, 2024: moving loan funds to group "
               "companies is diversion).",
    "round_trip": "Money that leaves a party and returns to it through one to three other parties within N days, at "
                  "80–105% of the amount. Sweeps, fixed deposits, reversals and refunds are excluded.",
    "structuring": "Cash deposits clustered just below a threshold, or split within a day to stay below it.",
    "pass_through": "Repeated credits passed on to a different party within two days at almost the same amount.",
    "duplicate_payment": "The same amount paid to the same party twice within a few days (standing instructions and "
                         "EMIs excluded).",
    "window_dressing": "A large credit in the last days of a quarter paid back to the same party soon after the "
                       "quarter end.",
}


def run_all(case: CaseData, params: Optional[dict] = None, only: Optional[list[str]] = None) -> list[Lead]:
    params = {k: {**v, **((params or {}).get(k) or {})} for k, v in DEFAULTS.items()}
    leads = []
    for name, fn in DETECTORS.items():
        if only and name not in only:
            continue
        leads += fn(case, params[name])
    return leads

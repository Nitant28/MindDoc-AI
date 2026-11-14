"""FB-Synth v0: seeded cases for the R7 detectors (H_BENCHMARK_STRATEGY "FB").

Each case is one borrower group: the borrower's account, a group company's account and sometimes an intermediary's
account, with ordinary business activity (customer receipts, supplier payments, salaries, EMIs, charges, cash takings)
and, planted in it, **schemes** (patterns a detector should report) and **benign look-alikes** (ordinary activity that
resembles a scheme and should not be reported). Ground truth: the transaction keys of every instance.

Splits: `dev` (seeds 0–39) for tuning; `test` (seeds 5000–5039) held out, with different party names, amounts, lags
and one variant per scheme family (e.g. round trips with fees, structuring nearer the threshold). Same author as the
detectors, so this is not independent; it measures whether the detectors do what they claim on the planted patterns
and how often ordinary look-alikes trip them.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import date, timedelta

from app.discovery.detectors import CaseData, Txn

VERSION = "fb-synth-v0"

POOLS = {
    "dev": {"subject": ["Sahyadri Agro Pvt Ltd", "Kaveri Textiles Ltd", "Narmada Steels Pvt Ltd"],
            "group": ["Sahyadri Holdings Pvt Ltd", "Kaveri Exports LLP", "Narmada Infra Pvt Ltd"],
            "related": ["Prakash Mehta", "Sunita Rao", "Vikram Joshi"],
            "people": ["Anil Kumar", "Rekha Shah", "Deepak Nair", "Meera Iyer", "Rahul Verma", "Pooja Das"],
            "firms": ["Orion Traders", "Zenith Polymers", "Apex Logistics", "Lotus Chemicals", "Vertex Metals",
                      "Pioneer Packaging", "Sterling Foods", "Crescent Agencies"]},
    "test": {"subject": ["Godavari Mills Pvt Ltd", "Tapti Ceramics Ltd", "Brahmaputra Tea Co Ltd"],
             "group": ["Godavari Ventures Pvt Ltd", "Tapti Realty LLP", "Brahmaputra Estates Pvt Ltd"],
             "related": ["Harish Kulkarni", "Lata Menon", "Sameer Bhatt"],
             "people": ["Kiran Patil", "Neha Gupta", "Arjun Reddy", "Divya Pillai", "Manoj Sinha", "Ritu Bose"],
             "firms": ["Meridian Supplies", "Northstar Fabrics", "Coastal Freight", "Saffron Dyes", "Granite Alloys",
                       "Harbor Cartons", "Monsoon Agro", "Summit Distributors"]},
}


@dataclass
class Instance:
    kind: str           # scheme | benign | (background is not an instance)
    family: str         # e.g. round_trip / round_trip_fee / refund
    detector: str       # the detector that should (scheme) or must not (benign) report it
    keys: list = field(default_factory=list)


class _Builder:
    def __init__(self, rng: random.Random, split: str, case_no: int):
        self.rng, self.split, self.case_no = rng, split, case_no
        self.txns: list[Txn] = []
        self.n = 0
        self.names: dict[str, str] = {}

    def party(self, key: str, name: str) -> str:
        self.names[key] = name
        return key

    def add(self, account: str, holder: str, d: date, amount_minor: int, direction: str, cp: str | None,
            channel: str, narration: str) -> Txn:
        self.n += 1
        t = Txn(key=f"{self.split}-{self.case_no}-{self.n}", document_id=hash(account) % 1000, account=account,
                holder=holder, date=d, amount_minor=int(amount_minor), direction=direction, counterparty=cp,
                counterparty_name=self.names.get(cp) if cp else None, channel=channel, narration=narration,
                page=1, seq=self.n)
        self.txns.append(t)
        return t

    def transfer(self, src_acct: str | None, src: str, dst_acct: str | None, dst: str, d: date, amount: int,
                 channel: str = "NEFT", note: str = "") -> list[Txn]:
        """One transfer, recorded in each side's statement that is part of the case."""
        out = []
        if src_acct:
            out.append(self.add(src_acct, src, d, amount, "debit", dst, channel,
                                f"{channel}/N{self.rng.randint(10**9, 10**10)}/{self.names[dst]}{('/' + note) if note else ''}"))
        if dst_acct:
            lag = d if channel != "CHQ" else d + timedelta(days=1)
            out.append(self.add(dst_acct, dst, lag, amount, "credit", src, channel,
                                f"{channel}/N{self.rng.randint(10**9, 10**10)}/{self.names[src]}{('/' + note) if note else ''}"))
        return out


def _rupees(rng: random.Random, lo: float, hi: float) -> int:
    """A random amount in rupees, returned in paise, rounded to whole rupees."""
    return int(rng.uniform(lo, hi)) * 100


def case(split: str, seed: int) -> tuple[CaseData, list[Instance]]:
    rng = random.Random(f"{VERSION}-{split}-{seed}")
    pool = POOLS[split]
    test = split == "test"
    b = _Builder(rng, split, seed)
    S = b.party("p:S", rng.choice(pool["subject"]))
    G = b.party("p:G", rng.choice(pool["group"]))
    R = b.party("p:R", rng.choice(pool["related"]))
    I1 = b.party("p:I1", rng.choice(pool["firms"]) + " (I1)")
    I2 = b.party("p:I2", rng.choice(pool["firms"]) + " (I2)")
    L = b.party("p:L", "Union Credit Bank (lender)")
    firms = [b.party(f"p:F{i}", f) for i, f in enumerate(pool["firms"])]
    people = [b.party(f"p:P{i}", n) for i, n in enumerate(pool["people"])]
    AS, AG, AI1 = "acct:S", "acct:G", "acct:I1"
    start = date(2024, 4, 1) if not test else date(2024, 7, 1)
    days = 180
    inst: list[Instance] = []

    def day(lo=0, hi=days - 1) -> date:
        return start + timedelta(days=rng.randint(lo, hi))

    # ------------------------------------------------------------------ background business activity
    for _ in range(rng.randint(90, 130)):
        f = rng.choice(firms)
        if rng.random() < 0.55:
            b.transfer(None, f, AS, S, day(), _rupees(rng, 20_000, 9_00_000), rng.choice(["NEFT", "RTGS", "IMPS", "UPI"]))
        else:
            b.transfer(AS, S, None, f, day(), _rupees(rng, 15_000, 7_00_000), rng.choice(["NEFT", "RTGS", "CHQ"]))
    for m in range(6):
        for p_ in people:
            b.transfer(AS, S, None, p_, start + timedelta(days=30 * m + 1), _rupees(rng, 25_000, 60_000), "NEFT",
                       "SALARY")
        b.add(AS, S, start + timedelta(days=30 * m + 5), 1_85_000_00, "debit", L, "NACH",
              f"NACH/UMRN{rng.randint(10**6, 10**7)}/{b.names[L]}/EMI")
        b.add(AS, S, start + timedelta(days=30 * m + 27), _rupees(rng, 100, 2_000), "debit", None, "OTHER",
              "SMS CHGS")
    for _ in range(rng.randint(30, 60)):
        f = rng.choice(firms)
        b.transfer(AG, G, None, f, day(), _rupees(rng, 10_000, 5_00_000), "NEFT")
        b.transfer(None, rng.choice(firms), AG, G, day(), _rupees(rng, 10_000, 5_00_000), "NEFT")

    # ------------------------------------------------------------------ schemes
    k = rng.randint(1, 2)
    for _ in range(k):  # end_use: disbursement, then payments to the group company or a related party
        d0 = day(0, days - 40)
        amt = _rupees(rng, 50_00_000, 2_00_00_000)
        disb = b.add(AS, S, d0, amt, "credit", L, "NEFT", f"NEFT/LN{rng.randint(10**6, 10**7)}/LOAN DISB/{b.names[L]}")
        keys = [disb.key]
        share = rng.uniform(0.35, 0.9) if not test else rng.uniform(0.28, 0.6)
        target = rng.choice([G, R])
        parts = rng.randint(1, 3)
        for j in range(parts):
            dd = d0 + timedelta(days=rng.randint(1, 20 if not test else 27))
            ts = b.transfer(AS, S, AG if target == G else None, target, dd, int(amt * share / parts) // 100 * 100,
                            "RTGS")
            keys += [t.key for t in ts]
        inst.append(Instance("scheme", "end_use", "end_use", keys))
    # round trip, two hops (out to an outside party and back)
    d0 = day(0, days - 20)
    amt = _rupees(rng, 6_00_000, 40_00_000)
    x = rng.choice(firms)
    back = int(amt * (rng.uniform(0.97, 1.0) if not test else rng.uniform(0.9, 0.97))) // 100 * 100  # test: fees
    keys = [t.key for t in b.transfer(AS, S, None, x, d0, amt, "RTGS")]
    keys += [t.key for t in b.transfer(None, x, AS, S, d0 + timedelta(days=rng.randint(2, 12)), back, "RTGS")]
    inst.append(Instance("scheme", "round_trip_2hop" + ("_fee" if test else ""), "round_trip", keys))
    # round trip through the group company and an intermediary whose statement is in the case
    d0 = day(0, days - 30)
    amt = _rupees(rng, 10_00_000, 80_00_000)
    keys = [t.key for t in b.transfer(AS, S, AG, G, d0, amt, "RTGS")]
    d1 = d0 + timedelta(days=rng.randint(1, 6))
    keys += [t.key for t in b.transfer(AG, G, AI1, I1, d1, int(amt * rng.uniform(0.95, 1.0)) // 100 * 100, "RTGS")]
    d2 = d1 + timedelta(days=rng.randint(1, 8))
    keys += [t.key for t in b.transfer(AI1, I1, AS, S, d2, int(amt * rng.uniform(0.9, 1.0)) // 100 * 100, "RTGS")]
    inst.append(Instance("scheme", "round_trip_3hop", "round_trip", keys))
    # structuring: deposits just below ₹50,000 (test: nearer the threshold), or same-day splits
    if rng.random() < 0.6:
        d0 = day(0, days - 25)
        keys = []
        for _ in range(rng.randint(4, 8)):
            lo, hi = (45_500, 49_900) if not test else (47_000, 49_990)
            keys.append(b.add(AS, S, d0 + timedelta(days=rng.randint(0, 20)), _rupees(rng, lo, hi), "credit", None,
                              "CASH", "CASH DEPOSIT BY SELF").key)
        inst.append(Instance("scheme", "structuring_cluster", "structuring", keys))
    else:
        keys = []
        for dd in rng.sample(range(0, days - 1), rng.randint(2, 4)):
            for _ in range(rng.randint(2, 3)):
                keys.append(b.add(AS, S, start + timedelta(days=dd), _rupees(rng, 30_000, 49_000), "credit", None,
                                  "CASH", "BY CASH").key)
        inst.append(Instance("scheme", "structuring_split", "structuring", keys))
    # pass-through on the group company's account
    d0 = day(0, days - 60)
    keys = []
    for _ in range(rng.randint(3, 6)):
        dd = d0 + timedelta(days=rng.randint(0, 50))
        amt = _rupees(rng, 2_00_000, 20_00_000)
        src, dst = rng.sample(firms, 2)
        keys += [t.key for t in b.transfer(None, src, AG, G, dd, amt, "NEFT")]
        out_amt = int(amt * rng.uniform(0.99, 1.0) if not test else amt * rng.uniform(0.985, 1.0)) // 100 * 100
        keys += [t.key for t in b.transfer(AG, G, None, dst, dd + timedelta(days=rng.randint(0, 2)), out_amt, "NEFT")]
    inst.append(Instance("scheme", "pass_through", "pass_through", keys))
    # duplicate payment
    f = rng.choice(firms)
    d0 = day(0, days - 10)
    amt = _rupees(rng, 50_000, 6_00_000)
    keys = [t.key for t in b.transfer(AS, S, None, f, d0, amt, "NEFT", "INV")]
    keys += [t.key for t in b.transfer(AS, S, None, f, d0 + timedelta(days=rng.randint(1, 6)), amt, "NEFT", "INV")]
    inst.append(Instance("scheme", "duplicate_payment", "duplicate_payment", keys))
    # window dressing at a quarter end inside the period
    qe = date(2024, 6, 30) if not test else date(2024, 9, 30)
    x = rng.choice(firms)
    amt = _rupees(rng, 10_00_000, 1_00_00_000)
    keys = [t.key for t in b.transfer(None, x, AS, S, qe - timedelta(days=rng.randint(0, 3)), amt, "RTGS")]
    keys += [t.key for t in b.transfer(AS, S, None, x, qe + timedelta(days=rng.randint(2, 12)),
                                       int(amt * rng.uniform(0.92, 1.0)) // 100 * 100, "RTGS")]
    inst.append(Instance("scheme", "window_dressing", "window_dressing", keys))

    # ------------------------------------------------------------------ benign look-alikes
    # a disbursement spent on suppliers
    d0 = day(0, days - 40)
    amt = _rupees(rng, 50_00_000, 1_50_00_000)
    keys = [b.add(AS, S, d0, amt, "credit", L, "NEFT", f"NEFT/LN{rng.randint(10**6, 10**7)}/LOAN DISB/{b.names[L]}").key]
    for _ in range(rng.randint(2, 4)):
        keys += [t.key for t in b.transfer(AS, S, None, rng.choice(firms), d0 + timedelta(days=rng.randint(1, 25)),
                                           int(amt * rng.uniform(0.1, 0.3)) // 100 * 100, "RTGS", "SUPPLY")]
    inst.append(Instance("benign", "disbursement_to_suppliers", "end_use", keys))
    # sweep to a fixed deposit and back (own account)
    d0 = day(0, days - 20)
    amt = _rupees(rng, 10_00_000, 50_00_000)
    keys = [b.add(AS, S, d0, amt, "debit", S, "OTHER", "SWEEP TO FD 4471").key,
            b.add(AS, S, d0 + timedelta(days=rng.randint(3, 15)), amt + _rupees(rng, 500, 5_000), "credit", S,
                  "OTHER", "FD CLOSURE PROCEEDS 4471").key]
    inst.append(Instance("benign", "sweep", "round_trip", keys))
    # refund from a supplier (the narration says so)
    f = rng.choice(firms)
    d0 = day(0, days - 15)
    amt = _rupees(rng, 1_00_000, 12_00_000)
    keys = [t.key for t in b.transfer(AS, S, None, f, d0, amt, "NEFT", "PO 77")]
    keys += [t.key for t in b.transfer(None, f, AS, S, d0 + timedelta(days=rng.randint(2, 10)), amt, "NEFT",
                                       "REFUND PO 77")]
    inst.append(Instance("benign", "refund", "round_trip", keys))
    # a short loan given and repaid after two months
    f = rng.choice(firms)
    d0 = day(0, days - 80)
    amt = _rupees(rng, 5_00_000, 20_00_000)
    keys = [t.key for t in b.transfer(AS, S, None, f, d0, amt, "RTGS")]
    keys += [t.key for t in b.transfer(None, f, AS, S, d0 + timedelta(days=rng.randint(45, 75)),
                                       int(amt * 1.02) // 100 * 100, "RTGS")]
    inst.append(Instance("benign", "loan_repaid", "round_trip", keys))
    # retail cash takings on the group company's account
    keys = []
    d0 = day(0, days - 60)
    for dd in range(0, 50):
        if rng.random() < 0.8:
            keys.append(b.add(AG, G, d0 + timedelta(days=dd), _rupees(rng, 5_000, 60_000), "credit", None, "CASH",
                              "CASH DEPOSIT").key)
    inst.append(Instance("benign", "cash_takings", "structuring", keys))
    # trading at a margin: receipt, then payment to a supplier a few days later
    keys = []
    d0 = day(0, days - 60)
    for _ in range(rng.randint(3, 6)):
        dd = d0 + timedelta(days=rng.randint(0, 50))
        amt = _rupees(rng, 2_00_000, 15_00_000)
        c, s = rng.sample(firms, 2)
        keys += [t.key for t in b.transfer(None, c, AS, S, dd, amt, "NEFT")]
        keys += [t.key for t in b.transfer(AS, S, None, s, dd + timedelta(days=rng.randint(1, 5)),
                                           int(amt * rng.uniform(0.82, 0.92)) // 100 * 100, "NEFT")]
    inst.append(Instance("benign", "trading_margin", "pass_through", keys))
    # the same amount to the same supplier, three weeks apart (two invoices)
    f = rng.choice(firms)
    d0 = day(0, days - 30)
    amt = _rupees(rng, 50_000, 3_00_000)
    keys = [t.key for t in b.transfer(AS, S, None, f, d0, amt, "NEFT", "INV A")]
    keys += [t.key for t in b.transfer(AS, S, None, f, d0 + timedelta(days=rng.randint(15, 28)), amt, "NEFT", "INV B")]
    inst.append(Instance("benign", "two_invoices", "duplicate_payment", keys))
    # a genuine quarter-end collection, later a smaller purchase from the same party
    x = rng.choice(firms)
    amt = _rupees(rng, 10_00_000, 60_00_000)
    keys = [t.key for t in b.transfer(None, x, AS, S, qe - timedelta(days=rng.randint(0, 3)), amt, "RTGS")]
    keys += [t.key for t in b.transfer(AS, S, None, x, qe + timedelta(days=rng.randint(3, 12)),
                                       int(amt * rng.uniform(0.2, 0.6)) // 100 * 100, "RTGS")]
    inst.append(Instance("benign", "quarter_end_collection", "window_dressing", keys))

    data = CaseData(txns=b.txns, names=b.names, related={R}, group={S, G, I1})
    return data, inst


def cases(split: str, n: int = 40) -> list[tuple[CaseData, list[Instance]]]:
    base = 0 if split == "dev" else 5000
    return [case(split, base + i) for i in range(n)]

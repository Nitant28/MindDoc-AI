"""HB-Synth v1: a seeded, generated claim set for the claim verifier (R6).

Why: HB v0 (cases.py) has 146 hand-written claims. Its test split was scored once, the bugs it revealed are known, so
it can no longer serve as a held-out test for fixes to those bugs. HB-Synth v1 is a fresh, larger set built before any
verifier v3 change (pre-registration: see README "HB-Synth v1").

What is held out in the test split:
  * name pools: companies, people, banks, cities, valuers and insurers never overlap with dev;
  * phrasing: every source template and every claim template has a dev wording and a different test wording;
  * document families: guarantee deeds, fund-flow notes and borrower correspondence appear only in test;
  * seeds: dev and test documents come from different seed strings.

Labels follow the annotation guideline in README.md: a claim is "supported" only if a careful analyst reading just
the passage would accept it (paraphrase, reformatting, unit conversion and simple arithmetic allowed; approximations
must be within 3% and say so). Every unsupported claim has exactly one injected error.

Limits (also in README): the same developer wrote these templates and the verifier; generated text is more regular
than real LLM answers; one domain (Indian lending), English, single-claim sentences against one passage.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Callable

S, U = "supported", "unsupported"
VERSION = "hb-synth-v1"

# ----------------------------------------------------------------------------------------------- name pools

POOLS = {
    "dev": dict(
        firms=["Shreeji", "Kaveri", "Sunrise", "Godavari", "Orbit", "Vaishnavi", "Kesar", "Prabhat", "Vardhman",
               "Saraswati", "Mahalaxmi", "Omkar", "Jyoti", "Shubham", "Vishwas", "Amrut"],
        banks=["Meridian Bank Ltd", "Coastal Union Bank", "Deccan Commercial Bank"],
        first=["Anil", "Rekha", "Suresh", "Kavita", "Manoj", "Priya", "Rajesh", "Sunita", "Vikas", "Asha"],
        last=["Mehta", "Shah", "Patil", "Iyer", "Kulkarni", "Desai", "Joshi", "Rao"],
        cities=["Thane", "Pune", "Surat", "Nashik", "Vapi", "Bhiwandi"],
        estates=["MIDC Tarapur", "GIDC Vapi", "MIDC Chakan"],
        insurers=["Sahyadri General Insurance", "Konkan General Insurance"],
        audit_firms=["Desai & Kulkarni", "Shah & Patil"],
    ),
    "test": dict(
        firms=["Narmada", "Tapti", "Vindhya", "Aravali", "Konark", "Malabar", "Nilgiri", "Hampi", "Chambal",
               "Sabari", "Teesta", "Kosi", "Pench", "Satpura", "Kanha", "Lohit"],
        banks=["Ganga Valley Bank", "Western Ghats Bank Ltd", "Indus Mercantile Bank"],
        first=["Farhan", "Lalitha", "Gurpreet", "Ananya", "Tenzin", "Dilip", "Meenal", "Joseph", "Harpreet", "Zoya"],
        last=["Bhattacharya", "Reddy", "Fernandes", "Chauhan", "Nair", "Siddiqui", "Dutta", "Menon"],
        cities=["Ludhiana", "Coimbatore", "Indore", "Guwahati", "Rajkot", "Jamshedpur"],
        estates=["SIPCOT Hosur", "RIICO Bhiwadi", "KIADB Peenya"],
        insurers=["Brahmaputra General Insurance", "Cauvery General Insurance"],
        audit_firms=["Reddy & Menon", "Dutta & Nair"],
    ),
}
SECTORS = ["Polymers", "Agro Foods", "Textiles", "Steel", "Pharma", "Logistics", "Cold Storage", "Chemicals",
           "Exports", "Infra", "Paper Mills", "Ceramics", "Engineering", "Packaging"]
FORMS = ["Pvt Ltd", "Pvt Ltd", "Ltd", "Private Limited"]
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December"]
NUM_WORDS = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight", 9: "nine",
             10: "ten", 12: "twelve", 15: "fifteen", 20: "twenty", 24: "twenty-four", 30: "thirty", 36: "thirty-six"}


# ------------------------------------------------------------------------------------------------- context

@dataclass
class Ctx:
    rng: random.Random
    split: str
    used: set = field(default_factory=set)  # names used in this document (so a "wrong entity" is really absent)
    values: set = field(default_factory=set)  # rupee values in this document (so a "wrong number" is really absent)

    @property
    def pool(self) -> dict:
        return POOLS[self.split]

    def pick(self, dev, test=None):
        """Split-specific phrasing: dev wording in dev documents, the held-out wording in test documents."""
        options = dev if (self.split == "dev" or test is None) else test
        return self.rng.choice(options) if isinstance(options, list) else options

    def company(self, sector: str | None = None, form: str | None = None) -> tuple[str, str]:
        for _ in range(100):
            first = self.rng.choice(self.pool["firms"])
            name = f"{first} {sector or self.rng.choice(SECTORS)}"
            if first not in {u.split()[0] for u in self.used}:
                break
        full = f"{name} {form or self.rng.choice(FORMS)}"
        self.used |= {full, name, first}
        return full, name  # ("Narmada Steel Pvt Ltd", "Narmada Steel")

    def person(self) -> str:
        for _ in range(100):
            p = f"{self.rng.choice(self.pool['first'])} {self.rng.choice(self.pool['last'])}"
            if p not in self.used and p.split()[1] not in {u.split()[-1] for u in self.used if " " in u}:
                break
        self.used.add(p)
        return p

    def other_person(self) -> str:
        for _ in range(100):
            p = f"{self.rng.choice(self.pool['first'])} {self.rng.choice(self.pool['last'])}"
            if p not in self.used and not any(w in " ".join(self.used) for w in p.split()):
                return p
        return "Kiran Bose"

    def other_company(self, sector: str | None = None) -> str:
        for _ in range(100):
            first = self.rng.choice(self.pool["firms"])
            if first not in " ".join(self.used):
                return f"{first} {sector or self.rng.choice(SECTORS)}"
        return "Tara Industries"

    def bank(self) -> tuple[str, str]:
        full = self.rng.choice(self.pool["banks"])
        short = full.replace(" Ltd", "")
        self.used |= {full, short}
        return full, short

    def other_bank(self) -> str:
        return next(b.replace(" Ltd", "") for b in self.pool["banks"] if b not in self.used)

    def day(self, year_from=2023, year_to=2025) -> date:
        y = self.rng.randint(year_from, year_to)
        return date(y, self.rng.randint(1, 12), self.rng.randint(1, 28))


# ----------------------------------------------------------------------------------------------- formatting

def grouped(n: int) -> str:
    """Indian digit grouping: 12400000 -> 1,24,00,000."""
    s = str(n)
    if len(s) <= 3:
        return s
    head, tail = s[:-3], s[-3:]
    parts = []
    while len(head) > 2:
        parts.insert(0, head[-2:])
        head = head[:-2]
    if head:
        parts.insert(0, head)
    return ",".join(parts + [tail])


def _trim(x: str) -> str:
    return x.rstrip("0").rstrip(".") if "." in x else x


def amt(n: int, style: str) -> str:
    """Render a rupee amount. Styles: g (₹12,40,000) g00 (₹12,40,000.00) rs (Rs 12,40,000) inr (INR 12,40,000)
    lakh (₹12.4 lakh) lakh2 (Rs. 12.40 lakh) crore (₹1.24 crore) crore2 (Rs 1.24 crore). Lakh/crore forms are only
    used when exact (see representable)."""
    if style == "g":
        return f"₹{grouped(n)}"
    if style == "g00":
        return f"₹{grouped(n)}.00"
    if style == "rs":
        return f"Rs {grouped(n)}"
    if style == "inr":
        return f"INR {grouped(n)}"
    if style in ("lakh", "lakh2"):
        v = f"{n / 1e5:.2f}"
        return f"₹{_trim(v)} lakh" if style == "lakh" else f"Rs. {v} lakh"
    if style in ("crore", "crore2"):
        v = f"{n / 1e7:.2f}"
        return f"₹{_trim(v)} crore" if style == "crore" else f"Rs {v} crore"
    raise ValueError(style)


def representable(n: int, style: str) -> bool:
    if style in ("lakh", "lakh2"):
        return n % 1000 == 0 and n >= 1e5
    if style in ("crore", "crore2"):
        return n % 100000 == 0 and n >= 1e7
    return True


def any_amt(ctx: Ctx, n: int, avoid: str | None = None, styles=None) -> str:
    styles = [s for s in (styles or ["g", "g00", "rs", "inr", "lakh", "lakh2", "crore", "crore2"])
              if representable(n, s) and s != avoid]
    return amt(n, ctx.rng.choice(styles))


def dt(d: date, style: str) -> str:
    m = MONTHS[d.month - 1]
    return {
        "long": f"{d.day} {m} {d.year}",
        "long0": f"{d.day:02d} {m} {d.year}",
        "short": f"{d.day} {m[:3]} {d.year}",
        "us": f"{m} {d.day}, {d.year}",
        "slash": f"{d.day:02d}/{d.month:02d}/{d.year}",
        "dash": f"{d.day:02d}-{d.month:02d}-{d.year}",
        "iso": d.isoformat(),
        "ord": f"{d.day}{'th' if 10 <= d.day % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(d.day % 10, 'th')} {m} {d.year}",
    }[style]


def any_dt(ctx: Ctx, d: date, avoid: str = "") -> str:
    return dt(d, ctx.rng.choice([s for s in ("long", "short", "us", "slash", "dash", "ord") if s != avoid]))


def fy(y: int) -> str:
    return f"FY {y}-{str(y + 1)[2:]}"


def pct(x: float) -> str:
    return _trim(f"{x:.2f}")


def words(n: int) -> str:
    return NUM_WORDS.get(n, str(n))


# --------------------------------------------------------------------------------------------- perturbations

def wrong_amount(ctx: Ctx, n: int) -> int:
    """A clearly different amount (>= 8% away, not another figure of the document, nor a sum/difference of two)."""
    vals = sorted(ctx.values)
    near = {a + b for i, a in enumerate(vals) for b in vals[i + 1:]} | {abs(a - b) for i, a in enumerate(vals)
                                                                       for b in vals[i + 1:]} | set(vals)
    unit = 100000 if n % 100000 == 0 and n >= 10**7 else 1000 if n % 1000 == 0 else 1
    for _ in range(200):
        if ctx.rng.random() < 0.4:  # swap two adjacent different significant digits
            digits = list(str(n // unit))
            idx = [i for i in range(len(digits) - 1) if digits[i] != digits[i + 1] and not (i == 0 and digits[1] == "0")]
            if not idx:
                continue
            i = ctx.rng.choice(idx)
            digits[i], digits[i + 1] = digits[i + 1], digits[i]
            m = int("".join(digits)) * unit
        else:
            m = int(round(n * ctx.rng.choice([0.5, 0.6, 0.7, 0.75, 0.8, 1.2, 1.25, 1.3, 1.4, 1.5, 2]) / unit)) * unit
        if m > 0 and abs(m - n) / n >= 0.08 and m not in near:
            return m
    return n * 3


def wrong_number(ctx: Ctx, x: float, choices=None) -> float:
    for _ in range(100):
        m = ctx.rng.choice(choices) if choices else round(x * ctx.rng.choice([0.6, 0.75, 1.3, 1.5]), 2)
        if abs(m - x) / max(abs(x), 1e-9) >= 0.08:
            return m
    return x * 2


def wrong_day(ctx: Ctx, d: date, others=()) -> date:
    for _ in range(100):
        kind = ctx.rng.choice(["month", "day", "year"])
        if kind == "month":
            m = (d.month - 1 + ctx.rng.choice([-2, -1, 1, 2])) % 12 + 1
            cand = d.replace(month=m)
        elif kind == "day":
            cand = d + timedelta(days=ctx.rng.choice([-11, -10, -7, 7, 10, 11]))
        else:
            cand = d.replace(year=d.year + ctx.rng.choice([-1, 1]))
        if cand != d and cand not in others:
            return cand
    return d.replace(year=d.year + 2)


def scale_swap(n: int) -> tuple[int, str]:
    """Same mantissa, wrong scale: a crore figure written as lakh (or lakh as crore)."""
    if n % 100000 == 0 and n >= 10**7:
        return n // 100, "lakh"
    return n * 100, "crore"


def computed_type(ctx: Ctx) -> str:
    """A wrong figure is an 'arithmetic' error where the passage does not state it (test templates compute it) and a
    plain 'wrong_number' where it does (dev templates state it)."""
    return "arithmetic" if ctx.split == "test" else "wrong_number"


# --------------------------------------------------------------------------------------------- doc families
# Each family returns (passage, question, claims) with claims = [(label, type, tag, text)].
# type: the benchmark category (as in v0); tag: the finer failure class targeted (converse, computed_pct, ...).

Claim = tuple


def fam_sanction(ctx: Ctx):
    bank, bank_s = ctx.bank()
    co, co_s = ctx.company()
    g1, g2 = ctx.person(), ctx.person()
    facility = ctx.rng.choice(["cash credit limit", "term loan", "working capital demand loan", "letter of credit limit"])
    a = ctx.rng.choice([250, 375, 450, 600, 725, 800, 1250, 1500]) * 10**5  # 2.5–15 crore
    rate = ctx.rng.choice([9.25, 9.75, 10.25, 10.5, 11.0, 11.75])
    d = ctx.day()
    tenure = ctx.rng.choice([12, 36, 60])
    fee_pct = ctx.rng.choice([0.25, 0.5, 1.0])
    fee = int(a * fee_pct / 100)
    security = ctx.rng.choice(["a first charge on stock and book debts", "hypothecation of plant and machinery",
                               "an equitable mortgage of the factory land and building"])
    ctx.values |= {a, fee}
    a_src = amt(a, ctx.pick(["crore", "crore2"], ["g", "rs"]))
    if ctx.split == "dev":
        passage = (f"{bank} sanctioned a {facility} of {a_src} to {co} on {dt(d, 'long')}. The facility carries "
                   f"interest at {pct(rate)}% per annum, payable monthly. It is secured by {security}. Personal "
                   f"guarantees of directors {g1} and {g2} are required. The sanction is valid for {tenure} months. "
                   f"A processing fee of {pct(fee_pct)}% of the limit, that is {amt(fee, 'g')}, is payable upfront.")
    else:
        passage = (f"Sanction letter dated {dt(d, 'slash')}. {bank} has approved a {facility} of {a_src} in favour of "
                   f"{co}. Rate of interest: {pct(rate)}% p.a., serviced monthly. Security: {security}. Guarantors: "
                   f"{g1} and {g2}. Tenure: {tenure} months. Processing fee: {pct(fee_pct)}% of the sanctioned "
                   f"amount.")
    a_alt = any_amt(ctx, a, styles=["lakh", "crore", "g", "rs"])
    sec_short = security.replace("a first charge on ", "").replace("hypothecation of ", "").replace(
        "an equitable mortgage of ", "")
    years = tenure // 12
    c = [
        (S, "faithful_hard", "reformat", ctx.pick(
            [f"{bank_s} sanctioned a {facility} of {a_alt} to {co_s}."],
            [f"{co_s} has been sanctioned a {facility} of {a_alt} by {bank_s}."])),
        (S, "faithful", "paraphrase", ctx.pick(
            [f"Interest is {pct(rate)}% a year, paid every month."],
            [f"The {facility} is priced at {pct(rate)}% per annum with interest serviced every month."])),
        (S, "faithful_hard", "reformat", ctx.pick(
            [f"The sanction is dated {any_dt(ctx, d, 'long')}."],
            [f"{bank_s} approved the facility on {any_dt(ctx, d, 'slash')}."])),
        (S, "faithful", "paraphrase", ctx.pick(
            [f"{g1} and {g2} must give personal guarantees."],
            [f"The facility is backed by guarantees from {g1} and {g2}."])),
        (S, "faithful_hard", "computed_pct" if ctx.split == "test" else "reformat", ctx.pick(
            [f"The processing fee amounts to {any_amt(ctx, fee, 'g')}."],
            [f"The upfront processing fee works out to {any_amt(ctx, fee)}."])),
        (S, "faithful_hard", "unit_conversion", ctx.pick(
            [f"The sanction is valid for {words(years)} year{'s' if years > 1 else ''}."],
            [f"The facility has a tenure of {years} year{'s' if years > 1 else ''}."])),
        (U, "wrong_number", "value", ctx.pick(
            [f"The facility carries interest at {pct(wrong_number(ctx, rate, [8.75, 9.5, 11.25, 12.0, 12.5]))}% per annum."],
            [f"The rate of interest on the {facility} is {pct(wrong_number(ctx, rate, [8.75, 9.5, 11.25, 12.0, 12.5]))}% p.a."])),
        (U, "wrong_scale", "value", ctx.pick(
            [f"{bank_s} sanctioned a {facility} of {amt(scale_swap(a)[0], scale_swap(a)[1])} to {co_s}."],
            [f"The sanctioned amount is {amt(scale_swap(a)[0], scale_swap(a)[1])}."])),
        (U, "wrong_date", "value", ctx.pick(
            [f"The {facility} was sanctioned on {any_dt(ctx, wrong_day(ctx, d))}."],
            [f"The sanction letter is dated {any_dt(ctx, wrong_day(ctx, d))}."])),
        (U, "wrong_period", "value", ctx.pick(
            [f"Interest at {pct(rate)}% is payable quarterly."],
            [f"The rate of interest is {pct(rate)}% per month."])),
        (U, "swapped_parties", "roles", ctx.pick(
            [f"{co_s} sanctioned a {facility} of {a_alt} to {bank_s}."],
            [f"{bank_s} has been sanctioned a {facility} of {a_alt} by {co_s}."])),
        (U, "negation", "negation", ctx.pick(
            [f"The {facility} is unsecured."],
            [f"No security has been stipulated for the {facility}."])),
        (U, "wrong_entity", "value", ctx.pick(
            [f"Personal guarantees of {g1} and {ctx.other_person()} are required."],
            [f"The guarantors are {ctx.other_person()} and {g2}."])),
        (U, "invented", "invented", ctx.pick(
            [f"{bank_s} also requires a fixed deposit of {amt(a // 10, 'g')} as cash margin."],
            [f"The sanction requires {co_s} to maintain a debt service coverage ratio of at least 1.5."])),
        (U, computed_type(ctx), "computed_pct" if ctx.split == "test" else "value", ctx.pick(
            [f"The processing fee amounts to {any_amt(ctx, wrong_amount(ctx, fee))}."],
            [f"The processing fee works out to {any_amt(ctx, wrong_amount(ctx, fee))}."])),
    ]
    if sec_short and ctx.split == "dev":
        c.append((S, "faithful", "paraphrase", f"The facility is secured by {sec_short}."))
    return passage, "What are the terms of the sanction?", c


def fam_statement_table(ctx: Ctx):
    bank, bank_s = ctx.bank()
    acct = str(ctx.rng.randint(10**13, 10**14 - 1))
    city = ctx.rng.choice(ctx.pool["cities"])
    month = ctx.rng.randint(1, 12)
    year = ctx.rng.randint(2023, 2025)
    cust1, cust1_s = ctx.company()
    cust2, cust2_s = ctx.company()
    supp, supp_s = ctx.company()
    land, land_s = ctx.company("Realty", "LLP")
    opening = ctx.rng.randint(5, 60) * 10**4 + ctx.rng.choice([0, 250, 500, 750]) * 1
    rows = []  # (day, narration, debit, credit, counterparty_short, kind)
    days = sorted(ctx.rng.sample(range(1, 28), 5))
    ch1, ch2 = ctx.rng.choice(["NEFT", "RTGS", "IMPS"]), ctx.rng.choice(["NEFT", "RTGS"])
    cr1 = ctx.rng.randint(30, 150) * 25000
    cr2 = ctx.rng.randint(10, 80) * 10000
    rent = ctx.rng.randint(8, 40) * 10000
    cash = ctx.rng.choice([20000, 25000, 40000, 50000])
    db1 = ctx.rng.randint(20, 120) * 10000
    seq = [("cr", f"{ch1} from {cust1}", cr1, cust1_s), ("atm", f"Cash withdrawal ATM {city}", cash, None),
           ("db", f"{ch2} to {supp} purchase", db1, supp_s), ("cr", f"NEFT from {cust2}", cr2, cust2_s),
           ("db", f"RTGS to {land} rent", rent, land_s)]
    ctx.rng.shuffle(seq)
    bal = opening + max(0, sum(v for k, _, v, _ in seq if k != "cr") - sum(v for k, _, v, _ in seq if k == "cr"))
    opening = bal
    lines = []
    for day_no, (kind, narr, v, cp) in zip(days, seq):
        d = date(year, month, day_no)
        if kind == "cr":
            bal += v
            rows.append((d, narr, None, v, cp, kind, bal))
        else:
            bal -= v
            rows.append((d, narr, v, None, cp, kind, bal))
    ctx.values |= {cr1, cr2, rent, cash, db1} | {r[6] for r in rows}
    if ctx.split == "dev":
        head = "Date | Narration | Debit | Credit | Balance"
        fmt = lambda d: dt(d, "dash")  # noqa: E731
    else:
        head = "Txn Date | Particulars | Withdrawals (Dr) | Deposits (Cr) | Balance"
        fmt = lambda d: dt(d, "slash")  # noqa: E731
    for d, narr, dbv, crv, _, _, b in rows:
        lines.append(f"{fmt(d)} | {narr} | {grouped(dbv) + '.00' if dbv else ''} | "
                     f"{grouped(crv) + '.00' if crv else ''} | {grouped(b)}.00")
    title = ctx.pick([f"Statement of account {acct}, {bank}, {city} branch, {MONTHS[month - 1]} {year}"],
                     [f"{bank} | A/c No. {acct} | Branch: {city} | Period: {MONTHS[month - 1][:3]} {year}"])
    passage = title + "\n" + head + "\n" + "\n".join(lines)

    credits = [r for r in rows if r[5] == "cr"]
    debits = [r for r in rows if r[5] in ("db",)]
    atm = next(r for r in rows if r[5] == "atm")
    c_in, c_out = ctx.rng.choice(credits), ctx.rng.choice(debits)
    last = rows[-1]
    total_cr = sum(r[3] for r in credits)
    ctx.values.add(total_cr)
    c = [
        (S, "faithful_hard", "table_column", ctx.pick(
            [f"On {any_dt(ctx, c_in[0], 'dash')} the account received {any_amt(ctx, c_in[3])} from {c_in[4]}."],
            [f"{c_in[4]} sent {any_amt(ctx, c_in[3])} to the account on {any_dt(ctx, c_in[0], 'slash')}."])),
        (S, "faithful_hard", "table_column", ctx.pick(
            [f"{any_amt(ctx, c_out[2])} was paid to {c_out[4]} on {any_dt(ctx, c_out[0], 'dash')}."],
            [f"On {any_dt(ctx, c_out[0], 'slash')} the account transferred {any_amt(ctx, c_out[2])} to {c_out[4]}."])),
        (S, "faithful", "paraphrase", ctx.pick(
            [f"After the transaction on {any_dt(ctx, last[0], 'dash')}, the balance was {any_amt(ctx, last[6])}."],
            [f"The balance stood at {any_amt(ctx, last[6])} after the last entry on {any_dt(ctx, last[0], 'slash')}."])),
        (S, "faithful_hard", "computed_total", ctx.pick(
            [f"Total credits in the period were {any_amt(ctx, total_cr)}."],
            [f"Deposits during the period added up to {any_amt(ctx, total_cr)}."])),
        (S, "faithful_hard", "table_column", ctx.pick(
            [f"{any_amt(ctx, cash)} was withdrawn in cash at an ATM in {city}."],
            [f"A cash withdrawal of {any_amt(ctx, cash)} was made in {city} on {any_dt(ctx, atm[0], 'slash')}."])),
        (U, "direction", "table_column", ctx.pick(
            [f"On {any_dt(ctx, c_in[0], 'dash')} the account paid {any_amt(ctx, c_in[3])} to {c_in[4]}."],
            [f"{any_amt(ctx, c_in[3])} was debited on {any_dt(ctx, c_in[0], 'slash')} towards {c_in[4]}."])),
        (U, "direction", "table_column", ctx.pick(
            [f"{c_out[4]} credited {any_amt(ctx, c_out[2])} to the account on {any_dt(ctx, c_out[0], 'dash')}."],
            [f"The account received {any_amt(ctx, c_out[2])} from {c_out[4]} on {any_dt(ctx, c_out[0], 'slash')}."])),
        (U, "wrong_number", "value", ctx.pick(
            [f"After the transaction on {any_dt(ctx, last[0], 'dash')}, the balance was {any_amt(ctx, wrong_amount(ctx, last[6]))}."],
            [f"The closing balance for the period was {any_amt(ctx, wrong_amount(ctx, last[6]))}."])),
        (U, "wrong_date", "value", ctx.pick(
            [f"{any_amt(ctx, c_out[2])} was paid to {c_out[4]} on {any_dt(ctx, wrong_day(ctx, c_out[0], [r[0] for r in rows]))}."],
            [f"The payment of {any_amt(ctx, c_out[2])} to {c_out[4]} went out on {any_dt(ctx, wrong_day(ctx, c_out[0], [r[0] for r in rows]))}."])),
        (U, "wrong_entity", "value", ctx.pick(
            [f"On {any_dt(ctx, c_in[0], 'dash')} the account received {any_amt(ctx, c_in[3])} from {ctx.other_company()}."],
            [f"{ctx.other_company()} sent {any_amt(ctx, c_in[3])} to the account on {any_dt(ctx, c_in[0], 'slash')}."])),
        (U, "wrong_number", "identifier", ctx.pick(
            [f"The statement is for account {acct[:-2] + acct[-1] + acct[-2] if acct[-1] != acct[-2] else acct[:-1] + str((int(acct[-1]) + 3) % 10)}."],
            [f"The account number is {acct[:-2] + acct[-1] + acct[-2] if acct[-1] != acct[-2] else acct[:-1] + str((int(acct[-1]) + 3) % 10)}."])),
        (U, "invented", "invented", ctx.pick(
            [f"A cheque of {amt(ctx.rng.randint(2, 9) * 10**5, 'g')} issued to {c_out[4]} was returned unpaid."],
            [f"The account was marked as a special mention account (SMA-1) during the period."])),
        (U, "arithmetic", "computed_total", ctx.pick(
            [f"Total credits in the period were {any_amt(ctx, wrong_amount(ctx, total_cr))}."],
            [f"Deposits during the period added up to {any_amt(ctx, wrong_amount(ctx, total_cr))}."])),
    ]
    return passage, "What does the statement show?", c


def fam_invoice(ctx: Ctx):
    seller, seller_s = ctx.company("Traders", ctx.rng.choice(["Pvt Ltd", "LLP"]))
    buyer, buyer_s = ctx.company()
    item, unit = ctx.rng.choice([("HDPE granules", "tonne"), ("cotton yarn", "bale"), ("steel coils", "tonne"),
                                 ("corrugated boxes", "bundle"), ("PVC resin", "tonne")])
    qty = ctx.rng.choice([10, 12, 20, 25, 40, 50])
    rate = ctx.rng.choice([18, 24, 36, 48, 52, 64, 96]) * 1000
    taxable = qty * rate
    g = ctx.rng.choice([5, 12, 18])
    gst = taxable * g // 100
    total = taxable + gst
    no = f"INV/{ctx.rng.randint(2023, 2025)}/{ctx.rng.randint(100, 999):04d}"
    d = ctx.day()
    due = ctx.rng.choice([15, 30, 45, 60])
    ctx.values |= {rate, taxable, gst, total}
    if ctx.split == "dev":
        passage = (f"Tax invoice {no} dated {dt(d, 'long')} was issued by {seller} to {buyer} for {qty} "
                   f"{unit}s of {item} at {amt(rate, 'g')} per {unit}. The taxable value is {amt(taxable, 'g')} and "
                   f"GST at {g}% amounts to {amt(gst, 'g')}, giving a total of {amt(total, 'g')}. Payment is due "
                   f"within {due} days of the invoice date.")
    else:
        passage = (f"Supplier: {seller}. Buyer: {buyer}. Invoice no. {no}, date {dt(d, 'dash')}. Description: {qty} "
                   f"{unit}s of {item} at {amt(rate, 'rs')} per {unit}. IGST @ {g}% is charged on the taxable value. "
                   f"Credit period: {due} days.")
    c = [
        (S, "faithful_hard", "computed_total" if ctx.split == "test" else "reformat", ctx.pick(
            [f"{seller_s} billed {buyer_s} {any_amt(ctx, total, 'g')} in total, including {any_amt(ctx, gst, 'g')} of GST."],
            [f"Including tax, the invoice comes to {any_amt(ctx, total)}."])),
        (S, "faithful", "paraphrase", ctx.pick(
            [f"The invoice covers {qty} {unit}s of {item} priced at {any_amt(ctx, rate, 'g')} a {unit}."],
            [f"{qty} {unit}s of {item} were invoiced at {any_amt(ctx, rate, 'rs')} each."])),
        (S, "faithful_hard", "converse", ctx.pick(
            [f"{buyer_s} was invoiced by {seller_s} on {any_dt(ctx, d, 'long')}."],
            [f"{buyer_s} bought {item} from {seller_s}."])),
        (S, "faithful_hard", "computed_product" if ctx.split == "test" else "reformat", ctx.pick(
            [f"The taxable value of the invoice is {any_amt(ctx, taxable, 'g')}."],
            [f"Before tax, the invoice is worth {any_amt(ctx, taxable)}."])),
        (S, "faithful_hard", "computed_pct" if ctx.split == "test" else "reformat", ctx.pick(
            [f"GST on the invoice is {any_amt(ctx, gst, 'g')}."],
            [f"The IGST charged comes to {any_amt(ctx, gst)}."])),
        (S, "faithful", "paraphrase", ctx.pick(
            [f"Payment falls due {due} days after the invoice date."],
            [f"{buyer_s} has {due} days to pay the invoice."])),
        (U, "wrong_number", "value", ctx.pick(
            [f"GST at {wrong_number(ctx, g, [x for x in (5, 12, 18, 28) if x != g]):g}% is charged on this invoice."],
            [f"IGST is levied at {wrong_number(ctx, g, [x for x in (5, 12, 18, 28) if x != g]):g}%."])),
        (U, computed_type(ctx), "computed_total" if ctx.split == "test" else "value", ctx.pick(
            [f"The invoice total comes to {any_amt(ctx, wrong_amount(ctx, total))}."],
            [f"Including tax, the invoice comes to {any_amt(ctx, wrong_amount(ctx, total))}."])),
        (U, "swapped_parties", "converse", ctx.pick(
            [f"Tax invoice {no} was issued by {buyer} to {seller}."],
            [f"{seller_s} bought {item} from {buyer_s}."])),
        (U, "wrong_number", "value", ctx.pick(
            [f"Payment is due within {wrong_number(ctx, due, [x for x in (7, 10, 21, 90) if x != due]):g} days of the invoice date."],
            [f"The credit period on the invoice is {wrong_number(ctx, due, [x for x in (7, 10, 21, 90) if x != due]):g} days."])),
        (U, "wrong_date", "value", ctx.pick(
            [f"Tax invoice {no} is dated {any_dt(ctx, wrong_day(ctx, d))}."],
            [f"The invoice was raised on {any_dt(ctx, wrong_day(ctx, d))}."])),
        (U, "invented", "invented", ctx.pick(
            [f"The invoice was paid in full on the day it was issued."],
            [f"{buyer_s} rejected part of the consignment for poor quality."])),
        (U, computed_type(ctx), "computed_pct" if ctx.split == "test" else "value", ctx.pick(
            [f"GST on the invoice is {any_amt(ctx, wrong_amount(ctx, gst))}."],
            [f"The IGST charged comes to {any_amt(ctx, wrong_amount(ctx, gst))}."])),
    ]
    return passage, "What does the invoice show?", c


def fam_board(ctx: Ctx):
    co, co_s = ctx.company()
    bank, bank_s = ctx.bank()
    firm, firm_s = ctx.company("Traders", "LLP")
    d1, d2 = ctx.person(), ctx.person()
    x = ctx.rng.choice([5, 8, 10, 12, 15, 20]) * 10**7
    y = ctx.rng.choice([75, 100, 150, 200, 250]) * 10**5
    d = ctx.day()
    ctx.values |= {x, y}
    if ctx.split == "dev":
        passage = (f"At its meeting on {dt(d, 'long')}, the board of {co} approved borrowing up to {amt(x, 'crore')} "
                   f"from {bank}. The board did not approve the proposed loan of {amt(y, 'crore')} to {firm}, a firm "
                   f"in which director {d1} is a partner. {d2} abstained from voting on both items.")
    else:
        passage = (f"Minutes of the board meeting of {co} held on {dt(d, 'ord')}. Resolution 1: the board declined "
                   f"the proposal to lend {amt(y, 'g')} to {firm}, a firm in which director {d1} is a partner. "
                   f"Resolution 2: the board approved borrowings of up to {amt(x, 'g')} from {bank}. {d2} did not "
                   f"vote on either resolution.")
    c = [
        (S, "faithful_hard", "declined", ctx.pick(
            [f"The proposed {any_amt(ctx, y)} loan to {firm_s} was rejected by the board."],
            [f"The board turned down the {any_amt(ctx, y)} loan proposal for {firm_s}."])),
        (S, "faithful", "paraphrase", ctx.pick(
            [f"The board authorised borrowing of up to {any_amt(ctx, x)} from {bank_s}."],
            [f"{co_s} may borrow up to {any_amt(ctx, x)} from {bank_s}, as approved by the board."])),
        (S, "faithful", "paraphrase", ctx.pick(
            [f"{d1} is a partner in {firm_s}."],
            [f"Director {d1} is a partner of {firm_s}."])),
        (S, "faithful_hard", "reformat", ctx.pick(
            [f"The board meeting was held on {any_dt(ctx, d, 'long')}."],
            [f"The board met on {any_dt(ctx, d, 'ord')}."])),
        (S, "faithful", "paraphrase", ctx.pick(
            [f"{d2} did not vote on either item."],
            [f"{d2} abstained from voting on both resolutions."])),
        (U, "negation", "declined", ctx.pick(
            [f"The board approved the proposed loan of {any_amt(ctx, y)} to {firm_s}."],
            [f"The loan of {any_amt(ctx, y)} to {firm_s} was approved by the board."])),
        (U, "wrong_number", "value", ctx.pick(
            [f"The board approved borrowing up to {any_amt(ctx, wrong_amount(ctx, x))} from {bank_s}."],
            [f"Borrowings of up to {any_amt(ctx, wrong_amount(ctx, x))} were approved."])),
        (U, "contradiction", "contradiction", ctx.pick(
            [f"{firm_s} is a firm in which director {d2} is a partner."],
            [f"{d1} abstained from voting on both resolutions."])),
        (U, "wrong_date", "value", ctx.pick(
            [f"The board met on {any_dt(ctx, wrong_day(ctx, d))} to approve the borrowing."],
            [f"The meeting took place on {any_dt(ctx, wrong_day(ctx, d))}."])),
        (U, "swapped_parties", "roles", ctx.pick(
            [f"The board approved borrowing up to {any_amt(ctx, x)} by {bank_s} from {co_s}."],
            [f"{co_s} may lend up to {any_amt(ctx, x)} to {bank_s} under the board's approval."])),
        (U, "invented", "invented", ctx.pick(
            [f"The board also approved a dividend of ₹2 per share."],
            [f"The board resolved to appoint a new statutory auditor."])),
    ]
    return passage, "What did the board decide?", c


def fam_lease(ctx: Ctx):
    lessor, lessor_s = ctx.company("Realty", "LLP")
    lessee, lessee_s = ctx.company()
    unit = f"{ctx.rng.choice(['warehouse unit', 'shed', 'godown'])} {ctx.rng.choice('ABCDEF')}-{ctx.rng.randint(1, 40)}"
    city = ctx.rng.choice(ctx.pool["cities"])
    years = ctx.rng.choice([3, 5, 9])
    rent = ctx.rng.choice([150, 225, 250, 325, 400, 480]) * 1000
    esc = ctx.rng.choice([5, 6, 10])
    k = ctx.rng.choice([3, 6, 10])
    dep = rent * k
    lock = ctx.rng.choice([12, 24, 36])
    notice = ctx.rng.choice([1, 2, 3])
    d = ctx.day(2022, 2024)
    ctx.values |= {rent, dep, rent * 12}
    if ctx.split == "dev":
        passage = (f"Under the lease dated {dt(d, 'long')}, {lessor} leases {unit} in {city} to {lessee} for "
                   f"{words(years)} years. Monthly rent is {amt(rent, 'g')}, rising by {esc}% every year. The tenant "
                   f"paid a refundable security deposit of {amt(dep, 'g')}. Either party may terminate the lease by "
                   f"giving {words(notice)} months' written notice, but not during the first {lock} months.")
    else:
        passage = (f"Lease deed dated {dt(d, 'slash')} between {lessor} (Lessor) and {lessee} (Lessee) for {unit}, "
                   f"{city}. Term: {years} years. Rent: {amt(rent, 'rs')} per month, escalating {esc}% annually. "
                   f"Security deposit: {amt(dep, 'rs')} (refundable). Lock-in period: {lock} months, during which "
                   f"neither party may terminate. Notice period thereafter: {notice} month{'s' if notice > 1 else ''}.")
    c = [
        (S, "faithful_hard", "converse", ctx.pick(
            [f"{lessee_s} rents {unit} in {city} from {lessor_s}."],
            [f"{lessee_s} has taken {unit} on lease from {lessor_s}."])),
        (S, "faithful_hard", "reformat", ctx.pick(
            [f"The rent starts at {any_amt(ctx, rent, 'g')} a month and increases {esc}% annually."],
            [f"Monthly rent is {any_amt(ctx, rent, 'rs')}, with a {esc}% increase each year."])),
        (S, "faithful_hard", "period_conversion", ctx.pick(
            [f"Rent for the first year comes to {any_amt(ctx, rent * 12)}."],
            [f"First-year rent totals {any_amt(ctx, rent * 12)}."])),
        (S, "faithful_hard", "computed_ratio", ctx.pick(
            [f"The security deposit equals {words(k)} months' rent."],
            [f"The deposit is {k} times the monthly rent."])),
        (S, "faithful_hard", "unit_conversion", ctx.pick(
            [f"Neither side can end the lease in its first year." if lock == 12 else
             f"Neither side can end the lease in its first {words(lock // 12)} years."],
            [f"The lock-in period is {lock // 12} year{'s' if lock > 12 else ''}."])),
        (U, "swapped_parties", "converse", ctx.pick(
            [f"{lessor_s} rents {unit} in {city} from {lessee_s}."],
            [f"{lessee_s} leases {unit} to {lessor_s}."])),
        (U, "wrong_number", "value", ctx.pick(
            [f"Monthly rent under the lease is {any_amt(ctx, wrong_amount(ctx, rent))}."],
            [f"The rent is {any_amt(ctx, wrong_amount(ctx, rent))} per month."])),
        (U, "wrong_period", "value", ctx.pick(
            [f"Annual rent for {unit} is {any_amt(ctx, rent)}."],
            [f"Rent of {any_amt(ctx, rent)} is payable every quarter."])),
        (U, "wrong_number", "value", ctx.pick(
            [f"The tenant paid a security deposit of {any_amt(ctx, wrong_amount(ctx, dep))}."],
            [f"The refundable deposit is {any_amt(ctx, wrong_amount(ctx, dep))}."])),
        (U, "negation", "negation", ctx.pick(
            [f"Either party may terminate the lease at any time, including the first {lock} months."],
            [f"There is no lock-in period under the lease."])),
        (U, "wrong_entity", "value", ctx.pick(
            [f"{lessor_s} leases {unit} in {city} to {ctx.other_company()}."],
            [f"{ctx.other_company()} has taken {unit} on lease from {lessor_s}."])),
        (U, "invented", "invented", ctx.pick(
            [f"The tenant is responsible for all structural repairs."],
            [f"The lessor must provide 24-hour security at the premises."])),
        (U, "arithmetic", "computed_ratio", ctx.pick(
            [f"The security deposit equals {words(k + 2)} months' rent."],
            [f"The deposit is {k + 4} times the monthly rent."])),
    ]
    return passage, "What are the lease terms?", c


def fam_financials(ctx: Ctx):
    co, co_s = ctx.company()
    y1 = ctx.rng.choice([2021, 2022, 2023])
    a = ctx.rng.randint(150, 600) * 10**6  # sales 15–60 crore, 0.1 crore granularity
    b = int(round(a * ctx.rng.uniform(1.08, 1.35) / 10**6)) * 10**6
    p = ctx.rng.randint(15, 45) * 10**6
    q = int(round(p * ctx.rng.uniform(0.45, 0.8) / 10**6)) * 10**6
    cr0 = ctx.rng.choice([1.21, 1.18, 1.3, 1.24])
    cr = round(cr0 - ctx.rng.choice([0.08, 0.13, 0.16]), 2)
    bm = 1.25 if cr < 1.25 else 1.33
    growth = (b - a) / a * 100
    ctx.values |= {a, b, p, q, b - a, p - q}
    if ctx.split == "dev":
        passage = (f"Sales of {co} grew from {amt(a, 'crore')} in {fy(y1)} to {amt(b, 'crore')} in {fy(y1 + 1)}, "
                   f"while net profit fell from {amt(p, 'crore')} to {amt(q, 'crore')}. The current ratio declined "
                   f"to {cr:.2f}, below the bank's benchmark of {bm:.2f}.")
    else:
        passage = (f"Key financials of {co} (₹ crore)\nParticulars | {fy(y1)} | {fy(y1 + 1)}\n"
                   f"Revenue from operations | {a / 1e7:.2f} | {b / 1e7:.2f}\nNet profit | {p / 1e7:.2f} | {q / 1e7:.2f}\n"
                   f"Current ratio | {cr0:.2f} | {cr:.2f}\nThe bank's benchmark for the current ratio is {bm:.2f}.")
    approx = round(growth)
    c = [
        (S, "faithful_hard", "computed_diff", ctx.pick(
            [f"{co_s}'s sales rose by {any_amt(ctx, b - a, styles=['crore', 'lakh'])} year on year."],
            [f"Revenue increased by {any_amt(ctx, b - a, styles=['crore', 'lakh'])} in {fy(y1 + 1)}."])),
        (S, "faithful", "paraphrase", ctx.pick(
            [f"Net profit dropped to {any_amt(ctx, q, styles=['crore', 'lakh'])} in {fy(y1 + 1)}."],
            [f"Net profit was {any_amt(ctx, q, styles=['crore', 'lakh'])} in {fy(y1 + 1)}, down from "
             f"{any_amt(ctx, p, styles=['crore', 'lakh'])}."])),
        (S, "faithful", "paraphrase", ctx.pick(
            [f"At {cr:.2f}, the current ratio is under the {bm:.2f} benchmark."],
            [f"The current ratio of {cr:.2f} is below the bank's benchmark."])),
        (S, "faithful_hard", "computed_pct_change", ctx.pick(
            [f"Sales grew about {approx}% while profit fell."],
            [f"Revenue rose roughly {approx}% year on year."])),
        (S, "faithful_hard", "declined", ctx.pick(
            [f"The current ratio declined to {cr:.2f}."],
            [f"The current ratio slipped from {cr0:.2f} to {cr:.2f}."])),
        (U, "direction", "from_to", ctx.pick(
            [f"Net profit rose from {any_amt(ctx, p, styles=['crore'])} to {any_amt(ctx, q, styles=['crore'])}."],
            [f"Net profit increased to {any_amt(ctx, q, styles=['crore', 'lakh'])} in {fy(y1 + 1)}."])),
        (U, "wrong_number", "value", ctx.pick(
            [f"The current ratio declined to {cr + 0.7:.2f}."],
            [f"The current ratio for {fy(y1 + 1)} was {cr + 0.7:.2f}."])),
        (U, "direction", "direction", ctx.pick(
            [f"The current ratio is above the bank's benchmark of {bm:.2f}."],
            [f"The current ratio of {cr:.2f} exceeds the bank's benchmark."])),
        (U, "wrong_date", "value", ctx.pick(
            [f"Sales reached {any_amt(ctx, b, styles=['crore'])} in {fy(y1 + 2)}."],
            [f"Revenue was {any_amt(ctx, b, styles=['crore'])} in {fy(y1 - 1)}."])),
        (U, "wrong_scale", "value", ctx.pick(
            [f"Sales of {co_s} were {amt(scale_swap(a)[0], scale_swap(a)[1])} in {fy(y1)}."],
            [f"Revenue for {fy(y1)} was {amt(scale_swap(a)[0], scale_swap(a)[1])}."])),
        (U, "arithmetic", "computed_pct_change", ctx.pick(
            [f"Sales grew about {approx + 9}% while profit fell."],
            [f"Revenue rose roughly {approx + 9}% year on year."])),
        (U, "invented", "invented", ctx.pick(
            [f"The bank rejected the renewal request because of the falling profit."],
            [f"{co_s} breached its DSCR covenant in {fy(y1 + 1)}."])),
    ]
    return passage, "How did the company perform financially?", c


def fam_valuation(ctx: Ctx):
    valuer = ctx.person()
    plot = f"Plot {ctx.rng.randint(3, 120)}, {ctx.rng.choice(ctx.pool['estates'])}"
    f = ctx.rng.choice([45, 60, 74, 88, 120, 150]) * 10**6
    share = ctx.rng.choice([0.7, 0.75, 0.8, 0.85])
    ds = int(round(f * share / 10**6)) * 10**6
    d = ctx.day()
    ratio = ds / f * 100
    ctx.values |= {f, ds}
    if ctx.split == "dev":
        passage = (f"The valuer, {valuer}, assessed the factory land and building at {plot} at a fair market value of "
                   f"{amt(f, 'crore')} and a distress sale value of {amt(ds, 'crore')} as of {dt(d, 'long')}. The "
                   f"valuation excludes plant and machinery.")
    else:
        passage = (f"Valuation report by {valuer}, government-approved valuer, dated {dt(d, 'dash')}. Property: "
                   f"industrial land and building, {plot}. Fair market value: {amt(f, 'rs')}. Distress sale value: "
                   f"{amt(ds, 'rs')}. Plant and machinery are not part of this valuation.")
    c = [
        (S, "faithful", "reformat", ctx.pick(
            [f"{valuer} valued the property at {any_amt(ctx, f, styles=['crore', 'lakh'])} (fair market value)."],
            [f"The fair market value of the property is {any_amt(ctx, f, styles=['crore', 'g'])}."])),
        (S, "faithful_hard", "computed_pct", ctx.pick(
            [f"The distress sale value is about {round(ratio)}% of the fair market value."],
            [f"The distress value is roughly {round(100 - ratio)}% below the fair market value."])),
        (S, "faithful_hard", "negation_paraphrase", ctx.pick(
            [f"Plant and machinery were not included in the valuation."],
            [f"The valuation leaves out plant and machinery."])),
        (S, "faithful_hard", "reformat", ctx.pick(
            [f"The valuation is as of {any_dt(ctx, d, 'long')}."],
            [f"The report was dated {any_dt(ctx, d, 'dash')}."])),
        (U, "direction", "direction", ctx.pick(
            [f"The valuation includes plant and machinery."],
            [f"Plant and machinery form part of the valuation."])),
        (U, "wrong_number", "value", ctx.pick(
            [f"The fair market value is {any_amt(ctx, wrong_amount(ctx, f))}."],
            [f"The distress sale value is {any_amt(ctx, wrong_amount(ctx, ds))}."])),
        (U, "wrong_entity", "value", ctx.pick(
            [f"The valuer, {ctx.other_person()}, assessed the factory at {plot}."],
            [f"The report was prepared by {ctx.other_person()}."])),
        (U, "wrong_date", "value", ctx.pick(
            [f"The valuation is as of {any_dt(ctx, wrong_day(ctx, d))}."],
            [f"The report is dated {any_dt(ctx, wrong_day(ctx, d))}."])),
        (U, "arithmetic", "computed_pct", ctx.pick(
            [f"The distress sale value is about {round(ratio) - 15}% of the fair market value."],
            [f"The distress value is roughly {round(100 - ratio) + 12}% below the fair market value."])),
        (U, "invented", "invented", ctx.pick(
            [f"The valuer noted that the building has no fire safety certificate."],
            [f"The valuer recommended a fresh valuation within six months."])),
    ]
    return passage, "What is the property worth?", c


def fam_insurance(ctx: Ctx):
    insurer = ctx.rng.choice(ctx.pool["insurers"])
    co, co_s = ctx.company()
    bank, bank_s = ctx.bank()
    pol = f"{ctx.rng.choice(['FP', 'SF', 'MB'])}-{ctx.rng.randint(10000, 99999)}"
    city = ctx.rng.choice(ctx.pool["cities"])
    si = ctx.rng.choice([4, 5, 6, 8, 10, 12]) * 10**7
    start = date(ctx.rng.randint(2023, 2025), ctx.rng.choice([1, 4, 7, 10]), 1)
    end = date(start.year + 1, start.month, 1) - timedelta(days=1)
    excl = ctx.rng.choice(["Theft", "Earthquake", "Burglary"])
    ctx.values |= {si}
    ctx.used.add(insurer)
    if ctx.split == "dev":
        passage = (f"Policy {pol} issued by {insurer} covers the stock of {co} at its {city} plant against fire and "
                   f"flood for a sum insured of {amt(si, 'crore')}. The policy runs from {dt(start, 'long')} to "
                   f"{dt(end, 'long')}. {bank} is named as the loss payee. {excl} is not covered.")
    else:
        passage = (f"Schedule to policy {pol}. Insurer: {insurer}. Insured: {co}. Location: {city} works. "
                   f"Perils: fire, flood. Sum insured: {amt(si, 'g')}. Period of insurance: {dt(start, 'slash')} to "
                   f"{dt(end, 'slash')}. Loss payee: {bank}. Exclusions: {excl.lower()}.")
    c = [
        (S, "faithful", "paraphrase", ctx.pick(
            [f"{co_s}'s {city} stock is insured for {any_amt(ctx, si)} against fire and flood."],
            [f"The stock at {co_s}'s {city} works is covered for {any_amt(ctx, si)} against fire and flood."])),
        (S, "faithful_hard", "interval", ctx.pick(
            [f"Cover lasts one year, from {any_dt(ctx, start)} to {any_dt(ctx, end)}."],
            [f"The policy is for a period of one year starting {any_dt(ctx, start)}."])),
        (S, "faithful", "paraphrase", ctx.pick(
            [f"Any claim payout goes to {bank_s} as loss payee."],
            [f"{bank_s} will receive claim proceeds as loss payee."])),
        (S, "faithful_hard", "negation_paraphrase", ctx.pick(
            [f"{excl} is excluded from the policy."],
            [f"The policy does not cover {excl.lower()}."])),
        (U, "negation", "negation", ctx.pick(
            [f"The policy also covers {excl.lower()} of stock at the {city} plant."],
            [f"{excl} is among the perils covered."])),
        (U, "wrong_number", "value", ctx.pick(
            [f"The stock is insured for a sum of {any_amt(ctx, wrong_amount(ctx, si))}."],
            [f"The sum insured under the policy is {any_amt(ctx, wrong_amount(ctx, si))}."])),
        (U, "wrong_entity", "value", ctx.pick(
            [f"{ctx.other_bank()} is named as the loss payee on policy {pol}."],
            [f"The loss payee is {ctx.other_bank()}."])),
        (U, "wrong_date", "value", ctx.pick(
            [f"The policy runs until {any_dt(ctx, end.replace(year=end.year + 1))}."],
            [f"The period of insurance ends on {any_dt(ctx, end.replace(year=end.year + 1))}."])),
        (U, "swapped_parties", "roles", ctx.pick(
            [f"Policy {pol} was issued by {co_s} to {insurer}."],
            [f"{co_s} insured the stock of {insurer}."])),
        (U, "invented", "invented", ctx.pick(
            [f"The policy carries a deductible of ₹5 lakh per claim."],
            [f"The policy was renewed without a claim in the previous year."])),
    ]
    return passage, "What does the insurance policy cover?", c


def fam_gst(ctx: Ctx):
    co, co_s = ctx.company()
    y = ctx.rng.randint(2023, 2025)
    m = ctx.rng.randint(1, 11)
    out = ctx.rng.choice([36, 48, 52, 75, 120]) * 10**6
    itc = ctx.rng.choice([18, 24, 42, 56]) * 10**5
    cash = ctx.rng.choice([9, 12, 21, 30]) * 10**5
    due = date(y, m + 1, 20)
    late = ctx.rng.choice([2, 5, 9, 12])
    filed = due + timedelta(days=late)
    ctx.values |= {out, itc, cash}
    if ctx.split == "dev":
        passage = (f"In GSTR-3B for {MONTHS[m - 1]} {y}, {co} reported outward taxable supplies of {amt(out, 'crore')} "
                   f"and an input tax credit of {amt(itc, 'lakh')}. Tax paid in cash was {amt(cash, 'lakh')}. "
                   f"The return was filed on {dt(filed, 'long')}; the due date was {dt(due, 'long')}.")
    else:
        passage = (f"GSTR-3B summary | GSTIN holder: {co} | Tax period: {MONTHS[m - 1][:3]} {y}\n"
                   f"Outward taxable supplies | {grouped(out)}.00\nEligible ITC | {grouped(itc)}.00\n"
                   f"Tax paid in cash | {grouped(cash)}.00\nDate of filing: {dt(filed, 'dash')} (due {dt(due, 'dash')})")
    c = [
        (S, "faithful_hard", "interval", ctx.pick(
            [f"{co_s} filed its {MONTHS[m - 1]} {y} GSTR-3B {words(late)} days late."],
            [f"The return was filed {late} days after the due date."])),
        (S, "faithful", "reformat", ctx.pick(
            [f"It claimed {any_amt(ctx, itc)} of input tax credit against {any_amt(ctx, out)} of taxable outward supplies."],
            [f"Eligible input tax credit was {any_amt(ctx, itc)}."])),
        (S, "faithful_hard", "reformat", ctx.pick(
            [f"Cash tax payment was {any_amt(ctx, cash)}."],
            [f"{co_s} paid {any_amt(ctx, cash)} of tax in cash for the period."])),
        (U, "wrong_scale", "value", ctx.pick(
            [f"{co_s} reported outward taxable supplies of {amt(scale_swap(out)[0], scale_swap(out)[1])}."],
            [f"Outward taxable supplies were {amt(scale_swap(out)[0], scale_swap(out)[1])}."])),
        (U, "wrong_date", "value", ctx.pick(
            [f"The return was filed on {any_dt(ctx, wrong_day(ctx, filed, [due]))}."],
            [f"The date of filing was {any_dt(ctx, wrong_day(ctx, filed, [due]))}."])),
        (U, "direction", "direction", ctx.pick(
            [f"The return was filed before the due date."],
            [f"{co_s} filed the return ahead of the due date."])),
        (U, "wrong_number", "interval", ctx.pick(
            [f"The return was filed {late + 10} days after the due date."],
            [f"{co_s} filed {late + 10} days late."])),
        (U, "invented", "invented", ctx.pick(
            [f"The company also reported zero-rated exports in the same return."],
            [f"The return shows a reversal of input tax credit for the period."])),
    ]
    return passage, "What does the GST return show?", c


def fam_repayment(ctx: Ctx):
    n = ctx.rng.choice([12, 16, 20, 24, 28])
    start = date(ctx.rng.randint(2024, 2025), ctx.rng.choice([3, 6, 9, 12]), 30 if ctx.rng.random() < 0.5 else 15)
    pre = ctx.rng.choice([12, 18, 24])
    od = ctx.rng.choice([60, 90])
    bank, bank_s = ctx.bank()
    co, co_s = ctx.company()
    if ctx.split == "dev":
        passage = (f"The Borrower, {co}, shall repay the term loan to {bank} in {n} equal quarterly instalments "
                   f"starting {dt(start, 'long')}. Prepayment is permitted without penalty after the first {pre} "
                   f"months. If any instalment is overdue by more than {od} days, the Lender may recall the entire loan.")
    else:
        passage = (f"Clause 7 (Repayment). {co} (the Borrower) will repay the loan from {bank} (the Lender) in {n} "
                   f"equal quarterly instalments, the first falling due on {dt(start, 'slash')}. Clause 8 "
                   f"(Prepayment). No prepayment charge applies after {pre} months from first disbursement. Clause 12 "
                   f"(Events of default). The Lender may recall the loan if an instalment remains unpaid for more "
                   f"than {od} days.")
    c = [
        (S, "faithful_hard", "unit_conversion", ctx.pick(
            [f"The loan is repaid over {words(n // 4)} years in quarterly instalments."],
            [f"Repayment takes {n // 4} years, one instalment every quarter."])),
        (S, "faithful_hard", "reformat", ctx.pick(
            [f"Repayment begins on {any_dt(ctx, start)}."],
            [f"The first instalment falls due on {any_dt(ctx, start, 'slash')}."])),
        (S, "faithful", "paraphrase", ctx.pick(
            [f"After the first {pre} months, the loan can be prepaid with no penalty."],
            [f"There is no prepayment charge after {pre} months."])),
        (S, "faithful", "paraphrase", ctx.pick(
            [f"The Lender can recall the whole loan if an instalment is more than {od} days overdue."],
            [f"{bank_s} may recall the loan if an instalment is unpaid for over {od} days."])),
        (U, "wrong_period", "value", ctx.pick(
            [f"The Borrower shall repay the term loan in {n} equal monthly instalments."],
            [f"The loan is repaid in {n} half-yearly instalments."])),
        (U, "negation", "negation", ctx.pick(
            [f"Prepayment is not permitted at any time during the life of the loan."],
            [f"A prepayment charge applies throughout the life of the loan."])),
        (U, "wrong_number", "value", ctx.pick(
            [f"The Lender may recall the loan if an instalment is overdue by more than {od - 30} days."],
            [f"The loan can be recalled once an instalment is {od - 30} days overdue."])),
        (U, "swapped_parties", "roles", ctx.pick(
            [f"If an instalment is overdue by more than {od} days, the Borrower may recall the entire loan."],
            [f"{co_s} may recall the loan if {bank_s} misses an instalment."])),
        (U, "wrong_date", "value", ctx.pick(
            [f"Repayment of the term loan starts on {any_dt(ctx, wrong_day(ctx, start))}."],
            [f"The first instalment is due on {any_dt(ctx, wrong_day(ctx, start))}."])),
    ]
    return passage, "How must the loan be repaid?", c


def fam_directors(ctx: Ctx):
    p = ctx.person()
    din = f"{ctx.rng.randint(1000000, 9999999):08d}"
    co, co_s = ctx.company()
    co2, co2_s = ctx.company("Traders", ctx.rng.choice(["Pvt Ltd", "LLP"]))
    since = ctx.day(2015, 2020)
    app = ctx.day(2021, 2022)
    res = app + timedelta(days=ctx.rng.choice([365 + 120, 600, 700, 730 + 61]))
    months = round((res - app).days / 30.44)
    if ctx.split == "dev":
        passage = (f"{p} (DIN {din}) has been a director of {co} since {dt(since, 'long')}. {p} was also appointed a "
                   f"director of {co2} on {dt(app, 'long')} and resigned from that board on {dt(res, 'long')}.")
    else:
        passage = (f"MCA master data extract. Director: {p}, DIN {din}.\nCompany | Appointed | Ceased\n"
                   f"{co} | {dt(since, 'dash')} | -\n{co2} | {dt(app, 'dash')} | {dt(res, 'dash')}")
    c = [
        (S, "faithful_hard", "reformat", ctx.pick(
            [f"{p}, DIN {din}, joined the {co_s} board in {MONTHS[since.month - 1]} {since.year}."],
            [f"{p} has served on the board of {co_s} since {MONTHS[since.month - 1][:3]} {since.year}."])),
        (S, "faithful_hard", "possessive", ctx.pick(
            [f"{p} left {co2_s}' board on {any_dt(ctx, res)}." if co2_s.endswith("s") else
             f"{p} left the board of {co2_s} on {any_dt(ctx, res)}."],
            [f"{p}'s directorship of {co2_s} ended on {any_dt(ctx, res, 'dash')}."])),
        (S, "faithful_hard", "interval", ctx.pick(
            [f"{p} served as a director of {co2_s} for about {months} months."],
            [f"{p} was on the {co2_s} board for roughly {months} months."])),
        (U, "wrong_number", "identifier", ctx.pick(
            [f"{p} holds DIN {din[:-2] + din[-1] + din[-2] if din[-1] != din[-2] else din[:-1] + str((int(din[-1]) + 4) % 10)}."],
            [f"The DIN of {p} is {din[:-2] + din[-1] + din[-2] if din[-1] != din[-2] else din[:-1] + str((int(din[-1]) + 4) % 10)}."])),
        (U, "wrong_date", "value", ctx.pick(
            [f"{p} has been a director of {co_s} since {any_dt(ctx, wrong_day(ctx, since))}."],
            [f"{p} was appointed to the {co_s} board on {any_dt(ctx, wrong_day(ctx, since))}."])),
        (U, "contradiction", "contradiction", ctx.pick(
            [f"{p} resigned from the board of {co2_s} on {any_dt(ctx, app)}."],
            [f"{p} was appointed a director of {co2_s} on {any_dt(ctx, res)}."])),
        (U, "wrong_entity", "value", ctx.pick(
            [f"{p} has been a director of {ctx.other_company()} since {any_dt(ctx, since)}."],
            [f"{p} is also a director of {ctx.other_company()}."])),
        (U, "wrong_number", "interval", ctx.pick(
            [f"{p} served as a director of {co2_s} for about {months + 9} months."],
            [f"{p} was on the {co2_s} board for roughly {months + 9} months."])),
    ]
    return passage, "What directorships does the person hold?", c


# ----------------------------------------------------------------------------------------- test-only families

def fam_guarantee(ctx: Ctx):
    g1, g2 = ctx.person(), ctx.person()
    co, co_s = ctx.company()
    bank, bank_s = ctx.bank()
    a = ctx.rng.choice([3, 5, 7, 9, 12]) * 10**7
    nw1, nw2 = ctx.rng.choice([18, 24, 31, 46]) * 10**6, ctx.rng.choice([9, 12, 15, 22]) * 10**6
    d = ctx.day()
    ctx.values |= {a, nw1, nw2, nw1 + nw2}
    passage = (f"By a deed of guarantee dated {dt(d, 'long')}, {g1} and {g2} jointly and severally guarantee the "
               f"repayment of the term loan of {amt(a, 'crore')} availed by {co} from {bank}. The guarantee is "
               f"irrevocable and continues until the loan is fully repaid. The guarantors' declared net worth is "
               f"{amt(nw1, 'crore')} and {amt(nw2, 'crore')} respectively.")
    c = [
        (S, "faithful_hard", "converse", f"{co_s} borrowed {any_amt(ctx, a)} from {bank_s}."),
        (S, "faithful_hard", "possessive", f"{g1} and {g2} guaranteed {co_s}'s term loan."),
        (S, "faithful_hard", "computed_total",
         f"The guarantors' combined declared net worth is {any_amt(ctx, nw1 + nw2, styles=['crore', 'lakh'])}."),
        (S, "faithful", "paraphrase", f"The guarantee cannot be revoked and lasts until the loan is repaid."),
        (U, "swapped_parties", "converse", f"{bank_s} borrowed {any_amt(ctx, a)} from {co_s}."),
        (U, "negation", "negation", f"The guarantors may revoke the guarantee at any time."),
        (U, "wrong_number", "value", f"The guaranteed term loan is {any_amt(ctx, wrong_amount(ctx, a))}."),
        (U, "wrong_entity", "value", f"{ctx.other_person()} is one of the guarantors."),
        (U, "arithmetic", "computed_total",
         f"The guarantors' combined declared net worth is {any_amt(ctx, wrong_amount(ctx, nw1 + nw2), styles=['crore', 'lakh'])}."),
        (U, "invented", "invented", f"The guarantee is capped at half of the loan amount."),
    ]
    return passage, "What does the guarantee deed say?", c


def fam_fundflow(ctx: Ctx):
    co, co_s = ctx.company()
    bank, bank_s = ctx.bank()
    rel, rel_s = ctx.company("Traders", "LLP")
    third, third_s = ctx.company()
    dirn = ctx.person()
    a = ctx.rng.choice([4, 5, 6, 8, 10]) * 10**7
    x = int(a * ctx.rng.choice([0.4, 0.5, 0.6, 0.75]))
    y = int(x * ctx.rng.choice([0.5, 0.8, 0.9]) / 10**5) * 10**5
    d1 = ctx.day(2023, 2024)
    gap = ctx.rng.choice([1, 2, 3, 6])
    d2 = d1 + timedelta(days=gap)
    d3 = d2 + timedelta(days=ctx.rng.choice([1, 4, 8]))
    ctx.values |= {a, x, y, a - x, x - y}
    passage = (f"Fund-flow note. On {dt(d1, 'long')}, {co} received {amt(a, 'crore')} from {bank} as disbursement of "
               f"the term loan. On {dt(d2, 'long')}, {co} transferred {amt(x, 'crore')} to {rel}, a firm in which "
               f"director {dirn} is a partner. On {dt(d3, 'long')}, {rel} transferred {amt(y, 'crore')} to {third}.")
    share = x / a * 100
    c = [
        (S, "faithful_hard", "converse", f"{rel_s} received {any_amt(ctx, x)} from {co_s} on {any_dt(ctx, d2)}."),
        (S, "faithful_hard", "interval",
         f"{words(gap).capitalize()} day{'s' if gap > 1 else ''} after the disbursement, {co_s} moved {any_amt(ctx, x)} to {rel_s}."),
        (S, "faithful_hard", "computed_pct", f"{round(share)}% of the disbursed loan was transferred to {rel_s}."),
        (S, "faithful", "paraphrase", f"{rel_s}, which is linked to director {dirn}, passed {any_amt(ctx, y)} on to {third_s}."),
        (U, "swapped_parties", "converse", f"{rel_s} transferred {any_amt(ctx, x)} to {co_s} on {any_dt(ctx, d2)}."),
        (U, "direction", "direction", f"{co_s} received {any_amt(ctx, x)} from {rel_s}."),
        (U, "wrong_number", "value", f"{co_s} transferred {any_amt(ctx, wrong_amount(ctx, x))} to {rel_s}."),
        (U, "wrong_date", "value", f"The loan was disbursed on {any_dt(ctx, wrong_day(ctx, d1, [d2, d3]))}."),
        (U, "arithmetic", "computed_pct", f"{round(share) + 15}% of the disbursed loan was transferred to {rel_s}."),
        (U, "invented", "invented", f"{rel_s} returned the funds to {co_s} within a week."),
    ]
    return passage, "Where did the loan money go?", c


def fam_email(ctx: Ctx):
    p = ctx.person()
    bank, bank_s = ctx.bank()
    co, co_s = ctx.company()
    d = ctx.day()
    days = ctx.rng.choice([30, 45, 60])
    amt_due = ctx.rng.choice([12, 18, 25, 40]) * 10**5
    reply = d + timedelta(days=ctx.rng.choice([3, 5, 9]))
    ctx.values |= {amt_due}
    passage = (f"On {dt(d, 'long')}, {p}, a director of {co}, wrote to {bank} asking for {days} more days to pay the "
               f"overdue instalment of {amt(amt_due, 'lakh')}. On {dt(reply, 'long')}, {bank_s} declined the request "
               f"and asked for payment within seven days.")
    c = [
        (S, "faithful_hard", "declined", f"{bank_s} refused {p}'s request for more time."),
        (S, "faithful", "paraphrase", f"{p} asked for a {days}-day extension to pay {any_amt(ctx, amt_due)}."),
        (S, "faithful_hard", "reformat", f"The bank replied on {any_dt(ctx, reply)}."),
        (U, "negation", "declined", f"{bank_s} agreed to give {co_s} {days} more days."),
        (U, "wrong_number", "value", f"{p} asked for {days + 30} more days to pay the instalment."),
        (U, "swapped_parties", "roles", f"{bank_s} asked {p} for {days} more days to pay."),
        (U, "wrong_scale", "value", f"The overdue instalment was {amt(scale_swap(amt_due)[0], scale_swap(amt_due)[1])}."),
        (U, "invented", "invented", f"{bank_s} also charged a penalty of 2% on the overdue amount."),
    ]
    return passage, "What did the borrower ask the bank?", c


FAMILIES: dict[str, tuple[Callable, tuple[str, ...]]] = {
    "sanction": (fam_sanction, ("dev", "test")),
    "statement_table": (fam_statement_table, ("dev", "test")),
    "invoice": (fam_invoice, ("dev", "test")),
    "board": (fam_board, ("dev", "test")),
    "lease": (fam_lease, ("dev", "test")),
    "financials": (fam_financials, ("dev", "test")),
    "valuation": (fam_valuation, ("dev", "test")),
    "insurance": (fam_insurance, ("dev", "test")),
    "gst": (fam_gst, ("dev", "test")),
    "repayment": (fam_repayment, ("dev", "test")),
    "directors": (fam_directors, ("dev", "test")),
    "guarantee": (fam_guarantee, ("test",)),
    "fundflow": (fam_fundflow, ("test",)),
    "email": (fam_email, ("test",)),
}
DOCS_PER_FAMILY = {"dev": 4, "test": 4}


def cases(split: str | None = None) -> list[dict]:
    """All generated cases for a split (or both). Deterministic: same code, same output."""
    out = []
    for sp in (["dev", "test"] if split in (None, "all") else [split]):
        for fam, (fn, splits) in FAMILIES.items():
            if sp not in splits:
                continue
            for i in range(DOCS_PER_FAMILY[sp]):
                ctx = Ctx(random.Random(f"{VERSION}:{sp}:{fam}:{i}"), sp)
                passage, question, claims = fn(ctx)
                doc_id = f"{sp[0].upper()}-{fam}-{i}"
                for j, (label, kind, tag, text) in enumerate(claims):
                    out.append({"id": f"{doc_id}-{j:02d}", "source_id": doc_id, "family": fam, "split": sp,
                                "question": question, "passage": passage, "claim": text, "label": label,
                                "type": kind, "tag": tag})
    return out

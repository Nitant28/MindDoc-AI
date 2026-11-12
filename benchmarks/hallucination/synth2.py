"""HB-Synth v2: a fresh held-out claim set, written before the R6 bug fixes (pre-registered).

HB-Synth v1's test split was scored once and then examined, so it is now tuning data. v2 exists only to measure the
fixes that follow it. Everything is new: name pools, document types, layouts and every passage and claim wording.
It has a single split, `test`, and the runner scores it only with --final on committed code.

Twelve document types: term sheet (table, ₹ in lakh), statement (Markdown table), purchase order, stock statement,
auditor's report, disbursement advice, leave-and-licence agreement, financial summary (table, ₹ lakh, two years),
GST show-cause notice, shareholding, guarantee invocation, and borrower correspondence.

Labels follow the annotation guideline in README.md. The same developer wrote this set and the verifier, and wrote
it knowing the five bug classes it must measure; it includes realistic claims the verifier is known not to handle
(three-figure totals, a date plus a number of days, labels written after the figure), so it is not tailored to
the fixes. Not an independent test.
"""
from __future__ import annotations

import random
from datetime import date, timedelta

from benchmarks.hallucination.synth import (MONTHS, S, U, Ctx, amt, any_amt, any_dt, dt, grouped, pct, scale_swap,
                                            words, wrong_amount, wrong_day)

VERSION = "hb-synth-v2"

POOL = dict(
    firms=["Brahmani", "Mahanadi", "Sharavati", "Tungabhadra", "Indravati", "Ghaghara", "Gomti", "Betwa",
           "Damodar", "Periyar", "Pamba", "Bhima", "Wainganga", "Sutlej", "Chenab", "Ravi"],
    banks=["Eastern Plains Bank", "Saurashtra Mercantile Bank", "Himalayan Commerce Bank Ltd"],
    first=["Arvind", "Nandini", "Kuldeep", "Shreya", "Imran", "Pallavi", "Rohan", "Sneha", "Abdul", "Geeta"],
    last=["Banerjee", "Kamath", "Sodhi", "Pillai", "Qureshi", "Hegde", "Mishra", "Bose"],
    cities=["Nagpur", "Visakhapatnam", "Mysuru", "Bhubaneswar", "Kochi", "Raipur"],
    estates=["APIIC Sri City", "MIDC Butibori", "IDCO Khurda"],
    insurers=["Ajanta General Insurance", "Ellora General Insurance"],
    audit_firms=["Kamath & Pillai", "Hegde & Bose"],
)
SECTORS = ["Polymers", "Foods", "Textiles", "Alloys", "Pharma", "Logistics", "Chemicals", "Exports", "Infra",
           "Papers", "Ceramics", "Engineering", "Packaging", "Agro"]


class Ctx2(Ctx):
    @property
    def pool(self) -> dict:
        return POOL

    def company(self, sector=None, form=None):
        return super().company(sector or self.rng.choice(SECTORS), form)


def lakh_cell(n: int) -> str:
    """A rupee amount written in a '₹ lakh' table: 85000000 -> 850.00."""
    return f"{grouped(n // 100000)}.{(n % 100000) // 1000:02d}"


# ------------------------------------------------------------------------------------------------- families

def fam_term_sheet(ctx: Ctx2):
    bank, bank_s = ctx.bank()
    co, co_s = ctx.company()
    tl = ctx.rng.choice([450, 600, 850, 1200]) * 10**5
    cc = ctx.rng.choice([150, 200, 300, 400]) * 10**5
    r1, r2 = ctx.rng.choice([10.4, 10.75, 11.1]), ctx.rng.choice([9.6, 9.9, 10.2])
    tenor = ctx.rng.choice([60, 72, 84])
    fee = ctx.rng.choice([0.5, 0.75])
    d = ctx.day()
    ctx.values |= {tl, cc, tl + cc, int((tl + cc) * fee / 100)}
    passage = (f"Term sheet: {bank} to {co} (amounts ₹ in lakh)\nFacility | Limit | Rate (% p.a.) | Tenor (months)\n"
               f"Term loan | {lakh_cell(tl)} | {r1:.2f} | {tenor}\nCash credit | {lakh_cell(cc)} | {r2:.2f} | 12\n"
               f"Processing charges: {pct(fee)}% of the total limit, plus GST. Date of sanction: {dt(d, 'dash')}.")
    total, charge = tl + cc, int((tl + cc) * fee / 100)
    c = [
        (S, "faithful_hard", "scaled_table", f"{bank_s} sanctioned a term loan of {any_amt(ctx, tl, styles=['crore', 'g'])} to {co_s}."),
        (S, "faithful", "paraphrase", f"The term loan carries interest at {r1:.2f}% a year."),
        (S, "faithful_hard", "unit_conversion", f"The term loan runs for {words(tenor // 12)} years."),
        (S, "faithful_hard", "computed_total", f"The two facilities add up to {any_amt(ctx, total, styles=['crore', 'lakh'])}."),
        (S, "faithful_hard", "computed_pct", f"Processing charges come to {any_amt(ctx, charge, styles=['g', 'lakh'])} before GST."),
        (S, "faithful_hard", "scaled_table", f"The cash credit limit is {any_amt(ctx, cc, styles=['crore', 'lakh'])}."),
        (U, "wrong_scale", "scaled_table", f"The term loan is {amt(scale_swap(tl)[0], scale_swap(tl)[1])}."),
        (U, "wrong_number", "value", f"The term loan carries interest at {r1 + 1:.2f}% a year."),
        (U, "wrong_number", "unit_conversion", f"The term loan runs for {words(tenor // 12 - 2)} years."),
        (U, "arithmetic", "computed_total", f"The two facilities add up to {any_amt(ctx, wrong_amount(ctx, total), styles=['g'])}."),
        (U, "swapped_parties", "roles", f"{co_s} sanctioned a term loan of {any_amt(ctx, tl, styles=['crore'])} to {bank_s}."),
        (U, "wrong_date", "value", f"The facilities were sanctioned on {any_dt(ctx, wrong_day(ctx, d))}."),
        (U, "invented", "invented", "The term sheet requires a debt service reserve equal to two instalments."),
    ]
    return passage, "What does the term sheet offer?", c


def fam_statement_md(ctx: Ctx2):
    bank, _ = ctx.bank()
    cust, cust_s = ctx.company()
    supp, supp_s = ctx.company()
    y, m = ctx.rng.randint(2023, 2025), ctx.rng.randint(1, 12)
    days = sorted(ctx.rng.sample(range(1, 28), 4))
    inflow = ctx.rng.randint(20, 90) * 15000
    upi = ctx.rng.randint(2, 12) * 2500
    pay = ctx.rng.randint(10, 60) * 12000
    atm = ctx.rng.choice([10000, 20000, 30000])
    bal = pay + atm + ctx.rng.randint(5, 40) * 10000 + 450  # never overdrawn
    entries = [("in", f"NEFT-{cust}", inflow, cust_s), ("out", f"UPI/{supp}/invoice", pay, supp_s),
               ("out", "ATM cash", atm, None), ("in", "UPI collection counter", upi, None)]
    ctx.rng.shuffle(entries)
    lines = ["| Value date | Transaction details | Debit (₹) | Credit (₹) | Balance (₹) |",
             "| --- | --- | --- | --- | --- |"]
    rows = []
    for dd, (kind, text, v, cp) in zip(days, entries):
        bal = bal + v if kind == "in" else bal - v
        d = date(y, m, dd)
        rows.append((d, kind, v, cp, bal))
        lines.append(f"| {dt(d, 'slash')} | {text} | {grouped(v) + '.00' if kind == 'out' else ''} | "
                     f"{grouped(v) + '.00' if kind == 'in' else ''} | {grouped(bal)}.00 |")
    ctx.values |= {inflow, upi, pay, atm, rows[-1][4], pay + atm}
    passage = f"Account statement, {bank}, {MONTHS[m - 1]} {y}\n" + "\n".join(lines)
    rin = next(r for r in rows if r[3] == cust_s)
    rout = next(r for r in rows if r[3] == supp_s)
    c = [
        (S, "faithful_hard", "table_column", f"{any_amt(ctx, inflow)} came in from {cust_s} on {any_dt(ctx, rin[0], 'slash')}."),
        (S, "faithful_hard", "table_column", f"{supp_s} was paid {any_amt(ctx, pay)} on {any_dt(ctx, rout[0], 'slash')}."),
        (S, "faithful_hard", "computed_total", f"Total withdrawals in the statement come to {any_amt(ctx, pay + atm)}."),
        (S, "faithful", "paraphrase", f"The month ended with a balance of {any_amt(ctx, rows[-1][4])}."),
        (S, "faithful_hard", "table_column", f"On {any_dt(ctx, rin[0])}, {any_amt(ctx, inflow)} was deposited by {cust_s}."),
        (U, "direction", "table_column", f"{cust_s} received {any_amt(ctx, inflow)} from the account on {any_dt(ctx, rin[0])}."),
        (U, "direction", "table_column", f"On {any_dt(ctx, rout[0])}, {any_amt(ctx, pay)} was deposited into the account by {supp_s}."),
        (U, "wrong_number", "value", f"The month ended with a balance of {any_amt(ctx, wrong_amount(ctx, rows[-1][4]))}."),
        (U, "wrong_date", "value", f"{supp_s} was paid {any_amt(ctx, pay)} on {any_dt(ctx, wrong_day(ctx, rout[0], [r[0] for r in rows]))}."),
        (U, "wrong_entity", "value", f"{any_amt(ctx, inflow)} came in from {ctx.other_company()} on {any_dt(ctx, rin[0])}."),
        (U, "arithmetic", "computed_total", f"Total withdrawals in the statement come to {any_amt(ctx, wrong_amount(ctx, pay + atm))}."),
        (U, "invented", "invented", "A standing instruction for loan repayment failed during the month."),
    ]
    return passage, "What happened in the account this month?", c


def fam_purchase_order(ctx: Ctx2):
    buyer, buyer_s = ctx.company()
    seller, seller_s = ctx.company()
    no = f"PO/{ctx.rng.randint(100, 999)}/{ctx.rng.randint(23, 25)}"
    item, unit = ctx.rng.choice([("ductile iron pipe", "metre"), ("copper cathodes", "tonne"),
                                 ("kraft paper", "reel"), ("PET preforms", "carton")])
    q = ctx.rng.choice([40, 60, 75, 120, 150])
    rate = ctx.rng.choice([850, 1200, 2400, 4500, 7800])
    value = q * rate
    adv = ctx.rng.choice([10, 20, 25])
    dd = ctx.rng.choice([14, 21, 28, 35])
    d = ctx.day()
    ctx.values |= {rate, value, value * adv // 100}
    passage = (f"Purchase order {no} | Date: {dt(d, 'long0')} | Buyer: {buyer} | Supplier: {seller}\n"
               f"Item: {item} | Quantity: {q} {unit}s | Rate: ₹{grouped(rate)} per {unit}\n"
               f"Delivery: within {dd} days of the order date. Advance: {adv}% of the order value, balance on "
               f"delivery.")
    c = [
        (S, "faithful_hard", "converse", f"{buyer_s} ordered {q} {unit}s of {item} from {seller_s}."),
        (S, "faithful_hard", "computed_product", f"The order is worth {any_amt(ctx, value)}."),
        (S, "faithful_hard", "computed_pct", f"An advance of {any_amt(ctx, value * adv // 100)} is payable."),
        (S, "faithful_hard", "unit_conversion", f"{seller_s} must deliver within {words(dd // 7)} weeks."),
        (S, "faithful_hard", "date_arithmetic", f"Delivery is due by {any_dt(ctx, d + timedelta(days=dd))}."),
        (S, "faithful", "paraphrase", f"The balance is payable on delivery."),
        (U, "swapped_parties", "converse", f"{seller_s} ordered {item} from {buyer_s}."),
        (U, "arithmetic", "computed_product", f"The order is worth {any_amt(ctx, wrong_amount(ctx, value))}."),
        (U, "wrong_number", "value", f"An advance of {adv + 15}% of the order value is payable."),
        (U, "wrong_date", "value", f"The purchase order is dated {any_dt(ctx, wrong_day(ctx, d))}."),
        (U, "invented", "invented", "The order carries a penalty of 1% for each week of delay."),
    ]
    return passage, "What does the purchase order say?", c


def fam_stock_statement(ctx: Ctx2):
    co, co_s = ctx.company()
    a, b, f = (ctx.rng.randint(40, 160) * 10**5, ctx.rng.randint(10, 60) * 10**5, ctx.rng.randint(30, 120) * 10**5)
    rec = ctx.rng.randint(50, 200) * 10**5
    m1, m2 = ctx.rng.choice([20, 25]), ctx.rng.choice([30, 40])
    d = ctx.day()
    ctx.values |= {a, b, f, rec, a + b + f}
    passage = (f"Stock and book-debt statement of {co} as on {dt(d, 'long')}\nRaw material: {amt(a, 'g')}\n"
               f"Work in progress: {amt(b, 'g')}\nFinished goods: {amt(f, 'g')}\nReceivables up to 90 days: "
               f"{amt(rec, 'g')}\nMargin: {m1}% on stock, {m2}% on receivables.")
    c = [
        (S, "faithful_hard", "computed_total3", f"Total stock, adding raw material, work in progress and finished goods, is {any_amt(ctx, a + b + f)}."),
        (S, "faithful", "reformat", f"Finished goods are valued at {any_amt(ctx, f, 'g')}."),
        (S, "faithful", "reformat", f"Receivables not older than 90 days stand at {any_amt(ctx, rec, 'g')}."),
        (S, "faithful", "paraphrase", f"A {m2}% margin applies to receivables."),
        (S, "faithful_hard", "computed_pct", f"After the {m2}% margin, receivables give drawing power of {any_amt(ctx, rec * (100 - m2) // 100)}."),
        (U, "wrong_number", "value", f"A {m1 + 10}% margin applies to stock."),
        (U, "wrong_scale", "value", f"Raw material is valued at {amt(scale_swap(a)[0], scale_swap(a)[1])}."),
        (U, "wrong_date", "value", f"The statement is as on {any_dt(ctx, wrong_day(ctx, d))}."),
        (U, "arithmetic", "computed_pct", f"After the {m2}% margin, receivables give drawing power of {any_amt(ctx, rec * (100 - m2 - 15) // 100)}."),
        (U, "invented", "invented", "The bank's stock auditor verified the inventory last quarter."),
    ]
    return passage, "What does the stock statement declare?", c


def fam_audit(ctx: Ctx2):
    co, co_s = ctx.company()
    firm = ctx.rng.choice(POOL["audit_firms"])
    ctx.used.add(firm)
    partner = ctx.person()
    y = ctx.rng.randint(2021, 2024)
    rec = ctx.rng.randint(80, 900) * 10**5
    signed = date(y + 1, ctx.rng.choice([5, 6, 8, 9]), ctx.rng.randint(1, 28))
    ctx.values |= {rec}
    passage = (f"Independent auditor's report on the financial statements of {co} for FY {y}-{str(y + 1)[2:]}. In our "
               f"opinion, except for the effects of the matter described in the Basis for Qualified Opinion paragraph, "
               f"the financial statements give a true and fair view. Basis for Qualified Opinion: trade receivables of "
               f"{amt(rec, 'lakh2')} could not be confirmed with the debtors. We have not reported any fraud under "
               f"section 143(12) of the Act. For {firm}, Chartered Accountants. {partner}, Partner. {dt(signed, 'slash')}.")
    c = [
        (S, "faithful", "paraphrase", f"The auditor gave a qualified opinion on {co_s}'s FY {y}-{str(y + 1)[2:]} accounts."),
        (S, "faithful_hard", "negation_paraphrase", f"{firm} reported no fraud under section 143(12)."),
        (S, "faithful", "reformat", f"Receivables of {any_amt(ctx, rec, 'lakh2')} could not be confirmed."),
        (S, "faithful_hard", "reformat", f"{partner} signed the report on {any_dt(ctx, signed, 'slash')}."),
        (U, "negation", "negation", "The auditor reported a fraud under section 143(12)."),
        (U, "contradiction", "contradiction", "The auditor gave an unqualified opinion on the financial statements."),
        (U, "wrong_date", "value", f"The report covers FY {y + 1}-{str(y + 2)[2:]}."),
        (U, "wrong_number", "value", f"Receivables of {any_amt(ctx, wrong_amount(ctx, rec))} could not be confirmed."),
        (U, "wrong_entity", "value", f"{ctx.other_person()} signed the report as partner."),
        (U, "invented", "invented", "The auditor resigned before the annual general meeting."),
    ]
    return passage, "What did the auditor report?", c


def fam_disbursement(ctx: Ctx2):
    bank, bank_s = ctx.bank()
    co, co_s = ctx.company()
    supp, supp_s = ctx.company("Engineering")
    x = ctx.rng.choice([5, 6, 8, 10]) * 10**7
    y = int(x * ctx.rng.choice([0.4, 0.5, 0.6, 0.75]))
    d1 = ctx.day()
    inv = f"{ctx.rng.choice(['SE', 'ME', 'TK'])}/{ctx.rng.randint(1000, 9999)}"
    ctx.values |= {x, y, x - y}
    passage = (f"Disbursement advice from {bank} to {co}. Of the sanctioned term loan of {amt(x, 'crore')}, "
               f"{amt(y, 'crore')} was released on {dt(d1, 'long')} directly to {supp} against invoice {inv} for "
               f"machinery. The undrawn balance is {amt(x - y, 'crore')}.")
    share = round(y / x * 100)
    c = [
        (S, "faithful_hard", "converse", f"{supp_s} received {any_amt(ctx, y)} from {bank_s} on {any_dt(ctx, d1)}."),
        (S, "faithful_hard", "computed_pct_label_after", f"About {share}% of the sanctioned loan has been released."),
        (S, "faithful", "reformat", f"{any_amt(ctx, x - y)} of the loan is yet to be drawn."),
        (S, "faithful", "paraphrase", "The money went straight to the machinery supplier."),
        (U, "swapped_parties", "converse", f"{supp_s} paid {any_amt(ctx, y)} to {bank_s}."),
        (U, "wrong_date", "value", f"The disbursement was made on {any_dt(ctx, wrong_day(ctx, d1))}."),
        (U, "wrong_number", "value", f"{any_amt(ctx, wrong_amount(ctx, y))} was released to {supp_s}."),
        (U, "arithmetic", "computed_pct_label_after", f"About {share + 20}% of the sanctioned loan has been released."),
        (U, "invented", "invented", f"{co_s} has asked to divert the balance to working capital."),
    ]
    return passage, "How was the loan disbursed?", c


def fam_licence(ctx: Ctx2):
    licensor, licensor_s = ctx.company("Estates", "LLP")
    licensee, licensee_s = ctx.company()
    premises = f"{ctx.rng.choice(['office', 'shop', 'warehouse'])} no. {ctx.rng.randint(101, 812)}"
    months = ctx.rng.choice([24, 36, 60])
    fee = ctx.rng.choice([80, 120, 175, 220]) * 1000
    fee2 = fee + ctx.rng.choice([5, 10, 15]) * 1000
    k = ctx.rng.choice([3, 6, 10])
    dep = fee * k
    d = ctx.day()
    ctx.values |= {fee, fee2, dep, fee * 12}
    passage = (f"Leave and licence agreement dated {dt(d, 'long')}. {licensor} (Licensor) permits {licensee} (Licensee) "
               f"to use {premises} for {months} months. Licence fee: {amt(fee, 'g')} per month for the first 12 months, "
               f"then {amt(fee2, 'g')} per month. Interest-free security deposit: {amt(dep, 'g')}.")
    c = [
        (S, "faithful_hard", "converse", f"{licensee_s} has taken {premises} on licence from {licensor_s}."),
        (S, "faithful_hard", "computed_ratio", f"The deposit equals {words(k)} months of the initial licence fee."),
        (S, "faithful_hard", "unit_conversion", f"The licence runs for {words(months // 12)} years."),
        (S, "faithful_hard", "period_conversion", f"Licence fee for the first year totals {any_amt(ctx, fee * 12)}."),
        (S, "faithful", "paraphrase", f"After the first year the monthly fee becomes {any_amt(ctx, fee2)}."),
        (U, "swapped_parties", "converse", f"{licensor_s} has taken {premises} on licence from {licensee_s}."),
        (U, "wrong_period", "value", f"The licence fee is {any_amt(ctx, fee)} per year."),
        (U, "wrong_number", "value", f"The security deposit is {any_amt(ctx, wrong_amount(ctx, dep))}."),
        (U, "arithmetic", "computed_ratio", f"The deposit equals {words(k + 3)} months of the initial licence fee."),
        (U, "invented", "invented", "The Licensee may sublet the premises with notice."),
    ]
    return passage, "What are the licence terms?", c


def fam_financials_lakh(ctx: Ctx2):
    co, co_s = ctx.company()
    y = ctx.rng.choice([2021, 2022, 2023])
    rev1 = ctx.rng.randint(150, 450) * 10**6
    rev2 = int(rev1 * ctx.rng.uniform(1.06, 1.3) / 10**6) * 10**6
    e1 = ctx.rng.randint(20, 60) * 10**6
    e2 = int(e1 * ctx.rng.uniform(0.6, 0.92) / 10**5) * 10**5
    nw1 = ctx.rng.randint(80, 200) * 10**6
    nw2 = nw1 + ctx.rng.randint(3, 15) * 10**6
    ctx.values |= {rev1, rev2, e1, e2, nw1, nw2, nw2 - nw1, rev2 - rev1}
    fy1, fy2 = f"FY {y}-{str(y + 1)[2:]}", f"FY {y + 1}-{str(y + 2)[2:]}"
    passage = (f"Summary financials of {co}\nParticulars (₹ lakh) | {fy1} | {fy2}\n"
               f"Revenue | {lakh_cell(rev1)} | {lakh_cell(rev2)}\nEBITDA | {lakh_cell(e1)} | {lakh_cell(e2)}\n"
               f"Net worth | {lakh_cell(nw1)} | {lakh_cell(nw2)}")
    growth = round((rev2 - rev1) / rev1 * 100)
    c = [
        (S, "faithful_hard", "scaled_table", f"Revenue rose from {any_amt(ctx, rev1, styles=['crore'])} to {any_amt(ctx, rev2, styles=['crore'])}."),
        (S, "faithful_hard", "scaled_table", f"EBITDA slipped to {any_amt(ctx, e2, styles=['crore', 'lakh'])} in {fy2}."),
        (S, "faithful_hard", "computed_diff", f"Net worth grew by {any_amt(ctx, nw2 - nw1, styles=['lakh', 'crore'])}."),
        (S, "faithful_hard", "computed_pct_change", f"Revenue grew roughly {growth}% year on year."),
        (U, "direction", "from_to", f"EBITDA increased to {any_amt(ctx, e2, styles=['crore', 'lakh'])} in {fy2}."),
        (U, "wrong_scale", "scaled_table", f"Revenue in {fy2} was {amt(scale_swap(rev2)[0], scale_swap(rev2)[1])}."),
        (U, "wrong_date", "table_cell", f"Net worth was {any_amt(ctx, nw2, styles=['crore', 'lakh'])} in {fy1}."),
        (U, "arithmetic", "computed_pct_change", f"Revenue grew roughly {growth + 12}% year on year."),
        (U, "invented", "invented", f"{co_s} raised fresh equity in {fy2}."),
    ]
    return passage, "How did the company perform?", c


def fam_gst_notice(ctx: Ctx2):
    co, co_s = ctx.company()
    city = ctx.rng.choice(POOL["cities"])
    officer = f"the Superintendent, CGST Range-{ctx.rng.choice(['II', 'IV', 'VI'])}, {city}"
    t = ctx.rng.randint(8, 90) * 10**5
    d = ctx.day()
    ref = f"SCN-{ctx.rng.randint(10, 99)}/{d.year}"
    ctx.values |= {t}
    passage = (f"Show cause notice {ref} dated {dt(d, 'long')} issued by {officer} to {co} under section 73: tax "
               f"short paid of {amt(t, 'g')} for {MONTHS[ctx.rng.randint(0, 11)]} {d.year - 1}, with interest at 18% "
               f"per annum. Reply within 30 days of this notice.")
    c = [
        (S, "faithful", "paraphrase", f"{co_s} has 30 days to reply to the notice."),
        (S, "faithful", "reformat", f"The tax demanded is {any_amt(ctx, t)}."),
        (S, "faithful", "paraphrase", "Interest is charged at 18% a year."),
        (S, "faithful", "paraphrase", "The notice was issued under section 73."),
        (U, "wrong_period", "value", "Interest is charged at 18% a month."),
        (U, "wrong_number", "value", f"The tax demanded is {any_amt(ctx, wrong_amount(ctx, t))}."),
        (U, "wrong_date", "value", f"The notice is dated {any_dt(ctx, wrong_day(ctx, d))}."),
        (U, "negation", "negation", "No interest is payable on the short-paid tax."),
        (U, "swapped_parties", "roles", f"{co_s} issued a show cause notice to the Superintendent."),
        (U, "invented", "invented", "A penalty of ₹10,000 has already been levied."),
    ]
    return passage, "What does the GST notice demand?", c


def fam_shareholding(ctx: Ctx2):
    co, co_s = ctx.company()
    p1, p2 = ctx.person(), ctx.person()
    inv, inv_s = ctx.company("Ventures", "LLP")
    total = ctx.rng.choice([10, 20, 25]) * 10**5
    s1 = total * ctx.rng.choice([40, 45, 50]) // 100
    s2 = total * ctx.rng.choice([20, 25, 30]) // 100
    s3 = total - s1 - s2
    d = ctx.day()
    passage = (f"Shareholding of {co} as on {dt(d, 'long')}: {p1}, {grouped(s1)} shares; {p2}, {grouped(s2)} shares; "
               f"{inv}, {grouped(s3)} shares. Total paid-up shares: {grouped(total)} of ₹10 each.")
    ctx.values |= {s1, s2, s3, total}
    c = [
        (S, "faithful_hard", "computed_pct", f"{p1} holds {round(s1 / total * 100)}% of the paid-up shares."),
        (S, "faithful_hard", "computed_total", f"Together, {p1} and {p2} hold {grouped(s1 + s2)} shares."),
        (S, "faithful_hard", "computed_product_each", f"The paid-up capital is {any_amt(ctx, total * 10)}."),
        (S, "faithful", "reformat", f"{inv_s} owns {grouped(s3)} shares."),
        (U, "wrong_number", "computed_pct", f"{p1} holds {round(s1 / total * 100) - 15}% of the paid-up shares."),
        (U, "wrong_number", "value", f"{p2} holds {grouped(wrong_amount(ctx, s2))} shares."),
        (U, "wrong_entity", "value", f"{ctx.other_person()} is the largest shareholder."),
        (U, "arithmetic", "computed_total", f"Together, {p1} and {p2} hold {grouped(s1 + s2 + total // 10)} shares."),
        (U, "invented", "invented", f"{inv_s} has pledged its shares with a lender."),
    ]
    return passage, "Who owns the company?", c


def fam_invocation(ctx: Ctx2):
    bank, bank_s = ctx.bank()
    co, co_s = ctx.company()
    g = ctx.person()
    y = ctx.rng.randint(20, 90) * 10**5
    i = ctx.rng.randint(2, 15) * 10**5
    x = y + i
    d0 = ctx.day(2019, 2022)
    d = ctx.day(2024, 2025)
    ctx.values |= {x, y, i}
    passage = (f"Notice of invocation dated {dt(d, 'long')}. {bank} invokes the guarantee dated {dt(d0, 'long')} given by "
               f"{g} for the dues of {co}. Amount demanded: {amt(x, 'g')}, being the outstanding principal of "
               f"{amt(y, 'g')} plus interest of {amt(i, 'g')}. Payment is required within 15 days.")
    c = [
        (S, "faithful", "paraphrase", f"{bank_s} has called on {g} to pay {any_amt(ctx, x)}."),
        (S, "faithful", "reformat", f"Interest accounts for {any_amt(ctx, i)} of the demand."),
        (S, "faithful_hard", "converse", f"{g} guaranteed the dues of {co_s}."),
        (S, "faithful_hard", "number_words", f"{g} must pay within {words(15)} days."),
        (S, "faithful_hard", "reformat", f"The guarantee was given on {any_dt(ctx, d0)}."),
        (U, "swapped_parties", "roles", f"{g} invoked the guarantee given by {bank_s}."),
        (U, "wrong_number", "value", f"The amount demanded is {any_amt(ctx, wrong_amount(ctx, x))}."),
        (U, "wrong_date", "value", f"The guarantee was given on {any_dt(ctx, wrong_day(ctx, d0))}."),
        (U, "negation", "negation", f"{bank_s} has not invoked the guarantee."),
        (U, "invented", "invented", f"{g} has offered a one-time settlement."),
    ]
    return passage, "What does the invocation notice demand?", c


def fam_correspondence(ctx: Ctx2):
    bank, bank_s = ctx.bank()
    co, co_s = ctx.company()
    drop = ctx.rng.choice([12, 18, 22])
    a = ctx.rng.choice([8, 10, 12]) * 10**7
    b = a - ctx.rng.choice([2, 3]) * 10**7
    d = ctx.day()
    d2 = d + timedelta(days=ctx.rng.choice([6, 9, 14]))
    ctx.values |= {a, b}
    passage = (f"Letter dated {dt(d, 'long')} from {co} to {bank}: our sales declined by {drop}% in the first half "
               f"because of a plant shutdown; we request a reduction of the cash credit limit from {amt(a, 'crore')} to "
               f"{amt(b, 'crore')}. Reply dated {dt(d2, 'long')}: the bank declined to reduce the stock margin but "
               f"approved the reduced limit.")
    c = [
        (S, "faithful_hard", "declined", f"{co_s}'s sales fell {drop}% in the first half."),
        (S, "faithful", "paraphrase", f"The limit is being cut from {any_amt(ctx, a)} to {any_amt(ctx, b)}."),
        (S, "faithful", "paraphrase", f"{bank_s} approved the lower limit of {any_amt(ctx, b)}."),
        (S, "faithful_hard", "declined", f"{bank_s} refused to reduce the stock margin."),
        (U, "direction", "declined", f"{co_s}'s sales rose {drop}% in the first half."),
        (U, "negation", "declined", f"{bank_s} refused the reduced limit."),
        (U, "direction", "from_to", f"The limit is being raised from {any_amt(ctx, a)} to {any_amt(ctx, b)}."),
        (U, "wrong_number", "value", f"Sales declined by {drop + 10}% in the first half."),
        (U, "invented", "invented", f"{bank_s} also waived the renewal charges."),
    ]
    return passage, "What did the borrower and the bank write?", c


FAMILIES = {
    "term_sheet": fam_term_sheet, "statement_md": fam_statement_md, "purchase_order": fam_purchase_order,
    "stock_statement": fam_stock_statement, "audit": fam_audit, "disbursement": fam_disbursement,
    "licence": fam_licence, "financials_lakh": fam_financials_lakh, "gst_notice": fam_gst_notice,
    "shareholding": fam_shareholding, "invocation": fam_invocation, "correspondence": fam_correspondence,
}
DOCS_PER_FAMILY = 5


def cases(split: str | None = None) -> list[dict]:
    """The held-out set (single split 'test'). Deterministic."""
    if split not in (None, "all", "test"):
        return []
    out = []
    for fam, fn in FAMILIES.items():
        for i in range(DOCS_PER_FAMILY):
            ctx = Ctx2(random.Random(f"{VERSION}:test:{fam}:{i}"), "test")
            passage, question, claims = fn(ctx)
            doc_id = f"H-{fam}-{i}"
            for j, (label, kind, tag, text) in enumerate(claims):
                out.append({"id": f"{doc_id}-{j:02d}", "source_id": doc_id, "family": fam, "split": "test",
                            "question": question, "passage": passage, "claim": text, "label": label,
                            "type": kind, "tag": tag})
    return out

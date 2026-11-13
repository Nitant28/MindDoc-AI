"""StatementBench-Synth v0: seeded synthetic Indian-style bank statements with exact ground truth.

    python -m benchmarks.statements.generator --out benchmarks/statements/data --dev 10 --test 10

* Account histories are generated in exact paise (app.finance.money.Money); running balances are exact.
* Six parameterised layout families. A–D are the dev split; E–F are held out for test (never used in development).
  Layouts are generic column arrangements seen across many banks; bank names, IFSCs, parties and identifiers are
  fictional and do not reproduce any real bank's branding or document.
* Every statement is written as a text-layer PDF plus <id>.gold.json (header facts + every transaction row + page).
* Scanned variants (rasterise + noise) are produced in R4; v0 is text-layer only.
"""
from __future__ import annotations

import argparse
import json
import random
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

from app.finance.money import Money

BANKS = [("Meridian Bank Ltd", "MERI"), ("Sahyadri Co-operative Bank", "SAHY"), ("Konkan Commercial Bank", "KONK"),
         ("Deccan Trust Bank", "DECT")]
PARTIES = ["Shreeji Polymers Pvt Ltd", "Kaveri Agro Foods Ltd", "Sunrise Traders", "Orbit Realty LLP",
           "Godavari Cold Storage Ltd", "Meridian Logistics", "Anil Mehta", "Rekha Mehta", "Prakash Joshi",
           "Desai & Kulkarni", "Tarapur Steel Works", "Silvassa Packaging", "Bhiwandi Warehousing Co",
           "Nashik Agro Exports", "Vidarbha Cotton Mills", "Konkan Fisheries", "Pune Auto Components"]

# column spec: (role, header label, width in points); roles: date, value_date, narration, ref, debit, credit,
# amount, drcr, balance
LAYOUTS = {
    "A": dict(split="dev", date_fmt="%d/%m/%y", grouping="indian", balance="plain", od=False, header_pages="all",
              carry=False, cols=[("date", "Date", 48), ("narration", "Narration", 175), ("ref", "Chq./Ref.No.", 78),
                                 ("value_date", "Value Dt", 46), ("debit", "Withdrawal Amt.", 70),
                                 ("credit", "Deposit Amt.", 70), ("balance", "Closing Balance", 78)]),
    "B": dict(split="dev", date_fmt="%d %b %Y", grouping="western", balance="plain", od=False, header_pages="all",
              carry=False, cols=[("date", "Txn Date", 58), ("value_date", "Value Date", 58),
                                 ("narration", "Description", 170), ("ref", "Ref No./Cheque No.", 70),
                                 ("debit", "Debit", 62), ("credit", "Credit", 62), ("balance", "Balance", 70)]),
    "C": dict(split="dev", date_fmt="%d-%m-%Y", grouping="indian", balance="plain", od=False, header_pages="all",
              carry=False, cols=[("date", "Date", 60), ("narration", "Particulars", 240), ("amount", "Amount", 80),
                                 ("drcr", "Dr/Cr", 40), ("balance", "Balance", 90)]),
    "D": dict(split="dev", date_fmt="%d-%m-%Y", grouping="indian", balance="suffix", od=True, header_pages="all",
              carry=True, cols=[("date", "Tran Date", 60), ("narration", "Particulars", 230),
                                ("debit", "Withdrawals", 80), ("credit", "Deposits", 80), ("balance", "Balance", 90)]),
    # ---- held-out test layouts --------------------------------------------------------------------------------
    "E": dict(split="test", date_fmt="%d.%m.%Y", grouping="indian", balance="plain", od=False, header_pages="first",
              carry=False, cols=[("date", "Posting Date", 62), ("narration", "Transaction Details", 210),
                                 ("debit", "Debit Amount", 78), ("credit", "Credit Amount", 78),
                                 ("balance", "Running Balance", 85)]),
    "F": dict(split="test", date_fmt="%d-%b-%y", grouping="western", balance="crdr", od=True, header_pages="all",
              carry=True, cols=[("date", "Date", 55), ("narration", "Remarks", 250),
                                ("amount", "Amount (INR)", 95), ("balance", "Balance (INR)", 105)]),
}


@dataclass
class Txn:
    date: date
    value_date: date
    narration: str
    ref: str
    debit: Money = field(default_factory=Money.zero)
    credit: Money = field(default_factory=Money.zero)
    balance: Money = field(default_factory=Money.zero)
    page: int = 0


def _digits(rng: random.Random, n: int) -> str:
    return "".join(rng.choice("0123456789") for _ in range(n))


def _amount(rng: random.Random, small: bool = False) -> Money:
    if small:
        return Money(rng.choice([1180, 2360, 5900, 11800, 17700]) + rng.randint(0, 99))
    if rng.random() < 0.25:  # round amounts are common in business accounts
        return Money(rng.choice([5000, 10000, 25000, 50000, 100000, 250000, 500000]) * 100)
    exp = rng.uniform(3.0, 6.7)
    return Money(int(10 ** exp) * 100 + rng.randint(0, 99))


def make_history(rng: random.Random, od: bool, n: int, start: date) -> tuple[Money, list[Txn]]:
    opening = Money(rng.randint(-500000, 3000000) * 100 if od else rng.randint(50000, 5000000) * 100)
    bal, d, txns = opening, start, []
    bank_code = rng.choice(BANKS)[1]
    limit = Money(-5000000 * 100)  # OD limit for overdraft accounts
    while len(txns) < n:
        d += timedelta(days=rng.choice([0, 0, 1, 1, 2, 3]))
        party = rng.choice(PARTIES)
        kind = rng.choices(["UPI", "NEFT", "RTGS", "IMPS", "NACH", "CHQ", "CASH", "INT", "CHG"],
                           [25, 22, 6, 10, 5, 10, 8, 2, 4])[0]
        credit = rng.random() < 0.48 if kind not in ("INT", "CHG", "NACH") else kind == "INT"
        amt = _amount(rng, small=kind in ("INT", "CHG"))
        if kind == "RTGS" and amt.minor < 20000000:
            amt = Money(amt.minor + 20000000)
        ref, narr = "", ""
        if kind == "UPI":
            rrn = _digits(rng, 12)
            narr = f"UPI/{rrn}/{party}/{party.split()[0].lower()}@ok{bank_code.lower()}/{'Collect' if credit else 'Payment'}"
            ref = rrn
        elif kind == "NEFT":
            utr = f"{bank_code}N{_digits(rng, 11)}"
            narr = f"NEFT/{utr}/{party}"
            ref = utr
        elif kind == "RTGS":
            utr = f"{bank_code}R{_digits(rng, 17)}"
            narr = f"RTGS/{utr}/{party}"
            ref = utr
        elif kind == "IMPS":
            rrn = _digits(rng, 12)
            narr = f"IMPS/P2A/{rrn}/{party}"
            ref = rrn
        elif kind == "NACH":
            narr = f"NACH/{bank_code}{_digits(rng, 16)}/{party} EMI"
        elif kind == "CHQ":
            chq = _digits(rng, 6)
            narr = f"{'CHQ DEP' if credit else 'CHQ PAID'} {chq} {party}"
            ref = chq
        elif kind == "CASH":
            narr = "CASH DEPOSIT BY SELF" if credit else f"ATM WDL {bank_code}{_digits(rng, 6)}"
        elif kind == "INT":
            narr = f"INT.PD:{(d - timedelta(days=90)).strftime('%d-%m-%Y')} TO {d.strftime('%d-%m-%Y')}"
        else:
            narr = rng.choice(["SMS CHARGES", "NEFT CHGS INCL GST", "ANNUAL MAINT CHGS", "CHQ BOOK CHGS"])
        if not credit and not od and (bal - amt).minor < 0:
            continue  # savings/current accounts here do not go negative
        if not credit and od and (bal - amt) < limit:
            continue
        t = Txn(d, d + timedelta(days=rng.choice([0, 0, 0, 1])), narr, ref)
        if credit:
            t.credit, bal = amt, bal + amt
        else:
            t.debit, bal = amt, bal - amt
        t.balance = bal
        txns.append(t)
        if not credit and kind in ("UPI", "IMPS", "NEFT") and rng.random() < 0.05 and len(txns) < n:
            rev = Txn(d, d, f"REV:{narr}"[:120], ref, credit=amt)
            bal = bal + amt
            rev.balance = bal
            txns.append(rev)
    return opening, txns


# ------------------------------------------------------------------------------------------------- rendering
def _fmt(m: Money, grouping: str) -> str:
    return m.format(indian=(grouping == "indian"))


def _fmt_balance(m: Money, style: str, grouping: str) -> str:
    if style == "suffix":
        return f"{_fmt(abs(m), grouping)} {'Dr' if m.minor < 0 else 'Cr'}"
    if style == "crdr":
        return f"{_fmt(abs(m), grouping)} {'DR' if m.minor < 0 else 'CR'}"
    return _fmt(m, grouping)


def render(path: Path, meta: dict, opening: Money, txns: list[Txn], layout: dict) -> int:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfbase.pdfmetrics import stringWidth
    from reportlab.pdfgen import canvas

    font, size, lead = "Helvetica", 7.2, 9.0
    c = canvas.Canvas(str(path), pagesize=A4)
    W, H = A4
    left, top, bottom = 28, H - 36, 46
    cols, x = [], left
    for role, label, w in layout["cols"]:
        cols.append((role, label, x, w))
        x += w

    def wrap(text: str, width: float) -> list[str]:
        words, lines, cur = text.replace("/", "/ ").split(" "), [], ""
        for wd in words:
            trial = (cur + (" " if cur and not cur.endswith("/") else "") + wd).strip()
            if stringWidth(trial, font, size) <= width - 4 or not cur:
                cur = trial
            else:
                lines.append(cur)
                cur = wd
        return lines + ([cur] if cur else [])

    def header_block(page_no: int) -> float:
        c.setFont("Helvetica-Bold", 10)
        c.drawString(left, top, meta["bank"])
        c.setFont(font, 7.5)
        y = top - 12
        if page_no == 1:
            for line in [f"Branch: {meta['branch']}   IFSC: {meta['ifsc']}",
                         f"Account Name: {meta['holder']}   Account No: {meta['account_masked']}   Type: {meta['account_type']}",
                         f"Statement of Account from {meta['period'][0]} to {meta['period'][1]}",
                         f"Opening Balance: {_fmt_balance(opening, layout['balance'] if layout['balance'] != 'plain' else 'plain', layout['grouping'])}"]:
                c.drawString(left, y, line)
                y -= 10
        c.drawRightString(W - left, top, f"Page {page_no}")
        return y - 6

    def table_header(y: float) -> float:
        c.setFont("Helvetica-Bold", 7.2)
        for role, label, cx, w in cols:
            if role in ("debit", "credit", "amount", "balance"):
                c.drawRightString(cx + w - 3, y, label)
            else:
                c.drawString(cx + 2, y, label)
        c.line(left, y - 3, x, y - 3)
        c.setFont(font, size)
        return y - 12

    def carry_row(y: float, label: str, bal: Money) -> float:
        narr_col = next(cx for role, _, cx, _ in cols if role == "narration")
        bal_col = next((cx, w) for role, _, cx, w in cols if role == "balance")
        c.drawString(narr_col + 2, y, label)
        c.drawRightString(bal_col[0] + bal_col[1] - 3, y, _fmt_balance(bal, layout["balance"], layout["grouping"]))
        return y - lead

    page = 1
    y = header_block(page)
    y = table_header(y)
    running = opening
    if layout["carry"]:
        y = carry_row(y, "OPENING BALANCE", opening)
    for t in txns:
        narr_w = next(w for role, _, _, w in cols if role == "narration")
        lines = wrap(t.narration, narr_w)
        need = lead * len(lines)
        if y - need < bottom:
            if layout["carry"]:
                carry_row(y, "BALANCE C/F", running)
            c.showPage()
            page += 1
            y = header_block(page)
            if layout["header_pages"] == "all":
                y = table_header(y)
            else:
                c.setFont(font, size)
            if layout["carry"]:
                y = carry_row(y, "BALANCE B/F", running)
        t.page = page
        for role, _, cx, w in cols:
            right = cx + w - 3
            if role == "date":
                c.drawString(cx + 2, y, t.date.strftime(layout["date_fmt"]))
            elif role == "value_date":
                c.drawString(cx + 2, y, t.value_date.strftime(layout["date_fmt"]))
            elif role == "narration":
                for i, ln in enumerate(lines):
                    c.drawString(cx + 2, y - i * lead, ln)
            elif role == "ref":
                c.drawString(cx + 2, y, t.ref[:16])
            elif role == "debit" and t.debit.minor:
                c.drawRightString(right, y, _fmt(t.debit, layout["grouping"]))
            elif role == "credit" and t.credit.minor:
                c.drawRightString(right, y, _fmt(t.credit, layout["grouping"]))
            elif role == "amount":
                amt = t.debit if t.debit.minor else t.credit
                txt = _fmt(amt, layout["grouping"])
                if layout["balance"] == "crdr":
                    txt += " (Dr)" if t.debit.minor else " (Cr)"
                c.drawRightString(right, y, txt)
            elif role == "drcr":
                c.drawString(cx + 2, y, "DR" if t.debit.minor else "CR")
            elif role == "balance":
                c.drawRightString(right, y, _fmt_balance(t.balance, layout["balance"], layout["grouping"]))
        running = t.balance
        y -= need
    closing = running
    if y - 30 < bottom:
        c.showPage()
        page += 1
        y = header_block(page)
    c.setFont("Helvetica-Bold", 7.5)
    c.drawString(left, y - 10, f"Closing Balance: {_fmt_balance(closing, layout['balance'] if layout['balance'] != 'plain' else 'plain', layout['grouping'])}")
    c.drawString(left, y - 20, "This is a computer-generated synthetic statement for benchmarking. Not a real bank document.")
    c.save()
    return page


def generate(out: Path, per_family_dev: int, per_family_test: int, seed: int = 2026) -> list[dict]:
    out.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)
    manifest = []
    for fam, layout in LAYOUTS.items():
        count = per_family_dev if layout["split"] == "dev" else per_family_test
        for k in range(count):
            r = random.Random(rng.random())
            bank, code = r.choice(BANKS)
            start = date(2024, r.randint(1, 9), 1)
            opening, txns = make_history(r, layout["od"], r.randint(15, 110), start)
            meta = {"bank": bank, "branch": r.choice(["Andheri East", "Thane West", "Pune Camp", "Nashik Road",
                                                      "Vashi", "Silvassa"]),
                    "ifsc": f"{code}0{r.randint(100000, 999999)}", "holder": r.choice(PARTIES),
                    "account_masked": "XXXXXXXX" + str(r.randint(1000, 9999)),
                    "account_type": "CASH CREDIT" if layout["od"] else r.choice(["CURRENT", "SAVINGS"]),
                    "period": [start.strftime("%d-%m-%Y"), txns[-1].date.strftime("%d-%m-%Y")]}
            sid = f"{fam}{k:03d}"
            pages = render(out / f"{sid}.pdf", meta, opening, txns, layout)
            gold = {"id": sid, "split": layout["split"], "layout": fam, "currency": "INR", "pages": pages, **meta,
                    "opening_minor": opening.minor, "closing_minor": txns[-1].balance.minor,
                    "rows": [{"date": t.date.isoformat(), "value_date": t.value_date.isoformat(),
                              "narration": t.narration, "ref": t.ref, "debit_minor": t.debit.minor,
                              "credit_minor": t.credit.minor, "balance_minor": t.balance.minor, "page": t.page}
                             for t in txns]}
            (out / f"{sid}.gold.json").write_text(json.dumps(gold, indent=1), encoding="utf-8")
            manifest.append({"id": sid, "split": layout["split"], "layout": fam, "pages": pages, "rows": len(txns)})
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    return manifest


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="benchmarks/statements/data")
    ap.add_argument("--dev", type=int, default=10, help="statements per dev layout family (A-D)")
    ap.add_argument("--test", type=int, default=10, help="statements per held-out test family (E-F)")
    ap.add_argument("--seed", type=int, default=2026)
    a = ap.parse_args()
    m = generate(Path(a.out), a.dev, a.test, a.seed)
    print(f"generated {len(m)} statements, {sum(x['rows'] for x in m)} rows, {sum(x['pages'] for x in m)} pages")

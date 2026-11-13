"""EntityBench (EB) v0: synthetic counterparty records with ground-truth identities, for ADR-0009 resolution.

Each "case" holds 15-35 parties (organisations and people) and 40-120 records, the way counterparties appear across
bank-statement narrations, invoices and KYC pages. Records vary the printed name:
- legal-form spellings, case, "M/s" prefix and punctuation;
- truncation (narration fields are cut at 18-30 characters);
- one-character typos, abbreviations (Infrastructure -> Infra), and initials or reordered names for people.
Each record carries identifiers with realistic sparsity: PAN or GSTIN rarely, UPI VPA sometimes, account+IFSC
sometimes.

Hard cases are deliberate:
- confusable siblings (Sunrise Traders vs Sunrise Trading Co; Mehta vs Mehra);
- homonyms: two different people with the same name, distinguishable only by identifiers if at all.
All identifiers are synthetic and follow the official layouts (app/finance/identifiers.py); none is a real taxpayer's.
Splits are seed ranges: dev 1000+, test 9000+.
"""
from __future__ import annotations

import random
import string

PLACES = ["Sunrise", "Konkan", "Meridian", "Godavari", "Tarapur", "Shreeji", "Kaveri", "Silvassa", "Vidarbha", "Orbit",
          "Bhiwandi", "Nashik", "Deccan", "Sahyadri", "Narmada", "Indus", "Ganga", "Malabar", "Coromandel", "Saurashtra",
          "Himalaya", "Aravali", "Nilgiri", "Konark", "Ajanta", "Ellora", "Satpura", "Vindhya", "Kaveri Delta", "Tapi"]
TRADES = ["Traders", "Polymers", "Logistics", "Agro Foods", "Steel Works", "Packaging", "Warehousing", "Cold Storage",
          "Realty", "Exports", "Textiles", "Pharma", "Infrastructure", "Engineering", "Industries", "Chemicals",
          "Auto Components", "Electricals", "Builders", "Fisheries"]
SIBLING_TRADE = {"Traders": "Trading Co", "Polymers": "Plastics", "Logistics": "Logistic Services",
                 "Exports": "Export House", "Textiles": "Textile Mills", "Industries": "Industrial Corp",
                 "Engineering": "Engineers", "Chemicals": "Chem Labs", "Builders": "Constructions"}
FORMS = ["Pvt Ltd", "Ltd", "LLP", "", "& Co"]
FIRST = ["Anil", "Rekha", "Prakash", "Sunita", "Rahul", "Priya", "Vikram", "Neha", "Suresh", "Kavita", "Amit", "Pooja",
         "Rajesh", "Meena", "Sanjay", "Asha", "Deepak", "Lata", "Manoj", "Geeta"]
LAST = ["Mehta", "Joshi", "Sharma", "Patil", "Kulkarni", "Desai", "Iyer", "Nair", "Reddy", "Gupta", "Shah", "Rao",
        "Pillai", "Kapoor", "Bhatt", "Chavan", "Menon", "Sinha", "Verma", "Yadav"]
SIBLING_LAST = {"Mehta": "Mehra", "Sharma": "Verma", "Shah": "Sah", "Rao": "Roy", "Nair": "Naik", "Patil": "Patel",
                "Joshi": "Jose", "Gupta": "Dutta", "Desai": "Dalal", "Reddy": "Raddi"}
ABBREV = {"Infrastructure": "Infra", "Industries": "Inds", "Engineering": "Engg", "International": "Intl",
          "Corporation": "Corp", "Electricals": "Elec", "Pharma": "Pharmaceuticals", "Components": "Comp"}
FORM_VARIANTS = {"Pvt Ltd": ["Pvt Ltd", "Pvt. Ltd.", "Private Limited", "PVT LTD", "P Ltd"],
                 "Ltd": ["Ltd", "Limited", "Ltd."], "LLP": ["LLP", "L.L.P."], "& Co": ["& Co", "and Company", "& Co."],
                 "": [""]}
BANKS = ["SBIN", "HDFC", "ICIC", "UTIB", "KKBK", "PUNB", "BARB", "CNRB", "MERI", "DECT"]
PSPS = ["okhdfcbank", "okicici", "oksbi", "okaxis", "ybl", "paytm", "ibl", "upi"]
STATE = ["27", "24", "29", "33", "07", "09", "19", "36"]


def _pan(rng, holder: str, name_letter: str) -> str:
    return ("".join(rng.choice(string.ascii_uppercase) for _ in range(3)) + holder + name_letter.upper()
            + f"{rng.randint(1, 9999):04d}" + rng.choice(string.ascii_uppercase))


def _typo(rng, s: str) -> str:
    letters = [i for i, ch in enumerate(s) if ch.isalpha()]
    if len(letters) < 6:
        return s
    i = rng.choice(letters[1:-1])
    op = rng.choice(["sub", "del", "swap"])
    if op == "sub":
        return s[:i] + rng.choice(string.ascii_lowercase if s[i].islower() else string.ascii_uppercase) + s[i + 1:]
    if op == "del":
        return s[:i] + s[i + 1:]
    return s[:i] + s[i + 1] + s[i] + s[i + 2:] if i + 1 < len(s) else s


def make_party(rng, pid: int, kind: str, base: dict | None = None, sibling: str | None = None) -> dict:
    if kind == "org":
        if sibling == "trade":
            place, trade = base["place"], SIBLING_TRADE.get(base["trade"], base["trade"] + " Group")
            form = rng.choice(FORMS)
        elif sibling == "group":  # group company: same name, different legal form
            place, trade = base["place"], base["trade"]
            form = rng.choice([f for f in ("Pvt Ltd", "Ltd", "LLP") if f != base["form"]])
        else:
            place, trade = base["place"], base["trade"]  # caller supplies an unused name
            form = rng.choice(FORMS)
        name = " ".join(x for x in (place, trade, form) if x)
        pan = _pan(rng, rng.choice("CF"), place[0])
        p = {"kind": "org", "place": place, "trade": trade, "form": form, "name": name}
    else:
        if sibling == "homonym":
            first, last = base["first"], base["last"]
        elif sibling == "surname":
            first, last = base["first"], SIBLING_LAST.get(base["last"], base["last"] + "a")
        else:
            first, last = rng.choice(FIRST), rng.choice(LAST)
        pan = _pan(rng, "P", last[0])
        p = {"kind": "person", "first": first, "last": last, "name": f"{first} {last}"}
    local = (p.get("place") or p.get("first")).lower().replace(" ", "") + (str(rng.randint(1, 99)) if rng.random() < .5 else "")
    p.update(id=pid, pan=pan, gstin=(rng.choice(STATE) + pan + str(rng.randint(1, 9)) + "Z" + rng.choice("0123456789ABCDEF"))
             if kind == "org" else None,
             vpas=[f"{local}@{rng.choice(PSPS)}" for _ in range(rng.choice([1, 1, 2]))],
             accounts=[f"{rng.randint(10 ** 9, 10 ** 12 - 1)}|{rng.choice(BANKS)}0{rng.randint(0, 999999):06d}"])
    return p


def variant(rng, p: dict) -> str:
    if p["kind"] == "org":
        trade = p["trade"]
        if rng.random() < 0.2:
            trade = " ".join(ABBREV.get(w, w) for w in trade.split())
        form = rng.choice(FORM_VARIANTS[p["form"]]) if rng.random() < 0.8 else ""
        name = " ".join(x for x in (p["place"], trade, form) if x)
        if rng.random() < 0.15:
            name = "M/s " + name
    else:
        r = rng.random()
        if r < 0.12:
            name = f"{p['first'][0]}. {p['last']}"
        elif r < 0.2:
            name = f"{p['last']} {p['first']}"
        else:
            name = p["name"]
    if rng.random() < 0.35:
        name = name.upper()
    if rng.random() < 0.08:
        name = _typo(rng, name)
    if rng.random() < 0.15:  # narration field truncation
        name = name[: rng.randint(18, 30)].rstrip()
    return name


def make_case(seed: int) -> dict:
    rng = random.Random(seed)
    parties, pid, used_names = [], 0, set()
    for _ in range(rng.randint(15, 35)):
        kind = "org" if rng.random() < 0.6 else "person"
        if kind == "org":  # no accidental same-name organisations; deliberate ones are added below
            while True:
                base = {"place": rng.choice(PLACES), "trade": rng.choice(TRADES)}
                if (base["place"], base["trade"]) not in used_names:
                    used_names.add((base["place"], base["trade"]))
                    break
            parties.append(make_party(rng, pid, kind, base))
        else:
            parties.append(make_party(rng, pid, kind))
        pid += 1
    # hard cases: confusable siblings, group companies and homonyms
    for base in rng.sample(parties, k=min(len(parties), rng.randint(3, 6))):
        if base["kind"] == "org":
            parties.append(make_party(rng, pid, "org", base, rng.choice(["trade", "group"])))
        else:
            parties.append(make_party(rng, pid, "person", base, rng.choice(["homonym", "surname"])))
        pid += 1
    used = set()  # a VPA belongs to one account holder: make generated VPAs unique within the case
    for p in parties:
        for i, v in enumerate(p["vpas"]):
            while v in used:
                local, psp = v.split("@")
                v = f"{local}{rng.randint(1, 999)}@{psp}"
            p["vpas"][i] = v
            used.add(v)
    records = []
    for p in parties:
        for _ in range(rng.choices([1, 2, 3, 4, 6], [25, 30, 20, 15, 10])[0]):
            rec = {"id": f"r{len(records)}", "truth": p["id"], "kind": p["kind"], "name": variant(rng, p),
                   "pan": None, "gstin": None, "vpa": None, "account": None}
            u = rng.random()
            if u < 0.10:
                rec["pan"] = p["pan"]
            elif u < 0.18 and p["gstin"]:
                rec["gstin"] = p["gstin"]
            if rng.random() < 0.40:
                rec["vpa"] = rng.choice(p["vpas"])
            if rng.random() < 0.20:
                rec["account"] = rng.choice(p["accounts"])
            records.append(rec)
    rng.shuffle(records)
    return {"seed": seed, "parties": len(parties), "records": records}


SPLITS = {"dev": 1000, "test": 9000}


def cases(split: str, n: int) -> list[dict]:
    return [make_case(SPLITS[split] + i) for i in range(n)]

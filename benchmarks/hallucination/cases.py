"""MindDoc hallucination test set v0 — claim-level, hand-labelled, fictional lending documents.

Every case is (source passage, question, claim, label, type). A claim is "supported" only if the passage
states it (paraphrase, reformatting and simple arithmetic allowed); otherwise "unsupported".

Two splits:
  dev  (D*) — used while building the verifier; rules may be tuned on it.
  test (T*) — written at the same time but only scored once, after the verifier was frozen.
Caveat: both splits were written by the same developer who wrote the verifier, so the test split is not
independent in the way a third-party benchmark is. Report it as such.

Error types (unsupported): wrong_number, wrong_scale (lakh/crore), wrong_date, wrong_period (per month vs per
year), swapped_parties, negation, direction (debit/credit, rose/fell, before/after, includes/excludes),
wrong_entity, contradiction (subtle, uses only words from the source), invented.
Faithful types (supported): faithful (plain paraphrase), faithful_hard (reformatted numbers/dates, passive voice,
number words, arithmetic, approximations, unit conversion).

All companies, people, banks and numbers are fictional.
"""

SOURCES = {
    # ----------------------------------------------------------------------------------------- dev
    "D1": dict(split="dev", question="What are the terms of the cash credit facility?", text=(
        "Meridian Bank Ltd sanctioned a cash credit limit of ₹4.50 crore to Shreeji Polymers Pvt Ltd on "
        "14 August 2024. The limit carries interest at 10.25% per annum, payable monthly. The facility is secured "
        "by a first charge on stock and book debts. Personal guarantees of directors Anil Mehta and Rekha Mehta "
        "are required. The limit is valid for 12 months and is subject to annual renewal.")),
    "D2": dict(split="dev", question="What transactions happened in April 2024?", text=(
        "Statement of account 50200014567892, Meridian Bank, Andheri branch, for April 2024. On 03 April 2024, "
        "₹12,40,000 was credited from Kaveri Agro Foods Ltd by RTGS. On 05 April 2024, ₹12,00,000 was debited "
        "by RTGS to Sunrise Traders. The closing balance on 30 April 2024 was ₹1,85,320.50.")),
    "D3": dict(split="dev", question="What does invoice INV/2024/0457 show?", text=(
        "Tax invoice INV/2024/0457 dated 18 June 2024 was issued by Sunrise Traders to Shreeji Polymers Pvt Ltd "
        "for 25 tonnes of HDPE granules at ₹96,000 per tonne. The taxable value is ₹24,00,000 and GST at 18% "
        "amounts to ₹4,32,000, giving a total of ₹28,32,000. Payment is due within 45 days of the invoice date.")),
    "D4": dict(split="dev", question="What did the board decide?", text=(
        "At its meeting on 2 February 2024, the board of Shreeji Polymers Pvt Ltd approved borrowing up to "
        "₹10 crore from Meridian Bank Ltd. The board did not approve the proposed loan of ₹1.5 crore to Sunrise "
        "Traders, a firm in which director Anil Mehta is a partner. Rekha Mehta abstained from voting on both "
        "items.")),
    "D5": dict(split="dev", question="How must the term loan be repaid?", text=(
        "The Borrower shall repay the term loan in 20 equal quarterly instalments starting 30 September 2024. "
        "Prepayment is permitted without penalty after the first 12 months. If any instalment is overdue by more "
        "than 90 days, the Lender may recall the entire loan.")),
    "D6": dict(split="dev", question="What does the March 2024 GST return show?", text=(
        "In GSTR-3B for March 2024, Kaveri Agro Foods Ltd reported outward taxable supplies of ₹3.6 crore and an "
        "input tax credit of ₹42.8 lakh. Tax paid in cash was ₹21.4 lakh. The return was filed on 22 April 2024, "
        "two days after the due date.")),
    "D7": dict(split="dev", question="What directorships does Anil Mehta hold?", text=(
        "Anil Mehta (DIN 07345612) has been a director of Shreeji Polymers Pvt Ltd since 11 January 2019. He was "
        "also appointed a director of Sunrise Agencies Pvt Ltd on 3 March 2022 and resigned from that board on "
        "15 November 2023.")),
    "D8": dict(split="dev", question="What does the June 2024 stock statement declare?", text=(
        "The stock statement for June 2024 submitted by Shreeji Polymers Pvt Ltd declares raw material of "
        "₹2.10 crore, finished goods of ₹1.35 crore and receivables older than 90 days of ₹48 lakh. Drawing power "
        "is calculated after a 25% margin on stock and excludes receivables older than 90 days.")),
    # ---------------------------------------------------------------------------------------- test
    "T1": dict(split="test", question="What are the lease terms?", text=(
        "Under the lease dated 1 April 2023, Orbit Realty LLP leases warehouse unit B-14 in Bhiwandi to Kaveri "
        "Agro Foods Ltd for five years. Monthly rent is ₹3,25,000, rising by 5% every year. The tenant paid a "
        "refundable security deposit of ₹19,50,000. Either party may terminate the lease by giving three months' "
        "written notice, but not during the first 24 months.")),
    "T2": dict(split="test", question="What did the auditor report?", text=(
        "The statutory auditor, Desai & Kulkarni, issued a qualified opinion on the FY 2023-24 financial "
        "statements of Sunrise Traders Pvt Ltd. The qualification relates to trade receivables of ₹6.8 crore for "
        "which no balance confirmations were obtained. The auditor did not report any fraud under section "
        "143(12).")),
    "T3": dict(split="test", question="What did the account show in early May 2024?", text=(
        "Date | Narration | Debit | Credit | Balance\n"
        "02-05-2024 | NEFT from Godavari Cold Storage Ltd | | 8,75,000.00 | 9,10,250.00\n"
        "04-05-2024 | Cash withdrawal ATM Thane | 40,000.00 | | 8,70,250.00\n"
        "06-05-2024 | RTGS to Orbit Realty LLP rent | 3,25,000.00 | | 5,45,250.00")),
    "T4": dict(split="test", question="What does purchase order PO-7781 cover?", text=(
        "Purchase order PO-7781 dated 9 January 2024 from Kaveri Agro Foods Ltd to Godavari Cold Storage Ltd "
        "covers cold-storage services for 400 pallets at ₹1,150 per pallet per month for six months. Godavari "
        "confirmed the order on 11 January 2024. Services began on 15 January 2024.")),
    "T5": dict(split="test", question="What did Rekha Mehta ask the bank?", text=(
        "In an email dated 28 August 2024, Rekha Mehta asked Meridian Bank to defer the September instalment by "
        "30 days because a customer payment of ₹2.2 crore was delayed. The bank has not yet responded to the "
        "request.")),
    "T6": dict(split="test", question="What is the property worth?", text=(
        "The valuer, Prakash Joshi, assessed the factory land and building at Plot 22, MIDC Tarapur, at a fair "
        "market value of ₹7.4 crore and a distress sale value of ₹5.9 crore as of 10 October 2024. The valuation "
        "excludes plant and machinery.")),
    "T7": dict(split="test", question="What does the insurance policy cover?", text=(
        "Policy FP-55120 issued by Sahyadri General Insurance covers the stock of Shreeji Polymers Pvt Ltd at its "
        "Silvassa plant against fire and flood for a sum insured of ₹6 crore. The policy runs from 1 July 2024 to "
        "30 June 2025. Meridian Bank is named as the loss payee. Theft is not covered.")),
    "T8": dict(split="test", question="How did Kaveri Agro Foods perform financially?", text=(
        "Sales of Kaveri Agro Foods Ltd grew from ₹38.2 crore in FY 2022-23 to ₹44.6 crore in FY 2023-24, while "
        "net profit fell from ₹2.9 crore to ₹1.7 crore. The current ratio declined to 1.08, below the bank's "
        "benchmark of 1.25.")),
}

S, U = "supported", "unsupported"

# (source, label, type, claim)
CLAIMS = [
    # D1 sanction letter
    ("D1", S, "faithful_hard", "Meridian Bank sanctioned a cash credit limit of ₹4.5 crore to Shreeji Polymers."),
    ("D1", S, "faithful", "Interest is charged at 10.25% a year and must be paid every month."),
    ("D1", S, "faithful_hard", "The facility is valid for twelve months and must be renewed annually."),
    ("D1", S, "faithful_hard", "The sanction is dated 14/08/2024."),
    ("D1", S, "faithful", "Anil Mehta and Rekha Mehta, the directors, must give personal guarantees."),
    ("D1", U, "wrong_number", "The limit carries interest at 11.25% per annum, payable monthly."),
    ("D1", U, "wrong_scale", "Meridian Bank Ltd sanctioned a cash credit limit of ₹4.50 lakh to Shreeji Polymers Pvt Ltd."),
    ("D1", U, "wrong_date", "The cash credit limit was sanctioned on 14 September 2024."),
    ("D1", U, "wrong_period", "Interest at 10.25% is payable quarterly."),
    ("D1", U, "swapped_parties", "Shreeji Polymers Pvt Ltd sanctioned a cash credit limit of ₹4.50 crore to Meridian Bank Ltd."),
    ("D1", U, "negation", "The facility is not secured by any charge on stock or book debts."),
    ("D1", U, "wrong_entity", "Personal guarantees of directors Anil Mehta and Sunil Kapoor are required."),
    ("D1", U, "invented", "The bank also requires the factory land to be mortgaged as collateral."),
    # D2 bank statement (prose)
    ("D2", S, "faithful_hard", "Kaveri Agro Foods Ltd sent ₹12.4 lakh to the account by RTGS on 3 April 2024."),
    ("D2", S, "faithful_hard", "Two days later, ₹12 lakh went out to Sunrise Traders."),
    ("D2", S, "faithful_hard", "The month closed with a balance of about ₹1.85 lakh."),
    ("D2", S, "faithful", "Most of the money credited on 3 April left the account by 5 April."),
    ("D2", U, "wrong_number", "On 05 April 2024, ₹21,00,000 was debited by RTGS to Sunrise Traders."),
    ("D2", U, "direction", "On 05 April 2024, ₹12,00,000 was credited to the account from Sunrise Traders."),
    ("D2", U, "wrong_date", "₹12,40,000 was credited from Kaveri Agro Foods Ltd on 13 April 2024."),
    ("D2", U, "wrong_entity", "₹12,40,000 was credited from Godavari Foods Ltd by RTGS."),
    ("D2", U, "wrong_number", "The statement is for account 50200014567829."),
    ("D2", U, "invented", "The account was classified as a non-performing asset in April 2024."),
    # D3 invoice
    ("D3", S, "faithful_hard", "Sunrise Traders billed Shreeji Polymers ₹28.32 lakh in total, including ₹4.32 lakh of GST."),
    ("D3", S, "faithful", "The invoice covers 25 tonnes of HDPE granules priced at ₹96,000 a tonne."),
    ("D3", S, "faithful_hard", "Shreeji Polymers was invoiced by Sunrise Traders on 18 June 2024."),
    ("D3", S, "faithful", "Payment falls due 45 days after the invoice date."),
    ("D3", U, "wrong_number", "GST at 12% amounts to ₹4,32,000 on this invoice."),
    ("D3", U, "wrong_number", "The invoice total comes to ₹27,32,000."),
    ("D3", U, "swapped_parties", "Tax invoice INV/2024/0457 was issued by Shreeji Polymers Pvt Ltd to Sunrise Traders."),
    ("D3", U, "wrong_number", "Payment is due within 60 days of the invoice date."),
    ("D3", U, "wrong_date", "Tax invoice INV/2024/0457 is dated 18 July 2024."),
    ("D3", U, "invented", "The invoice was paid in full on the same day it was issued."),
    # D4 board resolution
    ("D4", S, "faithful", "The board authorised borrowing of up to ₹10 crore from Meridian Bank."),
    ("D4", S, "faithful_hard", "The proposed ₹1.5 crore loan to Sunrise Traders was rejected by the board."),
    ("D4", S, "faithful", "Anil Mehta is a partner in Sunrise Traders."),
    ("D4", S, "faithful_hard", "The board meeting was held on 2 Feb 2024."),
    ("D4", U, "negation", "The board approved the proposed loan of ₹1.5 crore to Sunrise Traders."),
    ("D4", U, "wrong_number", "The board approved borrowing up to ₹12 crore from Meridian Bank Ltd."),
    ("D4", U, "contradiction", "Sunrise Traders is a firm in which director Rekha Mehta is a partner."),
    ("D4", U, "contradiction", "Rekha Mehta voted against both items."),
    ("D4", U, "wrong_date", "The board met on 2 March 2024 to approve the borrowing."),
    # D5 loan agreement
    ("D5", S, "faithful_hard", "Repayment is in twenty equal instalments every quarter, beginning on 30 September 2024."),
    ("D5", S, "faithful", "After the first year, the loan can be prepaid with no penalty."),
    ("D5", S, "faithful", "The Lender can recall the whole loan if an instalment is more than 90 days overdue."),
    ("D5", U, "wrong_period", "The Borrower shall repay the term loan in 20 equal monthly instalments."),
    ("D5", U, "negation", "Prepayment is not permitted at any time during the life of the loan."),
    ("D5", U, "wrong_number", "If any instalment is overdue by more than 60 days, the Lender may recall the entire loan."),
    ("D5", U, "swapped_parties", "If any instalment is overdue by more than 90 days, the Borrower may recall the entire loan."),
    ("D5", U, "wrong_date", "Repayment of the term loan starts on 30 June 2024."),
    # D6 GST return
    ("D6", S, "faithful", "Kaveri Agro Foods filed its March 2024 GSTR-3B late, on 22 April 2024."),
    ("D6", S, "faithful", "It claimed ₹42.8 lakh of input tax credit against ₹3.6 crore of taxable outward supplies."),
    ("D6", S, "faithful_hard", "Cash tax payment was ₹21,40,000."),
    ("D6", U, "wrong_scale", "Kaveri Agro Foods Ltd reported outward taxable supplies of ₹3.6 lakh."),
    ("D6", U, "wrong_date", "The March 2024 return was filed on 12 April 2024."),
    ("D6", U, "direction", "The return was filed before the due date."),
    ("D6", U, "wrong_number", "The return was filed ten days after the due date."),
    ("D6", U, "invented", "The company also reported zero-rated exports in the same return."),
    # D7 directorships
    ("D7", S, "faithful_hard", "Anil Mehta, DIN 07345612, joined the Shreeji Polymers board in January 2019."),
    ("D7", S, "faithful_hard", "He left the board of Sunrise Agencies on 15 Nov 2023."),
    ("D7", S, "faithful_hard", "Anil Mehta served as a director of Sunrise Agencies for about 20 months."),
    ("D7", U, "wrong_number", "Anil Mehta holds DIN 07345621."),
    ("D7", U, "wrong_date", "Anil Mehta has been a director of Shreeji Polymers Pvt Ltd since 11 January 2018."),
    ("D7", U, "contradiction", "He resigned from the board of Sunrise Agencies on 3 March 2022."),
    ("D7", U, "wrong_entity", "Anil Mehta has been a director of Shreeji Exports Pvt Ltd since 11 January 2019."),
    ("D7", U, "wrong_entity", "Anil Mehta is also a director of Kaveri Agro Foods Ltd."),
    # D8 stock statement
    ("D8", S, "faithful_hard", "In June 2024 Shreeji Polymers declared ₹3.45 crore of stock in total (raw material plus finished goods)."),
    ("D8", S, "faithful_hard", "Receivables over 90 days old, worth ₹48 lakh, are left out of the drawing power calculation."),
    ("D8", S, "faithful", "A 25% margin applies to stock when computing drawing power."),
    ("D8", U, "wrong_number", "Drawing power is calculated after a 20% margin on stock."),
    ("D8", U, "direction", "Drawing power includes receivables older than 90 days."),
    ("D8", U, "wrong_date", "The stock statement is for May 2024."),
    ("D8", U, "wrong_scale", "The stock statement declares finished goods of ₹1.35 lakh."),
    ("D8", U, "invented", "The stock was physically verified by the bank's auditor in June 2024."),
    # T1 lease
    ("T1", S, "faithful_hard", "Kaveri Agro Foods rents unit B-14 in Bhiwandi from Orbit Realty LLP."),
    ("T1", S, "faithful_hard", "The rent starts at ₹3.25 lakh a month and increases 5% annually."),
    ("T1", S, "faithful_hard", "Neither side can end the lease in its first two years."),
    ("T1", S, "faithful_hard", "The lease runs for 5 years from 1 April 2023."),
    ("T1", U, "wrong_number", "Monthly rent under the lease is ₹3,52,000."),
    ("T1", U, "wrong_period", "Annual rent for warehouse unit B-14 is ₹3,25,000."),
    ("T1", U, "swapped_parties", "Kaveri Agro Foods Ltd leases warehouse unit B-14 in Bhiwandi to Orbit Realty LLP."),
    ("T1", U, "negation", "Either party may terminate the lease at any time, including during the first 24 months."),
    ("T1", U, "wrong_number", "The tenant paid a refundable security deposit of ₹15,90,000."),
    ("T1", U, "invented", "The tenant is responsible for all structural repairs to the warehouse."),
    ("T1", U, "wrong_entity", "Orbit Realty LLP leases warehouse unit B-14 in Bhiwandi to Godavari Cold Storage Ltd."),
    # T2 auditor's report
    ("T2", S, "faithful", "Desai & Kulkarni qualified their opinion on Sunrise Traders' FY 2023-24 accounts."),
    ("T2", S, "faithful_hard", "No fraud was reported by the auditor under section 143(12)."),
    ("T2", S, "faithful_hard", "Balance confirmations were missing for receivables worth ₹6.8 crore."),
    ("T2", U, "contradiction", "The statutory auditor issued an unqualified opinion on the FY 2023-24 financial statements."),
    ("T2", U, "wrong_number", "The qualification relates to trade receivables of ₹8.6 crore."),
    ("T2", U, "wrong_entity", "The statutory auditor, Mehta & Shah, issued a qualified opinion on Sunrise Traders Pvt Ltd."),
    ("T2", U, "negation", "The auditor reported a fraud under section 143(12)."),
    ("T2", U, "wrong_date", "The qualified opinion covers the FY 2022-23 financial statements."),
    ("T2", U, "invented", "The auditor resigned shortly after issuing the report."),
    # T3 bank statement (table)
    ("T3", S, "faithful_hard", "On 2 May 2024 the account received ₹8.75 lakh by NEFT from Godavari Cold Storage Ltd."),
    ("T3", S, "faithful_hard", "₹3.25 lakh of rent was paid to Orbit Realty LLP on 6 May 2024."),
    ("T3", S, "faithful", "After the rent payment, the balance was ₹5,45,250."),
    ("T3", S, "faithful_hard", "₹40,000 was withdrawn in cash at an ATM in Thane on 4 May."),
    ("T3", U, "swapped_parties", "On 2 May 2024 the account paid ₹8.75 lakh to Godavari Cold Storage Ltd."),
    ("T3", U, "wrong_number", "After the rent payment, the balance was ₹4,54,250."),
    ("T3", U, "wrong_date", "₹3,25,000 was paid to Orbit Realty LLP on 16 May 2024."),
    ("T3", U, "direction", "The rent of ₹3,25,000 was credited to the account on 6 May 2024."),
    ("T3", U, "invented", "A cheque of ₹2,00,000 issued to Sunrise Traders bounced on 5 May 2024."),
    # T4 purchase order
    ("T4", S, "faithful_hard", "Godavari Cold Storage accepted Kaveri's purchase order PO-7781 on 11 Jan 2024."),
    ("T4", S, "faithful_hard", "The order is for 400 pallets at ₹1,150 a pallet each month, for 6 months."),
    ("T4", S, "faithful_hard", "Services started four days after the order was confirmed."),
    ("T4", U, "wrong_number", "Purchase order PO-7781 covers cold-storage services for 600 pallets."),
    ("T4", U, "wrong_period", "The rate under PO-7781 is ₹1,150 per pallet per week."),
    ("T4", U, "swapped_parties", "Purchase order PO-7781 was placed by Godavari Cold Storage Ltd with Kaveri Agro Foods Ltd."),
    ("T4", U, "wrong_date", "Services under PO-7781 began on 15 February 2024."),
    ("T4", U, "invented", "The order includes a penalty of ₹500 per pallet for late delivery."),
    # T5 email
    ("T5", S, "faithful", "Rekha Mehta requested a 30-day deferral of the September instalment."),
    ("T5", S, "faithful", "Her reason was a delayed ₹2.2 crore payment from a customer."),
    ("T5", S, "faithful_hard", "There has been no response from the bank so far."),
    ("T5", U, "swapped_parties", "Meridian Bank asked Rekha Mehta to defer the September instalment by 30 days."),
    ("T5", U, "negation", "The bank has approved the request to defer the September instalment."),
    ("T5", U, "wrong_number", "Rekha Mehta asked Meridian Bank to defer the September instalment by 60 days."),
    ("T5", U, "wrong_date", "Rekha Mehta's email asking for the deferral is dated 28 July 2024."),
    ("T5", U, "wrong_scale", "A customer payment of ₹2.2 lakh was delayed."),
    # T6 valuation
    ("T6", S, "faithful", "Prakash Joshi valued the Tarapur factory at ₹7.4 crore (fair market) and ₹5.9 crore (distress sale) on 10 October 2024."),
    ("T6", S, "faithful_hard", "Plant and machinery were not included in the valuation."),
    ("T6", S, "faithful_hard", "The distress sale value is about 80% of the fair market value."),
    ("T6", U, "wrong_number", "The factory land and building have a fair market value of ₹7.9 crore."),
    ("T6", U, "direction", "The valuation includes plant and machinery."),
    ("T6", U, "wrong_entity", "The valuer, Prakash Jain, assessed the factory at Plot 22, MIDC Tarapur."),
    ("T6", U, "wrong_date", "The valuation is as of 10 October 2023."),
    ("T6", U, "invented", "The valuer noted that the building has no fire safety certificate."),
    # T7 insurance
    ("T7", S, "faithful", "Shreeji Polymers' Silvassa stock is insured for ₹6 crore against fire and flood."),
    ("T7", S, "faithful_hard", "Cover lasts one year, from 1 July 2024 to 30 June 2025."),
    ("T7", S, "faithful", "Any claim payout goes to Meridian Bank as loss payee."),
    ("T7", S, "faithful_hard", "Theft is excluded from the policy."),
    ("T7", U, "negation", "The policy also covers theft of stock at the Silvassa plant."),
    ("T7", U, "wrong_number", "The stock at the Silvassa plant is insured for a sum of ₹4 crore."),
    ("T7", U, "wrong_entity", "Kaveri Agro Foods Ltd is named as the loss payee on policy FP-55120."),
    ("T7", U, "wrong_date", "The policy runs from 1 July 2024 to 30 June 2026."),
    ("T7", U, "invented", "The policy carries a deductible of ₹5 lakh per claim."),
    # T8 credit appraisal
    ("T8", S, "faithful_hard", "Kaveri's sales rose by ₹6.4 crore year on year."),
    ("T8", S, "faithful", "Net profit dropped to ₹1.7 crore in FY 2023-24."),
    ("T8", S, "faithful", "At 1.08, the current ratio is under the 1.25 benchmark."),
    ("T8", S, "faithful_hard", "Sales grew about 17% while profit fell."),
    ("T8", U, "direction", "Net profit rose from ₹2.9 crore to ₹1.7 crore."),
    ("T8", U, "wrong_number", "The current ratio declined to 1.8."),
    ("T8", U, "direction", "The current ratio is above the bank's benchmark of 1.25."),
    ("T8", U, "wrong_date", "Sales reached ₹44.6 crore in FY 2024-25."),
    ("T8", U, "wrong_scale", "Sales of Kaveri Agro Foods Ltd were ₹38.2 lakh in FY 2022-23."),
    ("T8", U, "invented", "The bank rejected Kaveri's renewal request because of the falling profit."),
]


def cases(split: str | None = None) -> list[dict]:
    out = []
    for i, (sid, label, kind, claim) in enumerate(CLAIMS):
        src = SOURCES[sid]
        if split and src["split"] != split:
            continue
        out.append({"id": f"{sid}-{i:03d}", "source_id": sid, "split": src["split"], "question": src["question"],
                    "passage": src["text"], "claim": claim, "label": label, "type": kind})
    return out

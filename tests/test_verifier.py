"""Claim verifier v2: deterministic checks, plus a regression guard on the hallucination benchmark."""
import pytest

from app.ai import verifier
from benchmarks.hallucination.cases import cases

SANCTION = ("Meridian Bank Ltd sanctioned a cash credit limit of ₹4.50 crore to Shreeji Polymers Pvt Ltd on "
            "14 August 2024. The limit carries interest at 10.25% per annum, payable monthly. The facility is "
            "secured by a first charge on stock and book debts. Drawing power excludes receivables older than "
            "90 days.")


def kinds(claim, source=SANCTION):
    return {i["kind"] for i in verifier.check_claim(claim, [source]).issues}


def test_numbers_formats_and_scales():
    assert "number" not in kinds("The limit is ₹4.5 crore.")
    assert "number" not in kinds("The limit is Rs. 4,50,00,000.")
    assert "number" in kinds("The limit is ₹4.50 lakh.")            # scale error
    assert "number" in kinds("Interest is 11.25% per annum.")       # wrong figure
    assert "number" not in kinds("Stock was about ₹4.4 crore.")      # 'about' allows 5%


def test_dates_and_identifiers():
    assert "date" not in kinds("The limit was sanctioned on 14/08/2024.")
    assert "date" not in kinds("It was sanctioned in August 2024.")
    assert "date" in kinds("The limit was sanctioned on 14 September 2024.")
    src = "Statement of account 50200014567892 for April 2024."
    assert "identifier" in kinds("The statement is for account 50200014567829.", src)
    assert "identifier" not in kinds("The statement is for account 50200014567892.", src)


def test_frequency_bound_to_number():
    assert "frequency" in kinds("Interest at 10.25% is payable quarterly.")
    assert "frequency" not in kinds("Interest is 10.25% a year, paid every month.")


def test_negation_and_scope():
    assert "negation" in kinds("The facility is not secured by any charge on stock or book debts.")
    # "excludes" scopes over receivables, so a claim about the charge on stock is not negated
    assert "negation" not in kinds("The facility is secured by a charge on stock and book debts.")
    assert kinds("Drawing power includes receivables older than 90 days.") & {"direction", "negation"}


def test_parties_and_roles():
    assert "party" in kinds("Sunil Kapoor guaranteed the facility.")
    assert "roles" in kinds("Shreeji Polymers Pvt Ltd sanctioned a cash credit limit of ₹4.50 crore to Meridian Bank Ltd.")
    assert "roles" not in kinds("Meridian Bank sanctioned a cash credit limit of ₹4.5 crore to Shreeji Polymers.")


def test_derived_figures():
    src = "Raw material is ₹2.10 crore and finished goods are ₹1.35 crore. Paid on 03 April 2024 and 05 April 2024."
    assert "number" not in kinds("Stock totals ₹3.45 crore.", src)
    assert "number" not in kinds("The second payment was two days later.", src)


@pytest.mark.parametrize("split", ["dev", "test"])
def test_benchmark_regression_guard(split):
    """Deterministic error types (no embeddings needed) must stay caught; measured 2026-11-10."""
    deterministic = {"wrong_number", "wrong_scale", "wrong_date", "wrong_period", "wrong_entity"}
    rows = [c for c in cases(split) if c["type"] in deterministic]
    caught = sum(not verifier.check_claim(c["claim"], [c["passage"]]).supported for c in rows)
    assert caught / len(rows) >= 0.9, f"{split}: {caught}/{len(rows)} deterministic errors caught"


# ---------------------------------------------------------------------------------------------- verifier v3 (R6)

INVOICE = ("Supplier: Kanha Traders LLP. Buyer: Konark Polymers Pvt Ltd. 12 bales of cotton yarn at Rs 96,000 per "
           "bale. IGST @ 5% is charged on the taxable value. Payment is due within 15 days.")
LEASE = ("Monthly rent is ₹1,50,000, rising by 5% every year. The tenant paid a refundable security deposit of "
         "₹9,00,000. Neither party may terminate during the first 36 months.")
TABLE = ("Date | Narration | Debit | Credit | Balance\n"
         "02-05-2024 | NEFT from Godavari Cold Storage Ltd | | 8,75,000.00 | 9,10,250.00\n"
         "04-05-2024 | NEFT from Kaveri Agro Foods Ltd | | 1,25,000.00 | 10,35,250.00\n"
         "06-05-2024 | RTGS to Orbit Realty LLP rent | 3,25,000.00 | | 7,10,250.00")


def check(claim, source):
    return verifier.check_claim(claim, [source])


def test_recomputed_figures_are_accepted_with_a_derivation():
    v = check("Before tax, the invoice is worth ₹11,52,000.", INVOICE)
    assert "number" not in {i["kind"] for i in v.issues}
    assert any("12 × 96,000" in d for d in v.derivations), v.derivations
    assert "number" not in kinds("The IGST charged comes to ₹57,600.", INVOICE)       # 5% of 12 × rate
    assert "number" not in kinds("Including tax, the invoice comes to ₹12,09,600.", INVOICE)
    assert "number" not in kinds("First-year rent totals ₹18,00,000.", LEASE)          # monthly × 12
    assert "number" not in kinds("The lock-in lasts three years.", LEASE)               # 36 months
    assert "number" not in kinds("The security deposit equals six months' rent.", LEASE)  # 9,00,000 ÷ 1,50,000
    assert "number" not in kinds("Credits in the period added up to ₹10,00,000.", TABLE)  # column total
    src = "The fair market value is ₹6 crore and the distress sale value is ₹4.5 crore."
    assert "number" not in kinds("The distress sale value is about 75% of the fair market value.", src)
    assert "number" not in kinds("The distress value is 25% below the fair market value.", src)


def test_wrong_computed_figures_are_still_flagged():
    assert "number" in kinds("Including tax, the invoice comes to ₹9,07,200.", INVOICE)
    assert "number" in kinds("The IGST charged comes to ₹75,600.", INVOICE)
    assert "number" in kinds("The security deposit equals eight months' rent.", LEASE)
    src = "The fair market value is ₹6 crore and the distress sale value is ₹4.5 crore."
    assert "number" in kinds("The distress sale value is about 60% of the fair market value.", src)
    # a duration is not an item count: 15 days × ₹96,000 must not explain a wrong total
    assert "number" in kinds("The invoice total comes to ₹14,40,000.", INVOICE)


def test_money_direction_from_table_columns_and_statement_words():
    assert "flow" in kinds("On 2 May 2024 the account paid ₹8.75 lakh to Godavari Cold Storage.", TABLE)
    assert "flow" in kinds("The rent of ₹3,25,000 was credited to the account on 6 May 2024.", TABLE)
    assert "flow" not in kinds("Godavari Cold Storage sent ₹8,75,000 to the account on 2 May 2024.", TABLE)
    assert "flow" not in kinds("₹3.25 lakh of rent was paid to Orbit Realty LLP on 6 May 2024.", TABLE)
    prose = "On 05 April 2024, ₹12,00,000 was debited by RTGS to Sunrise Traders."
    assert "flow" in kinds("On 05 April 2024, ₹12,00,000 was credited to the account from Sunrise Traders.", prose)
    md = "| Date | Particulars | Withdrawals | Deposits | Balance |\n| --- | --- | --- | --- | --- |\n" \
         "| 03/07/2024 | NEFT from Konark Infra | | 4,70,000.00 | 8,40,750.00 |"
    assert "flow" in kinds("₹4.7 lakh was debited on 3 July 2024 towards Konark Infra.", md)


def test_from_to_arithmetic():
    src = "Net profit fell from ₹2.9 crore in FY 2022-23 to ₹1.7 crore in FY 2023-24."
    assert "arithmetic" in kinds("Net profit rose from ₹2.9 crore to ₹1.7 crore.", src)
    assert "arithmetic" in kinds("Net profit increased to ₹1.7 crore in FY 2023-24.", src)
    assert "arithmetic" not in kinds("Net profit dropped to ₹1.7 crore.", src)


def test_wording_fixes():
    lease = "Orbit Realty LLP leases warehouse unit B-14 in Bhiwandi to Kaveri Agro Foods Ltd for five years."
    assert "roles" not in kinds("Kaveri Agro Foods rents unit B-14 in Bhiwandi from Orbit Realty LLP.", lease)
    assert "roles" in kinds("Orbit Realty rents unit B-14 in Bhiwandi from Kaveri Agro Foods.", lease)
    fin = "The current ratio declined to 1.08, below the bank's benchmark of 1.25."
    assert "negation" not in kinds("At 1.08, the current ratio is under the 1.25 benchmark.", fin)
    assert verifier._disambiguate("The ratio declined to 1.08.") == "The ratio decreased to 1.08."
    assert verifier._disambiguate("The bank declined the request.") == "The bank refused the request."
    val = "The valuation excludes plant and machinery."
    assert not kinds("Plant and machinery were not included in the valuation.", val) & {"negation", "direction"}
    audit = "The auditor issued a qualified opinion on the FY 2023-24 statements of Sunrise Traders Pvt Ltd."
    assert "party" not in kinds("The auditor qualified its opinion on Sunrise Traders' FY 2023-24 statements.", audit)
    assert "party" not in kinds("The processing fee is INR 3,12,500.", "The processing fee is ₹3,12,500.")

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

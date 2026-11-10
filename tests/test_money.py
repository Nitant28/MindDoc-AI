"""ADR-0010: exact money. Property-style tests without extra dependencies (seeded random cases)."""
import random
import re
from decimal import Decimal
from pathlib import Path

import pytest

from app.finance.money import Money, MoneyError, parse_amount, signed_balance


@pytest.mark.parametrize("text,minor,side,neg", [
    ("1,23,456.78", 12345678, None, False),
    ("123,456.78", 12345678, None, False),
    ("123456.78", 12345678, None, False),
    ("₹ 1,234", 123400, None, False),
    ("Rs. 1,234.50", 123450, None, False),
    ("INR 1,234.00", 123400, None, False),
    ("1,234.00 Cr", 123400, "CR", False),
    ("1,234.00Dr", 123400, "DR", False),
    ("(1,234.00)", -123400, None, True),
    ("-1,234.00", -123400, None, True),
    ("1,234.00-", -123400, None, True),
    ("0.05", 5, None, False),
    ("1,00,00,000.00", 1000000000, None, False),
])
def test_parse_valid(text, minor, side, neg):
    p = parse_amount(text)
    assert p.money == Money(minor) and p.side == side and p.negative == neg and p.raw == text


@pytest.mark.parametrize("text", ["", "abc", "1,2,3", "12,34.00", "1.234", "1,234.567", "$1.00", "1.2.3"])
def test_parse_rejects_ambiguous(text):
    with pytest.raises(MoneyError):
        parse_amount(text)


def test_no_silent_rounding_and_currency_safety():
    with pytest.raises(MoneyError):
        Money.from_decimal(Decimal("1.005"))
    with pytest.raises(MoneyError):
        Money(100, "INR") + Money(100, "USD")
    with pytest.raises(MoneyError):
        Money(1.5)  # type: ignore[arg-type]
    with pytest.raises(MoneyError):
        Money(1, "XXX")
    assert Money(5, "JPY").to_decimal() == Decimal("5")


def test_signed_balance_overdraft():
    assert signed_balance(parse_amount("2,500.00 Dr")) == Money(-250000)
    assert signed_balance(parse_amount("2,500.00 Cr")) == Money(250000)


def test_format_round_trip_random():
    rng = random.Random(7)
    for _ in range(2000):
        m = Money(rng.randint(-10**12, 10**12))
        for indian in (True, False):
            assert parse_amount(m.format(indian=indian)).money == m


def test_arithmetic_exact_and_associative():
    rng = random.Random(11)
    xs = [Money(rng.randint(-10**9, 10**9)) for _ in range(300)]
    total = Money.zero()
    for x in xs:
        total = total + x
    assert total.minor == sum(x.minor for x in xs)
    a, b, c = xs[:3]
    assert (a + b) + c == a + (b + c)
    assert Money(10) + Money(20) == Money(30)  # 0.10 + 0.20 == 0.30 exactly


def test_no_float_in_finance_package():
    """ADR-0010 guard: the financial package never uses float."""
    pkg = Path(__file__).resolve().parents[1] / "app" / "finance"
    offenders = []
    for f in pkg.rglob("*.py"):
        for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            code = line.split("#", 1)[0]
            if re.search(r"\bfloat\s*\(|:\s*float\b|->\s*float\b", code):
                offenders.append(f"{f.name}:{i}")
    assert not offenders, f"float used in app/finance: {offenders}"

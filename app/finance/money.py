"""Exact money (ADR-0010): integer minor units + explicit ISO-4217 currency. No floats anywhere in app/finance.

Parsing accepts the forms printed on Indian bank statements:
  1,23,456.78   123,456.78   123456.78   ₹ 1,234   Rs. 1,234.50   INR 1,234.00
  1,234.00 Cr   1,234.00Dr   (1,234.00)   -1,234.00   1,234.00-
and never rounds: an amount with more decimals than the currency allows is rejected, not silently rounded.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Optional

# Minor-unit exponents (ISO 4217). Extend deliberately; unknown currencies are rejected rather than assumed.
CURRENCY_EXPONENT = {"INR": 2, "USD": 2, "EUR": 2, "GBP": 2, "AED": 2, "SGD": 2, "AUD": 2, "CAD": 2, "CHF": 2,
                     "JPY": 0, "KWD": 3, "BHD": 3, "OMR": 3}


class MoneyError(ValueError):
    pass


@dataclass(frozen=True, order=False)
class Money:
    minor: int
    currency: str = "INR"

    def __post_init__(self):
        if isinstance(self.minor, bool) or not isinstance(self.minor, int):
            raise MoneyError(f"minor units must be int, got {type(self.minor).__name__}")
        if self.currency not in CURRENCY_EXPONENT:
            raise MoneyError(f"unknown currency {self.currency!r}")

    # ---- arithmetic (same currency only) -----------------------------------------------------------------------
    def _check(self, other: "Money") -> None:
        if not isinstance(other, Money):
            raise MoneyError(f"cannot combine Money with {type(other).__name__}")
        if other.currency != self.currency:
            raise MoneyError(f"currency mismatch: {self.currency} vs {other.currency}")

    def __add__(self, other: "Money") -> "Money":
        self._check(other)
        return Money(self.minor + other.minor, self.currency)

    def __sub__(self, other: "Money") -> "Money":
        self._check(other)
        return Money(self.minor - other.minor, self.currency)

    def __neg__(self) -> "Money":
        return Money(-self.minor, self.currency)

    def __abs__(self) -> "Money":
        return Money(abs(self.minor), self.currency)

    def __lt__(self, other: "Money") -> bool:
        self._check(other)
        return self.minor < other.minor

    def __le__(self, other: "Money") -> bool:
        self._check(other)
        return self.minor <= other.minor

    def __gt__(self, other: "Money") -> bool:
        self._check(other)
        return self.minor > other.minor

    def __ge__(self, other: "Money") -> bool:
        self._check(other)
        return self.minor >= other.minor

    @staticmethod
    def zero(currency: str = "INR") -> "Money":
        return Money(0, currency)

    # ---- conversion -------------------------------------------------------------------------------------------
    @property
    def exponent(self) -> int:
        return CURRENCY_EXPONENT[self.currency]

    def to_decimal(self) -> Decimal:
        return Decimal(self.minor).scaleb(-self.exponent)

    @classmethod
    def from_decimal(cls, value: Decimal, currency: str = "INR") -> "Money":
        exp = CURRENCY_EXPONENT.get(currency)
        if exp is None:
            raise MoneyError(f"unknown currency {currency!r}")
        scaled = value.scaleb(exp)
        if scaled != scaled.to_integral_value():
            raise MoneyError(f"{value} has more than {exp} decimal places for {currency}")
        return cls(int(scaled), currency)

    def format(self, indian: Optional[bool] = None, symbol: bool = False) -> str:
        """Human formatting; Indian digit grouping by default for INR."""
        indian = (self.currency == "INR") if indian is None else indian
        d = abs(self.to_decimal())
        whole, _, frac = f"{d:.{self.exponent}f}".partition(".")
        if indian and len(whole) > 3:
            head, tail = whole[:-3], whole[-3:]
            groups = []
            while len(head) > 2:
                groups.insert(0, head[-2:])
                head = head[:-2]
            if head:
                groups.insert(0, head)
            whole = ",".join(groups + [tail])
        elif not indian:
            whole = f"{int(whole):,}"
        text = whole + (f".{frac}" if frac else "")
        prefix = ("₹" if self.currency == "INR" else self.currency + " ") if symbol else ""
        return ("-" if self.minor < 0 else "") + prefix + text

    def __str__(self) -> str:
        return self.format(symbol=True)


@dataclass(frozen=True)
class ParsedAmount:
    money: Money
    side: Optional[str]          # "CR" | "DR" | None (as printed)
    negative: bool               # printed with a minus sign or parentheses
    raw: str


_CUR = r"(?:₹|rs\.?|inr|\$|usd|€|eur|£|gbp)"
_AMOUNT_RE = re.compile(
    rf"^\s*(?P<open>\()?\s*(?P<sign1>[-+])?\s*(?P<cur>{_CUR})?\s*(?P<sign2>[-+])?\s*"
    r"(?P<num>\d{1,3}(?:,\d{2,3})+(?:\.\d+)?|\d+(?:\.\d+)?|\.\d+)"
    r"\s*(?P<trail>-)?\s*(?P<close>\))?\s*\(?\s*(?P<side>cr|dr|c|d)?\.?\s*\)?\s*$",
    re.I)
_CUR_CODE = {"₹": "INR", "rs": "INR", "rs.": "INR", "inr": "INR", "$": "USD", "usd": "USD", "€": "EUR",
             "eur": "EUR", "£": "GBP", "gbp": "GBP"}


def _valid_grouping(num: str) -> bool:
    """Accept Indian (x,xx,xx,xxx) and western (x,xxx,xxx) grouping; reject malformed comma placement."""
    if "," not in num:
        return True
    whole = num.split(".")[0]
    parts = whole.split(",")
    if not (1 <= len(parts[0]) <= 3) or len(parts[-1]) != 3:
        return False
    middle = parts[1:-1]
    return all(len(p) == 3 for p in middle) or all(len(p) == 2 for p in middle)


def parse_amount(text: str, currency: str = "INR") -> ParsedAmount:
    """Parse one printed amount exactly. Raises MoneyError on anything ambiguous or malformed."""
    if text is None:
        raise MoneyError("empty amount")
    raw = text
    t = text.replace(" ", " ").strip()
    m = _AMOUNT_RE.match(t)
    if not m:
        raise MoneyError(f"not an amount: {raw!r}")
    num = m.group("num")
    if not _valid_grouping(num):
        raise MoneyError(f"malformed digit grouping: {raw!r}")
    if bool(m.group("open")) != bool(m.group("close")) and not m.group("side"):
        raise MoneyError(f"unbalanced parentheses: {raw!r}")
    cur = m.group("cur")
    if cur:
        code = _CUR_CODE.get(cur.lower().rstrip(".") if cur.lower() != "rs." else "rs.", _CUR_CODE.get(cur.lower()))
        if code and code != currency:
            raise MoneyError(f"amount is in {code}, expected {currency}: {raw!r}")
    try:
        value = Decimal(num.replace(",", ""))
    except InvalidOperation as e:
        raise MoneyError(f"not a number: {raw!r}") from e
    negative = bool(m.group("open") and m.group("close")) or m.group("sign1") == "-" or m.group("sign2") == "-" \
        or bool(m.group("trail"))
    money = Money.from_decimal(-value if negative else value, currency)
    side = m.group("side")
    side = {"cr": "CR", "c": "CR", "dr": "DR", "d": "DR"}[side.lower()] if side else None
    return ParsedAmount(money, side, negative, raw)


def signed_balance(p: ParsedAmount) -> Money:
    """Balance as a signed amount: DR (overdrawn) is negative, CR or unmarked is positive."""
    if p.side == "DR" and p.money.minor > 0:
        return -p.money
    return p.money

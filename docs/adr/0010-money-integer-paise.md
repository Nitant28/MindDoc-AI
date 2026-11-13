# ADR-0010 — Money as integer minor units with explicit currency

**Status:** Accepted (owner mandate 2026-11-10)

**Context.** The current code has no money type; the claim verifier parses amounts as Python `float`
(audit A14). Running-balance reconciliation must be exact: `0.1 + 0.2 != 0.3` in binary floating point, and a one-paisa
error is a reconciliation failure. Statements can also contain foreign-currency accounts.

**Decision.**
- Database: `amount_minor BIGINT NOT NULL` + `currency CHAR(3) NOT NULL` (ISO 4217). For INR the minor unit is the paisa
  (exponent 2). The exponent comes from a currency table, never assumed. Rates and ratios use `NUMERIC(18,8)`.
- Python: `app/finance/money.py` — an immutable `Money(minor: int, currency: str)` with exact add/sub, comparison only
  within one currency (mixing raises), parsing from text via `decimal.Decimal` with Indian and western digit grouping,
  `Cr`/`Dr` suffixes, parentheses and minus signs; formatting in Indian grouping.
- Every parsed amount keeps its raw text next to the normalised value.
- No `float` in `app/finance/` — enforced by a CI check.

**Alternatives.** `NUMERIC(20,2)` columns (exact, but invites mixing with floats in Python and hides the currency);
`float` (rejected: inexact).

**Consequences.** Conversions at the API boundary (JSON carries integers in minor units plus currency, and a formatted
string). Cross-currency totals require explicit FX with a recorded rate source.

**Acceptance.** Property tests: parse→format round-trips; addition is associative and exact; mixing currencies raises;
CI fails if `float` appears in `app/finance/`.

**Revisit when.** Crypto or sub-paisa instruments enter scope.

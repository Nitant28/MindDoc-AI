"""Bank accounts as entities (design F §2.3, §7): masked display, keyed hash for matching, holder name.

* Account numbers are never stored in full: `mask_account` keeps the last four digits, and `account_hash` is a keyed
  HMAC-SHA256 of the digits, so two statements of the same account match without the number being kept. When the
  statement itself prints a masked number (XXXX1234), the hash is of that masked form (`hash_basis = "masked"`); it
  only matches the same mask.
* The key comes from ACCOUNT_HASH_KEY, or is derived from JWT_SECRET. Set it explicitly in production and keep it
  stable: with a new key, the same account gets a new hash (re-analysis recomputes stored hashes).
* The holder name is read only from a labelled field in the statement header ("Account Name:", "Account Holder:",
  "Customer Name:"). Account Aggregator profile data is not read (see app/finance/aa.py); an analyst can set the
  holder for any account.
"""
from __future__ import annotations

import hashlib
import hmac
import re
from typing import Optional

from app.core.config import settings


def _key() -> bytes:
    if settings.account_hash_key:
        return settings.account_hash_key.encode()
    return hashlib.sha256(b"minddoc-account-hash:" + settings.jwt_secret.encode()).digest()


def normalise_account(raw: Optional[str]) -> Optional[str]:
    """Digits and mask characters only, masks as X: 'xxxx-1234' -> 'XXXX1234'. None when nothing usable."""
    if not raw:
        return None
    s = re.sub(r"[^0-9Xx*]", "", raw).upper().replace("*", "X")
    return s if len(re.sub(r"\D", "", s)) >= 3 and len(s) >= 6 else None


def mask_account(raw: Optional[str]) -> Optional[str]:
    """Keep only the last four digits: '50200014567892' -> 'XXXXXXXXXX7892'."""
    s = normalise_account(raw)
    if not s:
        return None
    digits_at = [i for i, ch in enumerate(s) if ch.isdigit()]
    keep = set(digits_at[-4:])
    return "".join(ch if i in keep else "X" for i, ch in enumerate(s))


def account_hash(raw: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    """(keyed hash, basis): basis "full" for an unmasked number, "masked" when the source printed a mask."""
    s = normalise_account(raw)
    if not s:
        return None, None
    basis = "masked" if "X" in s else "full"
    return hmac.new(_key(), s.encode(), hashlib.sha256).hexdigest(), basis


def account_key(ifsc: Optional[str], digest: str) -> str:
    return f"{(ifsc or '-').upper()}:{digest}"


_HOLDER = re.compile(
    r"(?:account\s*holder(?:'s)?(?:\s*name)?|name\s*of\s*(?:the\s*)?account\s*holder|account\s*name|customer\s*name)"
    r"\s*[:\-]\s*(?P<name>[A-Za-z][A-Za-z0-9&.,'()/\- ]{1,100}?)"
    r"(?=\s*(?:$|\n|\s{2,}|\b(?:account|a/c|acct|type|ifsc|branch|customer\s*id|cif|address|period|statement|"
    r"currency|mobile|email|pan)\b))",
    re.I | re.M)


def extract_holder(header_text: str) -> Optional[str]:
    """The account holder's name from a labelled header field, or None."""
    m = _HOLDER.search(header_text or "")
    if not m:
        return None
    name = " ".join(m.group("name").split()).strip(" ,.-")
    return name if 2 <= len(name) <= 100 and re.search(r"[A-Za-z]{2}", name) else None

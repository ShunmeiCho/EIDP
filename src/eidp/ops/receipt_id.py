"""Validation for opaque, non-secret operator receipt identifiers."""

from __future__ import annotations

import re

_RECEIPT_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:@+-]{0,127}$")


def require_receipt_id(value: str) -> str:
    """Return a receipt ID only when it matches the exact public allowlist."""

    if _RECEIPT_ID_PATTERN.fullmatch(value) is None:
        raise ValueError("receipt ID must be a bounded allowlisted identifier")
    return value

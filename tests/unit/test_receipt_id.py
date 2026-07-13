from __future__ import annotations

import pytest

from eidp.ops.receipt_id import require_receipt_id


@pytest.mark.parametrize(
    "value",
    (
        "A",
        "A" + "z" * 127,
        "receipt:2026-07-12_01.02@ICT+off-host",
    ),
)
def test_require_receipt_id_accepts_only_the_exact_allowlist_boundaries(value: str) -> None:
    assert require_receipt_id(value) == value


@pytest.mark.parametrize(
    "value",
    (
        "",
        "A" + "z" * 128,
        " leading",
        "trailing ",
        "line\nbreak",
        "tab\tvalue",
        "nul\x00value",
        "receipт",
        'quote"value',
        "quote'value",
        "dollar$value",
        "semi;colon",
        "pipe|value",
        "amp&value",
        "back`tick",
        "slash/value",
        "back\\slash",
        "(subshell)",
    ),
)
def test_require_receipt_id_rejects_outside_allowlist_or_unbounded_values(value: str) -> None:
    with pytest.raises(ValueError, match="receipt"):
        require_receipt_id(value)

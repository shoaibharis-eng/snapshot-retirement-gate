"""The concrete repairs the scenarios replay against the toy project."""

from __future__ import annotations

from reproduction.repairs import MoveFunction, RenameSymbol, Repair, ReplaceText

_RENAME_CLAIM = "Renamed quote_price to price_for and updated its caller in checkout."

_RENAME_EVERYWHERE = RenameSymbol(
    "quote_price", "price_for", ("shop/pricing.py", "shop/checkout.py")
)

CLEAN_RENAME = Repair(claim=_RENAME_CLAIM, edits=(_RENAME_EVERYWHERE,))

# The agent reports exactly what it reported for the clean rename. The
# off-by-one in the bulk discount appears nowhere in its own account.
RENAME_WITH_BEHAVIOUR_CHANGE = Repair(
    claim=_RENAME_CLAIM,
    edits=(
        _RENAME_EVERYWHERE,
        ReplaceText(
            "shop/pricing.py",
            "if quantity >= BULK_THRESHOLD:",
            "if quantity > BULK_THRESHOLD:",
        ),
    ),
)

RENAME_PLUS_SIGNATURE_CHANGE = Repair(
    claim="Renamed quote_price to price_for and added a currency option to unit_price.",
    edits=(
        _RENAME_EVERYWHERE,
        ReplaceText(
            "shop/catalog.py",
            "def unit_price(sku):",
            'def unit_price(sku, currency="USD"):',
        ),
    ),
)

# A correct rename, and next to it a change that has nothing to do with it.
RENAME_WITH_COLLATERAL_DAMAGE = Repair(
    claim=_RENAME_CLAIM,
    edits=(
        _RENAME_EVERYWHERE,
        ReplaceText(
            "shop/catalog.py",
            '"widget": Decimal("2.50"),',
            '"widget": Decimal("2.05"),',
        ),
    ),
)

RENAME_AND_EDIT_THE_SUITE = Repair(
    claim="Renamed quote_price to price_for and updated the tests to match.",
    edits=(
        _RENAME_EVERYWHERE,
        RenameSymbol("quote_price", "price_for", ("tests/test_pricing.py",)),
    ),
)

_RECEIPTS_HEADER = '''"""Receipts: the printed form of an order."""

import textwrap

from shop.checkout import order_total
from shop.pricing import quote_price
'''

SPLIT_OUT_RECEIPTS = Repair(
    claim=(
        "Moved format_receipt into a new shop.receipts module so that "
        "shop.checkout no longer imports textwrap."
    ),
    edits=(
        MoveFunction("shop/checkout.py", "format_receipt", "shop/receipts.py", _RECEIPTS_HEADER),
        ReplaceText("shop/checkout.py", "import textwrap\n", ""),
    ),
)

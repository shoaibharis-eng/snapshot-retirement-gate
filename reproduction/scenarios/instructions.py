"""The instructions the scenarios log, each with its scope."""

from __future__ import annotations

from reproduction.scenarios.model import Instruct
from verifier.log import Rename, Scope

RENAME_QUOTE_PRICE = Instruct(
    issued_by="orchestrator",
    instruction="Rename shop.pricing.quote_price to price_for. Pricing behaviour must not change.",
    scope=Scope((Rename("shop.pricing.quote_price", "shop.pricing.price_for"),)),
)

# The brief's own example: an instruction that says nothing about a boundary.
FIX_FAILING_IMPORT = Instruct(
    issued_by="orchestrator",
    instruction=(
        "Fix the failing import: shop.checkout must load without the receipt formatting dependency."
    ),
    scope=Scope(),
)

ACCEPT_RECEIPTS_SPLIT = Instruct(
    issued_by="human:reviewer",
    instruction="Accepted: format_receipt now lives in shop.receipts.",
    scope=Scope((Rename("shop.checkout.format_receipt", "shop.receipts.format_receipt"),)),
)

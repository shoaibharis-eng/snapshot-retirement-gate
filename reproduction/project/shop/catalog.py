"""Catalogue: what the shop sells and the list price of one unit."""

from decimal import Decimal

PRICES = {
    "widget": Decimal("2.50"),
    "gadget": Decimal("19.99"),
}


def unit_price(sku):
    """Return the list price of one unit of ``sku``."""
    if sku not in PRICES:
        raise KeyError(f"unknown product: {sku}")
    return PRICES[sku]

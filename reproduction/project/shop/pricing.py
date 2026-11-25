"""Pricing: what a quantity of one product costs."""

from decimal import ROUND_HALF_UP, Decimal

from shop.catalog import unit_price

BULK_THRESHOLD = 10
BULK_DISCOUNT = Decimal("0.10")
_CENT = Decimal("0.01")


def quote_price(sku, quantity):
    """Price ``quantity`` units of ``sku``. Ten units or more get 10% off."""
    if quantity < 1:
        raise ValueError("quantity must be at least 1")
    total = unit_price(sku) * quantity
    if quantity >= BULK_THRESHOLD:
        total -= total * BULK_DISCOUNT
    return total.quantize(_CENT, rounding=ROUND_HALF_UP)

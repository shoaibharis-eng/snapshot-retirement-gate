"""Checkout: the total of an order and its printed receipt."""

import textwrap
from decimal import Decimal

from shop.pricing import quote_price


def order_total(lines):
    """Sum the price of every ``(sku, quantity)`` line of an order."""
    return sum((quote_price(sku, quantity) for sku, quantity in lines), Decimal("0.00"))


def format_receipt(lines):
    """Render an order as one text row per line, followed by the total."""
    rows = [
        f"{quantity:>3} x {textwrap.shorten(sku, width=12):<12} {quote_price(sku, quantity):>8}"
        for sku, quantity in lines
    ]
    rows.append(f"{'TOTAL':<18} {order_total(lines):>8}")
    return "\n".join(rows)

import unittest
from decimal import Decimal

from shop.pricing import quote_price


class QuotePriceTests(unittest.TestCase):
    def test_single_unit_costs_the_list_price(self):
        self.assertEqual(quote_price("widget", 1), Decimal("2.50"))

    def test_five_units_get_no_discount(self):
        self.assertEqual(quote_price("widget", 5), Decimal("12.50"))

    def test_bulk_discount_starts_at_ten_units(self):
        self.assertEqual(quote_price("widget", 10), Decimal("22.50"))

    def test_discounted_price_is_rounded_to_cents(self):
        self.assertEqual(quote_price("gadget", 11), Decimal("197.90"))

    def test_quantity_must_be_positive(self):
        with self.assertRaises(ValueError):
            quote_price("widget", 0)

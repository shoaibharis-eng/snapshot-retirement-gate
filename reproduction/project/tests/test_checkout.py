import unittest
from decimal import Decimal

from shop.checkout import order_total


class OrderTotalTests(unittest.TestCase):
    def test_total_sums_every_line(self):
        self.assertEqual(order_total([("widget", 12), ("gadget", 1)]), Decimal("46.99"))

    def test_empty_order_costs_nothing(self):
        self.assertEqual(order_total([]), Decimal("0.00"))

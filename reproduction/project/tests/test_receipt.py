import unittest

from shop.checkout import format_receipt


class FormatReceiptTests(unittest.TestCase):
    ORDER = [("widget", 12), ("gadget", 1)]

    def test_one_row_per_line_plus_a_total_row(self):
        self.assertEqual(len(format_receipt(self.ORDER).splitlines()), 3)

    def test_total_row_shows_the_order_total(self):
        self.assertTrue(format_receipt(self.ORDER).splitlines()[-1].endswith("46.99"))

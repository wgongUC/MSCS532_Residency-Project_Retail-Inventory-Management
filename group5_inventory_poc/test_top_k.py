"""Tests for the Phase 3 curveball: top_k_bestsellers(k).

Run: python3 -m unittest -v
"""
import random
import unittest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from inventory import Inventory


def brute_force(expected_sales, k):
    """Reference answer: sort every product with sales > 0 by (-sold, sku)."""
    ranked = sorted(((-sold, sku) for sku, sold in expected_sales.items() if sold > 0))
    return [(sku, -neg) for neg, sku in ranked[:k]]


def pairs(result):
    return [(p['sku'], p['weekly_sold']) for p in result]


def heap_snapshot(inv):
    """Everything top-k must leave untouched: heap layout and saved positions."""
    return [(id(p), p.sku, p.weekly_sold, p.heap_index) for p in inv.heap.items]


class TopKBestsellerTests(unittest.TestCase):
    def setUp(self):
        self.i = Inventory()
        for sku in ['A', 'B', 'C', 'D', 'E', 'F']:
            self.i.add(sku, 'Product ' + sku, 1000, 100)

    def test_no_sales_returns_empty(self):
        self.assertEqual(self.i.top_k_bestsellers(3), [])

    def test_order_and_sku_tiebreak(self):
        for sku, qty in [('C', 5), ('A', 5), ('F', 9), ('B', 1), ('E', 5)]:
            self.i.sell(sku, qty)
        self.assertEqual(pairs(self.i.top_k_bestsellers(5)),
                         [('F', 9), ('A', 5), ('C', 5), ('E', 5), ('B', 1)])
        self.assertEqual(pairs(self.i.top_k_bestsellers(2)), [('F', 9), ('A', 5)])

    def test_k_larger_than_sellers_and_zero(self):
        self.i.sell('B', 2)
        self.i.sell('D', 7)
        self.assertEqual(pairs(self.i.top_k_bestsellers(100)), [('D', 7), ('B', 2)])
        self.assertEqual(self.i.top_k_bestsellers(0), [])

    def test_unsold_products_never_listed(self):
        self.i.sell('A', 1)
        self.assertEqual([p['sku'] for p in self.i.top_k_bestsellers(6)], ['A'])

    def test_invalid_k_rejected(self):
        for bad in (-1, 1.5, True, '3', None):
            with self.assertRaises(ValueError):
                self.i.top_k_bestsellers(bad)

    def test_first_item_matches_bestseller(self):
        self.i.sell('E', 4)
        self.i.sell('B', 4)
        self.assertEqual(self.i.top_k_bestsellers(1)[0], self.i.bestseller())

    def test_does_not_mutate_state(self):
        rng = random.Random(1)
        for sku in 'ABCDEF':
            self.i.sell(sku, rng.randint(1, 50))
        heap_before = heap_snapshot(self.i)
        records_before = self.i.sorted_by_price()
        for k in range(0, 8):
            self.i.top_k_bestsellers(k)
        self.assertEqual(heap_snapshot(self.i), heap_before)
        self.assertEqual(self.i.sorted_by_price(), records_before)
        self.i.validate()

    def test_returns_copies(self):
        self.i.sell('A', 3)
        result = self.i.top_k_bestsellers(1)
        result[0]['weekly_sold'] = 999
        self.assertEqual(self.i.get('A')['weekly_sold'], 3)

    def test_after_delete_and_reset(self):
        self.i.sell('A', 9)
        self.i.sell('B', 8)
        self.i.sell('C', 7)
        self.i.delete('A')
        self.assertEqual(pairs(self.i.top_k_bestsellers(2)), [('B', 8), ('C', 7)])
        self.i.reset_week()
        self.assertEqual(self.i.top_k_bestsellers(3), [])

    def test_lazy_week_rollover_applies(self):
        self.i.sell('A', 5)
        nxt = self.i.week_start + timedelta(days=7)
        self.i._maybe_roll_week(datetime(nxt.year, nxt.month, nxt.day, tzinfo=ZoneInfo('America/Detroit')))
        self.assertEqual(self.i.top_k_bestsellers(5), [])

    def test_randomized_against_brute_force(self):
        rng = random.Random(532)
        inv = Inventory()
        sales = {}
        for step in range(3000):
            sku = f'S{rng.randrange(120):03}'
            op = rng.random()
            if sku not in sales:
                inv.add(sku, sku, 100_000, rng.randrange(1, 500))
                sales[sku] = 0
            elif op < 0.75:
                qty = rng.randint(1, 4)            # small quantities => many ties
                inv.sell(sku, qty)
                sales[sku] += qty
            elif op < 0.80:
                inv.delete(sku)
                del sales[sku]
            elif op < 0.81:
                inv.reset_week()
                sales = {s: 0 for s in sales}
            if step % 25 == 0:
                before = heap_snapshot(inv)
                k = rng.randint(0, 40)
                self.assertEqual(pairs(inv.top_k_bestsellers(k)), brute_force(sales, k))
                self.assertEqual(heap_snapshot(inv), before)
        inv.validate()


if __name__ == '__main__':
    unittest.main()

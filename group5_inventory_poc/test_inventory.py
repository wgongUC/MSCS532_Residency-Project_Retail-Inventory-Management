"""Run: python3 -m unittest -v"""
import random
import unittest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from inventory import Inventory


class InventoryTests(unittest.TestCase):
    def setUp(self):
        self.i = Inventory()
        for sku, price in [('A', 400), ('B', 300), ('C', 600), ('D', 1000)]:
            self.i.add(sku, 'Product '+sku, 1000, price)

    def test_lookup_and_copy(self):
        data = self.i.get('A')
        data['stock'] = -123
        self.assertEqual(self.i.get('A')['stock'], 1000)

    def test_price_order_and_range_inclusive(self):
        self.assertEqual([p['sku'] for p in self.i.sorted_by_price()], ['B','A','C','D'])
        self.assertEqual([p['sku'] for p in self.i.price_range(300,600)], ['B','A','C'])
        self.i.change_price('D', 300)
        self.assertEqual([p['sku'] for p in self.i.sorted_by_price()], ['B','D','A','C'])
        self.i.validate()

    def test_sales_best_and_ties(self):
        self.assertIsNone(self.i.bestseller())
        self.i.sell('C', 50)
        self.i.sell('B', 50)
        self.assertEqual(self.i.bestseller()['sku'], 'B')
        self.i.sell('C', 1)
        self.assertEqual(self.i.bestseller()['sku'], 'C')
        self.i.validate()

    def test_delete_top_and_arbitrary(self):
        self.i.sell('A', 40)
        self.i.sell('C', 60)
        self.i.delete('C')
        self.assertEqual(self.i.bestseller()['sku'], 'A')
        self.i.delete('B')
        self.i.delete('D')
        self.i.delete('A')
        self.assertIsNone(self.i.bestseller())
        self.i.validate()

    def test_restock_rename_and_reset(self):
        self.i.rename('A', 'Oat milk')
        self.i.restock('A', 12)
        self.i.sell('A', 1000)
        self.assertEqual(self.i.get('A')['stock'], 12)
        self.i.reset_week()
        self.assertEqual(self.i.get('A')['weekly_sold'], 0)
        self.assertIsNone(self.i.bestseller())
        self.i.validate()

    def test_rejected_requests_leave_state_unchanged(self):
        before = self.i.sorted_by_price()
        bad = [
            lambda: self.i.add('A', 'duplicate', 1, 1),
            lambda: self.i.add('E', ' ', 1, 1),
            lambda: self.i.add('E', 'test', -1, 1),
            lambda: self.i.add('E', 'test', 1, -1),
            lambda: self.i.add('E', 'test', True, 1),
            lambda: self.i.sell('A', 1001),
            lambda: self.i.sell('A', 0),
            lambda: self.i.restock('A', 1_000_000),
            lambda: self.i.price_range(600, 300),
            lambda: self.i.change_price('A', -1),
            lambda: self.i.rename('A', ''),
            lambda: self.i.delete('missing'),
        ]
        for operation in bad:
            with self.assertRaises((ValueError, KeyError)):
                operation()
        self.assertEqual(self.i.sorted_by_price(), before)
        self.i.validate()

    def test_capacity_and_case_sensitive(self):
        i = Inventory(capacity=1)
        i.add('a', 'Lower', 0, 0)
        with self.assertRaises(KeyError):
            i.get('A')
        with self.assertRaises(ValueError):
            i.add('A', 'Upper', 1, 1)
        i.validate()

    def test_lazy_week_rollover(self):
        self.i.sell('A', 20)
        old = self.i.week_start
        tz = ZoneInfo('America/Detroit')
        following_monday = old + timedelta(days=7)
        self.i._maybe_roll_week(datetime(following_monday.year, following_monday.month,
                                         following_monday.day, 0, 0, tzinfo=tz))
        self.assertEqual(self.i.week_start, following_monday)
        self.assertIsNone(self.i.bestseller())
        self.i.validate()

    def test_randomized_invariants(self):
        rng = random.Random(42)
        i = Inventory()
        expected = {}
        for step in range(1500):
            sku = f'S{rng.randrange(70):03}'
            op = rng.choice(['add', 'delete', 'price', 'sale', 'restock'])
            if op == 'add' and sku not in expected:
                cents = rng.randrange(200)
                i.add(sku, sku, 500, cents)
                expected[sku] = [cents, 500, 0]
            elif op == 'delete' and sku in expected:
                i.delete(sku)
                del expected[sku]
            elif op == 'price' and sku in expected:
                cents = rng.randrange(200)
                i.change_price(sku, cents)
                expected[sku][0] = cents
            elif op == 'sale' and sku in expected and expected[sku][1] >= 1:
                qty = rng.randint(1, min(10, expected[sku][1]))
                i.sell(sku, qty)
                expected[sku][1] -= qty
                expected[sku][2] += qty
            elif op == 'restock' and sku in expected:
                i.restock(sku, 7)
                expected[sku][1] += 7
            i.validate()
            self.assertEqual([p['sku'] for p in i.sorted_by_price()],
                             [k for k, v in sorted(expected.items(), key=lambda kv: (kv[1][0],kv[0]))])
            active = [(v[2], sku) for sku, v in expected.items() if v[2] > 0]
            top = i.bestseller()
            if active:
                best = sorted(active, key=lambda pair: (-pair[0], pair[1]))[0]
                self.assertEqual((top['weekly_sold'], top['sku']), best)
            else:
                self.assertIsNone(top)


if __name__ == '__main__':
    unittest.main()

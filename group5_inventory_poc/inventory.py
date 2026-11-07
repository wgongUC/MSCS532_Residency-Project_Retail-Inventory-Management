"""Group 5 retail inventory PoC. All times use the configured store time zone."""
import time
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
from product import Product
from max_heap import IndexedMaxHeap
from avl_tree import AVLPriceTree


class Inventory:
    def __init__(self, *, store_timezone: str = 'America/Detroit', capacity: int = 1_000_000):
        self.records: dict[str, Product] = {}
        self.heap = IndexedMaxHeap()
        self.prices = AVLPriceTree()
        self.capacity = capacity
        self.timezone = ZoneInfo(store_timezone)
        self.week_start = self._monday(datetime.now(self.timezone).date())
        self._roll_for: date | None = None   # week_start the cached instant belongs to
        self._roll_at = 0.0                  # PERF fix 3 cache: next rollover, epoch seconds

    @staticmethod
    def _monday(d: date) -> date:
        return d - timedelta(days=d.weekday())

    def _next_roll_epoch(self) -> float:
        """Epoch seconds of the first store-local Monday 00:00 after week_start.

        _maybe_roll_week rolls exactly when _monday(today) > week_start, i.e.
        on or after that Monday, so before this instant no rollover can happen.
        """
        nxt = self.week_start + timedelta(days=7 - self.week_start.weekday())
        return datetime(nxt.year, nxt.month, nxt.day, tzinfo=self.timezone).timestamp()

    def _maybe_roll_week(self, now: datetime | None = None) -> None:
        # PERF fix 3: this check runs before EVERY public operation. The
        # original built a timezone-aware datetime.now(), converted it and
        # computed a Monday each time. Instead, cache the instant the next week
        # starts (recomputed whenever week_start changes) and compare it with
        # the cheap time.time(). An explicit `now` (used by tests), or reaching
        # that instant, falls through to the original logic unchanged.
        if now is None:
            if self._roll_for != self.week_start:
                self._roll_for = self.week_start
                self._roll_at = self._next_roll_epoch()
            if time.time() < self._roll_at:
                return
        now = now or datetime.now(self.timezone)
        if now.tzinfo is None:
            raise ValueError('now must have timezone information')
        today = now.astimezone(self.timezone).date()
        monday = self._monday(today)
        if monday > self.week_start:
            self.reset_week(monday)

    @staticmethod
    def _sku(sku: str) -> None:
        if not isinstance(sku, str) or not sku:
            raise ValueError('SKU must be a nonempty, case-sensitive string')

    @staticmethod
    def _int(value: int, label: str, *, minimum: int = 0, maximum: int | None = None) -> None:
        if isinstance(value, bool) or not isinstance(value, int) or value < minimum or (maximum is not None and value > maximum):
            raise ValueError(f'{label} must be an integer between {minimum} and {maximum or "unbounded"}')

    def _existing(self, sku: str) -> Product:
        self._sku(sku)
        if sku not in self.records:
            raise KeyError(f'Unknown SKU: {sku}')
        return self.records[sku]

    def add(self, sku: str, name: str, stock: int, price_cents: int) -> dict:
        self._maybe_roll_week()
        self._sku(sku)
        if sku in self.records:
            raise ValueError(f'Duplicate SKU: {sku}')
        if len(self.records) >= self.capacity:
            raise ValueError('Product capacity exceeded')
        if not isinstance(name, str) or not name.strip():
            raise ValueError('Product name must not be blank')
        self._int(stock, 'stock', maximum=1_000_000)
        self._int(price_cents, 'price_cents')
        p = Product(sku, name, stock, price_cents)
        self.prices.insert((p.price_cents, p.sku))
        self.heap.add(p)
        self.records[sku] = p
        return p.public()

    def get(self, sku: str) -> dict:
        self._maybe_roll_week()
        return self._existing(sku).public()

    def rename(self, sku: str, name: str) -> dict:
        self._maybe_roll_week()
        p = self._existing(sku)
        if not isinstance(name, str) or not name.strip():
            raise ValueError('Product name must not be blank')
        p.name = name
        return p.public()

    def restock(self, sku: str, units: int) -> dict:
        self._maybe_roll_week()
        p = self._existing(sku)
        self._int(units, 'receipt units', minimum=1)
        if p.stock + units > 1_000_000:
            raise ValueError('Receipt would exceed maximum product stock')
        p.stock += units
        return p.public()

    def sell(self, sku: str, units: int) -> dict:
        self._maybe_roll_week()
        p = self._existing(sku)
        self._int(units, 'sale units', minimum=1)
        if units > p.stock:
            raise ValueError('Insufficient stock: overselling is forbidden')
        p.stock -= units
        p.weekly_sold += units
        self.heap.updated(p)
        return p.public()

    def change_price(self, sku: str, price_cents: int) -> dict:
        self._maybe_roll_week()
        p = self._existing(sku)
        self._int(price_cents, 'price_cents')
        if price_cents != p.price_cents:
            old = p.price_cents
            self.prices.remove((old, sku))
            self.prices.insert((price_cents, sku))
            p.price_cents = price_cents
        return p.public()

    def delete(self, sku: str) -> dict:
        self._maybe_roll_week()
        p = self._existing(sku)
        snapshot = p.public()
        self.prices.remove((p.price_cents, sku))
        self.heap.remove(p)
        del self.records[sku]
        return snapshot

    def bestseller(self) -> dict | None:
        self._maybe_roll_week()
        winner = self.heap.top()
        return winner.public() if winner is not None else None

    def top_k_bestsellers(self, k: int) -> list[dict]:
        """Phase 3 curveball: the k top weekly sellers, best first.

        Ties: SKU ascending (same rule as bestseller()). Only products with
        weekly sales > 0 are listed, matching bestseller() returning None when
        nothing has sold. If fewer than k products have sold, all of them are
        returned. k = 0 returns [].

        Read-only: the heap is walked, never popped or reordered, so the system
        state is unchanged. (The usual lazy week check still runs first, exactly
        as in bestseller(); without it, a query on Monday would report last
        week's sales.)  Cost: O(k log k) after that check, independent of n.
        """
        self._maybe_roll_week()
        self._int(k, 'k')
        return [p.public() for p in self.heap.top_k(k)]

    def sorted_by_price(self) -> list[dict]:
        self._maybe_roll_week()
        return [self.records[sku].public() for _, sku in self.prices.sorted_keys()]

    def price_range(self, low_cents: int, high_cents: int) -> list[dict]:
        self._maybe_roll_week()
        self._int(low_cents, 'minimum price')
        self._int(high_cents, 'maximum price')
        if low_cents > high_cents:
            raise ValueError('Price-range bounds are reversed')
        return [self.records[sku].public() for _, sku in self.prices.between(low_cents, high_cents)]

    def reset_week(self, start: date | None = None) -> None:
        """Explicit reset; also invoked lazily after a new store-local Monday."""
        for p in self.records.values():
            p.weekly_sold = 0
        self.heap.rebuild()
        self.week_start = start or self._monday(datetime.now(self.timezone).date())

    def validate(self) -> None:
        """O(n) integrity check, for testing and demonstrations only."""
        self.heap.validate()
        self.prices.validate()
        assert len(self.heap.items) == len(self.records)
        assert {id(p) for p in self.heap.items} == {id(p) for p in self.records.values()}
        actual = list(self.prices.sorted_keys())
        expected = sorted((p.price_cents, p.sku) for p in self.records.values())
        assert actual == expected

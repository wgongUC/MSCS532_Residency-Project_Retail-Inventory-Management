"""Group 5 retail inventory PoC. All times use the configured store time zone."""
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

    @staticmethod
    def _monday(d: date) -> date:
        return d - timedelta(days=d.weekday())

    def _maybe_roll_week(self, now: datetime | None = None) -> None:
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

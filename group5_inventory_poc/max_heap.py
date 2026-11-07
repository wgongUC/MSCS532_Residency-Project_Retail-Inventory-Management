"""Indexed binary max-heap: most sales first; SKU ascending breaks ties."""
from product import Product


class IndexedMaxHeap:
    """Max-heap of Products; each Product stores its own slot in ``heap_index``."""

    def __init__(self):
        self.items: list[Product] = []

    @staticmethod
    def _higher(a: Product, b: Product) -> bool:
        """True when a outranks b: more sales, then smaller SKU wins the tie."""
        return (-a.weekly_sold, a.sku) < (-b.weekly_sold, b.sku)

    def _swap(self, i: int, j: int) -> None:
        self.items[i], self.items[j] = self.items[j], self.items[i]
        self.items[i].heap_index, self.items[j].heap_index = i, j

    def _down(self, i: int) -> None:
        """Push the item at i down until both children rank below it."""
        n = len(self.items)
        while (child := 2 * i + 1) < n:
            if child + 1 < n and self._higher(self.items[child + 1], self.items[child]):
                child += 1
            if not self._higher(self.items[child], self.items[i]):
                return
            self._swap(i, child)
            i = child

    def _sift(self, i: int) -> None:
        """Restore order after the item at i changes priority (either direction): O(log n)."""
        while i and self._higher(self.items[i], self.items[parent := (i - 1) // 2]):
            self._swap(i, parent)
            i = parent
        self._down(i)

    def add(self, product: Product) -> None:
        product.heap_index = len(self.items)
        self.items.append(product)
        self._sift(product.heap_index)

    def updated(self, product: Product) -> None:
        """Fix the heap after weekly_sold changes: O(log n)."""
        self._sift(product.heap_index)

    def remove(self, product: Product) -> None:
        """Remove any SKU in O(log n) using its saved position."""
        i = product.heap_index
        if not 0 <= i < len(self.items) or self.items[i] is not product:
            raise RuntimeError('heap/index inconsistency')
        last = self.items.pop()
        product.heap_index = -1
        if last is not product:
            self.items[i] = last
            last.heap_index = i
            self._sift(i)

    def top(self) -> Product | None:
        """Bestseller this week, or None when nothing has sold."""
        return self.items[0] if self.items and self.items[0].weekly_sold else None

    def rebuild(self) -> None:
        """Bottom-up heapify: O(n)."""
        for i, product in enumerate(self.items):
            product.heap_index = i
        for i in reversed(range(len(self.items) // 2)):
            self._down(i)

    def validate(self) -> None:
        for i, p in enumerate(self.items):
            assert p.heap_index == i, ('bad heap index', p.sku)
            assert not i or not self._higher(p, self.items[(i - 1) // 2]), ('bad heap order', p.sku)

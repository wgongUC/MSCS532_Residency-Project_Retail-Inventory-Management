"""Indexed binary max-heap: most sales first; SKU ascending breaks ties."""
from product import Product


class IndexedMaxHeap:
    def __init__(self):
        self.items: list[Product] = []

    @staticmethod
    def _higher(a: Product, b: Product) -> bool:
        return a.weekly_sold > b.weekly_sold or (
            a.weekly_sold == b.weekly_sold and a.sku < b.sku)

    def _swap(self, i: int, j: int) -> None:
        self.items[i], self.items[j] = self.items[j], self.items[i]
        self.items[i].heap_index = i
        self.items[j].heap_index = j

    def _up(self, i: int) -> None:
        while i:
            p = (i - 1) // 2
            if not self._higher(self.items[i], self.items[p]):
                break
            self._swap(i, p)
            i = p

    def _down(self, i: int) -> None:
        n = len(self.items)
        while 2 * i + 1 < n:
            left, right = 2 * i + 1, 2 * i + 2
            best = left
            if right < n and self._higher(self.items[right], self.items[left]):
                best = right
            if not self._higher(self.items[best], self.items[i]):
                break
            self._swap(i, best)
            i = best

    def _repair(self, i: int) -> None:
        if i and self._higher(self.items[i], self.items[(i - 1) // 2]):
            self._up(i)
        else:
            self._down(i)

    def add(self, product: Product) -> None:
        product.heap_index = len(self.items)
        self.items.append(product)
        self._up(product.heap_index)

    def updated(self, product: Product) -> None:
        """Fix the heap after weekly_sold changes: O(log n)."""
        self._repair(product.heap_index)

    def remove(self, product: Product) -> None:
        """Remove an arbitrary SKU in O(log n), using its saved position."""
        i = product.heap_index
        if i < 0 or i >= len(self.items) or self.items[i] is not product:
            raise RuntimeError('Heap/index inconsistency')
        last = len(self.items) - 1
        self._swap(i, last)
        removed = self.items.pop()
        removed.heap_index = -1
        if i < len(self.items):
            self._repair(i)

    def top(self) -> Product | None:
        if not self.items or self.items[0].weekly_sold == 0:
            return None
        return self.items[0]

    def rebuild(self) -> None:
        """Bottom-up heapify: O(n)."""
        for i, product in enumerate(self.items):
            product.heap_index = i
        for i in range(len(self.items) // 2 - 1, -1, -1):
            self._down(i)

    def validate(self) -> None:
        for i, p in enumerate(self.items):
            assert p.heap_index == i, ('bad heap index', p.sku)
            if i:
                assert not self._higher(p, self.items[(i - 1) // 2]), ('bad heap order', p.sku)

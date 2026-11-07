"""Indexed binary max-heap: most sales first; SKU ascending breaks ties."""
import heapq

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

    def top_k(self, k: int) -> list[Product]:
        """The k highest-ranked products with sales > 0, best first. Read-only.

        Phase 3 curveball. The root is #1 in O(1); #2..#k are found WITHOUT
        popping (which would destroy the heap) and without copying it (O(n)).

        Idea: in a max-heap every child ranks below its parent, so the next
        best item is always a child of something already reported. Keep a
        small auxiliary min-heap (the "frontier") of candidate positions,
        ordered by the same rank key (-weekly_sold, sku):
            start with the root; repeat k times:
                pop the best candidate, report it, push its two children.
        The frontier grows by at most one per step (pop 1, push <= 2), so each
        step is O(log k): O(k log k) in total, independent of n.
        self.items and every heap_index are never written to.
        """
        items = self.items
        n = len(items)
        out: list[Product] = []
        if k <= 0 or n == 0 or items[0].weekly_sold == 0:
            return out
        root = items[0]
        # (-sold, sku) reproduces the heap's own order: more sales first, SKU
        # ascending on ties. SKUs are unique, so position i is never compared.
        frontier = [(-root.weekly_sold, root.sku, 0)]
        while frontier and len(out) < k:
            neg_sold, _, i = heapq.heappop(frontier)
            if neg_sold == 0:
                break  # nothing that has sold remains: everything left is 0
            out.append(items[i])
            for c in (2 * i + 1, 2 * i + 2):
                if c < n:
                    p = items[c]
                    heapq.heappush(frontier, (-p.weekly_sold, p.sku, c))
        return out

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

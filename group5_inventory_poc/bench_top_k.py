"""Benchmark for top_k_bestsellers(k): many queries, small k, large n.

Compares the read-only frontier walk with the obvious alternatives:
  sort_all     sort every product, take the first k            O(n log n)
  nsmallest    heapq.nsmallest over every product               O(n log k)
  copy_and_pop copy the heap, heapify, pop k (non-destructive)  O(n + k log n)
  frontier     best-first walk of the existing heap (ours)      O(k log k)

Every method must return exactly the same list (checked before timing).

Run: python3 bench_top_k.py          (n = 10k, 50k, 200k)
     python3 bench_top_k.py --quick  (n = 10k, 50k)
"""
import heapq
import random
import sys
import time

from inventory import Inventory

RANK = lambda p: (-p.weekly_sold, p.sku)   # same order as the heap: sales desc, SKU asc


def sort_all(inv, k):
    ranked = sorted((p for p in inv.records.values() if p.weekly_sold > 0), key=RANK)
    return [p.public() for p in ranked[:k]]


def nsmallest(inv, k):
    best = heapq.nsmallest(k, (p for p in inv.records.values() if p.weekly_sold > 0), key=RANK)
    return [p.public() for p in best]


def copy_and_pop(inv, k):
    h = [(-p.weekly_sold, p.sku, p) for p in inv.heap.items if p.weekly_sold > 0]
    heapq.heapify(h)
    return [heapq.heappop(h)[2].public() for _ in range(min(k, len(h)))]


def frontier(inv, k):
    return inv.top_k_bestsellers(k)


def build(n, rng):
    """A store of n products with skewed weekly sales (setup is not timed)."""
    inv = Inventory()
    for i in range(n):
        inv.add(f"SKU{i:07d}", "item", 1_000_000, rng.randint(99, 19_999))
    for p in inv.records.values():
        # Pareto-shaped sales; ~10% of products sold nothing this week; many ties.
        p.weekly_sold = 0 if rng.random() < 0.10 else int(rng.paretovariate(1.3) * 5)
    inv.heap.rebuild()
    inv.validate()
    return inv


def per_query_us(fn, inv, ks):
    t0 = time.perf_counter()
    for k in ks:
        fn(inv, k)
    return (time.perf_counter() - t0) / len(ks) * 1e6


def main():
    sizes = [10_000, 50_000] if "--quick" in sys.argv else [10_000, 50_000, 200_000]
    rng = random.Random(532)
    methods = [("sort_all", sort_all, 20), ("nsmallest", nsmallest, 40),
               ("copy_and_pop", copy_and_pop, 40), ("frontier", frontier, 20_000)]
    print(f"{'n':>8} | " + " | ".join(f"{name + ' µs':>15}" for name, _, _ in methods) + " | speedup vs best O(n)")
    print("-" * 100)
    for n in sizes:
        inv = build(n, rng)
        ks = [rng.randint(1, 20) for _ in range(20_000)]     # small k, many queries
        for k in (1, 5, 20, n):                               # correctness first
            ref = sort_all(inv, k)
            for name, fn, _ in methods:
                assert fn(inv, k) == ref, (name, n, k)
        heap_before = [(id(p), p.heap_index) for p in inv.heap.items]
        res = {name: per_query_us(fn, inv, ks[:reps]) for name, fn, reps in methods}
        assert heap_before == [(id(p), p.heap_index) for p in inv.heap.items], "heap was mutated"
        best_on = min(res["sort_all"], res["nsmallest"], res["copy_and_pop"])
        print(f"{n:>8,} | " + " | ".join(f"{res[name]:>15.1f}" for name, _, _ in methods)
              + f" | {best_on / res['frontier']:>8.0f}x")
    print("\nAll methods returned identical results; the heap was unchanged after every query.")
    print("Frontier cost stays flat as n grows (O(k log k)); every alternative grows with n.")


if __name__ == "__main__":
    main()

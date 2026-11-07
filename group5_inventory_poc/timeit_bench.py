"""timeit micro-benchmarks for ONE implementation (original or optimized).

Times each operation in isolation with the standard-library timeit module
(best of 5 repeats, reported as microseconds per call) on an inventory of n
products. It also fingerprints the answers to a fixed set of queries, so
compare.py can confirm both versions return identical results.

Usually run through compare.py. Direct use:
    python3 timeit_bench.py --impl optimized --n 50000
    python3 timeit_bench.py --impl original  --n 50000
    python3 timeit_bench.py --impl optimized --dataset common.csv --n 10000

Dataset CSV format (header row required):
    sku,name,stock,price_cents[,weekly_sold]
"""
import argparse
import csv
import hashlib
import heapq
import itertools
import json
import os
import random
import sys
import timeit

HERE = os.path.dirname(os.path.abspath(__file__))


def load_impl(name):
    """Import Inventory from original_phase2/ (before) or this folder (after)."""
    path = os.path.join(HERE, "original_phase2") if name == "original" else HERE
    sys.path.insert(0, path)
    from inventory import Inventory  # noqa: E402
    return Inventory


def synthetic_products(n, rng):
    return [(f"SKU{i:07d}", f"Item {i}", 500_000, rng.randint(99, 19_999), 0) for i in range(n)]


def csv_products(path, n):
    rows = []
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            rows.append((row["sku"], row["name"], int(row["stock"]), int(row["price_cents"]),
                         int(row.get("weekly_sold") or 0)))
            if n and len(rows) >= n:
                break
    return rows


def build(Inventory, products, rng):
    inv = Inventory()
    for sku, name, stock, cents, weekly in products:
        # Add with extra stock, then sell `weekly` units, so the final stock and
        # weekly sales both match the dataset.
        inv.add(sku, name, min(stock + weekly, 1_000_000), cents)
        if weekly:
            inv.sell(sku, weekly)
    if not any(p[4] for p in products):
        # No sales in the data: simulate a skewed week of sales (2 per product).
        skus = [p[0] for p in products]
        cum = list(itertools.accumulate(rng.paretovariate(1.2) for _ in skus))
        for sku in rng.choices(skus, cum_weights=cum, k=2 * len(skus)):
            inv.sell(sku, rng.randint(1, 3))
    return inv


def top_k(inv, k, impl):
    if impl == "optimized":
        return inv.top_k_bestsellers(k)
    # The original has no top-k operation. The best read-only way to get one
    # without the new method is heapq.nsmallest over every record (O(n log k)).
    best = heapq.nsmallest(k, (p for p in inv.records.values() if p.weekly_sold > 0),
                           key=lambda p: (-p.weekly_sold, p.sku))
    return [p.public() for p in best]


def best_per_call(fn, number, repeat=5):
    """timeit: run fn `number` times, `repeat` times; return the best µs per call."""
    return min(timeit.Timer(fn).repeat(repeat=repeat, number=number)) / number * 1e6


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--impl", choices=["original", "optimized"], required=True)
    ap.add_argument("--n", type=int, default=50_000)
    ap.add_argument("--dataset", help="CSV: sku,name,stock,price_cents[,weekly_sold]")
    args = ap.parse_args()

    Inventory = load_impl(args.impl)
    rng = random.Random(532)
    products = csv_products(args.dataset, args.n) if args.dataset else synthetic_products(args.n, rng)
    inv = build(Inventory, products, rng)
    skus = [p[0] for p in products]

    # Fixed query sets (identical for both implementations).
    q = random.Random(7)
    lookups = itertools.cycle([q.choice(skus) for _ in range(2_000)])
    lows = [q.randint(99, 19_900) for _ in range(2_000)]
    ranges = itertools.cycle([(lo, lo + 20) for lo in lows])
    reprice_skus = itertools.cycle([q.choice(skus) for _ in range(2_000)])

    def reprice():
        # Every call must be a REAL change (an unchanged price skips the tree
        # work), so toggle between two adjacent prices: always a remove+insert.
        s = next(reprice_skus)
        cur = inv.records[s].price_cents
        inv.change_price(s, cur + 1 if cur % 2 == 0 else cur - 1)
    sales = itertools.cycle([q.choice(skus) for _ in range(2_000)])

    # 1) Fingerprint answers BEFORE timing (read-only queries only).
    answers = [
        [tuple(p["sku"] for p in inv.price_range(lo, lo + 20)) for lo in lows[:300]],
        [inv.get(s)["stock"] for s in skus[:300]],
        (inv.bestseller() or {}).get("sku"),
        [(p["sku"], p["weekly_sold"]) for p in top_k(inv, 20, args.impl)],
    ]
    fingerprint = hashlib.sha256(repr(answers).encode()).hexdigest()[:16]

    # 2) timeit each operation (read-only ones first, then the ones that change state).
    results = {
        "get": best_per_call(lambda: inv.get(next(lookups)), 20_000),
        "bestseller": best_per_call(inv.bestseller, 20_000),
        "price_range": best_per_call(lambda: inv.price_range(*next(ranges)), 2_000),
        "top_k(10)": best_per_call(lambda: top_k(inv, 10, args.impl), 200 if args.impl == "original" else 5_000),
        "sell": best_per_call(lambda: inv.sell(next(sales), 1), 20_000),
        "change_price": best_per_call(reprice, 5_000),
    }
    print(json.dumps({"impl": args.impl, "n": len(products), "us_per_call": results,
                      "answers": fingerprint}))


if __name__ == "__main__":
    main()

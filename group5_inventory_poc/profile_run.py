"""Phase 3 profiling harness for the Group 5 inventory system.

Builds a large, realistic, deterministic workload, runs it, and prints wall
time per operation type plus a checksum of every result. The checksum must not
change between optimization steps: same answers, less time.

Run from this folder:
    python3 profile_run.py                # timing + checksum
    python3 profile_run.py --profile      # also cProfile sorted by tottime
    python3 profile_run.py --scale 0.2    # quick smaller run
"""

from __future__ import annotations

import argparse
import cProfile
import hashlib
import io
import itertools
import os
import pstats
import random
import time
from collections import defaultdict

from inventory import Inventory


def build_workload(scale: float = 1.0, seed: int = 532):
    """Pre-generate products and an interleaved operation stream (never timed)."""
    rng = random.Random(seed)
    n_products = int(50_000 * scale)
    n_ops = int(500_000 * scale)

    products = []
    for i in range(n_products):
        cents = rng.randint(99, 19_999)                  # $0.99 - $199.99
        products.append((f"SKU{i:06d}", f"Item {i}", 200_000, cents))

    # Retail popularity is heavily skewed: a few SKUs sell far more than most.
    weights = [rng.paretovariate(1.2) for _ in range(n_products)]
    cum = list(itertools.accumulate(weights))
    skus = [p[0] for p in products]

    def popular():
        return rng.choices(skus, cum_weights=cum)[0]

    ops = []
    next_new = n_products
    live_extra = []
    for _ in range(n_ops):
        r = rng.random()
        if r < 0.50:
            ops.append(("sell", popular(), rng.randint(1, 3)))
        elif r < 0.70:
            ops.append(("get", rng.choice(skus)))
        elif r < 0.80:
            ops.append(("bestseller",))
        elif r < 0.85:
            low = rng.randint(99, 19_900)
            ops.append(("price_range", low, low + rng.randint(5, 40)))   # ~5-40 matches
        elif r < 0.90:
            ops.append(("change_price", rng.choice(skus), rng.randint(99, 19_999)))
        elif r < 0.95:
            ops.append(("restock", rng.choice(skus), rng.randint(1, 50)))
        else:
            # Catalog churn: add a new SKU, or delete one added earlier.
            if live_extra and rng.random() < 0.5:
                ops.append(("delete", live_extra.pop(rng.randrange(len(live_extra)))))
            else:
                sku = f"SKU{next_new:06d}"
                next_new += 1
                live_extra.append(sku)
                ops.append(("add", sku, "New item", 1_000, rng.randint(99, 19_999)))
    return products, ops


def run(products, ops):
    inv = Inventory()
    for p in products:
        inv.add(*p)

    out = []
    times = defaultdict(float)
    counts = defaultdict(int)
    clock = time.perf_counter
    for op in ops:
        name = op[0]
        t0 = clock()
        if name == "sell":
            res = inv.sell(op[1], op[2])["stock"]
        elif name == "get":
            res = inv.get(op[1])["stock"]
        elif name == "bestseller":
            b = inv.bestseller()
            res = (b["sku"], b["weekly_sold"]) if b else None
        elif name == "price_range":
            res = tuple(p["sku"] for p in inv.price_range(op[1], op[2]))
        elif name == "change_price":
            res = inv.change_price(op[1], op[2])["price_cents"]
        elif name == "restock":
            res = inv.restock(op[1], op[2])["stock"]
        elif name == "add":
            res = inv.add(op[1], op[2], op[3], op[4])["sku"]
        else:
            res = inv.delete(op[1])["sku"]
        times[name] += clock() - t0
        counts[name] += 1
        out.append(res)

    checksum = hashlib.sha256(repr(out).encode()).hexdigest()[:16]
    return inv, dict(times), dict(counts), checksum


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", action="store_true")
    ap.add_argument("--scale", type=float, default=1.0)
    ap.add_argument("--top", type=int, default=15)
    args = ap.parse_args()

    products, ops = build_workload(args.scale)
    print(f"workload: {len(products):,} products, {len(ops):,} mixed operations")

    prof = cProfile.Profile() if args.profile else None
    t0 = time.perf_counter()
    if prof:
        prof.enable()
    inv, times, counts, checksum = run(products, ops)
    if prof:
        prof.disable()
    wall = time.perf_counter() - t0

    for name in sorted(times, key=times.get, reverse=True):
        print(f"  {name:<13} {counts[name]:>8,} ops  {times[name]:7.3f} s  "
              f"{times[name] / counts[name] * 1e6:8.2f} µs/op")
    print(f"  {'TOTAL (wall, incl. initial load)':<36} {wall:7.3f} s")
    print(f"checksum: {checksum}")

    if prof:
        buf = io.StringIO()
        pstats.Stats(prof, stream=buf).sort_stats("tottime").print_stats(args.top)
        print(buf.getvalue().replace(os.path.dirname(os.path.abspath(__file__)) + os.sep, ""))


if __name__ == "__main__":
    main()

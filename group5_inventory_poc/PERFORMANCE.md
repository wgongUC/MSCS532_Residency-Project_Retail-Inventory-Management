# Phase 3: Profiling, Optimization, and the Curveball (Group 5 Inventory)

Process followed in class: **baseline first → profile (cProfile, sorted by tottime) → name the bottleneck → change one thing → re-measure → repeat until fast enough.** Every step is a separate git commit and tag (`baseline`, `fix1`, `fix2`, `fix3`, `topk`). Every step keeps all tests green and produces the **same checksum** over all 500,000 results.

## Workload (`profile_run.py`)

The workload is a realistic, deterministic store (fixed seed 532):

- **50,000 SKUs** priced from $0.99 to $199.99.
- **500,000 mixed operations**, interleaved: 50% sales (Pareto-skewed popularity, so a few SKUs sell most), 20% SKU lookups, 10% bestseller checks, 5% price-range queries (about 60 matches each), 5% price changes, 5% restocks, and 5% catalog churn (adds and deletes).
- Data generation is never timed. The checksum is the SHA-256 of every result, and it stays **`a46b80a767e7787e`** at every step.

```bash
python3 profile_run.py             # timing per operation + checksum
python3 profile_run.py --profile   # plus cProfile sorted by tottime
```

The full profiler output for each step is in `perf_results/` (`0_baseline.txt` through `3_cached_week_rollover.txt`).

## Results

Times are wall clock on the same machine, with two runs per step. Expect about ±5% noise; the trends are stable.

| Step | Change | Total (s) | price_range µs/op | change_price µs/op | sell µs/op | get µs/op |
|---|---|---|---|---|---|---|
| 0 baseline | none (inherited code) | **6.16 – 6.28** | 106 – 112 | 25.7 | 4.4 – 4.5 | 2.2 – 2.3 |
| 1 | Iterative AVL traversal | 5.13 – 5.14 | **73** | 25.7 | 4.4 | 2.2 |
| 2 | Inline AVL height bookkeeping | 5.13 – 5.20 | 73 | **19.7 – 20.7** | 4.4 | 2.2 |
| 3 | Cache next week-rollover instant | **4.42 – 4.88** | 73 | 20 | **3.3 – 3.5** | **1.25 – 1.33** |

Overall the workload is about **25% faster**. Range queries are about **31% faster**, and lookups about **42% faster**.

## The bottlenecks, named

### Suspect 1: the AVL range query (fixed in step 1)
- **Evidence:** in the baseline profile, `avl_tree.py:114(walk)` had the largest tottime (6.7 s of 22.8 s under the profiler), with **25.2 million calls for 24,820 queries**.
- **Cause:** `between()` and `sorted_keys()` were recursive generators chained with `yield from`. Every yielded key travels back up through **every ancestor generator frame** (about 17 at this size), and a generator object is created even for empty children. The README claims O(log n + k), but the real cost was **O(k · log n)**.
- **Fix:** one iterative in-order walk with an explicit stack and the same pruning. It has the same visit order and output; a check against the inherited traversal on 300 random trees × 20 ranges matched exactly.

### Suspect 2: AVL rebalancing overhead (fixed in step 2)
- **Evidence:** `_refresh`, `_balance` and `_height` together made about 12 million calls, mostly from `change_price` (a remove plus an insert) and `add`.
- **Cause:** every node on every insert or remove path made about 6 function calls just to recompute heights.
- **Fix:** read each child height once, inline, and return immediately when the node is balanced. Rotations are unchanged, and the trees are **identical** (checked on 200 random insert/remove sequences).
- **Lesson:** `change_price` improved by 22%, but the total barely moved because those operations are a small share of the workload. cProfile also exaggerates code with many tiny function calls, so always confirm on the wall clock.

### Suspect 3: the weekly-rollover check on every call (fixed in step 3)
- **Evidence:** `_maybe_roll_week` was called 550,000 times, one for every public operation, at 1.8 s cumulative under the profiler.
- **Cause:** each call built `datetime.now(ZoneInfo)`, converted it to the store time zone and computed a Monday.
- **Fix:** compute once the exact epoch instant the next week starts (store-local Monday 00:00), recompute it whenever `week_start` changes, and compare with `time.time()`. An explicit `now` (as in tests) and the boundary itself still take the original path. The rollover was tested at the boundary, including a week start that isn't a Monday.

### Why we stopped
What remains is mostly the required `public()` safe copies (part of the API contract) and heap repairs that are already O(log n). Further gains would mean changing the API or design, so the remaining time went to the curveball.

## Curveball: `top_k_bestsellers(k)`

**Requirement:** return the k top weekly sellers in order, with ties broken by SKU ascending, without mutating state. *"Your heap serves #1 in O(1). How do you serve #2 through #k without destroying it?"*

**Answer:** walk the existing indexed heap **best-first** without changing it (`max_heap.py: top_k`).

1. Every child ranks below its parent, so the next-best product is always a child of a product already reported.
2. Keep a small separate min-heap (the *frontier*) of candidate positions, keyed by `(-weekly_sold, sku)`, which is exactly the heap's own order.
3. Start with the root. Pop the best candidate, report it, push its two children. Repeat k times.
4. The frontier grows by at most one per step, so the total is **O(k log k), independent of n**. `heap.items` and every `heap_index` are never written to.

**Behavior rules:**
- Only products with sales > 0 are listed, matching `bestseller()` returning `None` when nothing has sold.
- `k = 0` returns `[]`. If fewer than k products have sold, all of them are returned.
- An invalid k (negative, float, bool or string) raises `ValueError`.
- The results are safe copies.
- The usual lazy week check runs first, exactly as in `bestseller()`.

**Tests (`test_top_k.py`, 11 tests):** ordering and SKU ties, k = 0, k larger than the number of sellers, unsold products excluded, invalid k, `top_k(1)` equal to `bestseller()`, results returned as copies, delete and reset, week rollover, **heap byte-for-byte unchanged after queries**, and a **3,000-step randomized comparison against brute force**. All 9 inherited tests still pass, for 20 in total.

**Benchmark (`bench_top_k.py`): many queries, small k (1–20), large n.** All methods return identical results, and the heap is unchanged afterwards.

| n | sort everything | heapq.nsmallest | copy heap + pop | **frontier walk (ours)** | speedup |
|---|---|---|---|---|---|
| 10,000 | 3,241 µs | 1,382 µs | 1,667 µs | **6.7 µs** | 208× |
| 50,000 | 17,341 µs | 5,173 µs | 13,728 µs | **7.0 µs** | 734× |
| 200,000 | 83,771 µs | 23,712 µs | 153,951 µs | **7.4 µs** | 3,214× |

The frontier walk stays flat as n grows, while every alternative grows with n.

## 7–8 minute presentation outline

1. **(30 s) System:** a hash table for SKUs, an indexed max-heap for weekly sales, and an AVL tree keyed by (price, SKU).
2. **(1.5 min) Baseline:** run `python3 profile_run.py --profile`. Point at the total, then at the top tottime row: `walk`, with 25 million calls for 25 thousand queries.
3. **(1.5 min) Fix 1 explained:** nested `yield from` means each result bubbles through about 17 generator frames, so the claimed O(log n + k) was really O(k log n). Rerun and show the same checksum with range queries 31% faster.
4. **(1 min) Fixes 2 and 3:** one change at a time. Fix 2 is a good honest lesson: it looked large in the profiler but was small on the wall clock. Fix 3 removed the clock work done on every call, making lookups 42% faster.
5. **(2 min) Curveball:** draw the heap as a tree, show the frontier walk, then run `python3 bench_top_k.py`: about 7 µs flat against milliseconds, up to 3,214× faster.
6. **(30 s) Correctness:** `python3 -m unittest -v` gives 20 passing tests, including the heap-unchanged and brute-force checks.
7. **(30 s) When to stop:** the remaining cost is the required safe copies and O(log n) heap repairs.

To show any step live: `git checkout baseline` (or `fix1`, `fix2`, `fix3`, `topk`), run the harness, then `git checkout main`.

# Group 5 — Dynamic Inventory Management: Phase 2 PoC

Implements the inherited Phase 1 design: a **Python dictionary** (hash table) for SKU lookup, a **custom indexed binary max-heap** for weekly bestsellers, and a **custom AVL tree** keyed by `(price_cents, SKU)` for price queries. Products are shared Python objects; indexes reference SKUs or objects and are not three independent copies of inventory.

## Run it (Python 3.10+ recommended)

1. Unzip the archive and open Terminal.
2. Move into the unzipped folder:

   ```bash
   cd ~/Downloads/group5_inventory_poc
   ```

   Adjust this path if your extracted directory is elsewhere. To avoid path mistakes, type `cd `, drag the extracted folder from Finder into Terminal, then press Return.

3. Run the walkthrough:

   ```bash
   python3 demo.py
   ```

4. Run all tests:

   ```bash
   python3 -m unittest -v
   ```

   **Phase 3:** `python3 profile_run.py --profile` (cProfile), `python3 compare.py` (timeit before vs after at 3 sizes), `python3 bench_top_k.py` (top-k benchmark). See `PERFORMANCE.md`.

5. Try your own example in the interactive Python interpreter:

   ```bash
   python3
   ```

   ```python
   from inventory import Inventory
   shop = Inventory()
   shop.add('SKU-1', 'Coffee', 25, 599)
   shop.add('SKU-2', 'Tea', 30, 399)
   shop.sell('SKU-2', 5)
   shop.bestseller()           # Tea
   shop.price_range(300, 600) # Tea then Coffee
   shop.change_price('SKU-1', 299)
   shop.sorted_by_price()     # Coffee then Tea
   shop.validate()            # assert indexes stay consistent
   quit()
   ```

No external libraries or installation needed. If `python3` is missing, install Python 3.10+ first.

## What each file does

| File | Purpose |
|---|---|
| `product.py` | Shared Product record with public-copy output |
| `inventory.py` | Inventory API and cross-index coordination |
| `max_heap.py` | Custom indexed max-heap, SKU ascending on sales ties |
| `avl_tree.py` | Custom balanced BST with rotations and range pruning |
| `demo.py` | 15 labeled steps with before/after effects (13–14 show top-k) |
| `test_inventory.py` | 9 unit tests, including 1,500 randomized operations with invariant checks |
| `test_top_k.py` | Phase 3: 11 tests for `top_k_bestsellers(k)`, including brute-force and heap-unchanged checks |
| `profile_run.py` | Phase 3: profiling harness (50k SKUs, 500k mixed operations, checksum) |
| `bench_top_k.py` | Phase 3: top-k benchmark against sort, nsmallest and copy-and-pop |
| `compare.py` | Phase 3: timeit before/after (original vs optimized) at 10k/50k/200k, checks identical answers; `--dataset file.csv` |
| `function_times.py` | Phase 3: per-operation and per-function times, before vs after (cProfile) |
| `timeit_bench.py` | Phase 3: timeit per-operation benchmark used by compare.py |
| `original_phase2/` | Phase 3: frozen copy of the inherited code, used as the "before" in compare.py |
| `Optimization_Notes.docx` | Phase 3: 1–2 page optimization notes with AI Usage Appendix |
| `PROGRESS_LOG.txt` | Phase 3: simple step-by-step log |
| `PERFORMANCE.md` | Phase 3: baseline, the three fixes, curveball, results and talk outline |
| `IMPLEMENTATION_NOTES.md` | Phase 3 handoff and AI appendix |
| `WALKTHROUGH.md` | Study guide and instructor-style questions |

## Key API and complexities

| Operation | Method | Intended complexity |
|---|---|---|
| Lookup | `get(sku)` | expected O(1) |
| Create/delete | `add(...)`, `delete(sku)` | expected O(log n) (hash avg + heap + AVL) |
| Sale | `sell(sku, units)` | expected O(log n) (heap repair) |
| Update price | `change_price(sku, cents)` | expected O(log n) (AVL removal + insertion) |
| Restock/rename | `restock(...)`, `rename(...)` | expected O(1) |
| Get bestseller | `bestseller()` | O(1) once week rollover check is complete |
| Top k bestsellers (Phase 3) | `top_k_bestsellers(k)` | O(k log k), read-only walk of the heap |
| Price-range query | `price_range(low, high)` | O(log n + k) |
| Full sorted listing | `sorted_by_price()` | O(n) |
| Reset weekly counts | `reset_week()` | O(n) bottom-up heapify |

**Important:** `bestseller()` and other public operations first check whether a new store-local week has begun. The first request after the weekly boundary may take O(n) to reset sales. Under normal same-week operation, bestseller lookup is O(1). Rare Python dictionary resizes and collisions can increase individual operations beyond their average cost.

## Inherited design rules

- SKU is a nonempty, case-sensitive string; immutable once created.
- Names cannot be blank; product count and on-hand stock capped at 1,000,000 each.
- Prices are nonnegative integer cents; receipts and sale units are positive integers.
- No overselling. On-hand stock may reach zero. Weekly sold may exceed 1 million across restocks.
- Bestseller tie: SKU ascending. When no sales occurred in the current week, winner is `None`.
- Price listing tie: `(price_cents, SKU)` ascending. Range bounds are inclusive.
- Public getters return copies; callers cannot mutate internal objects.

## Scope and implementation decisions

The Phase 1 brief did **not** specify the weekly reset trigger. This PoC uses **lazy rollover on the first request after Monday midnight** plus a manual `reset_week()` function. It is single-process and in-memory, with no persistence, threading, payments, or sales history. Validation occurs before ordinary mutations; **rollback on arbitrary internal failures is not implemented**. These are important choices to confirm with Group 5 and to tell Phase 3.

Run `python3 demo.py` first, then `python3 -m unittest -v`, then examine `inventory.py` for orchestration, `max_heap.py` for index maintenance, and `avl_tree.py` for rotations.

### Future Enhancement: Persistent Data Storage

The current Phase 2 implementation stores inventory data in memory. Data is lost when the application terminates.

For future development, we propose using **SQLite** to provide persistent storage.

1. **Save:** Store SKU, name, stock, price, weekly sales, and week-start date in the database.
2. **Load:** On application startup, load product records into the hash table and reconstruct the max-heap and AVL tree.
3. **Update:** Persist inventory changes, including additions, sales, restocking, price changes, and deletions.
4. **Consistency:** Use database transactions to maintain reliable updates.

The `heap_index` and AVL tree structure do not need to be stored because both can be reconstructed from the product records.

**Implementation status:** Proposed future enhancement; not implemented in Phase 2.

Team Mate: Phase 2 Group 5
Charles Ssekitto, Muhtadin Mushfiq, Rachana Peddi, Sanya Kamra,

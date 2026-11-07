# Phase 2 implementation notes — Group 5 design handoff

**Course:** MSCS-532 — Algorithms and Data Structures  
**Artifact:** Dynamic Inventory Management System for Retail (inherited Group 5 Phase 1 brief)  
**Date:** November 7, 2026  
**Status:** Working proof of concept; review and customize with the Phase 2 group before submission.

## Built

A Python `Inventory` facade coordinates (1) a built-in dictionary keyed by case-sensitive SKU, (2) a custom indexed binary max-heap keyed by `(weekly sales descending, SKU ascending)`, and (3) a custom AVL price tree keyed by `(price_cents, SKU)`. The dictionary and heap share `Product` object references; AVL nodes index the price/SKU key and reference the dictionary indirectly. Heap swaps update product heap positions. Supported operations: add, fetch, rename, restock, record sale, change price, price range, price-ordered listing, bestseller, delete, and weekly reset. Validation rejects duplicate or unknown SKUs, invalid prices and names, zero/negative receipts or sales, excess stock and capacity, and overselling. Public calls return copies of record data. `Inventory.validate()` tests index consistency, heap ordering and AVL balance.

## Tests and reproduction

Requires Python 3.10+ with the standard library; no packages. Run `python3 demo.py` for 13 labeled steps, then `python3 -m unittest -v`. The tests check lookups and snapshot copying, inclusive price queries, price ties, sales and bestseller ties, deletion of heap root and arbitrary SKUs, restock and reset, invalid operations that leave state unchanged, capacity and case sensitivity, a simulated new-week rollover, and 1,500 deterministic randomized operations with structural invariants. **Record actual test outcomes from your environment before submission.**

## Design decisions, limitations, and deferred work

The Phase 1 brief specifies a Monday store-local week reset without an invocation mechanism. This version chooses lazy rollover on the first subsequent API request, and provides manual `reset_week()` for demos. That first request may be O(n), even for `bestseller()`. Store time zone defaults to America/Detroit but is configurable. A normal same-week bestseller lookup is O(1), hash lookup expected O(1), and changes involving tree/heap expected O(log n). Missing: persistence, audit/sales history, payment logic, external API/UI, concurrency synchronization, crash safety, and transaction rollback for arbitrary internal exceptions. These exclusions are deliberate, **not** features of the PoC. The AVL tree uses Python recursion and custom rotations; expected AVL height remains logarithmic. Multi-structure changes rely on advance validation and assume normal in-process operations succeed. The group's author-consultation answers may require revising the reset or failure policy.

## AI Usage Appendix

**Significant prompt:** “Implement Group 5's inherited retail inventory Phase 1 design in Python, using a SKU hash table, indexed max-heap, and price AVL tree. Supply a working demonstration, tests, modular code, and concise implementation handoff.”

**Where AI output required correction:** An initial test scenario attempted to sell 1,100 units from an item with only 1,012 units on hand (1,000 initially plus 12 restocked). That violated the design's explicit no-overselling invariant and caused a test failure. The test was corrected to sell 1,000 units and leave 12 in stock, then the suite was rerun. The weekly reset and exceptional-failure consistency mechanisms also needed explicit human design review because the inherited brief did not prescribe them. The implementation chooses lazy weekly reset and documents the absence of general rollback rather than pretending these details were provided by the authoring group.

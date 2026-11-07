# Hands-on walkthrough — feel how Group 5's idea works

## Start here: run `python3 demo.py`

Watch the numbered headings. At each heading ask: **Which index changed and why?**

1. **Add products.** One `Product` object is entered into the `records` dictionary, the heap, and the AVL price index.
2. **Look up Eggs by SKU.** The dictionary returns its product record without walking the tree.
3. **Display sorted by price.** The AVL's *in-order traversal* yields products in ascending `(price, SKU)` order.
4. **Record sales.** Selling Bread increases its `weekly_sold` and moves it toward the top of the indexed max-heap. The tree is untouched.
5. **Inspect the heap array.** Heap order means every parent outranks its children, **not** that the entire array is sorted.
6. **Query the $3–$6 range.** The AVL prunes subtrees outside the requested bounds.
7. **Change Milk's price.** The old `(price, SKU)` AVL key is removed and a new key is inserted; heap and stock do not change.
8. **Restock Eggs.** Only the shared product's stock field changes.
9. **Delete Bread.** Its record leaves all three structures; the old runner-up becomes bestseller.
10. **Attempt overselling.** Validation rejects the request before altering stock or sales.
11. **Run `validate()`.** Confirm heap positions, parent priority, AVL heights/balance, and matching SKUs/price keys across all structures.
12. **Reset the week.** All weekly sales counters become zero and the heap is rebuilt in O(n).

## Instructor-style questions you should be able to answer

**Q: Why hash table + heap + AVL?** Each supports a different access pattern: exact SKU lookup, largest weekly-sales score, and ordered price queries. The tradeoff is additional memory and coordinated updates.

**Q: Why AVL instead of a plain BST?** A plain BST can become a chain with O(n) operations for unfortunate insertion order. AVL maintains a height balance via rotations and ensures O(log n) update/search cost.

**Q: Why store `heap_index` in Product?** Without it, removing or updating an arbitrary SKU would require an O(n) scan of the heap array to locate its position. Saved positions allow O(log n) repairs.

**Q: What happens when a customer buys 2 units?** Hash-find the SKU → reject if stock < 2 → decrease stock by 2 → increase weekly sales by 2 → bubble the product up in the heap if needed. AVL does not change.

**Q: What if a bestseller gets deleted?** Remove it from AVL, swap with the last heap element and pop it, repair heap order, then remove the hash entry. The next-highest weekly seller reaches the root.

**Q: Why does the AVL use `(price, SKU)`?** Two products can share a price. SKU provides an unambiguous sortable key and deterministic ordering.

**Q: Is this transactional/production safe?** No. It validates ordinary user input before changing data, but has no durability, rollback for unexpected internal failures, or concurrency control. Those are explicit limits of the PoC.

**Q: What is `O(log n + k)`?** Searching the AVL for the first relevant price costs O(log n); returning k matches costs O(k).

## Experiments to try

- In `demo.py`, change the sales quantities so Eggs outranks Bread. Run again and watch the heap root change.
- Make Milk and Bread have the exact same price; verify the AVL uses SKU ascending for ties.
- Delete a product that is *not* the bestseller, then run `inv.validate()`.
- Call `inv.sell('103', 100000)` to see the oversell rejection.
- Add a product with 0 units; check that a sale fails but lookup succeeds.
- Run `python3 -m unittest -v` and read each test name as a behavior contract.

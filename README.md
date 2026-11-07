# Dynamic Inventory Management System for Retail

MSCS 532: Algorithms and Data Structures

Residency Project

## Overview
A proposed Python inventory system for retail supporting product CRUD, stock receipts and sales, price changes, price-range searches, products ordered by price, and a weekly bestseller. The design assumes a mixed read/write workload. Reads include SKU lookups, price browsing, and bestseller checks while writes include stock receipts, sales, and product changes.

## Design
- **Hash table (SKU):** expected O(1) product lookup and basic updates.
- **Indexed max-heap (weekly sales):** O(1) bestseller lookup and O(log n) heap repairs.
- **AVL tree (price, SKU):** O(log n + k) price-range search and O(n) ordered listing (n products, k matches).
- **Limits:** up to 1,000,000 products and 0-1,000,000 stock units per product; prices use integer cents.
- **Out of scope:** persistence between runs, payments, and sales history.

## Phase 1 Handoff
[Design brief](Dynamic_Inventory_Phase_1_Design_Brief.docx): scope, validation rules, data-structure tradeoffs, complexity analysis, references, and AI usage appendix.

Phase 1 is design-only. No application, tests, or benchmarks have been implemented. The next phase is implementation and validation against the brief.

## Phase 1 Team
Kamlesh Kumar, Muhtadin Mushfiq, Pawan Sharma, and Weevern Gong.
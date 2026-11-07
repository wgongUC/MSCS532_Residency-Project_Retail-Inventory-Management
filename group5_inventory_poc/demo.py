"""Run with: python3 demo.py"""
from pprint import pprint
from inventory import Inventory


def show(title, value):
    print('\n' + '=' * 65)
    print(title)
    print('=' * 65)
    pprint(value, sort_dicts=False)


def main():
    inv = Inventory()
    print('GROUP 5 INVENTORY PROOF OF CONCEPT')
    print('Price is stored in integer cents; $4.00 = 400.')

    for sku, name, stock, cents in [
        ('101', 'Milk', 300, 400),
        ('102', 'Bread', 350, 300),
        ('103', 'Eggs', 250, 600),
        ('104', 'Rice', 300, 1000),
    ]:
        inv.add(sku, name, stock, cents)
    show('1. ADD: 4 products; hash table keys', list(inv.records))
    show('2. GET SKU 103 (hash lookup)', inv.get('103'))
    show('3. SORTED BY PRICE (AVL in-order)', inv.sorted_by_price())

    inv.sell('101', 120)
    inv.sell('102', 200)
    inv.sell('103', 75)
    inv.sell('104', 150)
    show('4. BESTSELLER (max-heap root): Bread', inv.bestseller())
    show('5. HEAP INTERNAL ORDER (not price sorted)',
         [(p.sku, p.weekly_sold, p.heap_index) for p in inv.heap.items])
    show('6. PRICE RANGE $3.00–$6.00 (AVL)', inv.price_range(300, 600))

    inv.change_price('101', 500)
    show('7. MILK PRICE CHANGE $4 -> $5 (AVL reordered)', inv.sorted_by_price())
    inv.restock('103', 50)
    show('8. RESTOCK EGGS by 50', inv.get('103'))
    inv.delete('102')
    show('9. DELETE BREAD: NEW BESTSELLER', inv.bestseller())
    show('10. RECORDS AFTER DELETION', inv.sorted_by_price())

    try:
        inv.sell('103', 10000)
    except ValueError as exc:
        show('11. OVERSALE REJECTED; NO STATE CHANGE', str(exc))
    inv.validate()
    print('\n12. INTEGRITY CHECK: PASS (hash = heap = AVL)')
    show('13. PHASE 3 CURVEBALL: top_k_bestsellers(3), read-only heap walk',
         [(p['sku'], p['name'], p['weekly_sold']) for p in inv.top_k_bestsellers(3)])
    show('14. HEAP ARRAY UNCHANGED BY THE TOP-K QUERY',
         [(p.sku, p.weekly_sold, p.heap_index) for p in inv.heap.items])
    inv.reset_week()
    show('15. WEEKLY RESET: NO BESTSELLER UNTIL NEXT SALE', inv.bestseller())
    inv.validate()
    print('\nALL DEMONSTRATION STEPS COMPLETED.')


if __name__ == '__main__':
    main()

"""Product record shared across the three inventory indexes."""
from dataclasses import dataclass


@dataclass(slots=True)
class Product:
    sku: str
    name: str
    stock: int
    price_cents: int
    weekly_sold: int = 0
    heap_index: int = -1

    def public(self) -> dict:
        """Return a safe copy (never expose mutable internal records)."""
        return dict(sku=self.sku, name=self.name, stock=self.stock,
                    price_cents=self.price_cents, weekly_sold=self.weekly_sold)

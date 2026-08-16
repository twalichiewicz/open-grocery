from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any


@dataclass
class Product:
    """
    Canonical representation of a retail product.

    The canonical product model is intentionally retailer-neutral while
    retaining retailer-specific identifiers and raw source data.
    """

    product_id: str
    retailer: str
    product_name: str

    upc_gtin: str | None = None
    sku: str | None = None

    brand: str | None = None
    category: str | None = None

    package_quantity: Decimal | None = None
    package_unit: str | None = None

    retailer_product_id: str | None = None

    source_name: str | None = None
    source_url: str | None = None

    raw_data: dict[str, Any] | None = None

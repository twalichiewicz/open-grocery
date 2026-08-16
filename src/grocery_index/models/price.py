from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any


@dataclass
class Price:
    """
    Canonical representation of a product price observation.
    """

    retailer: str
    product_id: str

    regular_price: Decimal | None = None
    sale_price: Decimal | None = None
    unit_price: Decimal | None = None

    currency: str = "USD"

    store_id: str | None = None

    loyalty_price: Decimal | None = None

    observed_at: datetime | None = None

    source_name: str | None = None
    source_url: str | None = None

    raw_data: dict[str, Any] | None = None

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class Observation:
    """
    A point-in-time observation collected from a retailer source.
    """

    retailer: str
    observed_at: datetime

    product_id: str | None = None
    store_id: str | None = None

    source_name: str | None = None
    source_url: str | None = None

    data_type: str | None = None

    raw_data: dict[str, Any] | None = None

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class Store:
    """
    Canonical representation of a physical retail location.
    """

    retailer: str
    store_id: str

    address: str | None = None
    city: str | None = None
    state: str | None = None
    zip_code: str | None = None

    latitude: float | None = None
    longitude: float | None = None

    store_name: str | None = None
    phone: str | None = None

    source_name: str | None = None
    source_url: str | None = None

    raw_data: dict[str, Any] | None = None

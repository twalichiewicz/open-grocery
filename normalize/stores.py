from __future__ import annotations

from typing import Any


def normalize_store(
    store: dict[str, Any],
) -> dict[str, Any]:
    """Normalize common store fields without inventing missing data."""
    return {
        "store_id": _text(store.get("store_id")),
        "retailer": _text(store.get("retailer")),
        "name": _text(
            store.get("name")
            or store.get("store_name")
        ),
        "address": _text(store.get("address")),
        "city": _text(store.get("city")),
        "state": _text(
            store.get("state")
            or store.get("state_code")
        ),
        "postal_code": _text(
            store.get("postal_code")
            or store.get("zip")
            or store.get("zip_code")
        ),
        "country": _text(store.get("country")),
        "latitude": store.get("latitude"),
        "longitude": store.get("longitude"),
        "phone": _text(store.get("phone")),
        "url": _text(store.get("url")),
    }


def normalize_stores(
    stores: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []

    for store in stores:
        results.append(normalize_store(store))

    return results


def _text(value: Any) -> str | None:
    if value is None:
        return None

    value = str(value).strip()

    return value or None

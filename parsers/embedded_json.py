from __future__ import annotations

import json
from typing import Any


JSON_SCRIPT_IDS = {
    "__NEXT_DATA__",
    "__NUXT_DATA__",
    "__APOLLO_STATE__",
    "node-apollo-state",
}


PRODUCT_TYPENAME_PREFIXES = (
    "ItemsResponseBackedItem",
)


def parse_json_scripts(
    scripts: list[str],
) -> list[Any]:
    """Parse JSON-bearing script contents, ignoring malformed scripts."""
    results: list[Any] = []

    for script in scripts:
        try:
            results.append(json.loads(script))
        except (json.JSONDecodeError, TypeError):
            continue

    return results


def walk_json(value: Any):
    """Yield every nested JSON value."""
    yield value

    if isinstance(value, dict):
        for child in value.values():
            yield from walk_json(child)

    elif isinstance(value, list):
        for child in value:
            yield from walk_json(child)


def _first(
    value: dict[str, Any],
    keys: tuple[str, ...],
) -> Any:
    for key in keys:
        result = value.get(key)

        if result not in (None, ""):
            return result

    return None


def _extract_offer(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value

    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                return item

    return {}


def _has_price_signal(value: dict[str, Any]) -> bool:
    """
    Return whether the object contains a scalar price-like field.

    Nested Instacart price objects are intentionally not handled here;
    that is the extraction-quality pass that follows this safety/precision
    pass. The important distinction here is that a generic object named
    "title" is not sufficient evidence of being a product.
    """
    for key in (
        "price",
        "currentPrice",
        "salePrice",
        "regularPrice",
    ):
        candidate = value.get(key)

        if candidate in (None, ""):
            continue

        if isinstance(candidate, (str, int, float)):
            return True

    return False


def _has_allowed_typename(value: dict[str, Any]) -> bool:
    typename = value.get("__typename")

    if not isinstance(typename, str):
        return False

    return any(
        typename.startswith(prefix)
        for prefix in PRODUCT_TYPENAME_PREFIXES
    )


def _is_product_candidate(
    value: dict[str, Any],
    *,
    gtin: Any,
    sku: Any,
) -> bool:
    """
    Require evidence beyond a generic name/title field.

    A product candidate must have:
      - a SKU or GTIN, or
      - a price-like field, or
      - a known product-bearing __typename.
    """
    if gtin not in (None, ""):
        return True

    if sku not in (None, ""):
        return True

    if _has_price_signal(value):
        return True

    if _has_allowed_typename(value):
        return True

    return False


def product_from_dict(
    value: dict[str, Any],
    source_url: str,
) -> dict[str, Any] | None:
    """
    Convert a JSON object that looks like a product into our common record.

    A name/title alone is not sufficient evidence. Embedded application
    JSON contains navigation labels, analytics events, localization data,
    and other objects that happen to contain those fields.
    """
    product_name = _first(
        value,
        (
            "productName",
            "product_name",
            "name",
            "title",
            "displayName",
        ),
    )

    if not product_name or not isinstance(product_name, str):
        return None

    brand = _first(
        value,
        (
            "brand",
            "brandName",
            "manufacturer",
        ),
    )

    if isinstance(brand, dict):
        brand = brand.get("name")

    gtin = _first(
        value,
        (
            "gtin",
            "gtin12",
            "gtin13",
            "gtin14",
            "upc",
            "upcCode",
        ),
    )

    sku = _first(
        value,
        (
            "sku",
            "itemNumber",
            "itemId",
            "productId",
        ),
    )

    if not _is_product_candidate(
        value,
        gtin=gtin,
        sku=sku,
    ):
        return None

    offer = _extract_offer(
        _first(
            value,
            (
                "offers",
                "offer",
                "pricing",
                "priceInfo",
            ),
        )
    )

    price = _first(
        value,
        (
            "price",
            "currentPrice",
            "salePrice",
            "regularPrice",
        ),
    )

    currency = _first(
        value,
        (
            "currency",
            "priceCurrency",
            "currencyCode",
        ),
    )

    if price is None:
        price = _first(
            offer,
            (
                "price",
                "currentPrice",
                "salePrice",
                "regularPrice",
            ),
        )

    if currency is None:
        currency = _first(
            offer,
            (
                "currency",
                "priceCurrency",
                "currencyCode",
            ),
        )

    availability = _first(
        value,
        (
            "availability",
            "stockStatus",
            "inventoryStatus",
        ),
    )

    if availability is None:
        availability = _first(
            offer,
            (
                "availability",
                "stockStatus",
                "inventoryStatus",
            ),
        )

    return {
        "source_url": source_url,
        "product_name": product_name.strip(),
        "brand": brand,
        "gtin": gtin,
        "sku": sku,
        "price": price,
        "currency": currency,
        "availability": availability,
    }


def extract_embedded_products(
    scripts: list[str],
    source_url: str,
) -> list[dict[str, Any]]:
    """
    Extract product-like objects from embedded JSON.

    Deduplicates records using the strongest available product identity.
    """
    records: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    for document in parse_json_scripts(scripts):
        for value in walk_json(document):
            if not isinstance(value, dict):
                continue

            product = product_from_dict(
                value,
                source_url,
            )

            if product is None:
                continue

            gtin = str(product.get("gtin") or "").strip()
            sku = str(product.get("sku") or "").strip()
            name = str(product.get("product_name") or "").strip().lower()

            if gtin:
                identity = ("gtin", gtin)
            elif sku:
                identity = ("sku", sku)
            else:
                identity = ("name", name)

            if identity in seen:
                continue

            seen.add(identity)
            records.append(product)

    return records

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


PRODUCT_NAME_KEYS = (
    "productName",
    "product_name",
    "itemName",
    "item_name",
    "name",
    "title",
    "productTitle",
    "product_title",
    "displayName",
    "display_name",
)


BRAND_KEYS = (
    "brand",
    "brandName",
    "brand_name",
    "manufacturer",
    "manufacturerName",
)


GTIN_KEYS = (
    "gtin",
    "gtin12",
    "gtin13",
    "gtin14",
    "gtin8",
    "upc",
    "upcCode",
    "upc_code",
)


SKU_KEYS = (
    "sku",
    "itemNumber",
    "item_number",
    "itemId",
    "item_id",
    "productId",
    "product_id",
    "retailerItemId",
    "retailer_item_id",
)


PRICE_KEYS = (
    "price",
    "priceString",
    "price_string",
    "priceValue",
    "price_value",
    "currentPrice",
    "current_price",
    "salePrice",
    "sale_price",
    "regularPrice",
    "regular_price",
)


CURRENCY_KEYS = (
    "currency",
    "priceCurrency",
    "currencyCode",
    "currency_code",
)


AVAILABILITY_KEYS = (
    "availability",
    "stockStatus",
    "stock_status",
    "inventoryStatus",
    "inventory_status",
)


PRODUCT_SIGNAL_KEYS = (
    "sku",
    "itemNumber",
    "item_number",
    "itemId",
    "item_id",
    "productId",
    "product_id",
    "retailerItemId",
    "retailer_item_id",
    "gtin",
    "gtin12",
    "gtin13",
    "gtin14",
    "gtin8",
    "upc",
    "upcCode",
    "upc_code",
    "price",
    "priceString",
    "price_string",
    "priceValue",
    "price_value",
    "currentPrice",
    "current_price",
    "salePrice",
    "sale_price",
    "regularPrice",
    "regular_price",
)


STRUCTURAL_PRODUCT_KEYS = (
    "brand",
    "brandName",
    "brand_name",
    "manufacturer",
    "manufacturerName",
    "description",
    "productDescription",
    "product_description",
    "image",
    "imageUrl",
    "image_url",
    "productUrl",
    "product_url",
    "url",
    "offers",
    "offer",
    "pricing",
    "priceInfo",
    "price_info",
    "inventory",
    "inventoryStatus",
    "inventory_status",
    "stockStatus",
    "stock_status",
    "availability",
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


def _scalar(
    value: Any,
) -> bool:
    return isinstance(
        value,
        (
            str,
            int,
            float,
        ),
    )


def _nonempty(
    value: Any,
) -> bool:
    return value not in (
        None,
        "",
        [],
        {},
    )


def _extract_brand(
    value: Any,
) -> Any:
    if isinstance(value, dict):
        return _first(
            value,
            (
                "name",
                "brandName",
                "brand_name",
            ),
        )

    return value


def _extract_nested_instacart_price(
    value: dict[str, Any],
) -> tuple[Any, Any]:
    """
    Extract the scalar price/currency from an Instacart item object.
    """
    price_object = value.get("price")

    if not isinstance(price_object, dict):
        return (
            price_object,
            value.get("currency"),
        )

    view_section = price_object.get(
        "viewSection"
    )

    if not isinstance(
        view_section,
        dict,
    ):
        return (
            None,
            None,
        )

    item_card = view_section.get(
        "itemCard"
    )

    if isinstance(
        item_card,
        dict,
    ):
        price_string = item_card.get(
            "priceString"
        )

        if _scalar(price_string):
            return (
                price_string,
                item_card.get(
                    "currency"
                ),
            )

        full_price_string = item_card.get(
            "fullPriceString"
        )

        if _scalar(full_price_string):
            return (
                full_price_string,
                item_card.get(
                    "currency"
                ),
            )

    badge = view_section.get(
        "badge"
    )

    if isinstance(
        badge,
        dict,
    ):
        tracking_properties = badge.get(
            "trackingProperties"
        )

        if isinstance(
            tracking_properties,
            dict,
        ):
            price = tracking_properties.get(
                "price"
            )

            if _scalar(price):
                return (
                    price,
                    tracking_properties.get(
                        "currency"
                    ),
                )

    return (
        None,
        None,
    )


def _extract_offer(
    value: Any,
) -> dict[str, Any]:
    if isinstance(
        value,
        dict,
    ):
        return value

    if isinstance(
        value,
        list,
    ):
        for item in value:
            if isinstance(
                item,
                dict,
            ):
                return item

    return {}


def _has_scalar_price_signal(
    value: dict[str, Any],
) -> bool:
    for key in PRICE_KEYS:
        candidate = value.get(key)

        if _scalar(candidate):
            return True

    return False


def _has_nested_price_signal(
    value: dict[str, Any],
) -> bool:
    if not isinstance(
        value.get("price"),
        dict,
    ):
        return False

    nested_price, _ = (
        _extract_nested_instacart_price(
            value
        )
    )

    return _scalar(nested_price)


def _has_product_signal(
    value: dict[str, Any],
) -> bool:
    """
    Return whether the object contains an independent product signal.

    A name/title by itself is deliberately insufficient.
    """
    for key in PRODUCT_SIGNAL_KEYS:
        candidate = value.get(key)

        if _nonempty(candidate):
            return True

    if _has_nested_price_signal(value):
        return True

    return False


def _structural_product_signal_count(
    value: dict[str, Any],
) -> int:
    return sum(
        1
        for key in STRUCTURAL_PRODUCT_KEYS
        if _nonempty(value.get(key))
    )


def _has_allowed_typename(
    value: dict[str, Any],
) -> bool:
    typename = value.get(
        "__typename"
    )

    if not isinstance(
        typename,
        str,
    ):
        return False

    return any(
        typename.startswith(prefix)
        for prefix in PRODUCT_TYPENAME_PREFIXES
    )


def _looks_like_navigation(
    value: dict[str, Any],
    product_name: str,
) -> bool:
    """
    Reject common navigation/content objects that happen to contain
    product-ish fields.
    """
    normalized = product_name.strip().lower()

    navigation_terms = (
        "navigation.",
        "navigation ",
        "store locator",
        "locations",
        "products & services",
        "products and services",
        "order deli",
        "find an ",
        "find a ",
        "service type",
        "live_link",
    )

    if any(
        term in normalized
        for term in navigation_terms
    ):
        return True

    typename = value.get(
        "__typename"
    )

    if isinstance(
        typename,
        str,
    ):
        lower_typename = typename.lower()

        if any(
            term in lower_typename
            for term in (
                "navigation",
                "menu",
                "location",
                "service",
            )
        ):
            return True

    return False


def _is_product_candidate(
    value: dict[str, Any],
    *,
    product_name: Any,
    gtin: Any,
    sku: Any,
) -> bool:
    if not isinstance(
        product_name,
        str,
    ):
        return False

    if not product_name.strip():
        return False

    if _looks_like_navigation(
        value,
        product_name,
    ):
        return False

    if _has_allowed_typename(value):
        return True

    if gtin not in (None, ""):
        return True

    if sku not in (None, ""):
        return True

    if _has_product_signal(value):
        return True

    return False


def product_from_dict(
    value: dict[str, Any],
    source_url: str,
) -> dict[str, Any] | None:
    """
    Convert a JSON object that looks like a product into our common record.
    """
    product_name = _first(
        value,
        PRODUCT_NAME_KEYS,
    )

    if not product_name:
        return None

    brand = _extract_brand(
        _first(
            value,
            BRAND_KEYS,
        )
    )

    gtin = _first(
        value,
        GTIN_KEYS,
    )

    sku = _first(
        value,
        SKU_KEYS,
    )

    if not _is_product_candidate(
        value,
        product_name=product_name,
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
                "price_info",
            ),
        )
    )

    price = _first(
        value,
        PRICE_KEYS,
    )

    currency = _first(
        value,
        CURRENCY_KEYS,
    )

    if isinstance(
        value.get("price"),
        dict,
    ):
        nested_price, nested_currency = (
            _extract_nested_instacart_price(
                value
            )
        )

        if price is None or isinstance(
            price,
            dict,
        ):
            price = nested_price

        if currency is None:
            currency = nested_currency

    if price is None:
        price = _first(
            offer,
            PRICE_KEYS,
        )

    if currency is None:
        currency = _first(
            offer,
            CURRENCY_KEYS,
        )

    availability = _first(
        value,
        AVAILABILITY_KEYS,
    )

    if availability is None:
        availability = _first(
            offer,
            AVAILABILITY_KEYS,
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


def _identity(
    product: dict[str, Any],
) -> tuple[str, str]:
    """
    Deduplicate within one extraction pass using the strongest available
    identity.
    """
    gtin = str(
        product.get("gtin")
        or ""
    ).strip()

    if gtin:
        return (
            "gtin",
            gtin,
        )

    sku = str(
        product.get("sku")
        or ""
    ).strip()

    if sku:
        return (
            "sku",
            sku,
        )

    source_url = str(
        product.get("source_url")
        or ""
    ).strip()

    name = str(
        product.get("product_name")
        or ""
    ).strip().lower()

    return (
        "url-name",
        f"{source_url}|{name}",
    )


def extract_embedded_products(
    scripts: list[str],
    source_url: str,
) -> list[dict[str, Any]]:
    """
    Extract product-like objects from embedded JSON.

    The complete script list is processed as one unit so duplicates shared
    between __NEXT_DATA__, Apollo state, etc. are removed.
    """
    records: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    for document in parse_json_scripts(
        scripts
    ):
        for value in walk_json(
            document
        ):
            if not isinstance(
                value,
                dict,
            ):
                continue

            product = product_from_dict(
                value,
                source_url,
            )

            if product is None:
                continue

            identity = _identity(
                product
            )

            if identity in seen:
                continue

            seen.add(identity)
            records.append(
                product
            )

    return records

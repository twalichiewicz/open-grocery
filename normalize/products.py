from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Any


WHITESPACE_RE = re.compile(r"\s+")

CURRENCY_SYMBOLS = {
    "$": "USD",
    "€": "EUR",
    "£": "GBP",
    "¥": "JPY",
}

CURRENCY_CODES = {
    "USD",
    "EUR",
    "GBP",
    "JPY",
}

AVAILABILITY_MAP = {
    "https://schema.org/instock": "in_stock",
    "https://schema.org/outofstock": "out_of_stock",
    "https://schema.org/limitedavailability": "limited",
    "https://schema.org/preorder": "preorder",
    "https://schema.org/discontinued": "discontinued",
    "instock": "in_stock",
    "in_stock": "in_stock",
    "in stock": "in_stock",
    "available": "in_stock",
    "availablefororder": "in_stock",
    "outofstock": "out_of_stock",
    "out_of_stock": "out_of_stock",
    "out of stock": "out_of_stock",
    "unavailable": "out_of_stock",
    "limitedavailability": "limited",
    "limited": "limited",
    "preorder": "preorder",
    "pre-order": "preorder",
    "discontinued": "discontinued",
}


def normalize_text(
    value: Any,
) -> str | None:
    """
    Normalize scalar text values.

    Structured values such as dictionaries and lists are rejected rather
    than coerced into Python repr() strings.
    """
    if value is None:
        return None

    if not isinstance(
        value,
        (
            str,
            int,
            float,
            Decimal,
            bool,
        ),
    ):
        return None

    value = WHITESPACE_RE.sub(
        " ",
        str(value),
    ).strip()

    return value or None


def normalize_gtin(
    value: Any,
) -> str | None:
    """
    Normalize and validate GTIN values.

    Supported GTIN lengths are 8, 12, 13, and 14 digits. The check digit
    is validated using the GS1 modulo-10 algorithm.
    """
    value = normalize_text(value)

    if value is None:
        return None

    digits = re.sub(
        r"\D",
        "",
        value,
    )

    if len(digits) not in {
        8,
        12,
        13,
        14,
    }:
        return None

    total = 0

    for index, digit in enumerate(
        reversed(digits[:-1])
    ):
        multiplier = (
            3
            if index % 2 == 0
            else 1
        )

        total += (
            int(digit)
            * multiplier
        )

    check_digit = (
        10 - (total % 10)
    ) % 10

    if check_digit != int(
        digits[-1]
    ):
        return None

    return digits


def _extract_nested_price(
    value: Any,
) -> Any:
    """
    Extract the scalar price from common nested retailer structures.

    Instacart/Aldi/Sprouts captures commonly contain:

        price.viewSection.itemCard.priceString

    with additional fallbacks in:

        price.viewSection.itemCard.fullPriceString
        price.viewSection.badge.trackingProperties.price

    This function only extracts a candidate. Actual numeric validation
    remains the responsibility of normalize_price().
    """
    if not isinstance(value, dict):
        return value

    # Already scalar-looking.
    for key in (
        "priceString",
        "price",
        "currentPrice",
        "salePrice",
        "regularPrice",
        "amount",
        "value",
    ):
        candidate = value.get(key)

        if isinstance(
            candidate,
            (str, int, float, Decimal),
        ):
            return candidate

    view_section = value.get(
        "viewSection"
    )

    if isinstance(
        view_section,
        dict,
    ):
        item_card = view_section.get(
            "itemCard"
        )

        if isinstance(
            item_card,
            dict,
        ):
            candidate = (
                item_card.get(
                    "priceString"
                )
            )

            if candidate not in (
                None,
                "",
            ):
                return candidate

            candidate = (
                item_card.get(
                    "fullPriceString"
                )
            )

            if candidate not in (
                None,
                "",
            ):
                return candidate

        badge = view_section.get(
            "badge"
        )

        if isinstance(
            badge,
            dict,
        ):
            tracking_properties = (
                badge.get(
                    "trackingProperties"
                )
            )

            if isinstance(
                tracking_properties,
                dict,
            ):
                candidate = (
                    tracking_properties.get(
                        "price"
                    )
                )

                if candidate not in (
                    None,
                    "",
                ):
                    return candidate

    return None


def _normalize_decimal_text(
    text: str,
) -> tuple[str, str | None]:
    """
    Normalize human-formatted price text.

    Returns:
        (numeric_text, inferred_currency)

    Examples:

        "$4.05"       -> ("4.05", "USD")
        "€4,39"       -> ("4.39", "EUR")
        "1.234,56"    -> ("1234.56", None)
        "1,234.56"    -> ("1234.56", None)
        "4.39 USD"    -> ("4.39", "USD")
    """
    currency: str | None = None

    for symbol, code in CURRENCY_SYMBOLS.items():
        if symbol in text:
            currency = code
            text = text.replace(
                symbol,
                "",
            )

    text = text.strip()

    suffix_match = re.search(
        r"\b(USD|EUR|GBP|JPY)\s*$",
        text,
        re.IGNORECASE,
    )

    if suffix_match:
        currency = (
            suffix_match.group(1).upper()
        )

        text = (
            text[
                :suffix_match.start()
            ]
            .strip()
        )

    # Remove ordinary grouping spaces.
    text = text.replace(
        " ",
        "",
    )

    has_comma = "," in text
    has_dot = "." in text

    if has_comma and has_dot:
        # Whichever separator occurs last is treated as the decimal
        # separator:
        #
        # 1,234.56 -> 1234.56
        # 1.234,56 -> 1234.56
        #
        if text.rfind(",") > text.rfind("."):
            text = text.replace(
                ".",
                "",
            )
            text = text.replace(
                ",",
                ".",
            )
        else:
            text = text.replace(
                ",",
                "",
            )

    elif has_comma:
        parts = text.split(",")

        # A final 1- or 2-digit group is overwhelmingly likely to be
        # a decimal fraction in grocery prices.
        if len(parts[-1]) in {
            1,
            2,
        }:
            text = (
                "".join(parts[:-1])
                + "."
                + parts[-1]
            )
        else:
            text = "".join(parts)

    elif has_dot:
        parts = text.split(".")

        # More than one dot is grouping, as is a single dot followed by
        # exactly three digits:
        #
        # 1.234      -> 1234
        # 1.234.567  -> 1234567
        #
        # A two-digit final group remains decimal:
        # 4.05 -> 4.05
        if (
            len(parts) > 2
            or len(parts[-1]) == 3
        ):
            text = "".join(parts)

    return (
        text,
        currency,
    )


def normalize_price(
    value: Any,
) -> Decimal | None:
    """
    Normalize a price to a finite non-negative Decimal with two decimals.

    Structured price objects are searched for a known nested scalar before
    numeric normalization.
    """
    if value is None:
        return None

    value = _extract_nested_price(
        value
    )

    if value is None:
        return None

    if isinstance(
        value,
        Decimal,
    ):
        price = value

    else:
        if not isinstance(
            value,
            (
                str,
                int,
                float,
            ),
        ):
            return None

        text = str(value).strip()

        if not text:
            return None

        text, _ = (
            _normalize_decimal_text(
                text
            )
        )

        try:
            price = Decimal(
                text
            )

        except (
            InvalidOperation,
            ValueError,
        ):
            return None

    try:
        if not price.is_finite():
            return None

        if price < 0:
            return None

        return price.quantize(
            Decimal("0.01")
        )

    except (
        InvalidOperation,
        ValueError,
        OverflowError,
    ):
        return None


def infer_currency(
    value: Any,
) -> str | None:
    """
    Infer a currency code from a scalar price value.
    """
    if not isinstance(
        value,
        (
            str,
            int,
            float,
            Decimal,
        ),
    ):
        return None

    text = str(value).strip()

    _, currency = (
        _normalize_decimal_text(
            text
        )
    )

    return currency


def normalize_currency(
    value: Any,
) -> str | None:
    """
    Normalize an explicitly supplied currency code.
    """
    value = normalize_text(
        value
    )

    if value is None:
        return None

    normalized = value.upper()

    if normalized in CURRENCY_CODES:
        return normalized

    return normalized


def normalize_availability(
    value: Any,
) -> str | None:
    """
    Normalize availability to a small stable enum.

    JSON-LD commonly supplies schema.org URLs. Embedded retailer data may
    supply equivalent textual values.
    """
    if isinstance(
        value,
        dict,
    ):
        # Common structured availability shapes.
        for key in (
            "availability",
            "status",
            "inventoryStatus",
            "stockStatus",
        ):
            candidate = value.get(
                key
            )

            if candidate not in (
                None,
                "",
            ):
                return normalize_availability(
                    candidate
                )

        # Instacart sometimes nests availability-like information under
        # item metadata. Don't stringify the object if it cannot be
        # interpreted.
        return None

    value = normalize_text(
        value
    )

    if value is None:
        return None

    normalized = value.strip().lower()

    return AVAILABILITY_MAP.get(
        normalized,
        normalized,
    )


def _extract_brand(
    value: Any,
) -> Any:
    if isinstance(
        value,
        dict,
    ):
        return (
            value.get("name")
            or value.get("brandName")
        )

    return value


def normalize_product(
    product: dict[str, Any],
) -> dict[str, Any]:
    """
    Normalize a parsed product into a stable JSON-serializable record.
    """
    brand = _extract_brand(
        product.get("brand")
    )

    raw_price = product.get(
        "price"
    )

    price = normalize_price(
        raw_price
    )

    currency = normalize_currency(
        product.get("currency")
    )

    # If the parser did not supply a currency, infer it from the price.
    if currency is None:
        currency = infer_currency(
            _extract_nested_price(
                raw_price
            )
        )

    return {
        "source_url": normalize_text(
            product.get("source_url")
        ),
        "source_name": normalize_text(
            product.get("source_name")
        ),
        "retailer": normalize_text(
            product.get("retailer")
        ),
        "observed_at": normalize_text(
            product.get("observed_at")
        ),
        "product_name": normalize_text(
            product.get("product_name")
        ),
        "brand": normalize_text(
            brand
        ),
        "gtin": normalize_gtin(
            product.get("gtin")
        ),
        "sku": normalize_text(
            product.get("sku")
        ),
        "price": price,
        "currency": currency,
        "availability": normalize_availability(
            product.get("availability")
        ),
    }


def normalize_products(
    products: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Normalize products and discard records without a product name.
    """
    results: list[dict[str, Any]] = []

    for product in products:
        normalized = normalize_product(
            product
        )

        if not normalized[
            "product_name"
        ]:
            continue

        results.append(
            normalized
        )

    return results

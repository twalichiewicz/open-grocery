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

    Structured values are rejected rather than coerced into Python repr()
    strings.
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

    Supported lengths are 8, 12, 13, and 14 digits. The GS1 modulo-10
    check digit must also validate.
    """
    value = normalize_text(
        value
    )

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


def _normalize_decimal_text(
    text: str,
) -> tuple[str, str | None]:
    """
    Normalize human-formatted price text.

    Examples:

        "$4.05"      -> ("4.05", "USD")
        "€4,39"      -> ("4.39", "EUR")
        "1.234,56"   -> ("1234.56", None)
        "1,234.56"   -> ("1234.56", None)
        "4.39 USD"   -> ("4.39", "USD")
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

    text = text.replace(
        " ",
        "",
    )

    has_comma = "," in text
    has_dot = "." in text

    if has_comma and has_dot:
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
    Normalize a scalar price to a finite, non-negative Decimal.

    Parser-specific structured prices should already have been extracted
    before this function is called.
    """
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

    _, currency = (
        _normalize_decimal_text(
            str(value).strip()
        )
    )

    return currency


def normalize_currency(
    value: Any,
) -> str | None:
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
    Normalize availability to a stable enum.

    Structured values are inspected for known fields; otherwise they are
    rejected rather than stringified.
    """
    if isinstance(
        value,
        dict,
    ):
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

        return None

    value = normalize_text(
        value
    )

    if value is None:
        return None

    normalized = value.lower()

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

    if currency is None:
        currency = infer_currency(
            raw_price
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

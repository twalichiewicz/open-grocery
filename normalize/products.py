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


def normalize_text(value: Any) -> str | None:
    """
    Normalize scalar text values.

    Structured values such as dictionaries and lists are rejected rather
    than coerced to Python repr() strings.
    """
    if value is None:
        return None

    if not isinstance(value, (str, int, float, Decimal, bool)):
        return None

    value = WHITESPACE_RE.sub(
        " ",
        str(value),
    ).strip()

    return value or None


def normalize_gtin(value: Any) -> str | None:
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

    if len(digits) not in {8, 12, 13, 14}:
        return None

    total = 0

    for index, digit in enumerate(reversed(digits[:-1])):
        multiplier = 3 if index % 2 == 0 else 1
        total += int(digit) * multiplier

    check_digit = (10 - (total % 10)) % 10

    if check_digit != int(digits[-1]):
        return None

    return digits


def _normalize_decimal_text(
    text: str,
) -> tuple[str, str | None]:
    """
    Normalize a human-formatted price and infer a currency code.

    Returns (numeric_text, currency). Currency is inferred only from
    an explicit symbol; callers should preserve separately supplied
    currency values when available.
    """
    currency: str | None = None

    for symbol, code in CURRENCY_SYMBOLS.items():
        if symbol in text:
            currency = code
            text = text.replace(symbol, "")

    text = text.strip()

    # Handle common textual currency suffixes.
    suffix_match = re.search(
        r"\b(USD|EUR|GBP|JPY)\s*$",
        text,
        re.IGNORECASE,
    )

    if suffix_match:
        currency = suffix_match.group(1).upper()
        text = text[:suffix_match.start()].strip()

    # Remove ordinary grouping spaces.
    text = text.replace(" ", "")

    has_comma = "," in text
    has_dot = "." in text

    if has_comma and has_dot:
        # The final separator is normally the decimal separator:
        # 1,234.56 -> 1234.56
        # 1.234,56 -> 1234.56
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "")
            text = text.replace(",", ".")
        else:
            text = text.replace(",", "")

    elif has_comma:
        comma_parts = text.split(",")

        if len(comma_parts[-1]) in {1, 2}:
            # 4,39 -> 4.39
            text = "".join(comma_parts[:-1]) + "." + comma_parts[-1]
        else:
            # 1,234 -> 1234
            text = "".join(comma_parts)

    elif has_dot:
        dot_parts = text.split(".")

        if (
            len(dot_parts) > 2
            or len(dot_parts[-1]) == 3
        ):
            # 1.234 or 1.234.567 -> grouping separators.
            text = "".join(dot_parts)

    return text, currency


def normalize_price(value: Any) -> Decimal | None:
    """
    Normalize a price to a finite non-negative Decimal with two decimals.
    """
    if value is None:
        return None

    if isinstance(value, Decimal):
        price = value

    else:
        if not isinstance(value, (str, int, float)):
            return None

        text = str(value).strip()

        if not text:
            return None

        text, _ = _normalize_decimal_text(text)

        try:
            price = Decimal(text)

        except (InvalidOperation, ValueError):
            return None

    try:
        if not price.is_finite():
            return None

        if price < 0:
            return None

        return price.quantize(
            Decimal("0.01")
        )

    except (InvalidOperation, ValueError, OverflowError):
        return None


def normalize_product(
    product: dict[str, Any],
) -> dict[str, Any]:
    """
    Normalize a parsed product into a stable JSON-serializable record.
    """
    brand = product.get("brand")

    if isinstance(brand, dict):
        brand = brand.get("name")

    return {
        "source_url": normalize_text(
            product.get("source_url")
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
        "price": normalize_price(
            product.get("price")
        ),
        "currency": normalize_text(
            product.get("currency")
        ),
        "availability": normalize_text(
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
        normalized = normalize_product(product)

        if not normalized["product_name"]:
            continue

        results.append(normalized)

    return results

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Any


WHITESPACE_RE = re.compile(r"\s+")


def normalize_text(value: Any) -> str | None:
    if value is None:
        return None

    value = WHITESPACE_RE.sub(" ", str(value)).strip()

    return value or None


def normalize_gtin(value: Any) -> str | None:
    value = normalize_text(value)

    if value is None:
        return None

    digits = re.sub(r"\D", "", value)

    if not digits:
        return None

    if len(digits) in {8, 12, 13, 14}:
        return digits

    return digits


def normalize_price(value: Any) -> Decimal | None:
    if value is None:
        return None

    text = str(value).strip()

    if not text:
        return None

    text = text.replace("$", "")
    text = text.replace(",", "")

    try:
        price = Decimal(text)
    except InvalidOperation:
        return None

    if price < 0:
        return None

    return price.quantize(Decimal("0.01"))


def normalize_product(
    product: dict[str, Any],
) -> dict[str, Any]:
    """Normalize a parsed product into a stable product record."""
    return {
        "source_url": normalize_text(product.get("source_url")),
        "product_name": normalize_text(product.get("product_name")),
        "brand": normalize_text(product.get("brand")),
        "gtin": normalize_gtin(product.get("gtin")),
        "sku": normalize_text(product.get("sku")),
        "price": normalize_price(product.get("price")),
        "currency": normalize_text(product.get("currency")),
        "availability": normalize_text(product.get("availability")),
    }


def normalize_products(
    products: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Normalize and discard records without a product name."""
    results: list[dict[str, Any]] = []

    for product in products:
        normalized = normalize_product(product)

        if not normalized["product_name"]:
            continue

        results.append(normalized)

    return results

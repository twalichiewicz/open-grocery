from __future__ import annotations

from typing import Any

from parsers.jsonld import (
    extract_jsonld,
    is_product,
    iter_jsonld_objects,
)


def extract_products(
    html: bytes,
    source_url: str,
) -> list[dict[str, Any]]:
    """Extract Product entities from JSON-LD."""
    records: list[dict[str, Any]] = []

    seen: set[tuple[str, str, str]] = set()

    for payload in extract_jsonld(html):
        for item in iter_jsonld_objects(payload):
            if not is_product(item):
                continue

            offers = item.get("offers")

            if isinstance(offers, list):
                offers = next(
                    (
                        offer
                        for offer in offers
                        if isinstance(offer, dict)
                    ),
                    {},
                )

            if not isinstance(offers, dict):
                offers = {}

            product_name = clean_value(item.get("name"))
            brand = extract_brand(item.get("brand"))

            gtin = (
                item.get("gtin13")
                or item.get("gtin12")
                or item.get("gtin14")
                or item.get("gtin8")
                or item.get("gtin")
            )

            sku = clean_value(item.get("sku"))
            price = clean_value(offers.get("price"))
            currency = clean_value(offers.get("priceCurrency"))
            availability = clean_value(offers.get("availability"))

            # Do not emit anonymous JSON-LD Product objects.
            #
            # A Product without a name, SKU, GTIN, or offer data is
            # generally not useful as grocery product data.
            if not any(
                (
                    product_name,
                    brand,
                    gtin,
                    sku,
                    price,
                )
            ):
                continue

            identity = (
                product_name or "",
                str(gtin or sku or ""),
                str(price or ""),
            )

            if identity in seen:
                continue

            seen.add(identity)

            records.append(
                {
                    "source_url": source_url,
                    "product_name": product_name,
                    "brand": brand,
                    "gtin": clean_value(gtin),
                    "sku": sku,
                    "price": price,
                    "currency": currency,
                    "availability": availability,
                }
            )

    return records


def extract_brand(value: Any) -> str:
    if isinstance(value, dict):
        return clean_value(value.get("name"))

    return clean_value(value)


def clean_value(value: Any) -> str:
    if value is None:
        return ""

    if isinstance(value, str):
        return value.strip()

    return str(value).strip()

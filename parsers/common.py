# parsers/common.py

from parsers.jsonld import extract_jsonld


def extract_products(html: bytes, source_url: str):
    records = []

    for obj in extract_jsonld(html):
        objects = obj if isinstance(obj, list) else [obj]

        for item in objects:
            if not isinstance(item, dict):
                continue

            if item.get("@type") != "Product":
                continue

            offers = item.get("offers", {})

            if isinstance(offers, list):
                offers = offers[0] if offers else {}

            records.append({
                "source_url": source_url,
                "product_name": item.get("name"),
                "brand": extract_brand(item.get("brand")),
                "gtin": (
                    item.get("gtin13")
                    or item.get("gtin12")
                    or item.get("gtin14")
                    or item.get("gtin")
                ),
                "sku": item.get("sku"),
                "price": offers.get("price"),
                "currency": offers.get("priceCurrency"),
                "availability": offers.get("availability"),
            })

    return records


def extract_brand(value):
    if isinstance(value, dict):
        return value.get("name")

    return value

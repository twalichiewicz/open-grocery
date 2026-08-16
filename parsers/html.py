from __future__ import annotations

from typing import Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup


def soup_from_html(html: bytes | str) -> BeautifulSoup:
    """Create a BeautifulSoup document from HTML bytes or text."""
    return BeautifulSoup(html, "html.parser")


def extract_text(
    html: bytes | str,
    selector: str,
) -> list[str]:
    """Extract normalized text from elements matching a CSS selector."""
    soup = soup_from_html(html)

    results: list[str] = []

    for element in soup.select(selector):
        text = element.get_text(" ", strip=True)

        if text:
            results.append(text)

    return results


def extract_links(
    html: bytes | str,
    source_url: str,
) -> list[dict[str, str]]:
    """Extract absolute links and their visible text."""
    soup = soup_from_html(html)

    results: list[dict[str, str]] = []

    for element in soup.find_all("a", href=True):
        href = urljoin(source_url, element["href"])
        text = element.get_text(" ", strip=True)

        results.append(
            {
                "url": href,
                "text": text,
            }
        )

    return results


def extract_meta(
    html: bytes | str,
) -> dict[str, str]:
    """Extract common HTML metadata."""
    soup = soup_from_html(html)

    metadata: dict[str, str] = {}

    title = soup.find("title")

    if title:
        metadata["title"] = title.get_text(" ", strip=True)

    for element in soup.find_all("meta"):
        name = (
            element.get("name")
            or element.get("property")
            or element.get("itemprop")
        )
        content = element.get("content")

        if name and content:
            metadata[name.strip().lower()] = content.strip()

    return metadata


def extract_json_scripts(
    html: bytes | str,
) -> list[str]:
    """
    Extract the raw contents of script elements that may contain JSON.

    JSON parsing itself is deliberately handled by parsers/embedded_json.py.
    """
    soup = soup_from_html(html)

    results: list[str] = []

    for script in soup.find_all("script"):
        script_type = (script.get("type") or "").lower()

        if (
            "json" in script_type
            or script.get("id") in {
                "__NEXT_DATA__",
                "__NUXT_DATA__",
                "__APOLLO_STATE__",
            }
        ):
            content = script.string or script.get_text()

            if content and content.strip():
                results.append(content.strip())

    return results


def _first_value(
    data: dict[str, Any],
    keys: tuple[str, ...],
) -> Any:
    for key in keys:
        value = data.get(key)

        if value not in (None, ""):
            return value

    return None


def extract_html_product(
    html: bytes | str,
    source_url: str,
) -> dict[str, Any] | None:
    """
    Extract a conservative product record from standard HTML metadata.

    This intentionally requires a product name before producing a record.
    """
    metadata = extract_meta(html)

    product_name = _first_value(
        metadata,
        (
            "product:name",
            "og:title",
            "twitter:title",
        ),
    )

    if not product_name:
        return None

    price = _first_value(
        metadata,
        (
            "product:price:amount",
            "price",
            "product:price",
        ),
    )

    currency = _first_value(
        metadata,
        (
            "product:price:currency",
            "pricecurrency",
            "currency",
        ),
    )

    brand = _first_value(
        metadata,
        (
            "product:brand",
            "brand",
        ),
    )

    sku = _first_value(
        metadata,
        (
            "product:sku",
            "sku",
        ),
    )

    gtin = _first_value(
        metadata,
        (
            "product:gtin",
            "gtin",
            "gtin13",
            "gtin12",
            "gtin14",
        ),
    )

    return {
        "source_url": source_url,
        "product_name": product_name,
        "brand": brand,
        "gtin": gtin,
        "sku": sku,
        "price": price,
        "currency": currency,
    }


def extract_html_products(
    html: bytes | str,
    source_url: str,
) -> list[dict[str, Any]]:
    """
    Extract product records from standard HTML metadata.

    Returns zero or one record. JSON-LD and embedded application JSON
    are handled by their dedicated parsers.
    """
    product = extract_html_product(html, source_url)

    if product is None:
        return []

    return [product]

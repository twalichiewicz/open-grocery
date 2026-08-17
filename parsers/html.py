from __future__ import annotations

from typing import Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup


KNOWN_JSON_SCRIPT_IDS = {
    "__NEXT_DATA__",
    "__NUXT_DATA__",
    "__APOLLO_STATE__",
    "node-apollo-state",
}


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
        href = urljoin(source_url, str(element["href"]))
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
            metadata[str(name).strip().lower()] = str(content).strip()

    return metadata


def _is_embedded_json_script(
    script_id: str | None,
    script_type: str,
) -> bool:
    """
    Return whether a script belongs to the embedded application-state path.

    JSON-LD is deliberately excluded because it has its own parser.
    """
    if script_type == "application/ld+json":
        return False

    if script_id in KNOWN_JSON_SCRIPT_IDS:
        return True

    return script_type == "application/json" or (
        script_type.endswith("+json")
        and script_type != "application/ld+json"
    )


def extract_json_scripts(
    html: bytes | str,
) -> list[str]:
    """
    Extract raw contents of embedded application JSON scripts.

    JSON-LD is excluded and handled by parsers.jsonld.
    """
    return [
        script["content"]
        for script in extract_json_scripts_with_ids(html)
    ]


def extract_json_scripts_with_ids(
    html: bytes | str,
) -> list[dict[str, str]]:
    """
    Extract embedded application JSON while retaining script IDs.
    """
    soup = soup_from_html(html)

    results: list[dict[str, str]] = []

    for script in soup.find_all("script"):
        script_id = script.get("id")
        script_type = (script.get("type") or "").lower()

        if not _is_embedded_json_script(
            script_id,
            script_type,
        ):
            continue

        content = script.string or script.get_text()

        if not content or not content.strip():
            continue

        results.append(
            {
                "id": str(script_id or ""),
                "type": script_type,
                "content": content.strip(),
            }
        )

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


def _has_product_metadata(
    metadata: dict[str, str],
) -> bool:
    """
    Return whether HTML metadata contains a product-specific signal.

    A page title alone is not sufficient. Generic pages such as store
    locators, navigation pages, category pages, and corporate landing pages
    routinely expose og:title/twitter:title without representing a product.
    """

    product_specific_keys = (
        "product:price:amount",
        "product:price:currency",
        "product:price",
        "product:brand",
        "product:sku",
        "product:gtin",
        "gtin",
        "gtin13",
        "gtin12",
        "gtin14",
        "sku",
        "price",
        "pricecurrency",
        "brand",
        "product:availability",
        "og:type",
    )

    for key in product_specific_keys:
        value = metadata.get(key)

        if not value:
            continue

        if key == "og:type" and value.lower() != "product":
            continue

        return True

    return False


def extract_html_product(
    html: bytes | str,
    source_url: str,
) -> dict[str, Any] | None:
    """
    Extract a conservative product record from standard HTML metadata.

    A product name alone is insufficient. At least one independent
    product-specific metadata signal must also be present.
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

    if not _has_product_metadata(metadata):
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

    availability = _first_value(
        metadata,
        (
            "product:availability",
            "og:availability",
            "availability",
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
        "availability": availability,
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

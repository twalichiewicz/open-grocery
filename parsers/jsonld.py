from __future__ import annotations

import json
from typing import Any

from bs4 import BeautifulSoup


def _load_json(text: str) -> Any:
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return None


def extract_jsonld(html: bytes) -> list[Any]:
    """Extract valid JSON-LD payloads from an HTML document."""
    soup = BeautifulSoup(html, "html.parser")

    results: list[Any] = []

    for script in soup.find_all(
        "script",
        attrs={"type": "application/ld+json"},
    ):
        text = script.string or script.get_text()

        if not text or not text.strip():
            continue

        data = _load_json(text)

        if data is not None:
            results.append(data)

    return results


def iter_jsonld_objects(value: Any):
    """Yield dictionary objects recursively from JSON-LD data."""
    if isinstance(value, dict):
        yield value

        for nested in value.values():
            yield from iter_jsonld_objects(nested)

    elif isinstance(value, list):
        for item in value:
            yield from iter_jsonld_objects(item)


def jsonld_type(value: Any) -> set[str]:
    """Return normalized @type values from a JSON-LD object."""
    raw_type = value.get("@type")

    if isinstance(raw_type, str):
        return {raw_type.strip().lower()}

    if isinstance(raw_type, list):
        return {
            str(item).strip().lower()
            for item in raw_type
            if item is not None
        }

    return set()


def is_product(value: Any) -> bool:
    """Return True only when a JSON-LD object represents a Product."""
    if not isinstance(value, dict):
        return False

    types = jsonld_type(value)

    return "product" in types

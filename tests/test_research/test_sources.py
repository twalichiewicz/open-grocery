from pathlib import Path

from scripts.discover_sources import (
    canonicalize_url,
    deduplicate,
    normalize_row,
    validate_row,
)


def make_row(**overrides):
    row = {
        "retailer": "Example",
        "source_name": "Example Products",
        "source_type": "Product Catalog",
        "url": "https://example.com/products/",
        "http_method": "GET",
        "authentication": "",
        "parameters": "",
        "response_format": "",
        "product_data": "",
        "pricing_data": "",
        "store_data": "",
        "promotion_data": "",
        "inventory_data": "",
        "upc_gtin": "",
        "store_level_data": "",
        "geographic_parameters": "",
        "request_frequency": "",
        "requires_session": "",
        "requires_account": "",
        "requires_javascript": "",
        "bot_protection": "",
        "observed_response": "",
        "first_discovered": "2026-08-16",
        "last_verified": "2026-08-16",
        "status": "candidate",
        "notes": "",
    }

    row.update(overrides)
    return row


def test_canonicalize_url_removes_tracking_parameters():
    url = (
        "https://example.com/products/"
        "?utm_source=test&utm_campaign=campaign&loc=177"
    )

    assert canonicalize_url(url) == "https://example.com/products?loc=177"


def test_normalize_row_normalizes_source_type():
    row = normalize_row(make_row(source_type="Product Catalog"))

    assert row["source_type"] == "product_catalog"


def test_normalize_row_assigns_source_id():
    row = normalize_row(make_row())

    assert row["source_id"]
    assert len(row["source_id"]) == 16


def test_duplicate_sources_are_removed():
    first = normalize_row(
        make_row(
            url="https://example.com/products?utm_source=a",
        )
    )

    second = normalize_row(
        make_row(
            url="https://example.com/products?utm_source=b",
        )
    )

    result = deduplicate([first, second])

    assert len(result) == 1


def test_valid_source_has_no_errors():
    row = normalize_row(make_row())

    assert validate_row(row) == []


def test_invalid_source_type_requires_review():
    row = normalize_row(
        make_row(source_type="Something Completely Unknown")
    )

    assert row["status"] == "needs_review"


def test_invalid_url_is_rejected():
    row = normalize_row(
        make_row(url="not-a-url")
    )

    errors = validate_row(row)

    assert errors
    assert "URL has no hostname" in errors


def test_project_source_file_exists():
    source_file = Path("data/sources.csv")

    assert source_file.exists()

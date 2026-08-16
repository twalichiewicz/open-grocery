#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
import hashlib
from pathlib import Path
from urllib.parse import (
    parse_qsl,
    urlencode,
    urlsplit,
    urlunsplit,
)

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_INPUT = ROOT / "data" / "sources.csv"
DEFAULT_OUTPUT = ROOT / "data" / "sources_discovered.csv"

SOURCE_TYPES = {
    "store_locator",
    "product_search",
    "product_catalog",
    "product",
}

TRACKING_PARAMETERS = {
    "utm_campaign",
    "utm_content",
    "utm_medium",
    "utm_source",
    "utm_term",
    "gclid",
    "fbclid",
}

REQUIRED_COLUMNS = [
    "retailer",
    "source_name",
    "source_type",
    "url",
    "http_method",
    "authentication",
    "parameters",
    "response_format",
    "product_data",
    "pricing_data",
    "store_data",
    "promotion_data",
    "inventory_data",
    "upc_gtin",
    "store_level_data",
    "geographic_parameters",
    "request_frequency",
    "requires_session",
    "requires_account",
    "requires_javascript",
    "bot_protection",
    "observed_response",
    "first_discovered",
    "last_verified",
    "status",
    "notes",
]


def canonicalize_url(url: str) -> str:
    """Remove tracking parameters while preserving functional parameters."""
    parts = urlsplit(url.strip())

    query = [
        (key, value)
        for key, value in parse_qsl(
            parts.query,
            keep_blank_values=True,
        )
        if key.lower() not in TRACKING_PARAMETERS
    ]

    return urlunsplit(
        (
            parts.scheme.lower(),
            parts.netloc.lower(),
            parts.path.rstrip("/") or "/",
            urlencode(query),
            "",
        )
    )


def source_id(
    retailer: str,
    source_type: str,
    url: str,
) -> str:
    value = (
        f"{retailer}|"
        f"{source_type}|"
        f"{canonicalize_url(url)}"
    )

    return hashlib.sha256(
        value.encode("utf-8")
    ).hexdigest()[:16]


def load_sources(
    path: Path,
) -> list[dict[str, str]]:
    with path.open(
        newline="",
        encoding="utf-8",
    ) as handle:
        reader = csv.DictReader(handle)

        if reader.fieldnames is None:
            raise ValueError(
                f"{path} does not contain a CSV header"
            )

        missing = [
            column
            for column in REQUIRED_COLUMNS
            if column not in reader.fieldnames
        ]

        if missing:
            raise ValueError(
                f"{path} is missing required columns: "
                f"{', '.join(missing)}"
            )

        return list(reader)


def _normalize_value(value) -> str:
    if value is None:
        return ""

    if isinstance(value, list):
        return "; ".join(
            str(item).strip()
            for item in value
            if item is not None
        )

    return str(value).strip()


def normalize_source_type(value: str) -> str:
    """
    Normalize human-readable source types to the canonical vocabulary.

    Examples:
        Product Catalog -> product_catalog
        Store Locator   -> store_locator
        Product Search  -> product_search
    """
    value = _normalize_value(value)

    if not value:
        return ""

    normalized = value.lower().replace("-", "_")
    normalized = "_".join(
        normalized.split()
    )

    return normalized


def normalize_http_method(value: str) -> str:
    return _normalize_value(value).upper()


def normalize_row(row: dict[str, str]) -> dict[str, str]:
    normalized = {
        key: _normalize_value(value)
        for key, value in row.items()
    }

    # Keep the CSV schema stable.
    for field in REQUIRED_COLUMNS:
        normalized.setdefault(field, "")

    # Normalize source type to the canonical vocabulary.
    source_type = normalized["source_type"].lower().replace("-", "_").replace(" ", "_")
    normalized["source_type"] = source_type

    # Normalize HTTP method.
    normalized["http_method"] = normalized["http_method"].upper()

    # Assign a deterministic ID before validation/deduplication.
    normalized["source_id"] = source_id(
        normalized["retailer"],
        normalized["source_type"],
        normalized["url"],
    )

    # Invalid source types should immediately require review.
    if normalized["source_type"] not in SOURCE_TYPES:
        normalized["status"] = "needs_review"
        normalized["notes"] = (
            f"unsupported source_type: {normalized['source_type']}"
        )

    return normalized


def deduplicate(
    rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    """Keep the first occurrence of each canonical source."""
    seen: set[str] = set()
    result: list[dict[str, str]] = []

    for row in rows:
        key = source_id(
            row["retailer"],
            row["source_type"],
            row["url"],
        )

        row["source_id"] = key

        if key in seen:
            continue

        seen.add(key)
        result.append(row)

    return result


def validate_row(row: dict[str, str]) -> list[str]:
    errors: list[str] = []

    if not row["retailer"]:
        errors.append("missing retailer")

    if not row["source_name"]:
        errors.append("missing source_name")

    if not row["url"]:
        errors.append("missing url")

    if row["source_type"] not in SOURCE_TYPES:
        errors.append(
            f"unsupported source_type: {row['source_type']}"
        )

    if row["http_method"] not in {"GET", "POST"}:
        errors.append(
            f"unsupported HTTP method: {row['http_method']}"
        )

    parts = urlsplit(row["url"])

    if parts.scheme not in {"http", "https"}:
        errors.append("URL must use http or https")

    if not parts.netloc:
        errors.append("URL has no hostname")

    return errors


def discover(
    input_path: Path = DEFAULT_INPUT,
    output_path: Path = DEFAULT_OUTPUT,
) -> tuple[int, int]:
    rows = load_sources(input_path)

    normalized = [
        normalize_row(row)
        for row in rows
    ]

    unique = deduplicate(normalized)

    valid: list[dict[str, str]] = []
    invalid_count = 0

    for row in unique:
        errors = validate_row(row)

        if errors:
            row["status"] = "needs_review"

            existing_notes = row.get("notes", "").strip()
            validation_notes = "; ".join(errors)

            if existing_notes and validation_notes:
                row["notes"] = f"{existing_notes}; {validation_notes}"
            else:
                row["notes"] = existing_notes or validation_notes

            invalid_count += 1

        valid.append(row)

    fieldnames = REQUIRED_COLUMNS + [
        "source_id"
    ]

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with output_path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
            extrasaction="ignore",
        )

        writer.writeheader()
        writer.writerows(valid)

    return len(valid), invalid_count


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Normalize and deduplicate "
            "grocery source candidates."
        )
    )

    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help="Input source CSV.",
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Output normalized source CSV.",
    )

    args = parser.parse_args()

    total, invalid = discover(
        args.input,
        args.output,
    )

    print(
        f"Sources written: {total}"
    )

    print(
        f"Sources requiring review: {invalid}"
    )

    print(
        f"Output: {args.output}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

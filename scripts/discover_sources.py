#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
import hashlib
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

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

OUTPUT_COLUMNS = REQUIRED_COLUMNS + ["source_id"]


def canonicalize_url(url: str) -> str:
    """Normalize a URL and remove known tracking parameters."""
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


def source_id(retailer: str, source_type: str, url: str) -> str:
    """Generate a stable identifier for a canonical source."""
    value = (
        f"{retailer.strip().lower()}|"
        f"{source_type.strip().lower()}|"
        f"{canonicalize_url(url)}"
    )

    return hashlib.sha256(
        value.encode("utf-8")
    ).hexdigest()[:16]


def load_sources(path: Path) -> list[dict[str, str]]:
    """Load source candidates from a CSV file."""
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


def _normalize_value(value: object) -> str:
    """Convert CSV values into stable string values."""
    if value is None:
        return ""

    if isinstance(value, list):
        return "; ".join(
            str(item).strip()
            for item in value
            if item is not None
        )

    return str(value).strip()


def normalize_row(row: dict[str, object]) -> dict[str, str]:
    """Normalize a source row and generate its stable source ID."""
    normalized = {
        key: _normalize_value(value)
        for key, value in row.items()
    }

    # Keep the CSV schema stable.
    for field in REQUIRED_COLUMNS:
        normalized.setdefault(field, "")

    # Normalize the URL before generating the ID.
    normalized["url"] = canonicalize_url(normalized["url"])

    normalized["source_id"] = source_id(
        normalized["retailer"],
        normalized["source_type"],
        normalized["url"],
    )

    return normalized


def deduplicate(
    rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    """Keep the first occurrence of each canonical source."""
    seen: set[str] = set()
    result: list[dict[str, str]] = []

    for row in rows:
        key = row["source_id"]

        if key in seen:
            continue

        seen.add(key)
        result.append(row)

    return result


def validate_row(row: dict[str, str]) -> list[str]:
    """Return validation errors for a normalized source row."""
    errors: list[str] = []

    if not row["retailer"]:
        errors.append("missing retailer")

    if not row["source_name"]:
        errors.append("missing source_name")

    if not row["source_type"]:
        errors.append("missing source_type")
    elif row["source_type"] not in SOURCE_TYPES:
        errors.append(
            f"unsupported source_type: {row['source_type']}"
        )

    if not row["url"]:
        errors.append("missing url")
    else:
        parts = urlsplit(row["url"])

        if parts.scheme not in {"http", "https"}:
            errors.append("URL must use http or https")

        if not parts.netloc:
            errors.append("URL has no hostname")

    if not row["http_method"]:
        errors.append("missing http_method")
    elif row["http_method"].upper() not in {"GET", "POST"}:
        errors.append(
            f"unsupported HTTP method: {row['http_method']}"
        )
    else:
        row["http_method"] = row["http_method"].upper()

    return errors


def discover(
    input_path: Path = DEFAULT_INPUT,
    output_path: Path = DEFAULT_OUTPUT,
) -> tuple[int, int]:
    """Load, normalize, deduplicate, validate, and write sources."""
    rows = load_sources(input_path)

    normalized = [
        normalize_row(row)
        for row in rows
    ]

    unique = deduplicate(normalized)

    invalid_count = 0

    for row in unique:
        errors = validate_row(row)

        if errors:
            row["status"] = "needs_review"

            existing_notes = row["notes"].strip()

            if existing_notes:
                row["notes"] = (
                    f"{existing_notes}; "
                    f"{'; '.join(errors)}"
                )
            else:
                row["notes"] = "; ".join(errors)

            invalid_count += 1

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
            fieldnames=OUTPUT_COLUMNS,
            extrasaction="ignore",
        )

        writer.writeheader()
        writer.writerows(unique)

    return len(unique), invalid_count


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Normalize, deduplicate, and validate "
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

    try:
        total, invalid = discover(
            args.input,
            args.output,
        )
    except (OSError, ValueError, csv.Error) as exc:
        print(f"Error: {exc}")
        return 1

    print(f"Sources written: {total}")
    print(f"Sources requiring review: {invalid}")
    print(f"Output: {args.output}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

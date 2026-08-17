from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

DEFAULT_INPUT = (
    ROOT
    / "data"
    / "normalized"
    / "products.jsonl"
)


REQUIRED_FIELDS = {
    "source_url",
    "product_name",
    "brand",
    "gtin",
    "sku",
    "price",
    "currency",
    "availability",
    "retailer",
    "observed_at",
}


def load_records(
    path: Path,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []

    with path.open(
        "r",
        encoding="utf-8",
    ) as handle:
        for line_number, line in enumerate(
            handle,
            start=1,
        ):
            if not line.strip():
                continue

            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"{path}:{line_number}: invalid JSON: {exc}"
                ) from exc

            if not isinstance(value, dict):
                raise ValueError(
                    f"{path}:{line_number}: record is not an object"
                )

            records.append(value)

    return records


def validate_record(
    record: dict[str, Any],
    index: int,
) -> list[str]:
    errors: list[str] = []

    missing = REQUIRED_FIELDS - record.keys()

    if missing:
        errors.append(
            f"record {index}: missing fields: "
            + ", ".join(sorted(missing))
        )

    product_name = record.get("product_name")

    if not isinstance(product_name, str) or not product_name.strip():
        errors.append(
            f"record {index}: invalid product_name"
        )

    price = record.get("price")

    if price is not None:
        try:
            decimal_price = Decimal(str(price))
        except (InvalidOperation, ValueError):
            errors.append(
                f"record {index}: invalid price {price!r}"
            )
        else:
            if not decimal_price.is_finite():
                errors.append(
                    f"record {index}: non-finite price"
                )

            if decimal_price < 0:
                errors.append(
                    f"record {index}: negative price"
                )

    availability = record.get("availability")

    if availability is not None and not isinstance(
        availability,
        str,
    ):
        errors.append(
            f"record {index}: availability is not a string"
        )

    for field in (
        "retailer",
        "observed_at",
    ):
        value = record.get(field)

        if value is not None and not isinstance(
            value,
            str,
        ):
            errors.append(
                f"record {index}: {field} is not a string"
            )

    return errors


def quality_report(
    records: list[dict[str, Any]],
) -> None:
    by_retailer: dict[str, list[dict[str, Any]]] = (
        defaultdict(list)
    )

    for record in records:
        retailer = (
            record.get("retailer")
            or "(unknown)"
        )

        by_retailer[retailer].append(record)

    print()
    print("QUALITY BY RETAILER")
    print("=" * 72)

    for retailer, rows in sorted(
        by_retailer.items()
    ):
        total = len(rows)

        def coverage(field: str) -> str:
            count = sum(
                1
                for row in rows
                if row.get(field) not in (
                    None,
                    "",
                )
            )

            percentage = (
                100 * count / total
                if total
                else 0
            )

            return f"{percentage:5.1f}%"

        print(
            f"{retailer}: "
            f"{total:5d} rows  "
            f"price {coverage('price')}  "
            f"sku {coverage('sku')}  "
            f"gtin {coverage('gtin')}  "
            f"brand {coverage('brand')}  "
            f"availability {coverage('availability')}"
        )


def validate(
    path: Path,
    *,
    report: bool = True,
) -> int:
    try:
        records = load_records(path)
    except (OSError, ValueError) as exc:
        print(
            f"ERROR: {exc}",
            file=sys.stderr,
        )
        return 1

    errors: list[str] = []

    for index, record in enumerate(
        records,
        start=1,
    ):
        errors.extend(
            validate_record(
                record,
                index,
            )
        )

    print(
        f"Records: {len(records)}"
    )

    if errors:
        print(
            f"Validation errors: {len(errors)}"
        )

        for error in errors[:50]:
            print(
                f"  {error}",
                file=sys.stderr,
            )

        if len(errors) > 50:
            print(
                f"  ... {len(errors) - 50} more",
                file=sys.stderr,
            )

    else:
        print("Validation errors: 0")

    if report:
        quality_report(records)

    return 1 if errors else 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate normalized Open Grocery records."
        )
    )

    parser.add_argument(
        "input",
        nargs="?",
        type=Path,
        default=DEFAULT_INPUT,
    )

    parser.add_argument(
        "--no-report",
        action="store_true",
        help="Skip the per-retailer quality report.",
    )

    args = parser.parse_args()

    return validate(
        args.input,
        report=not args.no_report,
    )


if __name__ == "__main__":
    raise SystemExit(main())

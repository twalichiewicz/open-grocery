from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path


DEFAULT_INPUT = Path(
    "data/normalized/products.jsonl"
)


def load_rows(path: Path) -> list[dict]:
    rows = []

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
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"{path}:{line_number}: "
                    f"invalid JSON: {exc}"
                ) from exc

    return rows


def validate(rows: list[dict]) -> int:
    errors = []

    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            errors.append(
                f"row {index}: not an object"
            )
            continue

        if not row.get("product_name"):
            errors.append(
                f"row {index}: missing product_name"
            )

        if not row.get("retailer"):
            errors.append(
                f"row {index}: missing retailer"
            )

        if not row.get("observed_at"):
            errors.append(
                f"row {index}: missing observed_at"
            )

        price = row.get("price")

        if price is not None and not isinstance(
            price,
            (int, float),
        ):
            errors.append(
                f"row {index}: price is not numeric"
            )

    print("=" * 72)
    print("NORMALIZED DATASET")
    print("=" * 72)
    print(f"rows: {len(rows)}")

    retailers = Counter(
        row.get("retailer")
        for row in rows
    )

    print()
    print("retailers:")

    for retailer, count in retailers.most_common():
        group = [
            row
            for row in rows
            if row.get("retailer") == retailer
        ]

        print(
            f"  {count:4} {retailer!r} "
            f"priced={sum(r.get('price') is not None for r in group)} "
            f"sku={sum(bool(r.get('sku')) for r in group)} "
            f"gtin={sum(bool(r.get('gtin')) for r in group)}"
        )

    print()
    print("availability:")
    for value, count in Counter(
        row.get("availability")
        for row in rows
    ).most_common():
        print(
            f"  {count:4} {value!r}"
        )

    print()
    print("errors:", len(errors))

    for error in errors[:20]:
        print("  ERROR:", error)

    if len(errors) > 20:
        print(
            f"  ... {len(errors) - 20} more"
        )

    return 1 if errors else 0


def main() -> int:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
    )

    args = parser.parse_args()

    return validate(
        load_rows(args.input)
    )


if __name__ == "__main__":
    raise SystemExit(main())

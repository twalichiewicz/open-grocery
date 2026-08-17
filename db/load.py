from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

DEFAULT_INPUT = (
    ROOT
    / "data"
    / "normalized"
    / "products.jsonl"
)

DEFAULT_DATABASE = (
    ROOT
    / "data"
    / "grocery.sqlite"
)

SCHEMA = (
    ROOT
    / "db"
    / "schema.sql"
)


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
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"{path}:{line_number}: invalid JSON"
                ) from exc

            if not isinstance(record, dict):
                raise ValueError(
                    f"{path}:{line_number}: expected object"
                )

            records.append(record)

    return records


def product_key(
    record: dict[str, Any],
) -> tuple[str, str, str]:
    retailer = (
        str(record.get("retailer") or "")
    )

    gtin = (
        str(record.get("gtin") or "")
    )

    sku = (
        str(record.get("sku") or "")
    )

    return (
        retailer,
        gtin,
        sku,
    )


def load(
    input_path: Path,
    database_path: Path,
) -> int:
    records = load_records(input_path)

    database_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    connection = sqlite3.connect(
        database_path
    )

    try:
        connection.executescript(
            SCHEMA.read_text(
                encoding="utf-8"
            )
        )

        product_ids: dict[
            tuple[str, str, str],
            int,
        ] = {}

        for record in records:
            retailer = (
                str(record.get("retailer") or "")
            )

            if not retailer:
                continue

            key = product_key(record)

            existing = product_ids.get(key)

            if existing is None:
                cursor = connection.execute(
                    """
                    INSERT INTO products (
                        retailer,
                        sku,
                        gtin,
                        product_name,
                        brand,
                        source_url,
                        source_name
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT DO NOTHING
                    """,
                    (
                        retailer,
                        record.get("sku"),
                        record.get("gtin"),
                        record.get("product_name"),
                        record.get("brand"),
                        record.get("source_url"),
                        record.get("source_name"),
                    ),
                )

                if cursor.lastrowid:
                    product_id = cursor.lastrowid
                else:
                    cursor = connection.execute(
                        """
                        SELECT id
                        FROM products
                        WHERE retailer = ?
                          AND (
                              (sku IS NOT NULL AND sku = ?)
                              OR
                              (gtin IS NOT NULL AND gtin = ?)
                          )
                        LIMIT 1
                        """,
                        (
                            retailer,
                            record.get("sku"),
                            record.get("gtin"),
                        ),
                    )

                    row = cursor.fetchone()

                    if row is None:
                        continue

                    product_id = int(row[0])

                product_ids[key] = product_id

            else:
                product_id = existing

            connection.execute(
                """
                INSERT INTO observations (
                    product_id,
                    observed_at,
                    price,
                    currency,
                    availability,
                    source_url,
                    source_name,
                    raw_data
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    product_id,
                    record.get("observed_at"),
                    record.get("price"),
                    record.get("currency"),
                    record.get("availability"),
                    record.get("source_url"),
                    record.get("source_name"),
                    json.dumps(
                        record,
                        ensure_ascii=False,
                    ),
                ),
            )

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()

    print(
        f"Loaded {len(records)} normalized records"
    )
    print(
        f"Database: {database_path}"
    )

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Load normalized grocery observations "
            "into SQLite."
        )
    )

    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
    )

    parser.add_argument(
        "--database",
        type=Path,
        default=DEFAULT_DATABASE,
    )

    args = parser.parse_args()

    return load(
        args.input,
        args.database,
    )


if __name__ == "__main__":
    raise SystemExit(main())

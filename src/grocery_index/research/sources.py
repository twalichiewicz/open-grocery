from __future__ import annotations

import csv
from pathlib import Path

from .schemas import Source


def load_sources(path: str | Path) -> list[Source]:
    """Load source definitions from a CSV file."""

    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"Source file not found: {path}")

    sources: list[Source] = []

    with path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)

        required_columns = {
            "retailer",
            "source_url",
            "source_type",
        }

        if reader.fieldnames is None:
            raise ValueError("Source CSV has no header row")

        missing = required_columns - set(reader.fieldnames)

        if missing:
            raise ValueError(
                f"Source CSV is missing required columns: {sorted(missing)}"
            )

        for row_number, row in enumerate(reader, start=2):
            try:
                enabled_value = row.get("enabled", "true").strip().lower()

                if enabled_value in {"true", "1", "yes", "y"}:
                    enabled = True
                elif enabled_value in {"false", "0", "no", "n"}:
                    enabled = False
                else:
                    raise ValueError(
                        f"Invalid enabled value: {enabled_value!r}"
                    )

                sources.append(
                    Source(
                        retailer=row["retailer"].strip(),
                        source_url=row["source_url"].strip(),
                        source_type=row["source_type"].strip(),
                        name=_optional_value(row.get("name")),
                        notes=_optional_value(row.get("notes")),
                        enabled=enabled,
                    )
                )

            except (KeyError, ValueError) as exc:
                raise ValueError(
                    f"Invalid source on CSV row {row_number}: {exc}"
                ) from exc

    return sources


def _optional_value(value: str | None) -> str | None:
    """Convert blank CSV values to None."""

    if value is None:
        return None

    value = value.strip()

    return value or None

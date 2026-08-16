from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import requests


DEFAULT_INPUT = Path("data/sources.csv")
DEFAULT_OUTPUT = Path("data/raw")

TIMEOUT = 30

HEADERS = {
    "User-Agent": (
        "open-grocery/0.1 "
        "(open grocery data research; contact project maintainers)"
    ),
    "Accept": "text/html,application/json;q=0.9,*/*;q=0.8",
}


def load_sources(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def source_is_eligible(row: dict[str, str]) -> bool:
    url = (row.get("url") or "").strip()
    status = (row.get("status") or "").strip().lower()
    method = (row.get("http_method") or "GET").strip().upper()

    return bool(url) and status in {"candidate", "verified"} and method == "GET"


def safe_name(value: str) -> str:
    value = value.strip().lower()
    return "".join(
        character if character.isalnum() or character in "-_" else "_"
        for character in value
    ).strip("_")


def response_filename(
    retailer: str,
    source_name: str,
    url: str,
) -> str:
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:12]

    retailer_part = safe_name(retailer) or "unknown"
    source_part = safe_name(source_name) or "source"

    return f"{retailer_part}__{source_part}__{digest}"


def fetch_source(row: dict[str, str]) -> tuple[requests.Response, float]:
    started = datetime.now(timezone.utc)

    response = requests.get(
        row["url"],
        headers=HEADERS,
        timeout=TIMEOUT,
        allow_redirects=True,
    )

    elapsed = (
        datetime.now(timezone.utc) - started
    ).total_seconds()

    return response, elapsed


def save_response(
    output_dir: Path,
    row: dict[str, str],
    response: requests.Response,
    elapsed: float,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)

    stem = response_filename(
        row.get("retailer", ""),
        row.get("source_name", ""),
        row["url"],
    )

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    metadata = {
        "retailer": row.get("retailer", ""),
        "source_name": row.get("source_name", ""),
        "source_type": row.get("source_type", ""),
        "url": row["url"],
        "requested_url": row["url"],
        "final_url": str(response.url),
        "http_method": row.get("http_method", "GET"),
        "status_code": response.status_code,
        "content_type": response.headers.get("content-type", ""),
        "elapsed_seconds": elapsed,
        "collected_at": timestamp,
    }

    suffix = ".html"

    content_type = response.headers.get("content-type", "").lower()

    if "json" in content_type:
        suffix = ".json"

    body_path = output_dir / f"{stem}__{timestamp}{suffix}"
    metadata_path = output_dir / f"{stem}__{timestamp}.metadata.json"

    body_path.write_bytes(response.content)

    metadata_path.write_text(
        json.dumps(metadata, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return body_path


def collect(
    input_path: Path,
    output_dir: Path,
) -> int:
    sources = load_sources(input_path)

    eligible = [
        row
        for row in sources
        if source_is_eligible(row)
    ]

    print(f"Loaded {len(sources)} sources")
    print(f"Eligible sources: {len(eligible)}")

    successful = 0

    for index, row in enumerate(eligible, start=1):
        retailer = row.get("retailer", "")
        source_name = row.get("source_name", "")
        url = row.get("url", "")

        print(
            f"[{index}/{len(eligible)}] "
            f"{retailer} / {source_name}"
        )
        print(f"  GET {url}")

        try:
            response, elapsed = fetch_source(row)

            path = save_response(
                output_dir,
                row,
                response,
                elapsed,
            )

            print(
                f"  {response.status_code} "
                f"({elapsed:.2f}s) -> {path}"
            )

            successful += 1

        except requests.RequestException as exc:
            print(f"  ERROR: {exc}")

    print(
        f"Completed: {successful}/{len(eligible)} successful"
    )

    return 0 if successful == len(eligible) else 1


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Collect raw responses from registered grocery sources."
    )

    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
    )

    args = parser.parse_args()

    return collect(args.input, args.output)


if __name__ == "__main__":
    raise SystemExit(main())

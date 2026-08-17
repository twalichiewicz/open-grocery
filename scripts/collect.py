from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests


DEFAULT_INPUT = Path("data/sources_discovered.csv")
DEFAULT_OUTPUT = Path("data/raw")

TIMEOUT = 30

HEADERS = {
    "User-Agent": (
        "open-grocery/0.1 "
        "(open grocery data research; contact project maintainers)"
    ),
    "Accept": "text/html,application/json;q=0.9,*/*;q=0.8",
}

SUCCESS_STATUS_CODES = set(range(200, 300))

PRODUCT_SOURCE_TYPES = {
    "product",
    "product_search",
    "product_catalog",
}

BLOCKING_PAGE_MARKERS = (
    "captcha",
    "verify you are human",
    "access denied",
    "unusual traffic",
    "enable javascript",
)

STORE_LOCATOR_MARKERS = (
    "find a location",
    "find a store",
    "store locator",
    "search by zip code",
    "city, state",
)


def load_sources(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)

        if reader.fieldnames is None:
            raise ValueError(f"{path} does not contain a CSV header")

        return list(reader)


def source_is_eligible(row: dict[str, str]) -> bool:
    url = (row.get("url") or "").strip()
    status = (row.get("status") or "").strip().lower()
    method = (row.get("http_method") or "GET").strip().upper()

    return (
        bool(url)
        and status in {"candidate", "verified"}
        and method == "GET"
    )


def safe_name(value: str) -> str:
    value = value.strip().lower()

    return "".join(
        character
        if character.isalnum() or character in "-_"
        else "_"
        for character in value
    ).strip("_")


def response_filename(
    retailer: str,
    source_name: str,
    url: str,
) -> str:
    digest = hashlib.sha256(
        url.encode("utf-8")
    ).hexdigest()[:12]

    retailer_part = safe_name(retailer) or "unknown"
    source_part = safe_name(source_name) or "source"

    return f"{retailer_part}__{source_part}__{digest}"


def fetch_source(
    row: dict[str, str],
) -> tuple[requests.Response, float]:
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


def response_suffix(response: requests.Response) -> str:
    content_type = response.headers.get(
        "content-type",
        "",
    ).lower()

    if "json" in content_type:
        return ".json"

    if "html" in content_type:
        return ".html"

    return ".bin"


def _response_text(response: requests.Response) -> str:
    content_type = response.headers.get(
        "content-type",
        "",
    ).lower()

    if "json" in content_type:
        return response.text

    return response.text


def _looks_like_block_page(text: str) -> bool:
    lowered = text.lower()

    return any(
        marker in lowered
        for marker in BLOCKING_PAGE_MARKERS
    )


def _looks_like_store_locator(text: str) -> bool:
    lowered = text.lower()

    matches = sum(
        marker in lowered
        for marker in STORE_LOCATOR_MARKERS
    )

    return matches >= 2


def classify_response(
    row: dict[str, str],
    response: requests.Response,
) -> tuple[str, str | None]:
    """
    Classify a response without pretending that HTTP 200 means
    successful product collection.

    The classifier is intentionally conservative. It only rejects
    obvious failures and obvious store-locator pages. Absence of
    product data is ultimately determined by the parser.
    """

    if response.status_code not in SUCCESS_STATUS_CODES:
        return (
            "http_error",
            f"HTTP {response.status_code}",
        )

    text = _response_text(response)

    if _looks_like_block_page(text):
        return (
            "blocked",
            "Response appears to be an access-control/block page",
        )

    source_type = (
        row.get("source_type") or ""
    ).strip().lower()

    if (
        source_type in PRODUCT_SOURCE_TYPES
        and _looks_like_store_locator(text)
    ):
        return (
            "wrong_source",
            "Product source returned a store-locator page",
        )

    return "success", None


def save_response(
    output_dir: Path,
    row: dict[str, str],
    response: requests.Response,
    elapsed: float,
    *,
    collection_status: str,
    collection_error: str | None,
) -> Path:
    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    stem = response_filename(
        row.get("retailer", ""),
        row.get("source_name", ""),
        row["url"],
    )

    timestamp = datetime.now(
        timezone.utc
    ).strftime("%Y%m%dT%H%M%SZ")

    metadata = {
        "source_id": row.get("source_id", ""),
        "retailer": row.get("retailer", ""),
        "source_name": row.get("source_name", ""),
        "source_type": row.get("source_type", ""),
        "url": row["url"],
        "requested_url": row["url"],
        "final_url": str(response.url),
        "http_method": row.get(
            "http_method",
            "GET",
        ),
        "status_code": response.status_code,
        "content_type": response.headers.get(
            "content-type",
            "",
        ),
        "elapsed_seconds": elapsed,
        "collected_at": timestamp,
        "collection_status": collection_status,
        "collection_error": collection_error,
    }

    suffix = response_suffix(response)

    body_path = (
        output_dir
        / f"{stem}__{timestamp}{suffix}"
    )

    metadata_path = (
        output_dir
        / f"{stem}__{timestamp}.metadata.json"
    )

    body_path.write_bytes(response.content)

    metadata_path.write_text(
        json.dumps(
            metadata,
            indent=2,
            sort_keys=True,
        ),
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
    failed = 0

    for index, row in enumerate(
        eligible,
        start=1,
    ):
        retailer = row.get(
            "retailer",
            "",
        )

        source_name = row.get(
            "source_name",
            "",
        )

        url = row.get(
            "url",
            "",
        )

        print(
            f"[{index}/{len(eligible)}] "
            f"{retailer} / {source_name}"
        )

        print(f"  GET {url}")

        try:
            response, elapsed = fetch_source(row)

            status, error = classify_response(
                row,
                response,
            )

            path = save_response(
                output_dir,
                row,
                response,
                elapsed,
                collection_status=status,
                collection_error=error,
            )

            print(
                f"  {response.status_code} "
                f"({elapsed:.2f}s) -> {path}"
            )

            if status == "success":
                successful += 1
            else:
                failed += 1
                print(
                    f"  {status.upper()}: {error}"
                )

        except requests.RequestException as exc:
            failed += 1
            print(f"  ERROR: {exc}")

    print()
    print(
        f"Completed: {successful}/{len(eligible)} "
        f"successful, {failed} failed"
    )

    return 0 if failed == 0 else 1


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Collect raw responses from "
            "registered grocery sources."
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
        help="Output directory for raw responses.",
    )

    args = parser.parse_args()

    return collect(
        args.input,
        args.output,
    )


if __name__ == "__main__":
    raise SystemExit(main())

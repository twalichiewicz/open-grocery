from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]

sys.path.insert(0, str(ROOT))

from normalize.products import normalize_products
from parsers.common import extract_products as extract_jsonld_products
from parsers.embedded_json import extract_embedded_products
from parsers.html import (
    extract_html_products,
    extract_json_scripts_with_ids,
)


DEFAULT_RAW_DIR = ROOT / "data" / "raw"
DEFAULT_OUTPUT = (
    ROOT
    / "data"
    / "normalized"
    / "products.jsonl"
)


def decode_json_script(
    content: str,
) -> str | None:
    """
    Return valid JSON text from an embedded script.

    Raw text is attempted first. URL-decoded text is accepted only if it
    parses as JSON.
    """
    candidates = [content]

    decoded = unquote(
        content
    )

    if decoded != content:
        candidates.append(
            decoded
        )

    for candidate in candidates:
        try:
            json.loads(
                candidate
            )
        except (
            json.JSONDecodeError,
            TypeError,
        ):
            continue

        return candidate

    return None


def load_source_metadata(
    path: Path,
) -> dict[str, str]:
    metadata_path = path.with_suffix(
        ".metadata.json"
    )

    try:
        metadata = json.loads(
            metadata_path.read_text(
                encoding="utf-8"
            )
        )
    except (
        OSError,
        json.JSONDecodeError,
    ):
        return {
            "source_url": "",
            "retailer": "",
            "observed_at": "",
            "source_name": "",
        }

    return {
        "source_url": str(
            metadata.get("final_url")
            or metadata.get("url")
            or ""
        ),
        "retailer": str(
            metadata.get("retailer")
            or ""
        ),
        "observed_at": str(
            metadata.get("collected_at")
            or ""
        ),
        "source_name": str(
            metadata.get("source_name")
            or ""
        ),
    }


def stamp_metadata(
    products: list[dict[str, Any]],
    metadata: dict[str, str],
) -> list[dict[str, Any]]:
    for product in products:
        product["retailer"] = (
            metadata["retailer"]
        )
        product["observed_at"] = (
            metadata["observed_at"]
        )
        product["source_name"] = (
            metadata["source_name"]
        )

    return products


def parse_html_file(
    path: Path,
) -> tuple[
    list[dict[str, Any]],
    dict[str, Any],
]:
    html = path.read_bytes()

    metadata = load_source_metadata(
        path
    )

    source_url = metadata[
        "source_url"
    ]

    products: list[
        dict[str, Any]
    ] = []

    stats: dict[str, Any] = {
        "file": str(path),
        "json_scripts": 0,
        "json_scripts_parsed": 0,
        "json_objects": 0,
        "jsonld_products": 0,
        "html_products": 0,
        "product_like_objects": 0,
        "script_ids": [],
    }

    # JSON-LD.
    jsonld_products = (
        extract_jsonld_products(
            html,
            source_url,
        )
    )

    stamp_metadata(
        jsonld_products,
        metadata,
    )

    products.extend(
        jsonld_products
    )

    stats["jsonld_products"] = (
        len(jsonld_products)
    )

    # HTML/meta extraction.
    html_products = (
        extract_html_products(
            html,
            source_url=source_url,
        )
    )

    stamp_metadata(
        html_products,
        metadata,
    )

    products.extend(
        html_products
    )

    stats["html_products"] = (
        len(html_products)
    )

    # Embedded application JSON.
    scripts = (
        extract_json_scripts_with_ids(
            html
        )
    )

    stats["json_scripts"] = len(
        scripts
    )

    json_texts: list[str] = []

    for script in scripts:
        script_id = script["id"]

        if script_id:
            stats[
                "script_ids"
            ].append(
                script_id
            )

        # JSON-LD has its own parser.
        if (
            script["type"]
            == "application/ld+json"
        ):
            continue

        json_text = (
            decode_json_script(
                script["content"]
            )
        )

        if json_text is None:
            continue

        stats[
            "json_scripts_parsed"
        ] += 1

        stats[
            "json_objects"
        ] += 1

        json_texts.append(
            json_text
        )

    if json_texts:
        embedded_products = (
            extract_embedded_products(
                json_texts,
                source_url,
            )
        )

        stamp_metadata(
            embedded_products,
            metadata,
        )

        products.extend(
            embedded_products
        )

        stats[
            "product_like_objects"
        ] = len(
            embedded_products
        )

    return (
        products,
        stats,
    )


def parse_json_file(
    path: Path,
) -> tuple[
    list[dict[str, Any]],
    dict[str, Any],
]:
    metadata = load_source_metadata(
        path
    )

    try:
        document = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )
    except (
        OSError,
        UnicodeDecodeError,
        json.JSONDecodeError,
    ) as exc:
        raise ValueError(
            f"Unable to parse JSON capture "
            f"{path}: {exc}"
        ) from exc

    source_url = metadata[
        "source_url"
    ]

    products = (
        extract_embedded_products(
            [json.dumps(document)],
            source_url,
        )
    )

    stamp_metadata(
        products,
        metadata,
    )

    return (
        products,
        {
            "file": str(path),
            "json_scripts": 1,
            "json_scripts_parsed": 1,
            "json_objects": 1,
            "jsonld_products": 0,
            "html_products": 0,
            "product_like_objects": len(
                products
            ),
            "script_ids": [],
        },
    )


def parse_raw_file(
    path: Path,
) -> tuple[
    list[dict[str, Any]],
    dict[str, Any],
]:
    if path.suffix.lower() == ".json":
        return parse_json_file(
            path
        )

    return parse_html_file(
        path
    )


def discover_raw_files(
    raw_dir: Path,
    pattern: str | None = None,
) -> list[Path]:
    if not raw_dir.exists():
        return []

    if pattern:
        files = list(
            raw_dir.glob(
                pattern
            )
        )
    else:
        files = [
            *raw_dir.glob("*.html"),
            *raw_dir.glob("*.htm"),
            *raw_dir.glob("*.json"),
        ]

    files = [
        path
        for path in files
        if (
            path.is_file()
            and not path.name.endswith(
                ".metadata.json"
            )
        )
    ]

    # Newest capture first. dedupe_products() retains the first occurrence.
    return sorted(
        files,
        reverse=True,
    )


def dedupe_products(
    products: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Deduplicate normalized products.

    Priority:
      1. GTIN
      2. SKU + retailer
      3. retailer + source URL + product name
    """
    seen: set[
        tuple[Any, ...]
    ] = set()

    results: list[
        dict[str, Any]
    ] = []

    for product in products:
        gtin = product.get(
            "gtin"
        )

        sku = product.get(
            "sku"
        )

        retailer = product.get(
            "retailer"
        )

        source_url = product.get(
            "source_url"
        )

        product_name = product.get(
            "product_name"
        )

        if gtin:
            key = (
                "gtin",
                gtin,
            )

        elif sku:
            key = (
                "sku",
                retailer,
                sku,
            )

        else:
            key = (
                "fallback",
                retailer,
                source_url,
                product_name,
            )

        if key in seen:
            continue

        seen.add(
            key
        )

        results.append(
            product
        )

    return results


def write_jsonl(
    path: Path,
    products: list[dict[str, Any]],
) -> None:
    """
    Atomically replace the output JSONL.
    """
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fd, temporary_name = (
        tempfile.mkstemp(
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
        )
    )

    temporary_path = Path(
        temporary_name
    )

    try:
        with os.fdopen(
            fd,
            "w",
            encoding="utf-8",
        ) as handle:
            for product in products:
                handle.write(
                    json.dumps(
                        product,
                        ensure_ascii=False,
                    )
                    + "\n"
                )

            handle.flush()
            os.fsync(
                handle.fileno()
            )

        os.replace(
            temporary_path,
            path,
        )

    except Exception:
        try:
            temporary_path.unlink()
        except FileNotFoundError:
            pass

        raise


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Parse raw grocery retailer captures "
            "into normalized product records."
        )
    )

    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=DEFAULT_RAW_DIR,
        help="Directory containing raw captures.",
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Output JSONL path.",
    )

    parser.add_argument(
        "--pattern",
        default=None,
        help=(
            "Optional glob pattern, e.g. "
            "'target__*.html'."
        ),
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print detailed parser statistics.",
    )

    args = parser.parse_args()

    raw_dir = (
        args.raw_dir
        if args.raw_dir.is_absolute()
        else ROOT / args.raw_dir
    )

    output = (
        args.output
        if args.output.is_absolute()
        else ROOT / args.output
    )

    files = discover_raw_files(
        raw_dir,
        args.pattern,
    )

    if not files:
        print(
            f"No raw captures found in {raw_dir}",
            file=sys.stderr,
        )
        return 1

    all_products: list[
        dict[str, Any]
    ] = []

    errors = 0

    print("=" * 80)
    print("OPEN GROCERY PARSER")
    print("=" * 80)
    print(
        f"raw directory: {raw_dir}"
    )
    print(
        f"files found:   {len(files)}"
    )
    print()

    for path in files:
        try:
            products, stats = (
                parse_raw_file(path)
            )

        except Exception as exc:
            errors += 1

            print(
                f"ERROR: {path.name}: {exc}",
                file=sys.stderr,
            )
            continue

        all_products.extend(
            products
        )

        print(path.name)
        print(
            "-" * len(path.name)
        )

        print(
            f"  JSON scripts:       "
            f"{stats['json_scripts']}"
        )

        print(
            f"  JSON parsed:        "
            f"{stats['json_scripts_parsed']}"
        )

        print(
            f"  JSON-LD products:   "
            f"{stats['jsonld_products']}"
        )

        print(
            f"  HTML products:      "
            f"{stats['html_products']}"
        )

        print(
            f"  embedded products:  "
            f"{stats['product_like_objects']}"
        )

        if stats["script_ids"]:
            print(
                "  script IDs:         "
                + ", ".join(
                    stats["script_ids"]
                )
            )

        if args.verbose:
            print(
                f"  raw product records: "
                f"{len(products)}"
            )

        print()

    if errors:
        print(
            f"ERROR: {errors} of {len(files)} "
            "files failed; output was not replaced.",
            file=sys.stderr,
        )
        return 1

    normalized = normalize_products(
        all_products
    )

    normalized = dedupe_products(
        normalized
    )

    if not normalized:
        print(
            "ERROR: parser produced zero normalized "
            "products; output was not replaced.",
            file=sys.stderr,
        )
        return 1

    write_jsonl(
        output,
        normalized,
    )

    print("=" * 80)
    print("DONE")
    print("=" * 80)

    print(
        f"raw records:        "
        f"{len(all_products)}"
    )

    print(
        f"normalized records: "
        f"{len(normalized)}"
    )

    print(
        f"output:             "
        f"{output}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )

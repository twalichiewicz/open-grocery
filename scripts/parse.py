from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any
from urllib.parse import unquote

# Allow running directly from the repository root:
# python3 scripts/parse.py
ROOT = Path(__file__).resolve().parents[1]

sys.path.insert(0, str(ROOT))

from parsers.embedded_json import extract_embedded_products
from parsers.html import (
    extract_html_products,
    extract_json_scripts_with_ids,
)
from parsers.jsonld import extract_jsonld
from normalize.products import normalize_products


DEFAULT_RAW_DIR = ROOT / "data" / "raw"
DEFAULT_OUTPUT = ROOT / "data" / "normalized" / "products.jsonl"


def decode_json_script(
    content: str,
    *,
    url_decode: bool = False,
) -> str | None:
    """
    Return the JSON text of an embedded script, or None if unparseable.

    Some retailers embed URL-encoded JSON, so an optional second attempt
    is made after urllib.parse.unquote(). The decoded text (not the
    parsed object) is returned because downstream parsers own parsing.
    """
    candidates = [content]

    if url_decode:
        decoded = unquote(content)

        if decoded != content:
            candidates.append(decoded)

    for candidate in candidates:
        try:
            json.loads(candidate)
        except (json.JSONDecodeError, TypeError):
            continue

        return candidate

    return None


def load_source_url(path: Path) -> str:
    """
    Read the capture URL from the fetcher's metadata sidecar, if present.
    """
    metadata_path = path.with_suffix(".metadata.json")

    try:
        metadata = json.loads(
            metadata_path.read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError):
        return ""

    url = metadata.get("final_url") or metadata.get("url")

    return url if isinstance(url, str) else ""


def parse_html_file(
    path: Path,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """
    Parse one raw HTML file using all currently supported strategies.
    """
    html = path.read_bytes()
    source_url = load_source_url(path)

    products: list[dict[str, Any]] = []

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

    # ---------------------------------------------------------------
    # JSON-LD
    # ---------------------------------------------------------------

    jsonld_products = extract_jsonld(html)

    if jsonld_products:
        products.extend(jsonld_products)
        stats["jsonld_products"] = len(jsonld_products)

    # ---------------------------------------------------------------
    # Ordinary HTML metadata
    # ---------------------------------------------------------------

    html_products = extract_html_products(
        html,
        source_url=source_url,
    )

    if html_products:
        products.extend(html_products)
        stats["html_products"] = len(html_products)

    # ---------------------------------------------------------------
    # Embedded application JSON
    # ---------------------------------------------------------------

    scripts = extract_json_scripts_with_ids(html)

    stats["json_scripts"] = len(scripts)

    for script in scripts:
        script_id = script["id"]

        if script_id:
            stats["script_ids"].append(script_id)

        json_text = decode_json_script(
            script["content"],
            url_decode=(script_id == "node-apollo-state"),
        )

        if json_text is None:
            continue

        stats["json_scripts_parsed"] += 1
        stats["json_objects"] += 1

        embedded_products = extract_embedded_products(
            [json_text],
            source_url,
        )

        if embedded_products:
            products.extend(embedded_products)
            stats["product_like_objects"] += len(embedded_products)

    return products, stats


def discover_raw_files(
    raw_dir: Path,
    pattern: str | None = None,
) -> list[Path]:
    if not raw_dir.exists():
        return []

    if pattern:
        files = list(raw_dir.glob(pattern))
    else:
        files = [
            *raw_dir.glob("*.html"),
            *raw_dir.glob("*.htm"),
        ]

    return sorted(
        path
        for path in files
        if path.is_file()
    )


def dedupe_products(
    products: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Deduplicate parsed products without throwing away distinct products
    that happen to share a name.

    Prefer GTIN, then SKU + retailer, then source URL + product name.
    """
    seen: set[tuple[Any, ...]] = set()
    results: list[dict[str, Any]] = []

    for product in products:
        gtin = product.get("gtin")
        sku = product.get("sku")
        retailer = product.get("retailer")
        source_url = product.get("source_url")
        product_name = product.get("product_name")

        if gtin:
            key = ("gtin", gtin)
        elif sku:
            key = ("sku", retailer, sku)
        else:
            key = ("fallback", source_url, product_name)

        if key in seen:
            continue

        seen.add(key)
        results.append(product)

    return results


def write_jsonl(
    path: Path,
    products: list[dict[str, Any]],
) -> None:
    """
    Atomically replace the output JSONL.

    The existing file is left untouched unless the complete new file has
    been successfully written.
    """
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fd, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
    )

    temporary_path = Path(temporary_name)

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
                        default=str,
                    )
                    + "\n"
                )

            handle.flush()
            os.fsync(handle.fileno())

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
        description="Parse raw grocery retailer HTML into normalized product records."
    )

    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=DEFAULT_RAW_DIR,
        help="Directory containing raw HTML files.",
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
        help="Optional glob pattern, e.g. 'target__*.html'.",
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
            f"No HTML files found in {raw_dir}",
            file=sys.stderr,
        )
        return 1

    all_products: list[dict[str, Any]] = []
    errors = 0

    print("=" * 80)
    print("OPEN GROCERY PARSER")
    print("=" * 80)
    print(f"raw directory: {raw_dir}")
    print(f"files found:   {len(files)}")
    print()

    for path in files:
        try:
            products, stats = parse_html_file(path)

        except Exception as exc:
            errors += 1

            print(
                f"ERROR: {path.name}: {exc}",
                file=sys.stderr,
            )
            continue

        all_products.extend(products)

        print(path.name)
        print("-" * len(path.name))
        print(f"  JSON scripts:       {stats['json_scripts']}")
        print(f"  JSON parsed:        {stats['json_scripts_parsed']}")
        print(f"  JSON-LD products:   {stats['jsonld_products']}")
        print(f"  HTML products:      {stats['html_products']}")
        print(f"  embedded products:  {stats['product_like_objects']}")

        if stats["script_ids"]:
            print(
                "  script IDs:         "
                + ", ".join(stats["script_ids"])
            )

        if args.verbose:
            print(f"  raw product records: {len(products)}")

        print()

    if errors:
        print(
            f"ERROR: {errors} of {len(files)} files failed; "
            "output was not replaced.",
            file=sys.stderr,
        )
        return 1

    # ---------------------------------------------------------------
    # Normalize
    # ---------------------------------------------------------------

    normalized = normalize_products(all_products)
    normalized = dedupe_products(normalized)

    write_jsonl(
        output,
        normalized,
    )

    print("=" * 80)
    print("DONE")
    print("=" * 80)
    print(f"raw records:        {len(all_products)}")
    print(f"normalized records: {len(normalized)}")
    print(f"output:             {output}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

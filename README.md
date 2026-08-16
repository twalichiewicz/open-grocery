# open-grocery

An open grocery price and store data collection project. It discovers retailer
data sources, captures raw HTML, parses product records out of embedded page
data, and normalizes everything into a common schema for analysis.

## Pipeline

```
discover sources → collect raw HTML → parse products → normalize → load
```

Each stage is a standalone script:

```bash
python3 scripts/discover_sources.py   # evaluate retailer sources → data/sources_discovered.csv
python3 scripts/collect.py            # fetch raw HTML → data/raw/ (+ .metadata.json sidecars)
python3 scripts/parse.py              # extract products → data/normalized/products.jsonl
python3 scripts/validate.py           # sanity-check output
python3 db/load.py                    # persist to database (schema in db/schema.sql)
```

`parse.py` tries three extraction strategies per page, in order of reliability:

1. **JSON-LD** (`application/ld+json` scripts)
2. **HTML metadata** (Open Graph / product meta tags)
3. **Embedded application JSON** (`__NEXT_DATA__`, `__APOLLO_STATE__`,
   `node-apollo-state`, and generic `application/json` scripts)

Every raw capture in `data/raw/` has a `.metadata.json` sidecar recording the
source URL, retailer, timestamp, and HTTP details; the parser uses it to stamp
each record with its `source_url`.

## Getting started

Requires Python 3.11+.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Run the tests:

```bash
python3 -m pytest
```

## Repository layout

```
config/           retailers.yaml — which retailers and source types are enabled
scripts/          entry points (discover, collect, parse, validate)
src/grocery_index/
  research/       source discovery, site inspection, robots.txt handling
  collectors/     per-retailer collectors sharing the base.py interface
  models/         Product, Store, Price, Observation
parsers/          HTML / JSON-LD / embedded-JSON extraction
normalize/        normalization into the common product record
db/               schema.sql and loader
data/             raw captures and normalized output (not tracked)
tests/            pytest suite
```

## Output format

`data/normalized/products.jsonl` — one JSON record per line:

```json
{
  "source_url": "https://www.aldi.us/store/aldi/pages/dairy-and-eggs",
  "product_name": "Friendly Farms Whole Milk",
  "brand": "friendly farms",
  "gtin": null,
  "sku": "16902710",
  "price": "4.05",
  "currency": "USD",
  "availability": "in_stock"
}
```

Records are deduplicated by the strongest available identity: GTIN, then
SKU + retailer, then source URL + product name.

## Data collection notes

Collection is for open research. The collectors identify themselves with a
descriptive User-Agent, respect robots.txt, and only fetch publicly available
pages.

## License

- **Code**: [GNU Affero General Public License v3.0](LICENSE) — if you run a
  modified version of the collectors or parsers as a network service, you must
  share your changes.
- **Data**: [Open Database License v1.0](DATA_LICENSE) — datasets built from
  this project's data must remain open under the same terms.

Copyright (c) 2026 Thomas Walichiewicz
([@twalichiewicz](https://github.com/twalichiewicz) · [thomas.design](https://thomas.design))

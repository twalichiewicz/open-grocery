# open-grocery

## Structure
### `research/`
Discovers and evaluates sources.

Produces:
```
data/sources.csv
data/retailer_matrix.csv
```

### `collectors/`
Data acquisition layer.

Every retailer collector implements the same interface defined by `base.py`.

_These will be the adapters._

### `models/`
What our data means, independent of where it came from.

Examples:
```
Product
Store
Price
Promotion
Availability
Observation
```

### `normalization/`
Converts retailer-specific data into common representation.

Example:
```
"Walmart: Great Value Whole Milk, 1 gal"
               ↓
          Product model
               ↓
       128 fl oz / gallon
```

### `storage/`
Database persistence.

Collectors shouldn't know whether we're using PostgreSQL, SQLite, Parquet, etc.

They produce records. 

Storage decides how those records are persisted.

### `geo/`
```
          "San Diego"
               ↓
          Geographic area
               ↓
          nearby stores
               ↓
            distance
               ↓
        price comparison
```

Separate from the collectors.

### `scripts/`
Entry points, not application logic.

```
python3 scripts/discover_sources.py
python3 scripts/inspect_retailer.py
python3 scripts/collect.py
python3 scripts/normalize.py
python3 scripts/load_database.py
```

Scripts call code under `src/grocery_index/`.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY,

    retailer TEXT NOT NULL,
    sku TEXT,
    gtin TEXT,

    product_name TEXT NOT NULL,
    brand TEXT,

    source_url TEXT,
    source_name TEXT,

    UNIQUE (retailer, sku),
    UNIQUE (retailer, gtin)
);

CREATE TABLE IF NOT EXISTS observations (
    id INTEGER PRIMARY KEY,

    product_id INTEGER NOT NULL,

    observed_at TEXT NOT NULL,

    store_id TEXT,

    price NUMERIC,
    currency TEXT,
    availability TEXT,

    source_url TEXT,
    source_name TEXT,

    raw_data TEXT,

    FOREIGN KEY (product_id)
        REFERENCES products(id)
);

CREATE INDEX IF NOT EXISTS idx_observations_product_time
ON observations (
    product_id,
    observed_at
);

CREATE INDEX IF NOT EXISTS idx_observations_retailer_time
ON observations (
    observed_at
);

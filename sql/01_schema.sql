-- Star schema for the Supplier & Inventory Performance Dashboard (SQLite dialect)
-- Grain:
--   fact_po_line          one row per purchase order line
--   fact_inventory_daily  one row per SKU, per location, per day (closing position)

DROP TABLE IF EXISTS fact_po_line;
DROP TABLE IF EXISTS fact_inventory_daily;
DROP TABLE IF EXISTS dim_date;
DROP TABLE IF EXISTS dim_location;
DROP TABLE IF EXISTS dim_supplier;
DROP TABLE IF EXISTS dim_product;

CREATE TABLE dim_date (
    date_key     INTEGER PRIMARY KEY,      -- yyyymmdd
    date         TEXT NOT NULL,
    year         INTEGER,
    month        INTEGER,
    month_name   TEXT,
    year_month   TEXT,
    iso_week     INTEGER,
    weekday      TEXT
);

CREATE TABLE dim_location (
    location_id   TEXT PRIMARY KEY,
    location_name TEXT NOT NULL,
    region        TEXT
);

CREATE TABLE dim_supplier (
    supplier_id              TEXT PRIMARY KEY,
    supplier_name            TEXT NOT NULL,
    category                 TEXT,
    promised_lead_time_days  INTEGER
);

CREATE TABLE dim_product (
    sku             TEXT PRIMARY KEY,
    product_name    TEXT,
    category        TEXT,
    supplier_id     TEXT REFERENCES dim_supplier(supplier_id),
    unit_cost_gbp   REAL,
    abc_class       TEXT CHECK (abc_class IN ('A','B','C')),
    min_cover_days  INTEGER,   -- below this = at risk
    max_cover_days  INTEGER    -- above this = excess
);

CREATE TABLE fact_po_line (
    po_number      TEXT,
    po_line        INTEGER,
    supplier_id    TEXT REFERENCES dim_supplier(supplier_id),
    sku            TEXT REFERENCES dim_product(sku),
    location_id    TEXT REFERENCES dim_location(location_id),
    order_date     TEXT,
    promised_date  TEXT,
    received_date  TEXT,       -- NULL = still open at period end
    qty_ordered    INTEGER,
    qty_received   INTEGER,
    unit_cost_gbp  REAL,
    line_value_gbp REAL,
    PRIMARY KEY (po_number, po_line)
);

CREATE TABLE fact_inventory_daily (
    date_key              INTEGER REFERENCES dim_date(date_key),
    sku                   TEXT REFERENCES dim_product(sku),
    location_id           TEXT REFERENCES dim_location(location_id),
    opening_stock         INTEGER,
    demand_units          INTEGER,
    sales_units           INTEGER,
    lost_sales_units      INTEGER,
    closing_stock         INTEGER,
    forecast_daily_demand REAL,
    PRIMARY KEY (date_key, sku, location_id)
);

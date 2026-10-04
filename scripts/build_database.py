"""
Load the CSVs into a SQLite database, run every KPI query in sql/02_kpis.sql
and save each result to sql/results/<name>.csv.

Run:  python scripts/build_database.py
"""
from pathlib import Path
import re
import sqlite3
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "supplier_inventory.db"
RESULTS = ROOT / "sql" / "results"
RESULTS.mkdir(parents=True, exist_ok=True)

con = sqlite3.connect(DB)
con.executescript((ROOT / "sql" / "01_schema.sql").read_text())

for table in ["dim_date", "dim_location", "dim_supplier", "dim_product", "fact_po_line", "fact_inventory_daily"]:
    df = pd.read_csv(ROOT / "data" / f"{table}.csv")
    df.to_sql(table, con, if_exists="append", index=False)
    print(f"loaded {table:<22} {len(df):>7,} rows")

sql = (ROOT / "sql" / "02_kpis.sql").read_text()
blocks = re.split(r"^-- name: ", sql, flags=re.M)[1:]
for block in blocks:
    name, body = block.split("\n", 1)
    df = pd.read_sql_query(body, con)
    df.to_csv(RESULTS / f"{name.strip()}.csv", index=False)
    print(f"\n== {name.strip()}\n{df.to_string(index=False)}")

con.close()

"""
Generate the synthetic dataset for the Supplier & Inventory Performance Dashboard.

All data is SYNTHETIC. Company, supplier and product names are invented.
The simulation is deliberately causal: suppliers with poor delivery
reliability cause late or short receipts, which cause stockouts downstream.
That is the link the dashboard is designed to expose.

Run:  python scripts/generate_data.py
Output: data/*.csv (star schema: 4 dimensions, 2 facts)
"""
from pathlib import Path
import numpy as np
import pandas as pd

SEED = 2026
rng = np.random.default_rng(SEED)
OUT = Path(__file__).resolve().parents[1] / "data"
OUT.mkdir(exist_ok=True)

START, END = pd.Timestamp("2025-01-01"), pd.Timestamp("2025-12-31")
DATES = pd.date_range(START, END, freq="D")

# ---------------------------------------------------------------- dim_date
dim_date = pd.DataFrame({"date": DATES})
dim_date["date_key"] = dim_date["date"].dt.strftime("%Y%m%d").astype(int)
dim_date["year"] = dim_date["date"].dt.year
dim_date["month"] = dim_date["date"].dt.month
dim_date["month_name"] = dim_date["date"].dt.strftime("%b")
dim_date["year_month"] = dim_date["date"].dt.strftime("%Y-%m")
dim_date["iso_week"] = dim_date["date"].dt.isocalendar().week.astype(int)
dim_date["weekday"] = dim_date["date"].dt.day_name()
dim_date = dim_date[["date_key", "date", "year", "month", "month_name", "year_month", "iso_week", "weekday"]]

# ------------------------------------------------------------ dim_location
dim_location = pd.DataFrame({
    "location_id": ["L01", "L02", "L03"],
    "location_name": ["North West DC", "Midlands DC", "Scotland DC"],
    "region": ["North West", "Midlands", "Scotland"],
})
loc_scale = {"L01": 1.0, "L02": 0.8, "L03": 0.55}

# ------------------------------------------------------------ dim_supplier
# reliability profile: p_late, mean days late when late, p_short, fill when short
suppliers = [
    # id, name, category, p_late, late_mean, p_short, short_fill, promised_lt
    ("S01", "Supplier A", "Beverages",     0.04, 1.5, 0.02, 0.90, 7),
    ("S02", "Supplier B", "Beverages",     0.18, 3.0, 0.08, 0.80, 10),
    ("S03", "Supplier C", "Snacks",        0.05, 1.5, 0.03, 0.92, 7),
    ("S04", "Supplier D", "Snacks",        0.30, 5.0, 0.15, 0.70, 14),
    ("S05", "Supplier E", "Household",     0.06, 2.0, 0.03, 0.90, 10),
    ("S06", "Supplier F", "Household",     0.12, 2.5, 0.10, 0.85, 10),
    ("S07", "Supplier G", "Personal Care", 0.03, 1.0, 0.02, 0.95, 7),
    ("S08", "Supplier H", "Personal Care", 0.22, 4.0, 0.12, 0.75, 14),
]
dim_supplier = pd.DataFrame(suppliers, columns=[
    "supplier_id", "supplier_name", "category", "p_late", "late_mean_days",
    "p_short", "short_fill_rate", "promised_lead_time_days"])
sup_profile = dim_supplier.set_index("supplier_id")

# ------------------------------------------------------------- dim_product
CATS = {
    "Beverages": (["S01", "S02"], (0.9, 2.2)),
    "Snacks": (["S03", "S04"], (1.1, 2.8)),
    "Household": (["S05", "S06"], (1.8, 5.5)),
    "Personal Care": (["S07", "S08"], (1.5, 6.0)),
}
prod_rows = []
n = 1
for cat, (sups, (cmin, cmax)) in CATS.items():
    for i in range(10):
        sup = sups[i % 2]
        base = float(rng.choice([4, 8, 15, 30, 55], p=[.2, .25, .25, .2, .1]))  # units/day at L01
        prod_rows.append({
            "sku": f"SKU{n:03d}",
            "product_name": f"{cat} item {i + 1:02d}",
            "category": cat,
            "supplier_id": sup,
            "unit_cost_gbp": round(float(rng.uniform(cmin, cmax)), 2),
            "base_daily_demand": base,
        })
        n += 1
dim_product = pd.DataFrame(prod_rows)

# ABC class by annual value at cost (A = top 80% of value, B = next 15%, C = rest)
val = dim_product["base_daily_demand"] * dim_product["unit_cost_gbp"]
order = val.sort_values(ascending=False)
cum = order.cumsum() / order.sum()
abc = pd.Series("C", index=order.index)
abc[cum <= 0.80] = "A"
abc[(cum > 0.80) & (cum <= 0.95)] = "B"
dim_product["abc_class"] = abc.sort_index()

# Cover band by class (days of forecast demand): below min = at risk, above max = excess
POLICY = {"A": (7, 21), "B": (10, 28), "C": (14, 42)}
# Safety stock (days of forecast) the planner holds on top of lead time + review period
SAFETY_DAYS = {"A": 3, "B": 4, "C": 6}
dim_product["min_cover_days"] = dim_product["abc_class"].map(lambda c: POLICY[c][0])
dim_product["max_cover_days"] = dim_product["abc_class"].map(lambda c: POLICY[c][1])

# ---------------------------------------------------------- simulation
season = 1 + 0.18 * np.sin(2 * np.pi * (DATES.dayofyear - 80) / 365)   # summer peak
dec_bump = np.where(DATES.month == 12, 1.25, 1.0)

po_rows, inv_rows = [], []
po_seq = 1
REVIEW_WEEKDAY = 0  # orders placed on Mondays

for _, p in dim_product.iterrows():
    sp = sup_profile.loc[p.supplier_id]
    for loc in dim_location.location_id:
        mean_d = p.base_daily_demand * loc_scale[loc] * season * dec_bump
        demand = rng.poisson(mean_d)
        fcst = pd.Series(mean_d).rolling(28, min_periods=1).mean().to_numpy()  # planner forecast

        lt = int(sp.promised_lead_time_days)
        safety = SAFETY_DAYS[p.abc_class]
        on_hand = float(np.round(mean_d[0] * (lt + 7 + safety)))
        pipeline = []  # (arrival_index, qty_received, po_row_index)
        for t, d in enumerate(DATES):
            # receipts arriving today
            arriving = [x for x in pipeline if x[0] == t]
            for a in arriving:
                on_hand += a[1]
            pipeline = [x for x in pipeline if x[0] != t]

            opening = on_hand
            sales = min(on_hand, demand[t])
            lost = demand[t] - sales
            on_hand -= sales

            inv_rows.append((int(d.strftime("%Y%m%d")), p.sku, loc, int(opening), int(demand[t]),
                             int(sales), int(lost), int(on_hand), round(float(fcst[t]), 2)))

            # weekly order-up-to review
            if d.weekday() == REVIEW_WEEKDAY and t < len(DATES) - 3:
                on_order = sum(x[1] for x in pipeline)
                order_up_to = fcst[t] * (lt + 7 + safety)
                qty = int(np.round(max(0.0, order_up_to - on_hand - on_order)))
                # occasional manual over-order (promo buy, MOQ, "just in case") -> excess stock
                if qty > 0 and rng.random() < 0.06:
                    qty = int(qty * rng.uniform(3.0, 5.0))
                if qty > 0:
                    late = rng.random() < sp.p_late
                    delay = int(max(1, rng.poisson(sp.late_mean_days))) if late else int(rng.choice([0, 0, 0, -1]))
                    short = rng.random() < sp.p_short
                    recv = int(np.round(qty * rng.uniform(sp.short_fill_rate - 0.1, sp.short_fill_rate))) if short else qty
                    arrive = t + lt + delay
                    promised = d + pd.Timedelta(days=lt)
                    received = d + pd.Timedelta(days=lt + delay) if arrive < len(DATES) else pd.NaT
                    po_rows.append({
                        "po_number": f"PO{po_seq:06d}", "po_line": 1,
                        "supplier_id": p.supplier_id, "sku": p.sku, "location_id": loc,
                        "order_date": d.date(), "promised_date": promised.date(),
                        "received_date": None if pd.isna(received) else received.date(),
                        "qty_ordered": qty, "qty_received": recv if arrive < len(DATES) else 0,
                        "unit_cost_gbp": p.unit_cost_gbp,
                    })
                    po_seq += 1
                    if arrive < len(DATES):
                        pipeline.append((arrive, recv, None))

fact_po_line = pd.DataFrame(po_rows)
fact_po_line["line_value_gbp"] = (fact_po_line.qty_ordered * fact_po_line.unit_cost_gbp).round(2)

fact_inventory_daily = pd.DataFrame(inv_rows, columns=[
    "date_key", "sku", "location_id", "opening_stock", "demand_units", "sales_units",
    "lost_sales_units", "closing_stock", "forecast_daily_demand"])

# ---------------------------------------------------------------- write
dim_product = dim_product.drop(columns=["base_daily_demand"])
dim_supplier_out = dim_supplier[["supplier_id", "supplier_name", "category", "promised_lead_time_days"]]

dim_date.to_csv(OUT / "dim_date.csv", index=False)
dim_location.to_csv(OUT / "dim_location.csv", index=False)
dim_supplier_out.to_csv(OUT / "dim_supplier.csv", index=False)
dim_product.to_csv(OUT / "dim_product.csv", index=False)
fact_po_line.to_csv(OUT / "fact_po_line.csv", index=False)
fact_inventory_daily.to_csv(OUT / "fact_inventory_daily.csv", index=False)

print(f"dim_product: {len(dim_product)} SKUs | ABC: {dim_product.abc_class.value_counts().to_dict()}")
print(f"fact_po_line: {len(fact_po_line):,} rows | fact_inventory_daily: {len(fact_inventory_daily):,} rows")

# KPI dictionary

One agreed definition per KPI. The SQL in `sql/02_kpis.sql`, the DAX in `powerbi/measures.dax` and the web dashboard all implement exactly these definitions.

> "A good KPI dictionary prevents most dashboard arguments. When finance and procurement disagree about 'on time', the fix is an agreed definition, not a new chart."

| KPI | Definition | Formula | Grain | Target | Owner | Source |
|---|---|---|---|---|---|---|
| **OTIF** (on time in full) | Share of received PO lines that arrived on or before the promised date **and** with the full ordered quantity | lines where `received_date <= promised_date` AND `qty_received >= qty_ordered` ÷ received lines | PO line | ≥ 95% | Head of Procurement | `fact_po_line` |
| **On-time %** | Share of received PO lines on or before the promised date | lines where `received_date <= promised_date` ÷ received lines | PO line | ≥ 95% | Head of Procurement | `fact_po_line` |
| **In-full %** | Share of received PO lines with the full ordered quantity | lines where `qty_received >= qty_ordered` ÷ received lines | PO line | ≥ 98% | Head of Procurement | `fact_po_line` |
| **Lead-time variance** | How unpredictable a supplier's delivery date is | Standard deviation (population) of `received_date − promised_date`, in days | PO line | ≤ 2 days | Head of Procurement | `fact_po_line` |
| **Days of cover** | How many days current stock lasts at forecast demand | `closing_stock ÷ forecast_daily_demand` | SKU × location × day | Within the class band (below) | Supply Planner | `fact_inventory_daily` |
| **Projected days of cover** | Days of cover including stock already on order | `(closing_stock + open order qty) ÷ forecast_daily_demand` | SKU × location × day | ≥ supplier promised lead time | Supply Planner | `fact_inventory_daily`, `fact_po_line` |
| **Stockout rate** | Share of SKU-location-days with no stock at close of day | SKU-location-days where `closing_stock = 0` ÷ all SKU-location-days | SKU × location × day | ≤ 2% | Supply Planner | `fact_inventory_daily` |
| **Lost sales (units)** | Demand that could not be met from stock | Σ `lost_sales_units` | SKU × location × day | Downward trend | Supply Planner | `fact_inventory_daily` |
| **Excess stock value** | Value of stock above the maximum cover for its class, at a point in time | Σ max(`closing_stock − max_cover_days × forecast_daily_demand`, 0) × `unit_cost_gbp` | SKU × location, at snapshot date | Downward trend | Finance | `fact_inventory_daily`, `dim_product` |

## Cover bands by ABC class

ABC class is set by annual demand value at cost: A = top 80% of value, B = next 15%, C = remaining 5%.

| Class | Minimum cover (days) | Maximum cover (days) | Meaning |
|---|---|---|---|
| A | 7 | 21 | High value, fast moving: keep lean but never out |
| B | 10 | 28 | |
| C | 14 | 42 | Low value: hold more cover, order less often |

Below the minimum = at risk of stockout. Above the maximum = excess.

## Status rules used on the scorecard

| Status | Rule |
|---|---|
| On target | OTIF ≥ 95% and lead-time variance ≤ 2 days |
| Watch | OTIF 85–94.9% and lead-time variance ≤ 2 days |
| Underperforming | OTIF < 85% **or** lead-time variance > 2 days |

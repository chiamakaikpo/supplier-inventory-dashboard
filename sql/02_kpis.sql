-- KPI queries. Every definition here matches requirements/kpi_dictionary.md.
-- Run with:  python scripts/build_database.py   (loads CSVs, runs these, writes sql/results/)

-- name: kpi_summary
-- Headline KPI cards for the full year.
WITH po AS (
    SELECT *,
           CASE WHEN received_date <= promised_date AND qty_received >= qty_ordered THEN 1 ELSE 0 END AS is_otif
    FROM fact_po_line
    WHERE received_date IS NOT NULL
),
inv AS (
    SELECT i.*, p.unit_cost_gbp, p.max_cover_days
    FROM fact_inventory_daily i JOIN dim_product p USING (sku)
),
last_day AS (SELECT MAX(date_key) AS dk FROM fact_inventory_daily)
SELECT
    ROUND(100.0 * AVG(po.is_otif), 1)                                        AS otif_pct,
    (SELECT ROUND(100.0 * AVG(CASE WHEN closing_stock = 0 THEN 1.0 ELSE 0 END), 2) FROM inv) AS stockout_rate_pct,
    (SELECT ROUND(SUM(MAX(closing_stock - max_cover_days * forecast_daily_demand, 0) * unit_cost_gbp), 0)
       FROM inv WHERE date_key = (SELECT dk FROM last_day))                AS excess_stock_value_gbp
FROM po;

-- name: supplier_scorecard
-- OTIF, lead-time variance (std dev of actual minus promised lead time, days) and spend.
WITH po AS (
    SELECT f.*, s.supplier_name, s.promised_lead_time_days,
           julianday(received_date) - julianday(order_date)         AS actual_lt,
           julianday(received_date) - julianday(promised_date)      AS days_late,
           CASE WHEN received_date <= promised_date AND qty_received >= qty_ordered THEN 1.0 ELSE 0 END AS is_otif,
           CASE WHEN received_date <= promised_date THEN 1.0 ELSE 0 END AS is_on_time,
           CASE WHEN qty_received >= qty_ordered THEN 1.0 ELSE 0 END    AS is_in_full
    FROM fact_po_line f JOIN dim_supplier s USING (supplier_id)
    WHERE received_date IS NOT NULL
)
SELECT
    supplier_id,
    supplier_name,
    COUNT(*)                                        AS po_lines,
    ROUND(SUM(line_value_gbp), 0)                   AS spend_gbp,
    ROUND(100 * AVG(is_on_time), 1)                 AS on_time_pct,
    ROUND(100 * AVG(is_in_full), 1)                 AS in_full_pct,
    ROUND(100 * AVG(is_otif), 1)                    AS otif_pct,
    -- population std dev: sqrt(E[x^2] - E[x]^2)
    ROUND(SQRT(AVG(days_late * days_late) - AVG(days_late) * AVG(days_late)), 2) AS lead_time_variance_days,
    CASE WHEN AVG(is_otif) >= 0.95 THEN 'On target'
         WHEN AVG(is_otif) >= 0.85 THEN 'Watch'
         ELSE 'Underperforming' END                 AS status
FROM po
GROUP BY supplier_id, supplier_name
ORDER BY otif_pct;

-- name: stockout_by_supplier
-- Connects supplier performance to inventory health: stockout rate of the SKUs each supplier provides.
SELECT
    p.supplier_id,
    ROUND(100.0 * AVG(CASE WHEN i.closing_stock = 0 THEN 1.0 ELSE 0 END), 2) AS stockout_rate_pct,
    SUM(i.lost_sales_units)                                                AS lost_sales_units,
    ROUND(SUM(i.lost_sales_units * p.unit_cost_gbp), 0)                    AS lost_sales_at_cost_gbp
FROM fact_inventory_daily i JOIN dim_product p USING (sku)
GROUP BY p.supplier_id
ORDER BY stockout_rate_pct DESC;

-- name: cover_by_class
-- Days of cover at the last snapshot, by ABC class, against the agreed cover band.
SELECT
    p.abc_class,
    p.min_cover_days,
    p.max_cover_days,
    COUNT(*)                                                                      AS sku_locations,
    ROUND(AVG(i.closing_stock / i.forecast_daily_demand), 1)                      AS avg_days_cover,
    SUM(CASE WHEN i.closing_stock / i.forecast_daily_demand < p.min_cover_days THEN 1 ELSE 0 END) AS below_band,
    SUM(CASE WHEN i.closing_stock / i.forecast_daily_demand > p.max_cover_days THEN 1 ELSE 0 END) AS above_band
FROM fact_inventory_daily i JOIN dim_product p USING (sku)
WHERE i.date_key = (SELECT MAX(date_key) FROM fact_inventory_daily)
GROUP BY p.abc_class, p.min_cover_days, p.max_cover_days
ORDER BY p.abc_class;

-- name: at_risk_skus
-- SKU-locations at the last snapshot whose PROJECTED cover (stock on hand + open orders,
-- divided by forecast daily demand) is shorter than the supplier's promised lead time:
-- the stock will run out before a new order placed today could arrive.
WITH snap AS (SELECT MAX(date_key) AS dk, date(substr(MAX(date_key),1,4)||'-'||substr(MAX(date_key),5,2)||'-'||substr(MAX(date_key),7,2)) AS d
              FROM fact_inventory_daily),
open_po AS (
    SELECT sku, location_id, SUM(qty_ordered) AS on_order
    FROM fact_po_line, snap
    WHERE order_date <= snap.d AND (received_date IS NULL OR received_date > snap.d)
    GROUP BY sku, location_id
)
SELECT
    i.sku, p.product_name, i.location_id, p.supplier_id, s.supplier_name,
    i.closing_stock,
    COALESCE(o.on_order, 0)                                                   AS on_order,
    ROUND(i.forecast_daily_demand, 1)                                         AS forecast_per_day,
    ROUND((i.closing_stock + COALESCE(o.on_order, 0)) / i.forecast_daily_demand, 1) AS projected_days_cover,
    s.promised_lead_time_days
FROM fact_inventory_daily i
JOIN snap ON i.date_key = snap.dk
JOIN dim_product p USING (sku)
JOIN dim_supplier s ON s.supplier_id = p.supplier_id
LEFT JOIN open_po o ON o.sku = i.sku AND o.location_id = i.location_id
WHERE (i.closing_stock + COALESCE(o.on_order, 0)) / i.forecast_daily_demand < s.promised_lead_time_days
ORDER BY projected_days_cover;

-- name: monthly_trend
-- OTIF (by promised month) against stockout rate, to show the relationship over time.
WITH otif AS (
    SELECT substr(promised_date, 1, 7) AS ym,
           ROUND(100.0 * AVG(CASE WHEN received_date <= promised_date AND qty_received >= qty_ordered THEN 1.0 ELSE 0 END), 1) AS otif_pct
    FROM fact_po_line WHERE received_date IS NOT NULL
    GROUP BY ym
),
so AS (
    SELECT d.year_month AS ym,
           ROUND(100.0 * AVG(CASE WHEN i.closing_stock = 0 THEN 1.0 ELSE 0 END), 2) AS stockout_rate_pct
    FROM fact_inventory_daily i JOIN dim_date d USING (date_key)
    GROUP BY d.year_month
)
SELECT so.ym AS year_month, otif.otif_pct, so.stockout_rate_pct
FROM so LEFT JOIN otif USING (ym)
ORDER BY so.ym;

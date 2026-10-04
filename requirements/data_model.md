# Data model

Star schema with two fact tables sharing four conformed dimensions. GitHub renders the diagram below.

```mermaid
erDiagram
    dim_date ||--o{ fact_inventory_daily : "date_key"
    dim_location ||--o{ fact_inventory_daily : "location_id"
    dim_product ||--o{ fact_inventory_daily : "sku"
    dim_location ||--o{ fact_po_line : "location_id"
    dim_product ||--o{ fact_po_line : "sku"
    dim_supplier ||--o{ fact_po_line : "supplier_id"
    dim_supplier ||--o{ dim_product : "supplier_id"

    fact_po_line {
        text po_number PK
        int po_line PK
        text supplier_id FK
        text sku FK
        text location_id FK
        date order_date
        date promised_date
        date received_date "NULL if still open"
        int qty_ordered
        int qty_received
        real unit_cost_gbp
        real line_value_gbp
    }
    fact_inventory_daily {
        int date_key PK
        text sku PK
        text location_id PK
        int opening_stock
        int demand_units
        int sales_units
        int lost_sales_units
        int closing_stock
        real forecast_daily_demand
    }
    dim_date {
        int date_key PK
        date date
        int year
        int month
        text year_month
        int iso_week
    }
    dim_location {
        text location_id PK
        text location_name
        text region
    }
    dim_supplier {
        text supplier_id PK
        text supplier_name
        text category
        int promised_lead_time_days
    }
    dim_product {
        text sku PK
        text product_name
        text category
        text supplier_id FK
        real unit_cost_gbp
        text abc_class
        int min_cover_days
        int max_cover_days
    }
```

## Grain and volumes (synthetic year, 2025)

| Table | Grain | Rows |
|---|---|---|
| `fact_po_line` | One purchase order line | 5,413 |
| `fact_inventory_daily` | One SKU, at one location, on one day (closing position) | 43,800 |
| `dim_date` | One calendar day | 365 |
| `dim_product` | One SKU | 40 |
| `dim_supplier` | One supplier | 8 |
| `dim_location` | One distribution centre | 3 |

## Modelling notes

- `fact_po_line` joins to `dim_date` on `promised_date` for OTIF trends (an inactive relationship on `order_date` in Power BI).
- Each SKU has one primary supplier (`dim_product.supplier_id`). This is what lets stockouts in `fact_inventory_daily` be attributed to a supplier.
- In Power BI, filter `dim_supplier` → `dim_product` → `fact_inventory_daily` (single direction) so selecting a supplier filters its SKUs' stock.

-- SIMULATED stock on hand (M5 ships no inventory data) - see src/ingest/simulate_inventory.py
select
    dp.product_key,
    ds.store_key,
    i.stock_on_hand
from {{ ref('stg_inventory') }} as i
inner join {{ ref('dim_product') }} as dp on i.item_id = dp.item_id
inner join {{ ref('dim_store') }} as ds on i.store_id = ds.store_id

select
    cast(strftime(s.full_date, '%Y%m%d') as integer) as date_key,
    dp.product_key,
    ds.store_key,
    pr.price_key,
    s.units_sold,
    s.revenue,
    s.snap_flag
from {{ ref('int_sales_long') }} as s
inner join {{ ref('dim_product') }} as dp on s.item_id = dp.item_id
inner join {{ ref('dim_store') }} as ds on s.store_id = ds.store_id
inner join {{ ref('dim_price') }} as pr
    on s.store_id = pr.store_id and s.item_id = pr.item_id and s.wm_yr_wk = pr.wm_yr_wk

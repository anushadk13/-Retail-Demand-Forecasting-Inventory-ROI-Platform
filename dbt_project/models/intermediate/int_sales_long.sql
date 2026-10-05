-- Unpivot the wide d_1..d_N sales table to one row per item/store/day, then attach
-- calendar and price. Rows before an item's first price are pre-launch and are dropped.
with long_sales as (
    unpivot {{ ref('stg_sales_wide') }}
    on columns(* exclude (id, item_id, dept_id, cat_id, store_id, state_id))
    into name d value units_sold
)

select
    s.id as series_id,
    s.item_id,
    s.dept_id,
    s.cat_id,
    s.store_id,
    s.state_id,
    c.full_date,
    c.wm_yr_wk,
    c.event_name,
    c.snap_ca,
    c.snap_tx,
    c.snap_wi,
    p.sell_price,
    cast(s.units_sold as integer) as units_sold,
    s.units_sold * p.sell_price as revenue,
    case s.state_id
        when 'CA' then c.snap_ca
        when 'TX' then c.snap_tx
        when 'WI' then c.snap_wi
    end as snap_flag
from long_sales as s
inner join {{ ref('stg_calendar') }} as c on s.d = c.d
inner join {{ ref('stg_prices') }} as p
    on s.store_id = p.store_id and s.item_id = p.item_id and c.wm_yr_wk = p.wm_yr_wk

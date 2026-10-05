-- One row per observed item/store/week price point; price_band is relative to that
-- item-store's own median price so promotions are identifiable.
with p as (
    select
        *,
        median(sell_price) over (partition by store_id, item_id) as median_price
    from {{ ref('stg_prices') }}
)

select
    row_number() over (order by store_id, item_id, wm_yr_wk) as price_key,
    store_id,
    item_id,
    wm_yr_wk,
    sell_price,
    case
        when sell_price <= 0.9 * median_price then 'promo'
        when sell_price >= 1.1 * median_price then 'premium'
        else 'regular'
    end as price_band
from p

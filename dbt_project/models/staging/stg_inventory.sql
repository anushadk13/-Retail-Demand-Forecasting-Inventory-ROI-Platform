select
    item_id,
    store_id,
    cast(stock_on_hand as integer) as stock_on_hand
from {{ source('raw', 'inventory_snapshot') }}

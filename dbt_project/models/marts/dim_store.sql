select
    row_number() over (order by store_id) as store_key,
    store_id,
    state_id as state
from (select distinct
    store_id,
    state_id
from {{ ref('stg_sales_wide') }})

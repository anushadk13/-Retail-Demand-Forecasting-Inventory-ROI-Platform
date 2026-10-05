select
    row_number() over (order by item_id) as product_key,
    item_id,
    dept_id as department,
    cat_id as category
from (select distinct
    item_id,
    dept_id,
    cat_id
from {{ ref('stg_sales_wide') }})

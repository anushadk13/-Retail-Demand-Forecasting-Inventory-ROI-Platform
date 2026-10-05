select
    date_key,
    product_key,
    store_key,
    count(*) as n
from {{ ref('fact_sales') }}
group by 1, 2, 3
having count(*) > 1

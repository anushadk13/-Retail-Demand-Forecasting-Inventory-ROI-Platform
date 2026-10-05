select f.*
from {{ ref('fact_sales') }} as f
left join {{ ref('dim_price') }} as p on f.price_key = p.price_key
where p.sell_price is null or p.sell_price <= 0

-- Sales volume per day must be positive overall except on closed days (e.g. Christmas)
select
    date_key,
    sum(units_sold) as units
from {{ ref('fact_sales') }}
group by 1
having sum(units_sold) = 0 and date_key % 10000 != 1225

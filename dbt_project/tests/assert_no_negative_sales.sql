select * from {{ ref('fact_sales') }}
where units_sold < 0 or revenue < 0

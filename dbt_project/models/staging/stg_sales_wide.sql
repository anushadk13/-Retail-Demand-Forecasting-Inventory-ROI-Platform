select * from {{ source('raw', 'sales_wide') }}

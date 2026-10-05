select
    cast(strftime(full_date, '%Y%m%d') as integer) as date_key,
    full_date,
    wm_yr_wk as week, -- noqa: RF04
    month,
    year,
    weekday,
    event_name is not null as is_holiday,
    event_name,
    snap_ca,
    snap_tx,
    snap_wi
from {{ ref('stg_calendar') }}

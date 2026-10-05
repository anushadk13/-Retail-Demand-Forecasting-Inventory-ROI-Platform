select
    d,
    cast(date as date) as full_date,
    wm_yr_wk,
    weekday,
    wday,
    month,
    year,
    event_name_1 as event_name,
    event_type_1 as event_type,
    snap_ca = 1 as snap_ca,
    snap_tx = 1 as snap_tx,
    snap_wi = 1 as snap_wi
from {{ source('raw', 'calendar') }}

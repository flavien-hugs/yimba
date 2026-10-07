select
    id as alert_id,
    watch_id,
    status,
    mentions,
    negative,
    negative_share,
    threshold_share,
    window_start,
    window_end,
    triggered_at,
    acknowledged_at,
    extract(epoch from acknowledged_at - triggered_at) / 3600.0 as hours_to_acknowledge
from {{ source('yimba', 'watch_alerts') }}

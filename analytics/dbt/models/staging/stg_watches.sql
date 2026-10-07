select
    id as watch_id,
    owner_id,
    name as watch_name,
    frequency_minutes,
    alert_negative_share,
    alert_min_mentions,
    active,
    created_at,
    updated_at
from {{ source('yimba', 'watches') }}

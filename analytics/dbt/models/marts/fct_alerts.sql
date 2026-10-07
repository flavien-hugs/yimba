select
    alerts.*,
    watches.watch_name
from {{ ref('stg_alerts') }} as alerts
left join {{ ref('stg_watches') }} as watches using (watch_id)

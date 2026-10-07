select
    id as run_id,
    watch_id,
    source,
    status,
    started_at,
    finished_at,
    (started_at at time zone 'UTC')::date as run_day,
    extract(epoch from finished_at - started_at) as duration_seconds,
    fetched,
    stored,
    error
from {{ source('yimba', 'collection_runs') }}

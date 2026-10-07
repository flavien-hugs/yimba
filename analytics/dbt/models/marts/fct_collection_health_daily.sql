-- Is each source working? Runs, failures and volumes per day, watch and source.
with runs as (
    select
        *,
        row_number() over (partition by run_day, watch_id, source order by started_at desc) as recency
    from {{ ref('stg_collection_runs') }}
)

select
    run_day,
    watch_id,
    source,
    count(*) as runs,
    count(*) filter (where status = 'succeeded') as succeeded,
    count(*) filter (where status = 'failed') as failed,
    (count(*) filter (where status = 'succeeded'))::float / count(*) as success_rate,
    sum(fetched) as fetched,
    sum(stored) as stored,
    avg(duration_seconds) as avg_duration_seconds,
    max(error) filter (where recency = 1) as last_error
from runs
group by 1, 2, 3

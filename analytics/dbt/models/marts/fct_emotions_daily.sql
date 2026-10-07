select
    published_day,
    watch_id,
    source,
    emotion,
    count(*) as mentions
from {{ ref('stg_mentions') }}
where emotion is not null and not published_at_missing
group by 1, 2, 3, 4

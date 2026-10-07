-- Signals that the data or the analysis is degrading, per collection day and source.
select
    (collected_at at time zone 'UTC')::date as collected_day,
    source,
    count(*) as mentions,
    avg(case when published_at_missing then 1.0 else 0.0 end) as published_at_missing_share,
    avg(case when language = 'und' then 1.0 else 0.0 end) as undetermined_language_share,
    avg(case when sentiment_label = 'neutral' then 1.0 else 0.0 end) as neutral_share,
    avg(case when emotion is null then 1.0 else 0.0 end) as no_emotion_share
from {{ ref('stg_mentions') }}
group by 1, 2

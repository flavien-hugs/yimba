-- Opinion per day, watch, source and language. Mentions without a real publication date are left out
-- (they would pile up on their collection day); fct_data_quality_daily counts them.
select
    published_day,
    watch_id,
    source,
    language,
    count(*) as mentions,
    count(*) filter (where sentiment_label = 'positive') as positive,
    count(*) filter (where sentiment_label = 'neutral') as neutral,
    count(*) filter (where sentiment_label = 'negative') as negative,
    (count(*) filter (where sentiment_label = 'negative'))::float / count(*) as negative_share,
    avg(sentiment_compound) as avg_compound,
    sum(likes) as likes,
    sum(shares) as shares,
    sum(views) as views,
    sum(comments) as comments
from {{ ref('stg_mentions') }}
where not published_at_missing
group by 1, 2, 3, 4

-- No text and no author reference: the analytics layer carries no personal data.
select
    id as mention_id,
    watch_id,
    source,
    language,
    sentiment_label,
    sentiment_positive,
    sentiment_neutral,
    sentiment_negative,
    sentiment_positive - sentiment_negative as sentiment_compound,
    emotion,
    likes,
    shares,
    views,
    comments,
    published_at,
    collected_at,
    (published_at at time zone 'UTC')::date as published_day,
    -- Ingestion uses the collection time when a source gives no usable date: such dates are not real.
    published_at = collected_at as published_at_missing
from {{ source('yimba', 'mentions') }}

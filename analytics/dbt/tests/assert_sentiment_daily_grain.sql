select published_day, watch_id, source, language, count(*)
from {{ ref('fct_sentiment_daily') }}
group by 1, 2, 3, 4
having count(*) > 1

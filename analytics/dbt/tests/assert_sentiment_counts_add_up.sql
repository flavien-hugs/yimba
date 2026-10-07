select * from {{ ref('fct_sentiment_daily') }} where positive + neutral + negative <> mentions

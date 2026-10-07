select mention_id from {{ ref('stg_mentions') }}
where abs(sentiment_positive + sentiment_neutral + sentiment_negative - 1) > 0.01

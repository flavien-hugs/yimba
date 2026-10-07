select 'fct_sentiment_daily' as model, negative_share as share from {{ ref('fct_sentiment_daily') }}
where negative_share not between 0 and 1
union all
select 'fct_collection_health_daily', success_rate from {{ ref('fct_collection_health_daily') }}
where success_rate not between 0 and 1
union all
select 'fct_data_quality_daily', published_at_missing_share from {{ ref('fct_data_quality_daily') }}
where published_at_missing_share not between 0 and 1

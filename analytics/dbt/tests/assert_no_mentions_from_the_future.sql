-- A publication date after the collection means a wrong date parser or time zone.
select mention_id from {{ ref('stg_mentions') }} where published_at > collected_at + interval '1 hour'

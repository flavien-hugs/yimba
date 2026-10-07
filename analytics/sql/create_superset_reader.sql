-- Read-only role for the dashboards. Every analytics run grants it SELECT on the marts (schema "analytics")
-- and nothing else: no access to the application tables, so no text and no author.
--   docker compose exec -T postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
--       -v password="'<password>'" < analytics/sql/create_superset_reader.sql
create role superset_reader login password :password;

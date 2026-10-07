{#
  Dashboards connect with a read-only role (sql/create_superset_reader.sql) that only sees the marts.
  Nothing happens when the role does not exist yet.
#}
{% macro grant_read_access() %}
    {% set role = env_var('ANALYTICS_READER_ROLE', 'superset_reader') %}
    do $$
    begin
        if exists (select 1 from pg_roles where rolname = '{{ role }}') then
            grant usage on schema {{ target.schema }} to {{ role }};
            grant select on all tables in schema {{ target.schema }} to {{ role }};
        end if;
    end
    $$;
{% endmacro %}

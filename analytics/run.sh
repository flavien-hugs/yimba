#!/bin/sh
# dbt (models + tests), source freshness, then Pandera checks.
# With ANALYTICS_EVERY_SECONDS set, repeats forever (a minimal scheduler until there is an orchestrator).
set -u

run_once() {
    dbt build --project-dir dbt --profiles-dir dbt || return 1
    dbt source freshness --project-dir dbt --profiles-dir dbt || echo "warning: sources are stale" >&2
    python -m quality
}

if [ -z "${ANALYTICS_EVERY_SECONDS:-}" ]; then
    run_once
    exit $?
fi

while true; do
    run_once || echo "analytics run failed" >&2
    sleep "$ANALYTICS_EVERY_SECONDS"
done

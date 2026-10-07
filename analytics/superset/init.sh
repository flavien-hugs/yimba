#!/bin/sh
# One-off setup: metadata migrations, admin account, roles, and the read-only connection to the marts.
set -eu
superset db upgrade
superset fab create-admin \
    --username "$SUPERSET_ADMIN_USERNAME" --password "$SUPERSET_ADMIN_PASSWORD" \
    --firstname Admin --lastname Yimba --email "$SUPERSET_ADMIN_EMAIL" || true
superset init
if [ -n "${SUPERSET_READER_PASSWORD:-}" ]; then
    superset set-database-uri --database_name "Yimba analytics" \
        --uri "postgresql+psycopg2://superset_reader:${SUPERSET_READER_PASSWORD}@postgres:5432/${POSTGRES_DB}"
fi

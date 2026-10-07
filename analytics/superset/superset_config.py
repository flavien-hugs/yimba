"""Superset settings for Yimba (loaded from /app/pythonpath)."""

import os

SECRET_KEY = os.environ["SUPERSET_SECRET_KEY"]
# Superset's own metadata (users, charts, dashboards), kept in its volume.
SQLALCHEMY_DATABASE_URI = os.environ.get("SUPERSET_METADATA_URI", "sqlite:////app/superset_home/superset.db")
# Dashboards only read the marts: no SQL Lab DML, no file uploads into the database.
PREVENT_UNSAFE_DB_CONNECTIONS = True
FEATURE_FLAGS = {"ENABLE_TEMPLATE_PROCESSING": False}

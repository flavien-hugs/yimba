FROM apache/superset:6.1.0

# The image ships without database drivers.
USER root
RUN uv pip install --python /app/.venv/bin/python --no-cache psycopg2-binary==2.9.13
COPY superset_config.py /app/pythonpath/superset_config.py
COPY init.sh /app/yimba-init.sh
USER superset

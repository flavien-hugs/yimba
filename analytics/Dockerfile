# Analytics image: dbt-core (transformations and tests) and Pandera (data quality), apart from the application.
FROM python:3.12-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    DBT_TARGET_PATH=/tmp/dbt/target \
    DBT_LOG_PATH=/tmp/dbt/logs

WORKDIR /analytics
COPY requirements.txt ./
RUN --mount=type=cache,target=/root/.cache pip install -r requirements.txt

ARG UID=10001
RUN adduser --uid $UID --disabled-password --gecos "" analytics
COPY dbt ./dbt
COPY quality ./quality
COPY run.sh ./
USER analytics

ENTRYPOINT ["./run.sh"]

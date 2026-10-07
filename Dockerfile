FROM python:3.12-slim-bookworm AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    VIRTUAL_ENV=/venv \
    PATH=/venv/bin:$PATH \
    PYTHONPATH=/app/src

FROM base AS builder

ARG POETRY_VERSION=2.3.4
# Set to "ml" to bake the transformers sentiment model dependencies into the image.
ARG EXTRAS=""

RUN python -m venv $VIRTUAL_ENV && pip install "poetry==${POETRY_VERSION}"
WORKDIR /app
COPY pyproject.toml poetry.lock ./
RUN --mount=type=cache,target=/root/.cache \
    POETRY_VIRTUALENVS_CREATE=false poetry install --no-root --only main ${EXTRAS:+--extras "$EXTRAS"}

FROM base AS runtime

# HF_HOME: transformers models are downloaded once into this directory (a volume in docker compose).
ENV HF_HOME=/models \
    GIT_PYTHON_REFRESH=quiet

ARG UID=10001
RUN adduser --uid $UID --disabled-password --gecos "" appuser \
    && mkdir -p /models && chown appuser /models

COPY --from=builder /venv /venv
WORKDIR /app
COPY src ./src
COPY migrations ./migrations
COPY alembic.ini appdesc.yml ./
USER appuser

EXPOSE 8800
ENTRYPOINT ["python", "-m", "yimba.entrypoints.cli"]
CMD ["api"]

# syntax=docker/dockerfile:1
# One image, three roles: api (default), worker, beat. Build with EXTRAS="ml tracking" for the worker that runs
# transformers models and MLflow evaluations.

ARG PYTHON_VERSION=3.12

FROM python:${PYTHON_VERSION}-slim-bookworm AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    VIRTUAL_ENV=/venv \
    PATH=/venv/bin:$PATH

# ---- dependencies: rebuilt only when pyproject.toml, poetry.lock or EXTRAS change --------------------------------
FROM base AS builder

ARG POETRY_VERSION=2.3.4
ARG EXTRAS=""
ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_CACHE_DIR=/root/.cache/pypoetry

# Poetry gets its own environment so that neither it nor its dependencies reach the runtime image.
RUN --mount=type=cache,target=/root/.cache/pip \
    python -m venv /opt/poetry \
    && /opt/poetry/bin/pip install "poetry==${POETRY_VERSION}" \
    && python -m venv "$VIRTUAL_ENV"

WORKDIR /build
COPY pyproject.toml poetry.lock ./
# Installs into the active virtualenv ($VIRTUAL_ENV); --compile ships bytecode, so imports do not recompile at start.
RUN --mount=type=cache,target=/root/.cache/pypoetry \
    /opt/poetry/bin/poetry install --no-root --only main --compile ${EXTRAS:+--extras "$EXTRAS"} \
    && "$VIRTUAL_ENV/bin/python" -m pip uninstall --yes --quiet pip

# ---- runtime ------------------------------------------------------------------------------------------------------
FROM base AS runtime

# HF_HOME: transformers models are downloaded once into this directory (a volume in docker compose).
ENV PYTHONPATH=/app/src \
    HF_HOME=/models \
    GIT_PYTHON_REFRESH=quiet

ARG UID=10001
RUN useradd --uid "$UID" --no-create-home --shell /usr/sbin/nologin appuser \
    && install --directory --owner appuser /models

COPY --from=builder /venv /venv
WORKDIR /app
COPY alembic.ini appdesc.yml ./
COPY migrations ./migrations
COPY src ./src
# The code is read-only for appuser: compile it now rather than on every start.
RUN python -m compileall -q -j 0 src migrations

USER appuser
EXPOSE 8800
ENTRYPOINT ["python", "-m", "yimba.entrypoints.cli"]
CMD ["api"]

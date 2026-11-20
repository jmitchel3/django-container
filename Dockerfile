# syntax=docker/dockerfile:1
#
# Default variant: Django + PostgreSQL (covers the large majority of projects).
# psycopg[binary] ships prebuilt wheels, so this image needs NO compiler and
# NO libpq system packages - keeping it small and fast to build.
#
#   docker build -t django-app .
#
ARG PYTHON_VERSION=3.13-slim-bookworm
ARG UV_VERSION=0.9.18
ARG DOPPLER_VERSION=3.77.1

FROM dopplerhq/cli:${DOPPLER_VERSION} AS doppler-cli

############################
# Stage 1 - build the venv
############################
FROM ghcr.io/astral-sh/uv:${UV_VERSION} AS uv
FROM python:${PYTHON_VERSION} AS builder

COPY --from=uv /uv /uvx /bin/

# Bytecode-compile on install, copy (not hardlink) across the cache mount,
# and never let uv reach out to download a Python - we already have one.
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0 \
    VIRTUAL_ENV=/opt/venv \
    PATH=/opt/venv/bin:$PATH

RUN uv venv /opt/venv
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=requirements.txt,target=/tmp/requirements.txt \
    uv pip install -r /tmp/requirements.txt

############################
# Stage 2 - runtime image
############################
FROM python:${PYTHON_VERSION} AS runtime

ARG PROJ_NAME="cfehome"
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/opt/venv/bin:$PATH \
    HOME=/app \
    PORT=8080 \
    DJANGO_SETTINGS_MODULE=${PROJ_NAME}.settings \
    DJANGO_WSGI_APP=${PROJ_NAME}.wsgi:application \
    RUN_MIGRATIONS=1 \
    RUN_COLLECTSTATIC=0 \
    RUN_AUTO_ADMIN=0

COPY --from=builder /opt/venv /opt/venv

WORKDIR /app
COPY ./src /app
COPY gunicorn.conf.py /app/
COPY scripts/ /app/scripts/

# /app holds the default SQLite database and the generated static files.
RUN groupadd -r app && useradd -r -g app -d /app app \
    && chmod +x scripts/entrypoint.sh \
    && chown app:app /app
USER app

# Only collectstatic sees this placeholder. Runtime settings come from deployment.
RUN DJANGO_SECRET_KEY=collectstatic-build-only python manage.py collectstatic --no-input --clear

EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD ["python", "/app/scripts/healthcheck.py"]

ENTRYPOINT ["/app/scripts/entrypoint.sh"]

# Opt in with docker build --target doppler. Supply credentials at runtime.
FROM runtime AS doppler
COPY --from=doppler-cli /bin/doppler /usr/local/bin/doppler
ENV RUNTIME_ENV_PROVIDER=doppler

FROM runtime AS final

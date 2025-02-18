# Build stage
ARG PYTHON_VERSION=3.12-slim-bullseye
FROM python:${PYTHON_VERSION} AS builder

# Combine venv creation and build dependencies
RUN python -m venv /opt/venv && \
    apt-get update && apt-get install -y \
    libpq-dev \
    zlib1g-dev \
    libjpeg-dev \
    libfreetype6-dev \
    python3-dev \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

ENV PATH=/opt/venv/bin:$PATH

# Install packages and cleanup in same layer
COPY requirements.txt /tmp/
RUN pip install --upgrade pip && \
    pip install -r /tmp/requirements.txt gunicorn && \
    rm -rf /root/.cache/pip/* /tmp/requirements.txt

# Final stage
FROM python:${PYTHON_VERSION}

# Copy virtual env from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH

# Install only runtime dependencies
RUN apt-get update && apt-get install -y \
    libpq5 \
    curl \
    libcairo2 \
    && rm -rf /var/lib/apt/lists/*

    # Create runtime script
ARG PROJ_NAME="cfehome"
# Set Python environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=${PROJ_NAME}.settings

WORKDIR /app
COPY ./src /app

# Add this line to copy gunicorn config
COPY gunicorn.conf.py /app/

RUN printf "#!/bin/bash\n" > ./paracord_runner.sh && \
    printf "RUN_PORT=\"\${PORT:-8080}\"\n\n" >> ./paracord_runner.sh && \
    printf "python manage.py collectstatic --no-input\n" >> ./paracord_runner.sh && \
    printf "python manage.py migrate --no-input\n" >> ./paracord_runner.sh && \
    printf "gunicorn ${PROJ_NAME}.wsgi:application -c gunicorn.conf.py --bind \"[::]:\$RUN_PORT\"\n" >> ./paracord_runner.sh

# Setup non-root user
RUN groupadd -r paracord && useradd -r -g paracord paracord && \
    chown -R paracord:paracord /app && \
    chown -R paracord:paracord /opt/venv && \
    chmod +x paracord_runner.sh && \
    chown paracord:paracord paracord_runner.sh

USER paracord

CMD ./paracord_runner.sh
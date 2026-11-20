#!/usr/bin/env bash
# Web startup runs after the entrypoint has populated the environment.
set -euo pipefail

if [ "${RUN_MIGRATIONS:-1}" = "1" ]; then
    python manage.py migrate --no-input
fi

if [ "${RUN_COLLECTSTATIC:-0}" = "1" ]; then
    python manage.py collectstatic --no-input
fi

if [ "${RUN_AUTO_ADMIN:-0}" = "1" ]; then
    python manage.py auto_admin
fi

# Bind to [::] so the container serves both IPv4 and IPv6.
exec gunicorn "${DJANGO_WSGI_APP:-cfehome.wsgi:application}" \
    -c gunicorn.conf.py --bind "[::]:${PORT:-8080}"

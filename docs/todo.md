# Container Refactor - Completion Checklist

Tracking the move to a lean, `uv`-based, multi-variant Docker setup aligned
with the common Django deployment shape: one small default Postgres image,
separate variants only when unavoidable, and static frontend assets bundled
only when the project actually needs Node.

## Core Refactor

- [x] Split requirements into db-agnostic `base.in` plus `postgres.in` and
  `mysql.in` overlays.
- [x] Compiled consistent `uv` locks for runtime and dev:
  `requirements.txt`, `requirements.mysql.txt`, `requirements.dev.txt`.
- [x] Modernized Django settings for Django 6.0:
  `STORAGES`, db-agnostic `DATABASE_URL`, deterministic `INSTALLED_APPS`,
  configurable `DJANGO_SITE_ID`, and container-safe healthcheck hosts.
- [x] Replaced inline Docker startup script generation with shared
  `scripts/entrypoint.sh`.
- [x] Added dependency-free `scripts/healthcheck.py` with configurable
  `HEALTHCHECK_PATH` and `HEALTHCHECK_HOST`.
- [x] Made startup release steps configurable:
  `RUN_MIGRATIONS=1`, `RUN_COLLECTSTATIC=0`, `RUN_AUTO_ADMIN=0`.
- [x] Made `auto_admin` opt-in safe by requiring `DJANGO_ADMIN_PASSWORD` and
  avoiding password output in logs.
- [x] Added `.dockerignore` to keep secrets, virtualenvs, `node_modules`,
  generated static files, docs, and local tooling out of image context.

## Docker Variants

- [x] `Dockerfile`: default Django + PostgreSQL image using `uv`,
  `psycopg[binary]`, no compiler, no `libpq` runtime package, build-time
  `collectstatic`, non-root user, and Docker `HEALTHCHECK`.
- [x] `Dockerfile.mysql`: MySQL/MariaDB variant using `mysqlclient`, with
  compiler and headers only in the builder stage and `libmariadb3` in runtime.
- [x] `Dockerfile.node`: bundled static frontend variant for Vite, React/CRA,
  or Next.js static export, with Node isolated to the frontend build stage and
  built files collected under `/static/frontend/`.

## Local Development

- [x] Added `compose.yaml` `web` service for the default Postgres image.
- [x] Added `compose.yaml` `web-mysql` plus `mysql` service for the MySQL
  image.
- [x] Added compose profiles: `--profile postgres` and `--profile mysql`.
- [x] Added database healthchecks so each web container waits for a ready
  database.
- [x] Overrode `DATABASE_URL` per compose web service so containers use the
  compose database hostname, while `.env.dev` remains useful for local/native
  development.
- [x] Made host ports overrideable with `WEB_PORT`, `POSTGRES_PORT`, and
  `MYSQL_PORT`.

## Tooling And Deploy Config

- [x] Updated `rav.yaml` with `build`, `build:mysql`, `build:node`, compose
  profile commands, `uv pip compile` lock command, and `uv pip sync` install.
- [x] Updated `railway.json` watch patterns for Dockerfiles, `.dockerignore`,
  requirements, scripts, and `src/**`.
- [x] Confirmed `gunicorn.conf.py` stays compatible with env-driven bind via
  `scripts/entrypoint.sh`.
- [x] Removed the obsolete `src/requirements/prod.in` in favor of the new
  overlay inputs.

## Docs

- [x] Rewrote `README.md` with a variant matrix, build commands, run command,
  compose profiles, env-var reference, dependency lock commands, and Railway
  notes.
- [x] Documented the SQLite path: no extra Dockerfile is needed when
  `DATABASE_URL` is unset or an explicit `sqlite:///` URL is supplied.
- [x] Documented frontend build args for Vite (`dist`), Create React App
  (`build`), and Next.js static export (`out`).

## Verification Evidence

Verified on 2026-06-21.

- [x] `docker compose --profile postgres config` renders successfully and
  points `web` at `postgres://postgres:postgres@db:5432/postgres`.
- [x] `docker compose --profile mysql config` renders successfully and points
  `web-mysql` at `mysql://root:mysql@mysql:3306/app`.
- [x] `docker build -t django-container:postgres-check .` succeeds.
- [x] `docker build -f Dockerfile.mysql -t django-container:mysql-check .`
  succeeds.
- [x] `Dockerfile.node` builds successfully as `django-container:node-check`
  against the minimal Vite-like fixture in
  `/private/tmp/django-container-node-test-20260621`.
- [x] Built Postgres image reports Django `6.0.6`, passes `python manage.py
  check`, and runs as UID `999`.
- [x] Built MySQL image reports Django `6.0.6`, passes `python manage.py
  check`, and runs as UID `999`.
- [x] Built Node image reports Django `6.0.6`, passes `python manage.py
  check`, and runs as UID `999`.
- [x] Node variant collects frontend files under `/app/static_root/frontend/`,
  including `index.html` and `assets/app.css`.
- [x] Isolated Postgres compose smoke test passes with project
  `django-container-postgres-check`: healthy `db` and `web` containers,
  migrations apply, and `GET http://127.0.0.1:18081/api/healthz/` returns
  `200 OK`.
- [x] Isolated MySQL compose smoke test passes with project
  `django-container-mysql-check`: healthy `mysql` and `web-mysql` containers,
  migrations apply, and `GET http://127.0.0.1:18082/api/healthz/` returns
  `200 OK`.
- [x] Current image sizes are acceptable for the target:
  Postgres `422MB`, MySQL `357MB`, Node `422MB`.

## Reproducibility Decisions

- [x] Pinned `UV_VERSION=0.9.18` in all Dockerfiles.
- [x] Kept base images pinned by version tag rather than digest so starter
  projects receive compatible patch updates without manual digest churn.
- [x] Kept variants minimal: no separate SQLite Dockerfile, no Node runtime in
  Python images, no MySQL libraries in the Postgres image, and no Postgres
  libraries in the MySQL image.

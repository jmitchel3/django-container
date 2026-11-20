# Django Container

A non-root Django container with PostgreSQL, MySQL, and static frontend variants.
Start a local stack with `docker compose --profile postgres up --build`, then
open [the health endpoint](http://localhost:8001/api/healthz/).

## Variant Matrix

| Need | Dockerfile | Python deps | System deps |
| --- | --- | --- | --- |
| Django + PostgreSQL | `Dockerfile` | `requirements.txt` | none |
| Django + MySQL or MariaDB | `Dockerfile.mysql` | `requirements.mysql.txt` | `libmariadb3` at runtime |
| Django + bundled static JS frontend | `Dockerfile.node` | `requirements.txt` | Node only in build stage |

The default image targets PostgreSQL because that covers most deployed Django
apps and `psycopg[binary]` avoids compiler and `libpq` packages. Use the MySQL
variant only when the app uses `mysqlclient`. Use the Node variant when the
frontend is compiled to static files and served by Django/WhiteNoise.

## Build

```bash
docker build -t django-container .
docker build -f Dockerfile.mysql -t django-container:mysql .
```

`Dockerfile.node` expects your frontend to provide a `package-lock.json` and
an npm `build` script. The default source directory is `frontend/` and its
default output directory is `dist/`.

```bash
docker build \
  -f Dockerfile.node \
  --build-arg FRONTEND_DIR=frontend \
  --build-arg FRONTEND_BUILD_DIR=dist \
  -t django-container:node .
```

For Create React App use `FRONTEND_BUILD_DIR=build`. For a Next.js static
export use `FRONTEND_BUILD_DIR=out`.

## Run

```bash
docker run --rm \
  -p 8001:8080 \
  --env-file .env.dev \
  -e PORT=8080 \
  -e DATABASE_URL=sqlite:////app/db.sqlite3 \
  django-container
```

The container listens on `PORT` inside the container. `8080` is the default for
the image and Railway deployment config.

## Runtime secrets

The entrypoint resolves credentials before migrations, collectstatic, admin
creation, or Gunicorn. Passing a command after the image name gives that
command the same environment and skips the web startup steps. After rotation,
recreate the container with the updated environment or mounts. Doppler
fetches its current config whenever the container starts. Builds use a
throwaway signing key for collectstatic.

### Doppler

Put `DJANGO_SECRET_KEY` and your deployment's `DATABASE_URL` in the intended
Doppler config. Obtain a read-only service token from that config's **Access**
tab. To check Django, run the following from the checkout. It uses an exported
`DOPPLER_TOKEN` or prompts privately in your terminal. The check skips migrations.

```bash
bin/check-doppler
```

For a live check from a noninteractive runner with an authenticated host
Doppler CLI, use `bin/check-doppler --cli PROJECT CONFIG` with the intended
project and config names. It builds the image, creates a read-only service
token that expires after five minutes, and passes it to Compose for this run.
[Doppler ephemeral service tokens](https://docs.doppler.com/docs/service-tokens)

To exercise the image without a Doppler account, run
`bin/check-doppler --self-test`. It runs the real CLI and Django's system
checks against a local API fixture with Docker networking disabled.

To start the web service, export `DOPPLER_TOKEN` in the shell that runs Compose,
or supply it through your deployment's secret store. A host-side `doppler login`
alone doesn't populate this variable. Compose mounts it as a secret, and the
container uses it to fetch the config on startup. [Doppler service tokens](https://docs.doppler.com/docs/service-tokens)

```bash
docker compose --profile doppler up --build
```

For a standalone container, build the `doppler` target of any variant. The
following uses the default PostgreSQL Dockerfile. The second command checks
Django configuration without running migrations. The third starts the app.

```bash
docker build --target doppler -t django-container:doppler .
docker run --rm -e DOPPLER_TOKEN django-container:doppler python manage.py check
docker run --rm -p 8001:8080 -e DOPPLER_TOKEN django-container:doppler
```

If Doppler is unavailable, startup exits before running any Django command.
The application child drops the provider token from its environment. Set
`PORT` on the container so Gunicorn and Docker's healthcheck use the same
port. [Doppler service tokens](https://docs.doppler.com/docs/service-tokens)

### 1Password and other environment providers

The default image accepts ordinary environment variables. With 1Password CLI
authenticated on the host, replace the vault, item and field names below.
Docker forwards only the named variables from the resolved environment.

```bash
DJANGO_SECRET_KEY=op://Production/Django/signing-key \
DATABASE_URL=op://Production/Django/database-url \
op run -- docker run --rm -p 8001:8080 -e DJANGO_SECRET_KEY -e DATABASE_URL django-container
```

The same Docker command works with a platform secret store or any manager
that exports environment variables. Docker stores values passed with `-e`
in container metadata. Use a mounted file when that matters for your
deployment. [1Password CLI reference](https://developer.1password.com/docs/cli/reference/commands/run/)

### Mounted files

For Docker secrets, Kubernetes Secret volumes, or files rendered by a secret
manager, point the corresponding `_FILE` variables at read-only mounts.
This example reads a signing key from `$PWD/secrets/django-key`.

```bash
docker run --rm \
  --mount "type=bind,src=$PWD/secrets/django-key,dst=/run/secrets/django-key,readonly" \
  -e DJANGO_SECRET_KEY_FILE=/run/secrets/django-key \
  django-container python manage.py check
```

All variants recognize `DJANGO_SECRET_KEY_FILE`, `DATABASE_URL_FILE` and
`DJANGO_ADMIN_PASSWORD_FILE`. The Doppler target also accepts
`DOPPLER_TOKEN_FILE` to authenticate the CLI. To load an additional key, set
both `SECRET_FILE_VARS=API_TOKEN` and `API_TOKEN_FILE=/run/secrets/api-token`.
Separate multiple names with spaces.

Provide one source per key. Setting both `KEY` and `KEY_FILE` stops startup.
Files must be readable by the container's app user and contain nonempty UTF-8
text without NUL bytes. One trailing LF or CRLF is removed. Embedded newlines,
spaces and shell characters are preserved.

## Local Compose

Start PostgreSQL and the Django web service.

```bash
docker compose --profile postgres up --build
```

For MySQL, select its profile.

```bash
docker compose --profile mysql up --build
```

Both profiles read development settings from `.env.dev` and override
`DATABASE_URL` to connect to the matching Compose database service.
Published ports bind to IPv4 loopback. You can choose different host ports.

```bash
WEB_PORT=18001 POSTGRES_PORT=15432 docker compose --profile postgres up --build
WEB_PORT=18002 MYSQL_PORT=13306 docker compose --profile mysql up --build
```

## Environment

| Variable | Default | Purpose |
| --- | --- | --- |
| `PORT` | `8080` in Docker | Gunicorn bind port inside the container |
| `DJANGO_SECRET_KEY` | required when debug is off | Stable signing key shared by all replicas |
| `DJANGO_DEBUG` | `False` | Enable Django debug behavior for local development |
| `DJANGO_ALLOWED_HOSTS` | loopback, Railway probe and assigned domains | Additional comma-separated hostnames |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | assigned public Railway HTTPS origin | Additional comma-separated origins including scheme |
| `DJANGO_SITE_ID` | `1` | Django sites framework ID |
| `DATABASE_URL` | unset | Selects Postgres, MySQL, SQLite, or another supported backend |
| `DJANGO_WSGI_APP` | `cfehome.wsgi:application` | Gunicorn WSGI target |
| `WEB_CONCURRENCY` | `1` | Gunicorn worker count per container |
| `HEALTHCHECK_PATH` | `/api/healthz/` | Path used by the Docker healthcheck |
| `HEALTHCHECK_HOST` | `localhost` | Host header used by the Docker healthcheck |
| `RUN_MIGRATIONS` | `1` | Run `python manage.py migrate --no-input` on startup |
| `RUN_COLLECTSTATIC` | `0` | Run collectstatic at startup instead of only at build time |
| `RUN_AUTO_ADMIN` | `0` | Bootstrap a superuser if none exists |
| `DJANGO_ADMIN_USERNAME` | `admin` | Account targeted by `auto_admin` |
| `DJANGO_ADMIN_PASSWORD` | unset | Required to create or explicitly rotate a superuser |
| `DJANGO_ADMIN_EMAIL` | `notset@notset.com` | Email used when creating the admin account |

Process variables take precedence over `.env.local`, followed by `.env`.
Static files are collected during the image build. Turn on `RUN_COLLECTSTATIC`
when assets are mounted or generated at runtime. With multiple web replicas,
run `python manage.py migrate --no-input` once as a release command and set
`RUN_MIGRATIONS=0` on the replicas.

For an explicit password rotation, supply the new admin password and run
`python manage.py auto_admin --force` as a one-off command. It can rotate an
active staff superuser or create the configured username if it is available.

## SQLite

With `DATABASE_URL` unset, Django creates `src/db.sqlite3` in a source
checkout or `/app/db.sqlite3` in the container. To set the container path
explicitly, use this URL.

```bash
DATABASE_URL=sqlite:////app/db.sqlite3
```

SQLite is useful for demos and smoke tests. Persistent production deployments
should use an external database and set `DATABASE_URL`.

## Dependency Locks

Compile the runtime and development locks for Python 3.13.

```bash
uv pip compile src/requirements/postgres.in --python-version 3.13 --output-file requirements.txt
uv pip compile src/requirements/mysql.in --python-version 3.13 --output-file requirements.mysql.txt
uv pip compile src/requirements/dev.in -c requirements.txt --python-version 3.13 --output-file requirements.dev.txt
```

Create a Python 3.13 environment and install the default runtime and dev tools.

```bash
uv venv --python 3.13
uv pip sync requirements.txt requirements.dev.txt
```

Run both test suites from the repository root.

```bash
.venv/bin/python -m unittest discover -s tests -v
DJANGO_SECRET_KEY=test-only DATABASE_URL=sqlite://:memory: .venv/bin/python src/manage.py test cfehome commando
```

## Railway

`railway.json` uses the default PostgreSQL Dockerfile. To deploy the MySQL or
Node variant on Railway, change `build.dockerfilePath` to `./Dockerfile.mysql`
or `./Dockerfile.node` and set the matching environment variables.

## Versions and changelog

Each completed commit in a checkout with the Git hooks enabled pushes its
current branch to `origin`. To enable the hooks in a new clone, run
`git config --local core.hooksPath .githooks`.

After a push to `main` passes CI, GitHub publishes a release for each new
first-parent commit. A merged PR gets one version with the changes it brought
in. The first version is `v0.1.0`. A `feat:` subject bumps the minor version,
a breaking-change marker (`feat!:` or a `BREAKING CHANGE:` footer) bumps the
major version, and other changes bump the patch. Write descriptive commit
subjects. Bullets in commit bodies are included in the release notes.

Tags point to the source on `main`. The publisher maintains `VERSION` and the
cumulative `CHANGELOG.md` on the `releases` branch. A failed publication can
be retried from the Container checks workflow.
[Changelog](https://github.com/jmitchel3/django-container/blob/releases/CHANGELOG.md) · [GitHub Releases](https://github.com/jmitchel3/django-container/releases)

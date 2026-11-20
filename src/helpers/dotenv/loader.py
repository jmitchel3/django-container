from pathlib import Path

from decouple import Config, RepositoryEnv

SOURCE_DIR = Path(__file__).resolve().parents[2]
# The source checkout has src/manage.py; the container puts manage.py in /app.
PROJECT_DIR = SOURCE_DIR.parent if SOURCE_DIR.name == "src" else SOURCE_DIR


def get_config(allowed_envs=(".env.local", ".env")):
    """Use process variables first, followed by the listed files in order."""
    values = {}
    for name in reversed(allowed_envs):
        try:
            values.update(RepositoryEnv(PROJECT_DIR / name).data)
        except FileNotFoundError:
            continue
    return Config(values)


config = get_config()

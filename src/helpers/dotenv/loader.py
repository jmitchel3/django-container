# using python-decouple to load environment variables
import logging
import pathlib
from functools import lru_cache

from decouple import Config, RepositoryEnv

THIS_DIR = pathlib.Path(__file__).parent
HELPERS_DIR = THIS_DIR.parent  # src/helpers/
BASE_DIR = HELPERS_DIR.parent  # src/
PROJECT_DIR = BASE_DIR.parent  # /

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_config(allowed_envs: list[str] = [".env", ".env.local"]):
    for env in allowed_envs:
        path = PROJECT_DIR / env
        if path.exists():
            try:
                logger.info(f"Loading {env}")
                return Config(RepositoryEnv(path))
            except FileNotFoundError:
                continue
    from decouple import config

    return config


config = get_config()

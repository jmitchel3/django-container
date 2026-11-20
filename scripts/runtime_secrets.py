"""Resolve container secrets before running the supplied command."""

import os
import re
import sys
from pathlib import Path


APP_SECRETS = ("DJANGO_SECRET_KEY", "DATABASE_URL", "DJANGO_ADMIN_PASSWORD")


def load_secret_file(name):
    pointer = f"{name}_FILE"
    if pointer not in os.environ:
        return
    if name in os.environ:
        sys.exit(f"Set only one of {name} and {pointer}.")

    path = Path(os.environ[pointer])
    try:
        if not path.is_file():
            sys.exit(f"{pointer} must point to a readable regular file.")
        data = path.read_bytes()
        if data.endswith(b"\r\n"):
            data = data[:-2]
        else:
            data = data.removesuffix(b"\n")
        value = data.decode("utf-8")
    except (OSError, UnicodeDecodeError):
        sys.exit(f"{pointer} must point to a readable UTF-8 text file.")
    if not value or "\x00" in value:
        sys.exit(f"{pointer} must contain a nonempty value without NUL bytes.")
    os.environ[name] = value
    del os.environ[pointer]


def execute(command):
    try:
        os.execvp(command[0], command)
    except FileNotFoundError:
        print(f"Executable not found: {command[0]}", file=sys.stderr)
        sys.exit(127)
    except OSError as error:
        print(f"Cannot start {command[0]}: {error.strerror}", file=sys.stderr)
        sys.exit(126)


def main(stage, command):
    if stage == "start":
        provider = os.environ.get("RUNTIME_ENV_PROVIDER", "env")
        if provider == "doppler":
            load_secret_file("DOPPLER_TOKEN")
            execute([
                "doppler", "run", "--no-fallback", "--forward-signals", "--preserve-env=PORT", "--",
                sys.executable, str(Path(__file__).resolve()), "after-doppler", *command,
            ])
        if provider != "env":
            sys.exit("RUNTIME_ENV_PROVIDER must be env or doppler.")
    elif stage == "after-doppler":
        # Only the CLI needs the provider credential.
        os.environ.pop("DOPPLER_TOKEN", None)
    else:
        sys.exit("Unknown runtime secret loading stage.")

    extra_names = os.environ.get("SECRET_FILE_VARS", "").split()
    for name in (*APP_SECRETS, *extra_names):
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
            sys.exit("SECRET_FILE_VARS must contain space-separated variable names.")
        load_secret_file(name)
    execute(command)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])

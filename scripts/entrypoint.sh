#!/bin/sh
set -eu

script_dir=$(dirname "$0")
if [ "$#" -eq 0 ]; then
    set -- bash "$script_dir/serve.sh"
fi
exec python3 "$script_dir/runtime_secrets.py" start "$@"

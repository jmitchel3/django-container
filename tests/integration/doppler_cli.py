"""Run inside the Doppler image with --network none to test the complete entrypoint."""

import json
import os
import subprocess
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
from urllib.parse import urlsplit


class SecretsAPI(BaseHTTPRequestHandler):
    def do_GET(self):
        if urlsplit(self.path).path != "/v3/configs/config/secrets/download":
            self.send_error(404)
            return
        if self.headers.get("Authorization") != "Bearer dp.st.ci-fixture":
            self.send_error(401)
            return
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        secrets = {"DJANGO_SECRET_KEY": "fixture-signing-key", "PORT": "8999"}
        self.wfile.write(json.dumps(secrets).encode())


def main():
    with HTTPServer(("127.0.0.1", 0), SecretsAPI) as api, TemporaryDirectory() as tmp:
        Thread(target=api.serve_forever, daemon=True).start()
        token_file = Path(tmp) / "token"
        token_file.write_text("dp.st.ci-fixture\n")
        env = {
            **os.environ,
            "DOPPLER_TOKEN_FILE": str(token_file),
            "DOPPLER_API_HOST": f"http://127.0.0.1:{api.server_port}",
            "DOPPLER_NO_CHECK_VERSION": "true",
            "PORT": "8080",
        }
        check = """
import os
import django
from django.conf import settings
from django.core.management import call_command
assert settings.SECRET_KEY == "fixture-signing-key"
assert settings.PORT == 8080
assert "DOPPLER_TOKEN" not in os.environ
assert "DOPPLER_TOKEN_FILE" not in os.environ
django.setup()
call_command("check")
"""
        try:
            subprocess.run(
                ["/app/scripts/entrypoint.sh", "python", "-c", check],
                env=env, check=True, timeout=20,
            )
        finally:
            api.shutdown()


if __name__ == "__main__":
    main()

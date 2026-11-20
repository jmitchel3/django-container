#!/usr/bin/env python
"""Dependency-free container HEALTHCHECK.

Hits the Django health endpoint over loopback using only the stdlib, so the
image needs neither curl nor wget. Exit 0 == healthy, non-zero == unhealthy.
"""

from http.client import HTTPConnection, HTTPException
import os
import sys


def main():
    conn = HTTPConnection("127.0.0.1", port=int(os.environ.get("PORT", "8080")), timeout=4)
    try:
        conn.request("GET", os.environ.get("HEALTHCHECK_PATH", "/api/healthz/"),
                     headers={"Host": os.environ.get("HEALTHCHECK_HOST", "localhost")})
        status = conn.getresponse().status
        if status != 200:
            print(f"Health endpoint returned HTTP {status}", file=sys.stderr)
        return int(status != 200)
    finally:
        conn.close()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (HTTPException, OSError, ValueError) as exc:
        sys.exit(f"Healthcheck failed: {exc}")

"""Minimal smoke test for a running Selenite backend.

Ensures the /health endpoint is reachable and that the seed admin user can log in.
"""

from __future__ import annotations

import argparse
import sys
import time
from typing import Optional

import requests


def wait_for_health(base_url: str, timeout: int) -> None:
    """Poll the /health endpoint until it returns HTTP 200 or timeout expires."""
    url = f"{base_url.rstrip('/')}/health"
    deadline = time.time() + timeout
    first_attempt = True
    while True:
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                print(f"[smoke] Health check OK: {url}")
                return
            if first_attempt:
                print("[smoke] Waiting for backend to start...")
                first_attempt = False
            print(f"[smoke] Health check returned {response.status_code}, retrying.")
        except requests.RequestException as exc:
            if first_attempt:
                print("[smoke] Waiting for backend to start...")
                first_attempt = False
            else:
                print(f"[smoke] Health check failed: {exc}")

        if time.time() > deadline:
            raise SystemExit(
                f"[smoke] HEALTH_TIMEOUT reached ({timeout}s) without success"
            )
        time.sleep(2)


def verify_login(base_url: str, username: str, password: str) -> None:
    """Attempt to log in using the supplied credentials."""
    url = f"{base_url.rstrip('/')}/auth/login"
    payload = {"username": username, "password": password}
    response: Optional[requests.Response] = None
    try:
        response = requests.post(url, json=payload, timeout=5)
    except requests.RequestException as exc:
        raise SystemExit(f"[smoke] Login request failed: {exc}") from exc

    if response.status_code != 200:
        raise SystemExit(
            f"[smoke] Login failed ({response.status_code}): {response.text.strip()}"
        )
    print("[smoke] Login succeeded")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Selenite backend smoke test")
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8100",
        help="Backend base URL (default: http://127.0.0.1:8100)",
    )
    parser.add_argument(
        "--username",
        default="admin",
        help="Username to authenticate (default: admin)",
    )
    parser.add_argument(
        "--password",
        default="changeme",
        help="Password to authenticate (default: changeme)",
    )
    parser.add_argument(
        "--health-timeout",
        type=int,
        default=60,
        help="Seconds to wait for /health to become ready (default: 60)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    wait_for_health(args.base_url, args.health_timeout)
    verify_login(args.base_url, args.username, args.password)
    print("[smoke] Backend smoke test completed successfully")


if __name__ == "__main__":
    try:
        main()
    except SystemExit as exc:
        print(exc, file=sys.stderr)
        raise

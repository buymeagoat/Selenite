"""Minimal smoke test for a running Selenite backend.

Ensures the /health endpoint is reachable and that the seed admin user can log in.
"""

from __future__ import annotations


from pathlib import Path
from urllib.parse import urlparse, urlunparse


def _read_workspace_role(repo_root: Path) -> str:
    role_file = repo_root / '.workspace-role'
    if role_file.exists():
        return role_file.read_text(encoding='utf-8').splitlines()[0].strip().lower()
    return ''


def _read_env_ports(repo_root: Path) -> tuple[int | None, int | None]:
    env_file = repo_root / '.env'
    if not env_file.exists():
        return None, None
    env_text = env_file.read_text(encoding='utf-8', errors='ignore').splitlines()
    backend_port = None
    frontend_port = None
    for line in env_text:
        if line.strip().startswith('PORT='):
            value = line.split('=', 1)[1].strip()
            if value.isdigit():
                backend_port = int(value)
        if line.strip().startswith('FRONTEND_URL=') and ':' in line:
            value = line.rsplit(':', 1)[1].strip()
            if value.isdigit():
                frontend_port = int(value)
    return backend_port, frontend_port


def _default_base_url() -> str:
    repo_root = Path(__file__).resolve().parents[1]
    role = _read_workspace_role(repo_root)
    is_prod = role == 'prod'
    env_backend_port, _ = _read_env_ports(repo_root)
    backend_port = (
        int(os.environ["SELENITE_BACKEND_PORT"])
        if os.environ.get("SELENITE_BACKEND_PORT")
        else env_backend_port
        if env_backend_port
        else 8100
        if is_prod
        else 8201
    )
    return f"http://127.0.0.1:{backend_port}"


def _read_env_value(repo_root: Path, key: str) -> str | None:
    env_file = repo_root / ".env"
    if not env_file.exists():
        return None
    for line in env_file.read_text(encoding="utf-8", errors="ignore").splitlines():
        if line.strip().startswith(f"{key}="):
            return line.split("=", 1)[1].strip()
    return None


def _env_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _select_https_origin(cors_origins: str | None) -> str | None:
    if not cors_origins:
        return None
    for origin in cors_origins.split(","):
        origin = origin.strip()
        if origin.startswith("https://"):
            return origin.rstrip("/")
    return None


def _normalize_base_url(base_url: str, repo_root: Path) -> str:
    require_https = _env_bool(_read_env_value(repo_root, "REQUIRE_HTTPS"))
    allow_http_dev = _env_bool(_read_env_value(repo_root, "ALLOW_HTTP_DEV"))
    cors_origins = _read_env_value(repo_root, "CORS_ORIGINS")
    vite_api_url = _read_env_value(repo_root, "VITE_API_URL") or "/api"

    if vite_api_url.startswith("http"):
        return vite_api_url.rstrip("/")

    path_prefix = vite_api_url.strip()
    if not path_prefix.startswith("/"):
        path_prefix = f"/{path_prefix}"

    base = base_url.rstrip("/")
    if require_https and not allow_http_dev:
        https_origin = _select_https_origin(cors_origins)
        if https_origin:
            base = https_origin
        else:
            parsed = urlparse(base)
            if parsed.netloc:
                base = urlunparse(("https", parsed.netloc, "", "", "", ""))

    if not base.endswith(path_prefix):
        base = f"{base}{path_prefix}"
    return base

import argparse
import os
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


def verify_login(base_url: str, email: str, password: str) -> None:
    """Attempt to log in using the supplied credentials."""
    url = f"{base_url.rstrip('/')}/auth/login"
    payload = {"email": email, "password": password}
    response: Optional[requests.Response] = None
    try:
        response = requests.post(url, json=payload, timeout=5)
    except requests.RequestException as exc:
        raise SystemExit(f"[smoke] Login request failed: {exc}") from exc

    if response.status_code != 200:
        hint = (
            "Hint: if this is local/dev and admin password drifted, run "
            "`python scripts/reset_admin_password.py --password changeme` from repo root, "
            "then rerun bootstrap."
        )
        raise SystemExit(
            f"[smoke] Login failed ({response.status_code}): "
            f"{response.text.strip()} | {hint}"
        )
    print("[smoke] Login succeeded")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Selenite backend smoke test")
    parser.add_argument(
        "--base-url",
        default=_default_base_url(),
        help="Backend base URL (default: derived from .env/role)",
    )
    parser.add_argument(
        "--email",
        default="admin@selenite.local",
        help="Email to authenticate (default: admin@selenite.local)",
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
    repo_root = Path(__file__).resolve().parents[1]
    args.base_url = _normalize_base_url(args.base_url, repo_root)
    wait_for_health(args.base_url, args.health_timeout)
    verify_login(args.base_url, args.email, args.password)
    print("[smoke] Backend smoke test completed successfully")


if __name__ == "__main__":
    try:
        main()
    except SystemExit as exc:
        print(exc, file=sys.stderr)
        raise





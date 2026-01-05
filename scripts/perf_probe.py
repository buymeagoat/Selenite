from pathlib import Path

#!/usr/bin/env python3
"""
Simple performance probe: hits a configured URL and fails if it exceeds a latency budget.

Usage:
  PERF_PROBE_URL=https://example.com/health PERF_PROBE_BUDGET_MS=200 python scripts/perf_probe.py

Defaults:
  - Skips if PERF_PROBE_URL is not set.
  - Budget defaults to 200 ms.
"""
from __future__ import annotations

from pathlib import Path

def _ensure_dev_workspace() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    role_file = repo_root / '.workspace-role'
    if role_file.exists():
        role = role_file.read_text(encoding='utf-8').splitlines()[0].strip().lower()
        if role != 'dev':
            raise RuntimeError('This script must be run from a dev workspace.')
_ensure_dev_workspace()

import os
import sys
import time
from urllib.error import URLError, HTTPError
from urllib.request import Request, urlopen


def main() -> None:
    url = os.getenv("PERF_PROBE_URL")
    if not url:
        print("PERF_PROBE_URL not set; skipping perf probe.")
        return

    budget_ms = int(os.getenv("PERF_PROBE_BUDGET_MS", "200"))
    req = Request(url, method="GET")

    start = time.perf_counter()
    try:
        with urlopen(req, timeout=budget_ms / 1000) as resp:  # nosec: standard GET
            status = resp.getcode()
            body = resp.read()
    except (HTTPError, URLError, TimeoutError) as exc:
        print(f"Perf probe failed to connect to {url}: {exc}")
        sys.exit(1)
    elapsed_ms = (time.perf_counter() - start) * 1000

    if status >= 400:
        print(f"Perf probe got HTTP {status} from {url}")
        sys.exit(1)

    if elapsed_ms > budget_ms:
        print(
            f"Perf probe exceeded budget: {elapsed_ms:.1f} ms > {budget_ms} ms "
            f"(URL: {url}, body_len={len(body) if body else 0})"
        )
        sys.exit(1)

    print(
        f"Perf probe OK: {elapsed_ms:.1f} ms <= {budget_ms} ms "
        f"(URL: {url}, status={status}, body_len={len(body) if body else 0})"
    )


if __name__ == "__main__":
    main()




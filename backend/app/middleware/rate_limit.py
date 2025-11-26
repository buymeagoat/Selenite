import os
import time
from typing import Dict, Tuple

from fastapi import HTTPException, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

DEFAULT_LIMIT = {"max_tokens": 100, "refill_rate": 100 / 60}
SPECIAL_LIMITS: Dict[Tuple[str, str], Dict[str, float]] = {
    ("POST", "/auth/login"): {"max_tokens": 5, "refill_rate": 5 / 60},
    ("POST", "/jobs/upload"): {"max_tokens": 10, "refill_rate": 10 / 60},
}


class RateLimiter:
    def __init__(self):
        self._buckets: Dict[str, Dict[str, float]] = {}
        self._cleanup_counter = 0

    def is_allowed(self, key: str, *, max_tokens: int, refill_rate: float) -> bool:
        now = time.time()
        bucket = self._buckets.get(key, {"tokens": float(max_tokens), "last_refill": now})

        # Refill tokens based on elapsed time
        elapsed = now - bucket["last_refill"]
        bucket["tokens"] = min(float(max_tokens), bucket["tokens"] + elapsed * refill_rate)
        bucket["last_refill"] = now

        allowed = bucket["tokens"] >= 1.0
        if allowed:
            bucket["tokens"] -= 1.0

        self._buckets[key] = bucket
        self._cleanup_counter += 1
        return allowed


rate_limiter = RateLimiter()


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, exclude_paths=None):
        super().__init__(app)
        self.exclude_paths = set(exclude_paths or [])

    def _get_client_key(self, request: Request) -> str:
        user_id = getattr(request.state, "user_id", None)
        if user_id:
            return f"user:{user_id}"
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return f"ip:{forwarded.split(',')[0].strip()}"
        client_ip = request.client[0] if request.client else "unknown"
        return f"ip:{client_ip}"

    def _get_limit_config(self, path: str, method: str) -> Dict[str, float]:
        return SPECIAL_LIMITS.get((method.upper(), path), DEFAULT_LIMIT)

    async def dispatch(self, request: Request, call_next) -> Response:
        if os.getenv("DISABLE_RATE_LIMIT") == "1" or request.url.path in self.exclude_paths:
            return await call_next(request)

        config = self._get_limit_config(request.url.path, request.method)
        key = f"{self._get_client_key(request)}:{request.url.path}:{request.method.upper()}"

        if not rate_limiter.is_allowed(
            key, max_tokens=int(config["max_tokens"]), refill_rate=float(config["refill_rate"])
        ):
            raise HTTPException(
                status_code=429, detail="Rate limit exceeded. Please try again later."
            )

        return await call_next(request)

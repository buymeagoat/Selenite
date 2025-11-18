"""Rate limiting middleware to prevent abuse."""

import time
from typing import Dict, Tuple
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware


class RateLimiter:
    """Simple in-memory rate limiter using token bucket algorithm."""

    def __init__(self):
        # Store: {key: (tokens, last_update_time)}
        self._buckets: Dict[str, Tuple[float, float]] = {}
        self._cleanup_counter = 0

    def _cleanup_old_buckets(self) -> None:
        """Periodically clean up old bucket entries to prevent memory bloat."""
        self._cleanup_counter += 1
        if self._cleanup_counter % 1000 == 0:
            current_time = time.time()
            # Remove buckets not accessed in last hour
            stale_keys = [
                key
                for key, (_, last_update) in self._buckets.items()
                if current_time - last_update > 3600
            ]
            for key in stale_keys:
                del self._buckets[key]

    def is_allowed(
        self,
        key: str,
        max_tokens: int,
        refill_rate: float,
    ) -> bool:
        """
        Check if request is allowed based on token bucket algorithm.

        Args:
            key: Unique identifier for the client (IP or user ID)
            max_tokens: Maximum tokens in bucket (burst capacity)
            refill_rate: Tokens added per second

        Returns:
            True if request is allowed, False otherwise
        """
        current_time = time.time()

        if key not in self._buckets:
            # New bucket with max tokens minus one for current request
            self._buckets[key] = (max_tokens - 1, current_time)
            return True

        tokens, last_update = self._buckets[key]

        # Calculate tokens to add based on elapsed time
        elapsed = current_time - last_update
        tokens_to_add = elapsed * refill_rate
        new_tokens = min(max_tokens, tokens + tokens_to_add)

        if new_tokens < 1:
            # Not enough tokens
            self._buckets[key] = (new_tokens, current_time)
            return False

        # Consume one token
        self._buckets[key] = (new_tokens - 1, current_time)

        self._cleanup_old_buckets()
        return True


# Global rate limiter instance
rate_limiter = RateLimiter()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware to apply rate limiting to API requests."""

    def __init__(self, app, exclude_paths: list[str] = None):
        super().__init__(app)
        self.exclude_paths = exclude_paths or ["/health", "/docs", "/openapi.json"]

        # Rate limit configurations for different endpoint types
        self.limits = {
            # Auth endpoints: stricter limits to prevent brute force
            "/auth/login": {"max_tokens": 5, "refill_rate": 0.1},  # 5 attempts, 1 per 10s
            "/auth/register": {"max_tokens": 3, "refill_rate": 0.05},  # 3 attempts, 1 per 20s
            "/auth/password": {"max_tokens": 3, "refill_rate": 0.05},  # 3 attempts, 1 per 20s
            # Job creation: moderate limits
            "/jobs": {"max_tokens": 10, "refill_rate": 0.2},  # 10 jobs, 1 per 5s
            # Default: generous limits for general API usage
            "default": {"max_tokens": 100, "refill_rate": 2.0},  # 100 requests, 2 per second
        }

    def _get_client_key(self, request: Request) -> str:
        """Get unique identifier for client (IP address or user ID)."""
        # Prefer user ID if authenticated
        user_id = getattr(request.state, "user_id", None)
        if user_id:
            return f"user:{user_id}"

        # Fall back to IP address
        # Check for X-Forwarded-For header (proxy/load balancer)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"

        return f"ip:{client_ip}"

    def _get_limit_config(self, path: str, method: str) -> dict:
        """Get rate limit configuration for given path."""
        # Only apply rate limits to POST requests for creation endpoints
        if method == "POST":
            for endpoint, config in self.limits.items():
                if endpoint != "default" and path.startswith(endpoint):
                    return config

        # Use default for all other requests
        return self.limits["default"]

    async def dispatch(self, request: Request, call_next):
        """Apply rate limiting to requests."""
        path = request.url.path

        # Skip excluded paths
        if any(path.startswith(excluded) for excluded in self.exclude_paths):
            return await call_next(request)

        # Get client identifier and rate limit config
        client_key = self._get_client_key(request)
        config = self._get_limit_config(path, request.method)

        # Check rate limit
        key = f"{client_key}:{path}"
        if not rate_limiter.is_allowed(
            key=key,
            max_tokens=config["max_tokens"],
            refill_rate=config["refill_rate"],
        ):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please try again later.",
            )

        # Process request
        response = await call_next(request)
        return response

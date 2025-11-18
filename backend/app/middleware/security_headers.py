"""Security headers middleware."""

from starlette.middleware.base import BaseHTTPMiddleware


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""

    async def dispatch(self, request, call_next):
        response = await call_next(request)

        # Content Security Policy - restrict resource loading
        # Allow self for most resources, inline styles for React, and data: for images
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: blob:; "
            "font-src 'self' data:; "
            "connect-src 'self'; "
            "media-src 'self' blob:; "
            "object-src 'none'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )

        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"

        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # XSS protection (legacy, but still useful for older browsers)
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Referrer policy - limit referrer information
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions policy - disable unnecessary browser features
        response.headers["Permissions-Policy"] = (
            "geolocation=(), "
            "microphone=(), "
            "camera=(), "
            "payment=(), "
            "usb=(), "
            "magnetometer=(), "
            "gyroscope=(), "
            "accelerometer=()"
        )

        # HSTS - force HTTPS in production
        # Note: Only enable this when deployed with HTTPS
        # Commented out for local development
        # response.headers["Strict-Transport-Security"] = (
        #     "max-age=31536000; includeSubDomains; preload"
        # )

        return response

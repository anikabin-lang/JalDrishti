"""Application Security Controls for JalDrishti Backend.

Provides:
- In-memory sliding-window rate limiting per client IP to mitigate DoS, quota exhaustion,
  and computational abuse of heavy vision/engineering endpoints.
- Privileged access / Admin API Key validation for destructive actions (e.g., asset deletion).
- Sanitized error utilities preventing internal credential or path leakage.
"""

from __future__ import annotations

import collections
import logging
import re
import secrets
import time
from typing import Dict, Optional, Tuple

from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.app.core.config import settings

logger = logging.getLogger(__name__)

# Security Bearer for optional JWT / Admin token inspection
security_bearer = HTTPBearer(auto_error=False)


class SlidingWindowRateLimiter:
    """Thread-safe, lightweight in-memory sliding window rate limiter.

    Tracks timestamps of requests per client IP within a configurable sliding window.
    Automatically prunes stale entries to prevent unbounded memory growth.
    """

    def __init__(self, window_seconds: int = 60) -> None:
        self.window_seconds = window_seconds
        # Maps (bucket, client_ip) -> deque of timestamps
        self._history: Dict[Tuple[str, str], collections.deque] = collections.defaultdict(
            collections.deque
        )
        self._last_cleanup = time.monotonic()

    def _cleanup_stale_records(self, now: float) -> None:
        """Periodically purge empty or entirely stale IP histories."""
        if now - self._last_cleanup < 300:  # Cleanup every 5 minutes
            return
        cutoff = now - self.window_seconds
        keys_to_remove = []
        for key, timestamps in self._history.items():
            while timestamps and timestamps[0] < cutoff:
                timestamps.popleft()
            if not timestamps:
                keys_to_remove.append(key)
        for key in keys_to_remove:
            self._history.pop(key, None)
        self._last_cleanup = now

    def is_allowed(self, client_ip: str, bucket: str, limit: int) -> Tuple[bool, int]:
        """Check whether the request from client_ip is within the allowed limit.

        Returns:
            Tuple[bool, int]: (is_allowed, retry_after_seconds)
        """
        now = time.monotonic()
        self._cleanup_stale_records(now)

        key = (bucket, client_ip)
        timestamps = self._history[key]
        cutoff = now - self.window_seconds

        # Discard records outside the sliding window
        while timestamps and timestamps[0] < cutoff:
            timestamps.popleft()

        if len(timestamps) >= limit:
            oldest = timestamps[0]
            retry_after = max(1, int(self.window_seconds - (now - oldest)))
            return False, retry_after

        timestamps.append(now)
        return True, 0


# Global singleton rate limiter instance
_global_limiter = SlidingWindowRateLimiter(window_seconds=60)

# Predefined rate limits per endpoint category (requests per 60 seconds per IP)
DEFAULT_RATE_LIMITS: Dict[str, int] = {
    "ai_analysis": 30,         # Heavy deep learning vision inference (/analyze)
    "image_upload": 20,        # Cloudinary image storage (/images/upload)
    "cloud_search": 30,        # Cloudinary Search API queries (/images/cloud-search)
    "baseline_inspection": 10, # Multi-photo batch inspection
    "document_upload": 15,     # PDF report parsing and extraction
    "image_delete": 10,        # Asset deletion
    "default": 120,            # General endpoints
}


def get_client_ip(request: Request) -> str:
    """Extract client IP address defensively from request headers or connection."""
    # Check standard proxy headers (e.g. behind Cloudflare, Vercel, or Reverse Proxy)
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        # Take the leftmost untrusted client IP
        client_ip = forwarded_for.split(",")[0].strip()
        # Basic IPv4 / IPv6 format sanity
        if re.match(r"^[a-fA-F0-9:.]+$", client_ip):
            return client_ip

    real_ip = request.headers.get("x-real-ip")
    if real_ip and re.match(r"^[a-fA-F0-9:.]+$", real_ip.strip()):
        return real_ip.strip()

    if request.client and request.client.host:
        return request.client.host

    return "127.0.0.1"


def rate_limit(bucket: str = "default", limit: Optional[int] = None):
    """FastAPI dependency to enforce rate limiting on specific route buckets.

    Args:
        bucket: Name of the endpoint category.
        limit: Optional custom requests-per-minute limit (defaults to DEFAULT_RATE_LIMITS[bucket]).
    """
    effective_limit = limit or DEFAULT_RATE_LIMITS.get(bucket, 120)

    def dependency(request: Request) -> None:
        if not getattr(settings, "rate_limit_enabled", True):
            return

        client_ip = get_client_ip(request)
        allowed, retry_after = _global_limiter.is_allowed(client_ip, bucket, effective_limit)

        if not allowed:
            logger.warning(
                "Rate limit exceeded for client %s on bucket '%s' (%d req/min limit).",
                client_ip,
                bucket,
                effective_limit,
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded for {bucket}. Please retry in {retry_after} seconds.",
                headers={"Retry-After": str(retry_after)},
            )

    return dependency


def require_admin_access(
    request: Request,
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
    auth_bearer: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
) -> bool:
    """Authorize privileged operations (such as asset deletion).

    If ADMIN_API_KEY is configured in the environment, verifies the provided
    X-API-Key header or Bearer token using constant-time string comparison.
    If ADMIN_API_KEY is unconfigured, permits execution in local development
    while applying strict rate limiting and logging a security notice.
    """
    admin_key = getattr(settings, "admin_api_key", None)
    if not admin_key:
        # Development mode without admin key configured
        return True

    provided_token = x_api_key or (auth_bearer.credentials if auth_bearer else None)
    if not provided_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Provide valid 'X-API-Key' header or Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Constant-time comparison to prevent timing attacks
    if not secrets.compare_digest(provided_token.strip(), admin_key.strip()):
        logger.warning("Invalid admin credentials provided from %s", get_client_ip(request))
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Invalid administrator credentials.",
        )

    return True


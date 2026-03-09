"""
Redis Cache & Session Service for ZeRoN 360°
Provides caching, JWT token management, and rate limiting support.
"""

import json
import hashlib
import logging
from typing import Optional, Any
from datetime import timedelta

import redis

from app.core.config import settings

logger = logging.getLogger(__name__)

# ── Redis Connection Pool ─────────────────────────────────────────────────────

_pool: Optional[redis.ConnectionPool] = None
_client: Optional[redis.Redis] = None


def get_redis() -> redis.Redis:
    """Get or create a Redis client with connection pooling."""
    global _pool, _client
    if _client is None:
        _pool = redis.ConnectionPool.from_url(
            settings.REDIS_URL,
            max_connections=20,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True,
        )
        _client = redis.Redis(connection_pool=_pool)
    return _client


def redis_health_check() -> bool:
    """Check if Redis is reachable."""
    try:
        return get_redis().ping()
    except Exception as e:
        logger.warning(f"Redis health check failed: {e}")
        return False


# ── Generic Cache ─────────────────────────────────────────────────────────────

def cache_get(key: str) -> Optional[Any]:
    """Get a cached value. Returns None if not found or Redis is down."""
    try:
        val = get_redis().get(key)
        if val is not None:
            return json.loads(val)
    except Exception as e:
        logger.warning(f"Redis cache_get error: {e}")
    return None


def cache_set(key: str, value: Any, ttl_seconds: int = 300) -> bool:
    """Set a cached value with TTL. Returns False if Redis is down."""
    try:
        get_redis().setex(key, ttl_seconds, json.dumps(value, default=str))
        return True
    except Exception as e:
        logger.warning(f"Redis cache_set error: {e}")
        return False


def cache_delete(key: str) -> bool:
    """Delete a cached key."""
    try:
        get_redis().delete(key)
        return True
    except Exception as e:
        logger.warning(f"Redis cache_delete error: {e}")
        return False


def cache_invalidate_pattern(pattern: str) -> int:
    """Delete all keys matching a pattern (e.g. 'dash:*'). Returns count deleted."""
    try:
        r = get_redis()
        keys = list(r.scan_iter(match=pattern, count=100))
        if keys:
            return r.delete(*keys)
    except Exception as e:
        logger.warning(f"Redis cache_invalidate error: {e}")
    return 0


def make_cache_key(*parts) -> str:
    """Build a deterministic cache key from parts."""
    raw = ":".join(str(p) for p in parts if p is not None)
    return f"zrn:{raw}"


def make_hash_key(params: dict) -> str:
    """Create a short hash from a dict of parameters for cache keys."""
    raw = json.dumps(params, sort_keys=True, default=str)
    return hashlib.md5(raw.encode()).hexdigest()[:12]


# ── JWT Token Management ─────────────────────────────────────────────────────

TOKEN_PREFIX = "zrn:token:"
BLACKLIST_PREFIX = "zrn:blacklist:"


def store_token(user_id: int, token: str, ttl_minutes: int = 480) -> bool:
    """Store an active JWT token in Redis for reference."""
    try:
        key = f"{TOKEN_PREFIX}{user_id}"
        get_redis().setex(key, ttl_minutes * 60, token)
        return True
    except Exception as e:
        logger.warning(f"Redis store_token error: {e}")
        return False


def blacklist_token(token: str, ttl_minutes: int = 480) -> bool:
    """Blacklist a JWT token (e.g., on logout). Token is invalid after this."""
    try:
        # Use the token hash as key to save memory
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        key = f"{BLACKLIST_PREFIX}{token_hash}"
        get_redis().setex(key, ttl_minutes * 60, "1")
        return True
    except Exception as e:
        logger.warning(f"Redis blacklist_token error: {e}")
        return False


def is_token_blacklisted(token: str) -> bool:
    """Check if a token has been blacklisted (logged out)."""
    try:
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        key = f"{BLACKLIST_PREFIX}{token_hash}"
        return get_redis().exists(key) > 0
    except Exception as e:
        logger.warning(f"Redis is_token_blacklisted error: {e}")
        return False  # Fail open — if Redis is down, don't block users


# ── Rate Limiting ─────────────────────────────────────────────────────────────

RATE_PREFIX = "zrn:rate:"


def check_rate_limit(identifier: str, max_requests: int, window_seconds: int) -> dict:
    """
    Check rate limit for an identifier (IP, user_id, etc).
    Returns: {"allowed": bool, "remaining": int, "retry_after": int}
    Uses Redis sliding window with INCR + EXPIRE.
    """
    try:
        r = get_redis()
        key = f"{RATE_PREFIX}{identifier}"
        current = r.get(key)

        if current is None:
            # First request in window
            pipe = r.pipeline()
            pipe.incr(key)
            pipe.expire(key, window_seconds)
            pipe.execute()
            return {"allowed": True, "remaining": max_requests - 1, "retry_after": 0}

        count = int(current)
        if count >= max_requests:
            ttl = r.ttl(key)
            return {"allowed": False, "remaining": 0, "retry_after": max(ttl, 1)}

        r.incr(key)
        return {"allowed": True, "remaining": max_requests - count - 1, "retry_after": 0}

    except Exception as e:
        logger.warning(f"Redis rate_limit error: {e}")
        return {"allowed": True, "remaining": max_requests, "retry_after": 0}  # Fail open


# ── Online Users ──────────────────────────────────────────────────────────────

ONLINE_PREFIX = "zrn:online:"


def set_user_online(user_id: int, ttl_seconds: int = 90) -> bool:
    """Mark a user as online with auto-expiry."""
    try:
        get_redis().setex(f"{ONLINE_PREFIX}{user_id}", ttl_seconds, "1")
        return True
    except Exception:
        return False


def get_online_users() -> list:
    """Get list of online user IDs."""
    try:
        r = get_redis()
        keys = list(r.scan_iter(match=f"{ONLINE_PREFIX}*", count=100))
        return [int(k.replace(ONLINE_PREFIX, "")) for k in keys]
    except Exception:
        return []

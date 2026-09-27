import json
import logging
import time
from typing import Any, Dict, Optional, Tuple

import redis.asyncio as aioredis

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class CacheProvider:
    """Manages Redis connections, read-through caching for stats,
    content-hash caching for AI triage, and distributed rate limiting.
    Includes in-memory fallback for offline test environments.
    """

    def __init__(self, redis_url: Optional[str] = None) -> None:
        settings = get_settings()
        self.redis_url = redis_url if redis_url is not None else settings.REDIS_URL
        self._redis: Optional[aioredis.Redis] = None
        self._last_failed_connect_time: float = 0.0
        self._in_memory_store: Dict[str, Tuple[str, float]] = {}
        self._in_memory_rate_limits: Dict[str, list[float]] = {}
        self._triage_hits: int = 0
        self._triage_misses: int = 0

    async def get_redis(self) -> Optional[aioredis.Redis]:
        # If disabled or explicitly empty, return None immediately
        if not self.redis_url or self.redis_url.startswith("none"):
            return None

        # Cooldown: If connection failed in the last 15 seconds, avoid waiting for socket timeout
        if time.time() - self._last_failed_connect_time < 15.0:
            return None

        if self._redis is None:
            try:
                client = aioredis.from_url(
                    self.redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                    socket_connect_timeout=0.5,
                )
                await client.ping()
                self._redis = client
            except Exception as e:
                self._last_failed_connect_time = time.time()
                logger.warning(
                    f"Redis unavailable ({e}), using in-memory cache/rate-limiter fallback."
                )
                self._redis = None
        return self._redis

    async def close(self) -> None:
        if self._redis is not None:
            await self._redis.close()
            self._redis = None

    # --- Job 1: Stats Read-Through Cache ---

    async def get_stats_cache(self) -> Tuple[Optional[Dict[str, Any]], bool]:
        """Returns (cached_stats_dict, is_cache_hit)."""
        cache_key = "civicpulse:cache:stats"
        r = await self.get_redis()
        if r:
            try:
                cached_data = await r.get(cache_key)
                if cached_data:
                    return json.loads(cached_data), True
                return None, False
            except Exception as e:
                logger.warning(f"Redis get_stats_cache error: {e}")

        # In-memory fallback
        now = time.time()
        if cache_key in self._in_memory_store:
            data_str, expiry = self._in_memory_store[cache_key]
            if now < expiry:
                return json.loads(data_str), True
            else:
                del self._in_memory_store[cache_key]
        return None, False

    async def set_stats_cache(self, stats: Dict[str, Any], ttl_seconds: int = 30) -> None:
        """Stores aggregated stats in cache with specified TTL."""
        cache_key = "civicpulse:cache:stats"
        val = json.dumps(stats)
        r = await self.get_redis()
        if r:
            try:
                await r.set(cache_key, val, ex=ttl_seconds)
                return
            except Exception as e:
                logger.warning(f"Redis set_stats_cache error: {e}")

        # In-memory fallback
        self._in_memory_store[cache_key] = (val, time.time() + ttl_seconds)

    async def invalidate_stats_cache(self) -> None:
        """Explicit cache invalidation on write (new complaint or status update)."""
        cache_key = "civicpulse:cache:stats"
        r = await self.get_redis()
        if r:
            try:
                await r.delete(cache_key)
            except Exception as e:
                logger.warning(f"Redis invalidate_stats_cache error: {e}")

        if cache_key in self._in_memory_store:
            del self._in_memory_store[cache_key]

    # --- AI Triage Content-Hash Cache (24h TTL) ---

    async def get_triage_cache(self, content_hash: str) -> Optional[Dict[str, Any]]:
        """Returns cached TriageResult dict if present, tracking hit rate."""
        cache_key = f"civicpulse:triage:{content_hash}"
        r = await self.get_redis()
        if r:
            try:
                cached_val = await r.get(cache_key)
                if cached_val:
                    self._triage_hits += 1
                    await r.incr("civicpulse:triage_stats:hits")
                    return json.loads(cached_val)
                self._triage_misses += 1
                await r.incr("civicpulse:triage_stats:misses")
                return None
            except Exception as e:
                logger.warning(f"Redis get_triage_cache error: {e}")

        # In-memory fallback
        now = time.time()
        if cache_key in self._in_memory_store:
            data_str, expiry = self._in_memory_store[cache_key]
            if now < expiry:
                self._triage_hits += 1
                return json.loads(data_str)
            else:
                del self._in_memory_store[cache_key]

        self._triage_misses += 1
        return None

    async def set_triage_cache(
        self, content_hash: str, triage_data: Dict[str, Any], ttl_seconds: int = 86400
    ) -> None:
        """Caches AI triage result by SHA-256 hash for 24 hours."""
        cache_key = f"civicpulse:triage:{content_hash}"
        val = json.dumps(triage_data)
        r = await self.get_redis()
        if r:
            try:
                await r.set(cache_key, val, ex=ttl_seconds)
                return
            except Exception as e:
                logger.warning(f"Redis set_triage_cache error: {e}")

        # In-memory fallback
        self._in_memory_store[cache_key] = (val, time.time() + ttl_seconds)

    async def get_triage_cache_metrics(self) -> Dict[str, Any]:
        """Returns content-hash triage cache hit metrics."""
        r = await self.get_redis()
        hits, misses = self._triage_hits, self._triage_misses
        if r:
            try:
                h = await r.get("civicpulse:triage_stats:hits")
                m = await r.get("civicpulse:triage_stats:misses")
                if h is not None:
                    hits = int(h)
                if m is not None:
                    misses = int(m)
            except Exception:
                pass

        total = hits + misses
        hit_rate = (hits / total) if total > 0 else 0.0
        return {"hits": hits, "misses": misses, "total": total, "hit_rate": round(hit_rate, 4)}

    # --- Job 2: Distributed IP-based Rate Limiter ---

    async def check_rate_limit(
        self, client_ip: str, limit: int = 60, window_seconds: int = 60
    ) -> Tuple[bool, int]:
        """Fixed-window distributed rate limiter in Redis.
        Returns (is_allowed, retry_after_seconds).
        """
        now = int(time.time())
        window_bucket = now // window_seconds
        cache_key = f"civicpulse:ratelimit:{client_ip}:{window_bucket}"
        retry_after = window_seconds - (now % window_seconds)

        r = await self.get_redis()
        if r:
            try:
                current_count = await r.incr(cache_key)
                if current_count == 1:
                    await r.expire(cache_key, window_seconds)

                if current_count > limit:
                    return False, max(1, retry_after)
                return True, 0
            except Exception as e:
                logger.warning(f"Redis rate limiter error: {e}")

        # In-memory sliding window fallback
        timestamps = self._in_memory_rate_limits.setdefault(client_ip, [])
        cutoff = time.time() - window_seconds
        # Filter older timestamps
        self._in_memory_rate_limits[client_ip] = [t for t in timestamps if t > cutoff]
        if len(self._in_memory_rate_limits[client_ip]) >= limit:
            return False, max(1, retry_after)

        self._in_memory_rate_limits[client_ip].append(time.time())
        return True, 0


# Global cache instance
cache_provider = CacheProvider()


async def get_cache_provider() -> CacheProvider:
    return cache_provider

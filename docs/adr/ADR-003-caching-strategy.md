# ADR-003: Caching Strategy

**Status:** Accepted  
**Date:** 2026-09-27  
**Deciders:** Development Team

## Context

CivicPulse serves aggregate statistics and processes AI triage calls that are computationally expensive. Without caching, every `/api/stats` request runs aggregate SQL queries, and every duplicate complaint triggers a redundant AI inference call.

## Decision

We use **Redis** as the primary cache with an **in-memory fallback** for resilience.

### Cache Layers

| Cache Key Pattern              | TTL      | Purpose                                     |
| ------------------------------ | -------- | ------------------------------------------- |
| `stats:all`                   | 30s      | Aggregate statistics (read-through)          |
| `triage:<sha256>`             | 24h      | AI triage results (content-hash key)         |
| `rate:<ip>:<window>`          | 60s      | Distributed rate limiter (sliding window)    |

### Cache Provider Interface

```python
class CacheProvider:
    async def get(self, key: str) -> Optional[str]
    async def set(self, key: str, value: str, ttl: int) -> None
    async def incr_rate(self, key: str, ttl: int) -> int
    async def close(self) -> None
```

### Fallback Behavior

If Redis is unavailable:
- Stats queries fall through to the database (no caching)
- Rate limiting is bypassed (fail-open to avoid blocking legitimate users)
- Triage caching is skipped (AI inference runs every time)
- The in-memory provider is used for tests to avoid Redis dependency

### Stats Response

The `/api/stats` response includes `"cache_hit": true|false` so the frontend can display a cache indicator (⚡ Cache Hit / 🔄 Fresh).

## Consequences

### Positive
- Significant latency reduction for stats (p99 < 50ms cached vs ~200ms uncached)
- No redundant AI API calls for identical complaints
- Graceful degradation when Redis is down

### Negative
- Stats may be up to 30s stale
- Cache invalidation is time-based, not event-driven (acceptable for this use case)

## Alternatives Considered

- **Application-level dict cache**: Not shared across backend replicas.
- **PostgreSQL materialized views**: Higher complexity; doesn't cover triage caching.

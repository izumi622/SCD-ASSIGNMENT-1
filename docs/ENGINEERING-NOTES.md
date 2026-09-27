# Engineering Notes

## Architecture Decisions

### Why Four Layers?

The four-layer pattern (Routes → Services → Repositories → Providers) was chosen over a simpler two-layer model because:

1. **Testability**: The service layer can be unit-tested with mock repositories, without needing a running database.
2. **AI Provider Isolation**: The Strategy pattern for triage providers lives in the provider layer, cleanly separated from business logic.
3. **State Machine Enforcement**: Status transitions (`open → in_progress → resolved`) are enforced in the service layer, not scattered across routes.

### Status State Machine

```
open ──→ in_progress ──→ resolved
  │                         
  └──→ rejected        rejected
```

Invalid transitions return `400 Bad Request` with a descriptive error. Terminal states (`resolved`, `rejected`) cannot transition further.

### AI Triage Fallback Chain

The triage system is designed to **never fail**. If the primary provider (LLM/Ollama) fails:

1. First retry with exponential backoff (3 attempts)
2. Fall back to `RuleBasedTriage` (keyword matching)
3. Fall back to `SimulatedTriage` (deterministic hash-based)

This ensures every complaint gets triaged, even during AI service outages.

### Content-Hash Caching

Triage results are cached using `SHA-256(description + location)` as the key. This means:
- Identical complaints produce identical cache keys → no redundant API calls
- Different wordings of the same issue → different keys (acceptable trade-off)
- TTL of 24 hours balances freshness vs cost

### Why Redis for Rate Limiting?

A distributed rate limiter using Redis `INCR` + `EXPIRE` was chosen over in-process counting because:
- It works correctly across multiple backend replicas
- The sliding window approach (per-minute) uses atomic Redis operations
- Fail-open behavior: if Redis is down, rate limiting is bypassed rather than blocking all requests

## Database Design

### Indexes

- **Composite index** on `(status, priority)` — covers the most common dashboard filter query
- **Single index** on `created_at` — supports date-range queries and sort-by-newest

### Idempotent Seeding

The seed script checks for existing data using `(location, description)` uniqueness before inserting. This makes it safe to run `python -m app.seed` multiple times.

## Frontend Design

### Runtime Configuration

The frontend reads `API_BASE_URL` from `/config.js` rather than baking it into the Vite build. This allows the same Docker image to be deployed to different environments by mounting a different `config.js`.

### Optimistic UI

Status transitions update the local state optimistically, then reconcile with the server response. Failed updates trigger a toast notification and revert the state.

## Docker

### Multi-Stage Builds

Both Dockerfiles use multi-stage builds:
- **Backend**: `python:3.12-slim` builder → `python:3.12-slim` runner (non-root `appuser`)
- **Frontend**: `node:20-alpine` builder → `nginx:1.25-alpine` runner

This minimizes image sizes and attack surface.

### Health Checks

Docker Compose and Kubernetes health checks use different probes:
- **Liveness** (`/health`): Is the process alive? (lightweight, no DB check)
- **Readiness** (`/ready`): Can it serve traffic? (checks DB + Redis connectivity)

## Observability

### Prometheus Metrics

Exposed at `/metrics` in OpenMetrics format:
- `http_requests_total{method, endpoint, status_code}` — Counter
- `http_request_duration_seconds{method, endpoint}` — Histogram
- Path normalization prevents cardinality explosion from UUIDs

### Structured Logging

All backend logs are JSON-formatted with:
- `request_id` (X-Request-ID propagation)
- `status_code`, `latency_ms`
- Correlation across request lifecycle

## Testing Strategy

- **Unit tests**: Service + triage provider logic with mocked repositories
- **Integration tests**: Full FastAPI `TestClient` with real async database
- **Determinism**: `SimulatedTriage` uses hash-based output for reproducible test results
- **Coverage target**: ≥ 75% line coverage on `app/` module

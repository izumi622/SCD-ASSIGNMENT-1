# CivicPulse Runbook

## Table of Contents

1. [Service Overview](#service-overview)
2. [Starting the Stack](#starting-the-stack)
3. [Health Checks](#health-checks)
4. [Common Operations](#common-operations)
5. [Troubleshooting](#troubleshooting)
6. [Scaling](#scaling)
7. [Disaster Recovery](#disaster-recovery)

---

## Service Overview

| Service    | Port | Technology       | Purpose                     |
| ---------- | ---- | ---------------- | --------------------------- |
| frontend   | 3000 | Nginx + React    | SPA serving + API proxy     |
| backend    | 8000 | FastAPI/Uvicorn  | REST API + AI triage        |
| postgres   | 5432 | PostgreSQL 16    | Persistent complaint data   |
| redis      | 6379 | Redis 7          | Cache + rate limiting       |

## Starting the Stack

### Development

```bash
cp .env.example .env
docker compose up --build -d
# Verify all services healthy
docker compose ps
```

### Production (Docker Compose)

```bash
docker compose -f docker-compose.yaml -f docker-compose.prod.yaml up -d
```

### Kubernetes

```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/secrets.yaml -f k8s/configmap.yaml
kubectl apply -f k8s/postgres.yaml -f k8s/redis.yaml
kubectl wait --for=condition=ready pod -l app=postgres -n civicpulse --timeout=60s
kubectl apply -f k8s/migration-job.yaml
kubectl wait --for=condition=complete job/migrations -n civicpulse --timeout=120s
kubectl apply -f k8s/backend.yaml -f k8s/frontend.yaml
kubectl apply -f k8s/ingress.yaml -f k8s/hpa.yaml
```

## Health Checks

| Endpoint   | Expected | Description                              |
| ---------- | -------- | ---------------------------------------- |
| `/health`  | `200`    | Liveness — backend process is running    |
| `/ready`   | `200`    | Readiness — database + Redis connected   |
| `/metrics` | `200`    | Prometheus metrics (text/plain)          |

```bash
# Quick health check
curl -s http://localhost:8000/health | jq .
curl -s http://localhost:8000/ready  | jq .
```

## Common Operations

### Run database migrations

```bash
# Docker Compose
docker compose run --rm migrations sh -c "alembic upgrade head"

# Kubernetes
kubectl apply -f k8s/migration-job.yaml
```

### Re-seed sample data

```bash
docker compose run --rm migrations sh -c "python -m app.seed"
```

### View logs

```bash
# All services
docker compose logs -f

# Backend only (structured JSON)
docker compose logs -f backend | jq -R 'fromjson? // .'
```

### Change AI triage provider

Edit `.env`:
```bash
TRIAGE_PROVIDER=rules  # or: llm, ollama, simulated
```

Then restart the backend:
```bash
docker compose restart backend
```

## Troubleshooting

### Backend returns 503 on all endpoints

**Cause:** Graceful shutdown in progress or backend crashed.

**Fix:**
```bash
docker compose restart backend
docker compose logs backend --tail 50
```

### Rate limit errors (429)

**Cause:** Client exceeded `RATE_LIMIT_PER_MINUTE` (default: 60).

**Fix:** Wait for the window to expire or increase the limit in `.env`.

### Redis connection errors in logs

**Cause:** Redis container not healthy or network issue.

**Fix:**
```bash
docker compose restart redis
# Verify
docker compose exec redis redis-cli ping
```

The backend falls back to in-memory cache when Redis is unavailable.

### Database connection pool exhaustion

**Symptoms:** 500 errors with "too many connections" in logs.

**Fix:**
```bash
# Check active connections
docker compose exec postgres psql -U civicpulse -c "SELECT count(*) FROM pg_stat_activity;"

# Restart to reset pool
docker compose restart backend
```

### AI triage returns generic results

**Cause:** Primary provider failed, fell back to `RuleBasedTriage` or `SimulatedTriage`.

**Fix:** Check `TRIAGE_PROVIDER`, API keys, and provider connectivity in logs.

## Scaling

### Docker Compose

```bash
docker compose up --scale backend=3
```

### Kubernetes HPA

The HPA is pre-configured:
- **Backend**: 2–8 replicas (CPU 70%, Memory 80%)
- **Frontend**: 2–6 replicas (CPU 75%)

Manual override:
```bash
kubectl scale deployment backend --replicas=5 -n civicpulse
```

## Disaster Recovery

### Database backup

```bash
docker compose exec postgres pg_dump -U civicpulse civicpulse_db > backup_$(date +%Y%m%d).sql
```

### Database restore

```bash
cat backup_20260927.sql | docker compose exec -T postgres psql -U civicpulse civicpulse_db
```

### Redis flush (if corrupted cache)

```bash
docker compose exec redis redis-cli FLUSHALL
```

# CivicPulse — Municipal Complaint Intake & AI Triage Platform

> A full-stack complaint management system with AI-powered triage, built with FastAPI, React/TypeScript, PostgreSQL, Redis, Docker, and Kubernetes.

## 🏗️ Architecture

```
┌──────────┐    ┌───────────────┐    ┌──────────────┐    ┌──────────┐
│ React UI │───▶│ FastAPI + AI  │───▶│ PostgreSQL   │    │  Redis   │
│ (Nginx)  │◀───│ Triage Engine │◀───│ (complaints) │    │ (cache)  │
└──────────┘    └───────────────┘    └──────────────┘    └──────────┘
       :80             :8000                :5432             :6379
```

**Four-layer backend**: Routes → Services → Repositories → Providers

## 🚀 Quick Start

### Prerequisites

- Docker Desktop ≥ 24.x
- Docker Compose v2

### 1. Clone & configure

```bash
git clone https://github.com/your-org/civicpulse.git
cd civicpulse
cp .env.example .env
```

### 2. Start the stack

```bash
docker compose up --build -d
```

This starts:

| Service      | URL                          |
| ------------ | ---------------------------- |
| Frontend     | http://localhost:3000         |
| Backend API  | http://localhost:8000         |
| API Docs     | http://localhost:8000/docs    |
| Health       | http://localhost:8000/health  |
| Readiness    | http://localhost:8000/ready   |
| Metrics      | http://localhost:8000/metrics |

### 3. Run migrations & seed data

The `migrations` service runs automatically on `docker compose up`.
To run manually:

```bash
docker compose run --rm migrations sh -c "alembic upgrade head && python -m app.seed"
```

### 4. Run tests

```bash
cd backend
pip install -r requirements.txt
pip install pytest pytest-asyncio pytest-cov httpx
pytest tests/ -v --cov=app --cov-report=term-missing
```

## 📁 Repository Structure

```
civicpulse/
├── backend/
│   ├── app/
│   │   ├── core/           # Config, database engine, logging
│   │   ├── models/         # SQLAlchemy models, Pydantic schemas, enums
│   │   ├── providers/      # AI triage, cache, metrics (Strategy pattern)
│   │   ├── repositories/   # Data access layer (async SQLAlchemy)
│   │   ├── routes/         # FastAPI routers (complaints, probes)
│   │   ├── services/       # Business logic, state machine
│   │   ├── main.py         # Application entry point
│   │   └── seed.py         # Idempotent seed data
│   ├── alembic/            # Database migrations
│   ├── tests/              # pytest suite
│   ├── Dockerfile          # Multi-stage backend image
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/            # Typed API client
│   │   ├── components/     # Reusable React components
│   │   ├── hooks/          # Custom React hooks
│   │   └── pages/          # Page-level components
│   ├── Dockerfile          # Multi-stage frontend image (Vite → Nginx)
│   └── nginx.conf          # Reverse proxy config
├── k8s/                    # Kubernetes manifests
│   ├── namespace.yaml
│   ├── secrets.yaml
│   ├── configmap.yaml
│   ├── postgres.yaml
│   ├── redis.yaml
│   ├── backend.yaml
│   ├── frontend.yaml
│   ├── ingress.yaml
│   ├── hpa.yaml
│   └── migration-job.yaml
├── .github/workflows/      # CI/CD pipelines
│   ├── ci.yaml             # Lint + test + build
│   └── cd.yaml             # Build & push images on tag
├── docs/                   # Architecture Decision Records + operational docs
├── docker-compose.yaml     # Development stack
├── docker-compose.prod.yaml# Production overrides
└── .env.example
```

## 🤖 AI Triage Providers

| Provider     | `TRIAGE_PROVIDER` | Description                                     |
| ------------ | ----------------- | ----------------------------------------------- |
| Hosted LLM   | `llm`             | OpenAI-compatible API (Groq, OpenAI, etc.)     |
| Ollama        | `ollama`          | Local Ollama instance for offline inference     |
| Rule-Based    | `rules`           | Deterministic keyword matching (no API needed)  |
| Simulated     | `simulated`       | Hash-based deterministic output (for testing)   |

All providers implement the same `TriageProvider` interface with:
- **Validation**: Structured JSON output parsing
- **Timeout**: 30s configurable timeout
- **Retry**: 3 attempts with exponential backoff
- **Fallback**: Automatic cascade to `rules` → `simulated` on failure
- **Caching**: 24h content-hash-based Redis cache

## 🔧 API Endpoints

| Method  | Path                              | Description              |
| ------- | --------------------------------- | ------------------------ |
| `POST`  | `/api/complaints`                 | Submit new complaint     |
| `GET`   | `/api/complaints`                 | List (paginated, filter) |
| `GET`   | `/api/complaints/{id}`            | Get single complaint     |
| `PATCH` | `/api/complaints/{id}`            | Update status            |
| `GET`   | `/api/stats`                      | Aggregate statistics     |
| `GET`   | `/health`                         | Liveness probe           |
| `GET`   | `/ready`                          | Readiness probe          |
| `GET`   | `/metrics`                        | Prometheus metrics       |

## ☸️ Kubernetes Deployment

```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/postgres.yaml
kubectl apply -f k8s/redis.yaml
kubectl apply -f k8s/migration-job.yaml
kubectl wait --for=condition=complete job/migrations -n civicpulse --timeout=120s
kubectl apply -f k8s/backend.yaml
kubectl apply -f k8s/frontend.yaml
kubectl apply -f k8s/ingress.yaml
kubectl apply -f k8s/hpa.yaml
```

HPA scales backend 2–8 replicas (CPU 70%, memory 80%) and frontend 2–6 replicas (CPU 75%).

## 📚 Documentation

- [ADR-001: Four-Layer Architecture](docs/adr/ADR-001-four-layer-architecture.md)
- [ADR-002: AI Triage Strategy Pattern](docs/adr/ADR-002-ai-triage-strategy.md)
- [ADR-003: Caching Strategy](docs/adr/ADR-003-caching-strategy.md)
- [Runbook](docs/RUNBOOK.md)
- [Engineering Notes](docs/ENGINEERING-NOTES.md)
- [AI Usage Disclosure](docs/AI-USAGE.md)

## 📄 License

MIT — See [LICENSE](LICENSE).

# CivicPulse Requirements Checklist & Rubric Traceability

Based on `CivicPulse_Assignment_1.md` (CS4032 - Software Construction and Design).

---

## 1. Collaboration & Version Control (15 Marks)
- [ ] Git repository initialized with `main` and `dev` branch structure.
- [ ] Conventional commit messages (`feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`).
- [ ] `.gitignore` configured to strictly prevent committing `.env`, credentials, pycache, node_modules.
- [ ] Documentation of branch protection rules, required CI checks, and PR workflow in `docs/evidence/`.
- [ ] Prepared merge conflict scenario script/documentation in `docs/evidence/merge-conflict.md`.

---

## 2. Frontend Layer (18 Marks)
- [ ] Stack: React 18 + Vite + TypeScript.
- [ ] Serving: Multi-stage Dockerfile using `node:22-alpine` builder and `nginx:1.27-alpine` runtime.
- [ ] Presentation only: Zero business rules, status transitions or triage categories hardcoded as business logic.
- [ ] **Submit View**:
  - Free-text complaint (10–2000 chars), location (3–200 chars), optional contact.
  - Client-side validation mirroring server constraints.
  - Honest loading state reflecting multi-second AI inference.
  - Display result: Category, Priority, AI Summary, Triaged By provider, Latency.
- [ ] **Dashboard View**:
  - Filterable by Category, Priority, Status.
  - Paginated list (with total count).
  - Status transition controls with immediate feedback.
  - Verbatim display of server 409 conflict errors on invalid state transition.
- [ ] **Stats View**:
  - Aggregated metrics by category and priority.
  - Real-time display of cache state (`X-Cache: HIT` or `X-Cache: MISS`).
- [ ] **Runtime Configuration**:
  - Build-once-deploy-many: Dynamic API proxy via Nginx (`/api/`) and dynamic `/config.js` support.
  - Documented in `docs/adr/0002-frontend-runtime-config.md`.
- [ ] **Component Tests**:
  - $\ge 5$ Vitest component tests covering Submit, Dashboard, Stats, and error handling.

---

## 3. Backend Layer (25 Marks)
- [ ] Stack: FastAPI + Pydantic v2 + SQLAlchemy (async/sync).
- [ ] Strict 4-layer architecture:
  - `app/routes/`: HTTP handling, serialization, status codes. No business rules or direct DB session logic.
  - `app/services/`: Business rules, triage orchestration, status transition state machine, stats aggregation.
  - `app/repositories/`: Persistence layer. All SQL queries live here.
  - `app/providers/`: Outbound integrations (AI triage, Redis cache, metrics) behind interfaces.
- [ ] API Contract Endpoints (10 endpoints):
  1. `POST /api/complaints`: Validate $\to$ triage $\to$ persist (201, 400 with field errors, 429 on rate limit).
  2. `GET /api/complaints/{id}`: Return complaint by UUID (200 / 404).
  3. `GET /api/complaints`: Filter (category, priority, status), paginate (`page`, `page_size` $\le 100$), return `total`.
  4. `PATCH /api/complaints/{id}/status`: Enforce state machine table; return 409 naming attempted transition on failure.
  5. `GET /api/stats`: Category & priority aggregates, Redis-cached with 30s TTL, `X-Cache` header.
  6. `GET /api/meta/providers`: Active triage provider + rolling window of last 20 triage outcomes (provider, latency_ms, fallback).
  7. `GET /health`: Liveness probe — process alive, does NOT touch database.
  8. `GET /ready`: Readiness probe — 200 only if PostgreSQL and Redis are both reachable; 503 naming failed dependency.
  9. `GET /metrics`: Prometheus metrics (request count, latency histogram, triage latency, fallback counter).
  10. OpenAPI documentation (`/docs`, `/openapi.json`).
- [ ] Domain Rules:
  - Status State Machine: Explicit transition table (`open` $\to$ `in_progress` $\to$ `resolved`; `open` $\to$ `rejected`; `in_progress` $\to$ `rejected`). Terminal states: `resolved`, `rejected`.
  - Graceful Shutdown: Handle `SIGTERM` / `SIGINT` gracefully draining in-flight requests.
  - Structured Logging: JSON to stdout with `request_id` propagated via `X-Request-ID`. Warning logged on fallback.
- [ ] Testing:
  - $\ge 14$ tests (unit and integration), 100% deterministic with `SimulatedTriage`, test coverage $\ge 65\%$.
  - Explicit test asserting fallback on provider exception.
  - Explicit test asserting prompt injection resistance.

---

## 4. Data Layer (12 Marks)
- [ ] PostgreSQL 16 managed exclusively via Alembic migrations (zero DDL on app startup).
- [ ] Schema:
  - `id`: UUID primary key, server-generated.
  - `text`: VARCHAR(2000), CHECK constraint `length(text) >= 10`.
  - `location`: VARCHAR(200), CHECK constraint `length(location) >= 3`.
  - `reporter_contact`: VARCHAR(255), nullable.
  - `category`: Enum (`water`, `electricity`, `sanitation`, `roads`, `streetlights`, `other`).
  - `priority`: Enum (`high`, `normal`, `low`).
  - `status`: Enum (`open`, `in_progress`, `resolved`, `rejected`), default `open`.
  - `ai_summary`: VARCHAR(140), nullable.
  - `triaged_by`: VARCHAR(64) (`llm:groq`, `llm:ollama`, `rules`, `rules:fallback`, `simulated`).
  - `triage_latency_ms`: INTEGER.
  - `created_at`, `updated_at`: TIMESTAMPTZ (UTC).
- [ ] Indexes:
  - Compound index on `(status, priority)`.
  - Index on `created_at`.
  - Justifications documented in `docs/ENGINEERING-NOTES.md`.
- [ ] Idempotent Seeding:
  - CLI script `python -m app.seed` loading $\ge 30$ realistic complaints in Urdu-influenced English.
  - Re-running script produces zero duplicates.

---

## 5. Cache & Rate Limiting Layer (10 Marks)
- [ ] Redis 7 instance serving dual purposes.
- [ ] Job 1: Read-through cache for `/api/stats` with 30s TTL and `X-Cache: HIT|MISS` headers.
- [ ] Write-invalidation: Immediate cache invalidation on complaint creation or status update.
- [ ] Job 2: Distributed IP-based rate limiter on `POST /api/complaints` returning 429 with `Retry-After`.
- [ ] Persistence: Redis AOF enabled with named volume `redisdata`, justified in docs.

---

## 6. AI Triage Layer (25 Marks)
- [ ] `TriageResult` Pydantic model (`category`, `priority`, `summary` $\le 140$, `confidence` $\in [0, 1]$).
- [ ] `TriageProvider` Protocol with 4 implementations:
  1. `LLMTriage`: Hosted provider (Groq / Gemini / OpenRouter) with structured output.
  2. `OllamaTriage`: Local offline containerized LLM.
  3. `RuleBasedTriage`: Deterministic keyword fallback.
  4. `SimulatedTriage`: Deterministic fake for CI with error-injection triggers.
- [ ] Robustness features:
  - 10-second hard timeout.
  - Single jittered retry on retryable codes (timeout, 429, 5xx) — never on 400.
  - Automatic fallback to `RuleBasedTriage` logging warning with `triaged_by = "rules:fallback"`.
  - 24-hour content-hash caching in Redis for duplicate complaints.
  - Prompt-injection guardrail treating complaint text as untrusted data.
- [ ] Latency and Observability:
  - Latency in milliseconds tracked and stored in database.
  - Exposed via `/api/meta/providers` and Prometheus `/metrics`.
- [ ] PII/Data Governance ADR in `docs/adr/0004-pii-and-data-governance.md`.

---

## 7. Containerization & Docker Compose (15 Marks)
- [ ] Multi-stage Dockerfiles:
  - Backend: `python:3.12-slim`, builder stage, non-root user, exec form CMD, healthcheck.
  - Frontend: `node:22-alpine` builder, `nginx:1.27-alpine` runtime, non-root user, slim (<60MB target).
- [ ] `.dockerignore` for both frontend and backend build contexts.
- [ ] Dual-network segmentation:
  - `edge`: bridge (frontend $\leftrightarrow$ backend).
  - `internal`: bridge, `internal: true` (backend $\leftrightarrow$ postgres $\leftrightarrow$ redis).
  - Verifiable isolation: Frontend container cannot ping or route to Postgres.
- [ ] Volumes:
  - `pgdata` (PostgreSQL), `redisdata` (Redis AOF), `ollama_models` (Ollama weights).
- [ ] Development (`compose.yaml`): Local source bind mounts, exposed debug ports.
- [ ] Production (`compose.prod.yaml`): Immutable image references `${IMAGE_TAG}`, no build directives, no exposed DB/cache ports.
- [ ] Healthchecks and `depends_on: condition: service_healthy` for all services.

---

## 8. Kubernetes & Autoscaling (20 Marks)
- [ ] Namespace: Dedicated `civicpulse` namespace.
- [ ] Workloads:
  - Backend `Deployment` ($\ge 2$ replicas).
  - Frontend `Deployment` ($\ge 2$ replicas).
  - Postgres `StatefulSet` with `volumeClaimTemplates` $\to$ PVC.
  - Redis `Deployment` with PVC.
- [ ] Services: ClusterIP for all internal components (no NodePort/LoadBalancer on DB).
- [ ] Ingress: Single host routing `/` $\to$ frontend and `/api` $\to$ backend.
- [ ] Probes:
  - `startupProbe`: `/health` with generous threshold.
  - `livenessProbe`: `/health` (independent of database).
  - `readinessProbe`: `/ready` (dependent on database and Redis).
- [ ] Resources: Explicit `requests` and `limits` on all containers.
- [ ] Rolling update policy: `maxSurge: 1`, `maxUnavailable: 0`, `terminationGracePeriodSeconds`, `preStop` hook.
- [ ] Autoscaling:
  - HPA v2 configuration targeting 60% CPU utilization with scale-up/scale-down stabilization windows.
  - VPA configuration in recommender mode (`updateMode: "Off"`).
  - PodDisruptionBudget with `minAvailable: 1`.
- [ ] Kustomize directory structure: `k8s/base/` and `k8s/overlays/{dev,prod}/`.

---

## 9. CI/CD Workflows (20 Marks)
- [ ] `.github/workflows/ci.yml`:
  - Lint and type checking (`ruff`, `mypy`, `eslint`, `tsc --noEmit`).
  - Backend test with coverage $\ge 65\%$.
  - Frontend Vitest suite.
  - Docker multi-stage build test.
  - Trivy vulnerability scanning.
  - Kubeconform manifest validation.
  - Docker Compose integration smoke test.
- [ ] `.github/workflows/cd.yml`:
  - Triggered on push to `main` with `needs: test` gating.
  - Build and push to GHCR with commit SHA and latest tags.
  - Syft SBOM generation.
  - Automated deployment to test cluster and smoke test.
- [ ] `.github/workflows/release.yml`: Tag-based release pipeline.
- [ ] Least-privilege permissions blocks and secrets security.

---

## 10. Documentation & Verification (15 Marks + Bonus)
- [ ] `README.md` with problem statement, quickstart, architecture diagram, API table.
- [ ] 4 Architecture Decision Records (ADRs) in `docs/adr/`.
- [ ] `docs/RUNBOOK.md`.
- [ ] `docs/ENGINEERING-NOTES.md` answering all 8 questions in §5.2.
- [ ] `docs/AI-USAGE.md` documenting transparent AI tool usage.
- [ ] `docs/TRIAGE.md` detailing triage pipeline and resilience.
- [ ] `scripts/check_submission.py` automated submission lint tool.

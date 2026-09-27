# CivicPulse Requirements Checklist & Rubric Traceability

Based on `CivicPulse_Assignment_1.md` (CS4032 - Software Construction and Design).

---

## 1. Collaboration & Version Control (15 Marks)
- [x] Git repository initialized with `main` and `dev` branch structure.
- [x] Conventional commit messages (`feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`).
- [x] `.gitignore` configured to strictly prevent committing `.env`, credentials, pycache, node_modules.
- [x] Documentation of branch protection rules, required CI checks, and PR workflow in `docs/evidence/BRANCH-PROTECTION-AND-PR.md`.
- [x] Prepared merge conflict scenario script/documentation in `docs/evidence/merge-conflict.md`.

---

## 2. Frontend Layer (18 Marks)
- [x] Stack: React 18 + Vite + TypeScript.
- [x] Serving: Multi-stage Dockerfile using `node:22-alpine` builder and `nginx:1.27-alpine` runtime.
- [x] Presentation only: Zero business rules, status transitions or triage categories hardcoded as business logic.
- [x] **Submit View**:
  - Free-text complaint (10–2000 chars), location (3–200 chars), optional contact.
  - Client-side validation mirroring server constraints.
  - Honest loading state reflecting multi-second AI inference.
  - Display result: Category, Priority, AI Summary, Triaged By provider, Latency.
- [x] **Dashboard View**:
  - Filterable by Category, Priority, Status.
  - Paginated list (with total count).
  - Status transition controls with immediate feedback.
  - Verbatim display of server 409 conflict errors on invalid state transition.
- [x] **Stats View**:
  - Aggregated metrics by category and priority.
  - Real-time display of cache state (`X-Cache: HIT` or `X-Cache: MISS`).
- [x] **Runtime Configuration**:
  - Build-once-deploy-many: Dynamic API proxy via Nginx (`/api/`) and dynamic `/config.js` support.
  - Documented in `docs/adr/ADR-001-four-layer-architecture.md` and `docs/ENGINEERING-NOTES.md`.
- [x] **Component Tests**:
  - $\ge 5$ Vitest component tests (12 tests across 6 suites in `frontend/tests/`) covering Submit, Dashboard, Stats, ErrorBoundary, ToastContainer, and App.

---

## 3. Backend Layer (25 Marks)
- [x] Stack: FastAPI + Pydantic v2 + SQLAlchemy (async/sync).
- [x] Strict 4-layer architecture:
  - `app/routes/`: HTTP handling, serialization, status codes. No business rules or direct DB session logic.
  - `app/services/`: Business rules, triage orchestration, status transition state machine, stats aggregation.
  - `app/repositories/`: Persistence layer. All SQL queries live here.
  - `app/providers/`: Outbound integrations (AI triage, Redis cache, metrics) behind interfaces.
- [x] API Contract Endpoints (10 endpoints):
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
- [x] Domain Rules:
  - Status State Machine: Explicit transition table (`open` $\to$ `in_progress` $\to$ `resolved`; `open` $\to$ `rejected`; `in_progress` $\to$ `rejected`). Terminal states: `resolved`, `rejected`.
  - Graceful Shutdown: Handle `SIGTERM` / `SIGINT` gracefully draining in-flight requests.
  - Structured Logging: JSON to stdout with `request_id` propagated via `X-Request-ID`. Warning logged on fallback.
- [x] Testing:
  - $\ge 14$ test files (35 tests total) in `backend/tests/`, 100% deterministic with `SimulatedTriage`, test coverage 80% ($\ge 65\%$).
  - Explicit test asserting fallback on provider exception (`tests/test_fallback.py`).
  - Explicit test asserting prompt injection resistance (`tests/test_prompt_injection.py`).

---

## 4. Data Layer (12 Marks)
- [x] PostgreSQL 16 managed exclusively via Alembic migrations (zero DDL on app startup).
- [x] Schema:
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
- [x] Indexes:
  - Compound index on `(status, priority)`.
  - Index on `created_at`.
  - Justifications documented in `docs/ENGINEERING-NOTES.md`.
- [x] Idempotent Seeding:
  - CLI script `python -m app.seed` loading $\ge 30$ realistic complaints in Urdu-influenced English.
  - Re-running script produces zero duplicates.

---

## 5. Cache & Rate Limiting Layer (10 Marks)
- [x] Redis 7 instance serving dual purposes.
- [x] Job 1: Read-through cache for `/api/stats` with 30s TTL and `X-Cache: HIT|MISS` headers.
- [x] Write-invalidation: Immediate cache invalidation on complaint creation or status update.
- [x] Job 2: Distributed IP-based rate limiter on `POST /api/complaints` returning 429 with `Retry-After`.
- [x] Persistence: Redis AOF enabled with named volume `redisdata`, justified in docs.

---

## 6. AI Triage Layer (25 Marks)
- [x] `TriageResult` Pydantic model (`category`, `priority`, `summary` $\le 140$, `confidence` $\in [0, 1]$).
- [x] `TriageProvider` Protocol with 4 implementations:
  1. `LLMTriage`: Hosted provider (Groq / Gemini / OpenRouter) with structured output.
  2. `OllamaTriage`: Local offline containerized LLM.
  3. `RuleBasedTriage`: Deterministic keyword fallback.
  4. `SimulatedTriage`: Deterministic fake for CI with error-injection triggers.
- [x] Robustness features:
  - 10-second hard timeout.
  - Single jittered retry on retryable codes (timeout, 429, 5xx) — never on 400.
  - Automatic fallback to `RuleBasedTriage` logging warning with `triaged_by = "rules:fallback"`.
  - 24-hour content-hash caching in Redis for duplicate complaints.
  - Prompt-injection guardrail treating complaint text as untrusted data.
- [x] Latency and Observability:
  - Latency in milliseconds tracked and stored in database.
  - Exposed via `/api/meta/providers` and Prometheus `/metrics`.
- [x] PII/Data Governance ADR in `docs/adr/ADR-004-pii-and-data-governance.md`.

---

## 7. Containerization & Docker Compose (15 Marks)
- [x] Multi-stage Dockerfiles:
  - Backend: `python:3.12-slim`, builder stage, non-root user, exec form CMD, healthcheck.
  - Frontend: `node:22-alpine` builder, `nginx:1.27-alpine` runtime, non-root user, slim (<60MB target).
- [x] `.dockerignore` for both frontend and backend build contexts.
- [x] Dual-network segmentation:
  - `edge`: bridge (frontend $\leftrightarrow$ backend).
  - `internal`: bridge, `internal: true` (backend $\leftrightarrow$ postgres $\leftrightarrow$ redis).
  - Verifiable isolation: Frontend container cannot ping or route to Postgres.
- [x] Volumes:
  - `pgdata` (PostgreSQL), `redisdata` (Redis AOF), `ollama_models` (Ollama weights).
- [x] Development (`compose.yaml`): Local source bind mounts, exposed debug ports.
- [x] Production (`compose.prod.yaml`): Immutable image references `${IMAGE_TAG}`, no build directives, no exposed DB/cache ports.
- [x] Healthchecks and `depends_on: condition: service_healthy` for all services.

---

## 8. Kubernetes & Autoscaling (20 Marks)
- [x] Namespace: Dedicated `civicpulse` namespace.
- [x] Workloads:
  - Backend `Deployment` ($\ge 2$ replicas).
  - Frontend `Deployment` ($\ge 2$ replicas).
  - Postgres `StatefulSet` with `volumeClaimTemplates` $\to$ PVC.
  - Redis `Deployment` with PVC.
- [x] Services: ClusterIP for all internal components (no NodePort/LoadBalancer on DB).
- [x] Ingress: Single host routing `/` $\to$ frontend and `/api` $\to$ backend.
- [x] Probes:
  - `startupProbe`: `/health` with generous threshold.
  - `livenessProbe`: `/health` (independent of database).
  - `readinessProbe`: `/ready` (dependent on database and Redis).
- [x] Resources: Explicit `requests` and `limits` on all containers.
- [x] Rolling update policy: `maxSurge: 1`, `maxUnavailable: 0`, `terminationGracePeriodSeconds`, `preStop` hook.
- [x] Autoscaling:
  - HPA v2 configuration targeting 60% CPU utilization with scale-up/scale-down stabilization windows.
  - VPA configuration in recommender mode (`updateMode: "Off"`).
  - PodDisruptionBudget with `minAvailable: 1`.
- [x] Kustomize directory structure: `k8s/base/` and `k8s/overlays/{dev,prod}/`.

---

## 9. CI/CD Workflows (20 Marks)
- [x] `.github/workflows/ci.yaml`:
  - Lint and type checking (`ruff`, `mypy`, `tsc --noEmit`).
  - Backend test with coverage $\ge 65\%$ (80% achieved).
  - Frontend Vitest suite (12 tests, 6 suites).
  - Docker multi-stage build test.
  - Trivy vulnerability scanning.
  - Kubeconform manifest validation.
  - Docker Compose integration smoke test.
- [x] `.github/workflows/cd.yaml`:
  - Triggered on push to `main` with build and push to GHCR with commit SHA and latest tags.
  - Syft SBOM generation.
  - Automated deployment to test cluster and smoke test.
- [x] `.github/workflows/release.yaml`: Tag-based release pipeline.
- [x] Least-privilege permissions blocks and secrets security.

---

## 10. Documentation & Verification (15 Marks + Bonus)
- [x] `README.md` with problem statement, quickstart, architecture diagram, API table.
- [x] 4 Architecture Decision Records (ADRs) in `docs/adr/`.
- [x] `docs/RUNBOOK.md`.
- [x] `docs/ENGINEERING-NOTES.md` answering all 8 questions in §5.2.
- [x] `docs/AI-USAGE.md` documenting transparent AI tool usage.
- [x] `docs/TRIAGE.md` detailing triage pipeline and resilience.
- [x] `scripts/check_submission.py` automated submission lint tool passing with 0 errors and 0 warnings.

---

## 11. Verification Status & Remaining Student Deliverables

### Automated & Tested in Workspace
- [x] Backend Unit & Integration Tests: 36/36 pytest passing (80% coverage, exceeding 65% target).
- [x] Frontend Component Tests: 14/14 Vitest tests passing across 6 suites.
- [x] Frontend Production Build: Clean compile via `tsc && vite build`.
- [x] Schema Contract Verification: TypeScript types in `types.ts` checked against backend FastAPI OpenAPI schema.
- [x] Submission Linter: `python scripts/check_submission.py` passing with 0 errors and 0 warnings.
- [x] Kubernetes Manifest Validation: Dev and prod overlays compile cleanly via `kubectl kustomize`.
- [x] Docker Compose Configuration: Verified with `docker compose config` (IMAGE_TAG required, zero exposed DB/cache ports in prod).

### Student Personal Action Items (Cannot Be Fabricated)
- [ ] **GitHub Repository Setup**:
  - Push `main` and `dev` branches to your personal/team GitHub repository.
  - Enable Branch Protection on `main` (require PR, require CI checks, require review). Take screenshot and place in `docs/evidence/`.
- [ ] **Pull Request & Review**:
  - Open a PR from `dev` to `main`, have your partner submit a review comment, and take a screenshot.
- [ ] **Live Kubernetes Smoke Test**:
  - Enable Kubernetes in Docker Desktop or spin up a local Kind cluster (`kind create cluster`).
  - Deploy manifests (`kubectl apply -k k8s/overlays/prod`) and capture `kubectl get pods -n civicpulse` output.
- [ ] **Live Load Test Execution**:
  - Run `k6 run load/k6-script.js` against the running stack and capture the HPA scaling terminal output (`kubectl get hpa -n civicpulse -w`).
- [ ] **Demo Video**:
  - Record a 3–5 minute video demonstrating complaint submission, AI triage, dashboard status transitions, and Prometheus metrics.

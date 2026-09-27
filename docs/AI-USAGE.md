# AI Usage Disclosure

This document discloses how AI tools were used during the development of CivicPulse, in accordance with the assignment's honest disclosure requirements.

## AI Tools Used

| Tool                  | Purpose                                                   |
| --------------------- | --------------------------------------------------------- |
| Google Gemini (Antigravity) | Code generation, architecture design, documentation |

## Scope of AI Assistance

### Architecture & Design
- AI assisted in designing the four-layer backend architecture (Routes → Services → Repositories → Providers).
- AI recommended the Strategy pattern for the triage provider system with fallback chain.
- AI suggested the content-hash caching approach for triage results.

### Code Generation
- AI generated the initial scaffolding for FastAPI routes, SQLAlchemy models, Pydantic schemas, and React components.
- AI wrote the Docker Compose configuration, Kubernetes manifests, and GitHub Actions workflows.
- AI generated the Alembic migration scripts.

### Testing
- AI wrote the pytest test suite covering service logic, triage providers, and API endpoints.
- AI designed the `SimulatedTriage` provider specifically for deterministic test execution.

### Documentation
- AI generated the README, ADRs, RUNBOOK, and these engineering notes.
- AI wrote inline code comments and docstrings.

## Human Contributions

- **Requirements Analysis**: The developer interpreted the assignment specification and translated requirements into implementation tasks.
- **Review & Validation**: All AI-generated code was reviewed, tested, and corrected by the developer before inclusion.
- **Environment Setup**: Docker Desktop, database provisioning, and local development configuration were done manually.
- **Debugging**: Runtime issues (Windows compatibility, dependency conflicts, async database session management) were diagnosed and resolved with human judgement.
- **Design Decisions**: Final architectural decisions were made by the developer, informed by AI suggestions.

## Verification

- All backend tests pass (`pytest tests/ -v`).
- Docker Compose stack builds and runs successfully.
- Frontend compiles without TypeScript errors.
- Linting passes (`ruff check .` and `ruff format --check .`).

## Ethical Statement

AI was used as a productivity tool to accelerate development, not to bypass understanding. The developer comprehends all code in the repository and can explain every design decision documented in the ADRs.

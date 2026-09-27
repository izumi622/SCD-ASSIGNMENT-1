# ADR-001: Four-Layer Backend Architecture

**Status:** Accepted  
**Date:** 2026-09-27  
**Deciders:** Development Team

## Context

The CivicPulse backend must support multiple AI triage providers, caching strategies, and data access patterns while remaining testable and maintainable. A monolithic approach would tightly couple routes to database access and AI provider calls.

## Decision

We adopt a **four-layer architecture**:

1. **Routes** — HTTP request parsing, validation, and response formatting. No business logic.
2. **Services** — Business rules, status state machine enforcement, orchestration of repositories and providers.
3. **Repositories** — Data access layer encapsulating all SQLAlchemy queries. Returns domain models.
4. **Providers** — External integrations (AI triage, Redis cache, Prometheus metrics). Each uses the Strategy pattern.

### Dependency Flow

```
Routes → Services → Repositories → Database
                  → Providers    → Redis / AI APIs
```

FastAPI's `Depends()` injects service instances into routes, enabling clean testability.

## Consequences

### Positive
- **Testability**: Services can be tested with mock repositories/providers.
- **Separation of Concerns**: Route handlers are thin; business logic is centralized.
- **Provider Swappability**: New AI providers implement `TriageProvider` without touching services.

### Negative
- Slightly more boilerplate for simple CRUD operations.
- Developers must understand the layer boundaries.

## Alternatives Considered

- **Two-layer (Routes + Models)**: Simpler but mixes concerns; hard to test AI fallback logic.
- **Hexagonal Architecture**: More formal but over-engineered for current scope.

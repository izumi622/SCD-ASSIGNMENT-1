# ADR-002: AI Triage Strategy Pattern

**Status:** Accepted  
**Date:** 2026-09-27  
**Deciders:** Development Team

## Context

CivicPulse requires AI-powered triage of incoming complaints to classify priority, category, and generate summaries. The system must support multiple AI backends (hosted LLM, local Ollama, rule-based, simulated) and gracefully handle failures.

## Decision

We implement the **Strategy Pattern** with a common `TriageProvider` interface:

```python
class TriageProvider(ABC):
    @abstractmethod
    async def triage(self, text: str, location: str) -> TriageResult:
        ...
```

### Implementations

| Provider        | Purpose                    | Fallback Order |
| --------------- | -------------------------- | -------------- |
| `LLMTriage`     | Production (Groq/OpenAI)   | 1st            |
| `OllamaTriage`  | Offline / local dev        | 2nd            |
| `RuleBasedTriage` | No-API deterministic     | 3rd            |
| `SimulatedTriage` | Testing (hash-based)     | 4th (terminal) |

### Resilience Chain

Each provider wraps calls with:
1. **Timeout** (30s configurable)
2. **Retry** (3 attempts, exponential backoff)
3. **JSON validation** (structured output parsing)
4. **Fallback** cascade: `primary → rules → simulated`

### Caching

Triage results are cached in Redis using a SHA-256 content hash of `(text + location)`, with a 24-hour TTL. This avoids redundant API calls for identical complaints.

## Consequences

### Positive
- Runtime provider switching via `TRIAGE_PROVIDER` env var
- Deterministic test runs with `SimulatedTriage`
- No single point of failure — always produces a triage result

### Negative
- Rule-based fallback is less accurate than LLM
- Content-hash caching means rephrased duplicates aren't caught

## Alternatives Considered

- **Single LLM-only provider**: Fragile; fails without API access.
- **Queue-based async triage**: More complex; assignment spec requires synchronous response.

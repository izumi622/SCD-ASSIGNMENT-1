# CivicPulse AI Triage Pipeline

## Overview

CivicPulse uses an AI-powered triage system to automatically classify incoming citizen complaints by **category**, **priority**, and generate a brief **AI summary** (≤ 140 chars). The system is designed for resilience — it guarantees a triage result for every complaint, regardless of AI service availability.

## Architecture

```
Complaint Text + Location
        │
        ▼
┌─────────────────────┐
│ Content-Hash Cache   │ ──── Redis (24h TTL)
│ SHA-256(text+loc)   │       HIT → Return cached result
└─────────────────────┘
        │ MISS
        ▼
┌─────────────────────┐
│ Primary Provider     │ ──── Selected via TRIAGE_PROVIDER env var
│ (LLM/Ollama/Rules)  │
└─────────────────────┘
        │ Failure / Timeout
        ▼
┌─────────────────────┐
│ Fallback Chain       │
│ Rules → Simulated    │ ──── Always produces a result
└─────────────────────┘
        │
        ▼
  TriageResult stored in DB
  (category, priority, summary, triaged_by, latency_ms)
```

## Providers

### 1. LLMTriage (`TRIAGE_PROVIDER=llm`)

- **Backend**: Any OpenAI-compatible API (Groq, OpenAI, OpenRouter)
- **Model**: Configurable via `GROQ_MODEL` (default: `llama-3.1-8b-instant`)
- **Prompt**: Structured JSON output with system instructions
- **triaged_by**: `"llm:groq"` (or provider name)

### 2. OllamaTriage (`TRIAGE_PROVIDER=ollama`)

- **Backend**: Local Ollama instance (containerized or host)
- **Model**: Configurable via `OLLAMA_MODEL` (default: `llama3.2:1b`)
- **Use Case**: Offline inference, air-gapped environments, data privacy
- **triaged_by**: `"llm:ollama"`

### 3. RuleBasedTriage (`TRIAGE_PROVIDER=rules`)

- **Backend**: No external dependencies
- **Algorithm**: Keyword matching against category and priority word lists
- **Deterministic**: Same input always produces same output
- **triaged_by**: `"rules"` (or `"rules:fallback"` when used as fallback)

### 4. SimulatedTriage (`TRIAGE_PROVIDER=simulated`)

- **Backend**: No external dependencies
- **Algorithm**: SHA-256 hash of input text mapped to deterministic category/priority
- **Use Case**: CI/CD pipelines, automated testing
- **triaged_by**: `"simulated"`
- **Error Injection**: Special trigger texts cause deliberate failures for testing fallback paths

## TriageResult Schema

```python
class TriageResult(BaseModel):
    category: Category     # water | electricity | sanitation | roads | streetlights | other
    priority: Priority     # high | normal | low
    summary: str           # ≤ 140 characters
    confidence: float      # 0.0 – 1.0
```

## Resilience Features

### Timeout

All providers are wrapped with a configurable hard timeout (default: 10 seconds). If the AI inference exceeds this, an `asyncio.TimeoutError` is raised and caught by the fallback mechanism.

### Retry

A single jittered retry is attempted on retryable errors:
- Timeout
- HTTP 429 (rate limited)
- HTTP 5xx (server error)

Retries are **never** attempted on:
- HTTP 400 (bad request / malformed prompt)
- JSON parsing failures

### Fallback Chain

When the primary provider fails (after retry):
1. A **warning** is logged with the original error
2. `RuleBasedTriage` is invoked as the first fallback
3. If rules also fail (shouldn't happen), `SimulatedTriage` is the terminal fallback
4. The `triaged_by` field is set to `"rules:fallback"` to indicate degradation

### Content-Hash Caching

- **Key**: `triage:SHA256(text + "|" + location)`
- **TTL**: 24 hours
- **Purpose**: Avoid redundant API calls for identical complaints
- **Cache Miss**: AI inference runs, result is cached
- **Cache Hit**: Cached result is returned immediately (< 1ms)

### Prompt Injection Guardrails

Complaint text is treated as **untrusted user input**:
1. Text is wrapped in clear delimiters (`<complaint>...</complaint>`)
2. System prompt explicitly instructs the model to ignore instructions within the complaint
3. Output is validated against the `TriageResult` schema — any non-conforming response triggers fallback

## Observability

### Metrics

- `triage_latency_ms`: Histogram of triage duration per provider
- `triage_fallback_total`: Counter of fallback events
- `triage_cache_hit_total` / `triage_cache_miss_total`: Cache hit ratio

### Meta Endpoint

`GET /api/meta/providers` returns:
```json
{
  "active_provider": "llm",
  "recent_outcomes": [
    {
      "provider": "llm:groq",
      "latency_ms": 1234,
      "fallback": false,
      "timestamp": "2026-09-27T10:00:00Z"
    }
  ]
}
```

The `recent_outcomes` array is a rolling window of the last 20 triage operations.

## Configuration

| Environment Variable       | Default                | Description                        |
| -------------------------- | ---------------------- | ---------------------------------- |
| `TRIAGE_PROVIDER`          | `simulated`            | Active provider selection          |
| `GROQ_API_KEY`             | (none)                 | API key for Groq-hosted LLM       |
| `GROQ_MODEL`               | `llama-3.1-8b-instant` | Model name for hosted LLM         |
| `OLLAMA_BASE_URL`          | `http://ollama:11434`  | Ollama API endpoint               |
| `OLLAMA_MODEL`             | `llama3.2:1b`          | Model name for local Ollama       |
| `TRIAGE_CACHE_TTL_SECONDS` | `86400`                | Content-hash cache TTL            |

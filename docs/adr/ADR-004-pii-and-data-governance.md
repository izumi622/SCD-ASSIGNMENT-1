# ADR-004: PII and Data Governance

**Status:** Accepted  
**Date:** 2026-09-27  
**Deciders:** Development Team

## Context

CivicPulse collects citizen complaint data that may contain personally identifiable information (PII) such as names, addresses, phone numbers, and email addresses. This data is processed by AI triage providers (including external hosted APIs like Groq). We need a clear policy on how PII is handled throughout the system.

## Decision

### Data Classification

| Field               | Classification | Handling                                     |
| ------------------- | -------------- | -------------------------------------------- |
| `text`              | Potentially PII| Stored as-is; sent to triage provider        |
| `location`          | Low sensitivity| Stored as-is; sent to triage provider        |
| `reporter_contact`  | PII            | Stored encrypted at rest; **never** sent to AI|
| `ai_summary`        | Non-PII        | AI-generated; ≤ 140 chars                    |
| `id`                | Non-PII        | UUID, no correlation to person               |

### AI Provider PII Policy

1. **reporter_contact is NEVER included in AI prompts.** The triage prompt template only uses `text` and `location`.
2. **Prompt injection guardrails** treat complaint text as untrusted user input, wrapped in clear delimiters to prevent the model from treating it as instructions.
3. **Hosted providers** (Groq, OpenAI) process data subject to their own privacy policies. For deployments with strict data residency requirements, use `OllamaTriage` (local inference) or `RuleBasedTriage`.

### Data Retention

- Complaints are stored indefinitely for municipal record-keeping.
- Redis triage cache entries expire after 24 hours.
- Logs containing request data are rotated at the infrastructure level (not application-managed).

### Access Control

- Database credentials are stored in Kubernetes Secrets (should be migrated to external-secrets-operator or HashiCorp Vault in production).
- The backend runs as a non-root user (`appuser:appgroup`, UID 1000).
- Network segmentation (Docker dual-network or Kubernetes NetworkPolicy) prevents frontend containers from directly accessing the database.

## Consequences

### Positive
- Clear boundary: `reporter_contact` never leaks to AI providers.
- Prompt injection defense reduces risk of data exfiltration via crafted complaints.
- Local triage option available for privacy-sensitive deployments.

### Negative
- `text` field may still contain PII that users voluntarily include. Future work: implement PII redaction before AI processing.
- No encryption at rest for `text` field (database-level encryption deferred to infrastructure).

## Alternatives Considered

- **Full PII redaction before storage**: Too aggressive; municipal teams need original complaint text.
- **Client-side PII detection**: Unreliable and would degrade UX.

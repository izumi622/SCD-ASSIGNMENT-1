# Branch Protection Rules, Required CI Checks & PR Workflow

## 1. Branch Strategy and Hierarchy

CivicPulse adheres to a structured Git branching model designed for collaboration, auditability, and production safety:

```
main (protected - production-ready releases)
  ▲
  │ (Pull Request with CI status checks & peer review)
develop (protected - active integration branch)
  ▲
  ├── feat/frontend-triage-card
  ├── feat/redis-rate-limiter
  ├── fix/state-machine-409-response
  └── chore/k8s-resource-limits
```

- **`main`**: Production trunk. Only updated via squash-merge PRs from `develop` or critical tagged releases. Direct pushes and force pushes are blocked.
- **`develop`**: Primary staging branch. All feature and fix branches are cut from `develop` and merged back via Pull Requests.
- **Feature/Fix Branches**: Format `feat/<feature-name>`, `fix/<issue-name>`, or `chore/<task>`. Short-lived, focused on a single responsibility.

---

## 2. GitHub Branch Protection Policy

The following rules are configured for both `main` and `develop` in GitHub Settings $\to$ Branches:

### A. Pull Request Reviews
- **Require a pull request before merging**: Enabled.
- **Required approving reviews**: Minimum `1` approval from a code owner / peer reviewer.
- **Dismiss stale pull request approvals when new commits are pushed**: Enabled.
- **Require review from Code Owners**: Enabled (referencing `.github/CODEOWNERS`).

### B. Required Status Checks (Gating CI)
Commits cannot be merged unless the following GitHub Actions CI jobs pass:
1. `backend-lint`: Ruff linting and format verification.
2. `backend-test`: Pytest suite execution ensuring $\ge 65\%$ test coverage against real PostgreSQL and Redis service containers.
3. `frontend-test`: TypeScript compilation (`tsc --noEmit`), Vitest component tests (12 tests across 6 suites), and production bundle build.
4. `kubeconform`: Kubernetes manifest schema validation against strict API standards.
5. `docker-and-security`: Multi-stage Docker builds and Trivy vulnerability scan (severity: CRITICAL, HIGH).
6. `compose-smoke-test`: End-to-end container health probe validation (`/health`, `/ready`, `/`).

### C. Safety Constraints
- **Require linear history**: Enabled (PRs must be rebased or squashed).
- **Require branches to be up to date before merging**: Enabled (ensures PR was tested against the latest target branch tip).
- **Include administrators**: Enabled (enforces rules even on repository owners).
- **Allow force pushes**: Disabled (never permitted).
- **Allow deletions**: Disabled (prevents accidental branch loss).

---

## 3. Pull Request Workflow Checklist

Every PR must satisfy the following lifecycle before merge:

1. **Local Pre-flight**:
   ```bash
   # Run backend tests & linters
   pytest tests/ --cov=app --cov-report=term
   ruff check .

   # Run frontend typecheck & tests
   npm run lint
   npm test
   ```
2. **Conventional Commit Messages**:
   - `feat(triage): add fallback to keyword rules on timeout`
   - `fix(state-machine): return 409 conflict with transition details`
   - `docs(adr): document Redis dual-job caching strategy`
   - `test(api): assert 429 response on rate limit breach`
3. **PR Description & Traceability**:
   - Link related issue/task.
   - Describe changes and verification performed.
   - Attach test output or screenshots for UI modifications.
4. **CI Verification**: Green checkmarks on all 6 CI pipeline jobs.
5. **Peer Review Approval**: Written approval after architectural review.
6. **Merge**: Squash and merge with conventional commit summary into `develop`.

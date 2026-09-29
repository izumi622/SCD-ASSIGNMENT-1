# Reproducible assignment evidence

The `Assignment Evidence` Actions workflow runs on pushes to
`feat/kubernetes-evidence` and can be dispatched after it reaches the default
branch. It runs tests, builds commit-tagged images, deploys a disposable Kind
cluster, waits for database migrations, collects a baseline load experiment,
applies actual recommendation-only VPA targets capped to existing limits,
repeats the same workload, and verifies rollback.

Download `assignment-evidence-<commit>` from the completed Actions run. Read
`REPORT.md` and `findings.json`, not just the green check. Failed runs retain
available diagnostics. Never describe absent measurements as completed work.
The workflow does not deploy a permanent public website.

## What the measurements mean

- The workload reads the dashboard API with simulated triage configured. It does
  not benchmark an external LLM or prove an API provider is configured.
- The baseline and adjusted runs each use a 10/50/100 virtual-user ramp.
  See `load/evidence.js` for durations and thresholds.
- HPA observations are sampled every ten seconds. Ready replica growth is
  required; a desired replica count alone is insufficient.
- VPA remains in Off mode. The script records target, lower and upper bounds,
  changes requests within existing limits, and waits for rollout before testing.
- Cache state, replica count and cluster contention may differ between runs.
  Discuss those limitations when comparing latency and throughput.
- The six-minute cooldown records downscaling; rate limits may require longer
  for a full return to minimum replicas. Inspect the timeline.
- The graph and CSV contain actual observations, not expected scaling curves.
- The bad image used for rollback is confined to the disposable evidence cluster.

## Review and adoption

Aoun should inspect the changes and explain their purpose. Izumi should review
that work through a pull request. AI-generated changes should be disclosed as
such; the author name is not proof of independent implementation.

Review `resource-changes.json` and `measured-resource-patches.json` alongside
latency, errors and replica graphs before changing persistent Kubernetes requests.
Those patches describe proposed resources, not complete Deployment manifests.
Use a separate reviewed commit for any measured resource changes you adopt.
Preserve the run URL, tested commit and unmodified raw results in the submission.
Do not commit the whole runner workspace, Secrets or local `.env` files.

## Remaining submission gates

This workflow does not establish the full rubric. Check the actual assignment
against the repository. In particular, real partner review, issue-linked work,
red-to-green PR evidence, a genuine code-conflict resolution, release publication,
report interpretation and contribution requirements still need verification.
Do not create empty commits or invent these events to fill a quota.

The GitHub runner must have Actions minutes available. No Groq key or local
Ollama download is needed for this evidence run. The local Compose application
and the existing laptop Kind cluster are not modified by this workflow.

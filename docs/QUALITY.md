# Offline Enterprise AI Copilot | Quality & reproducibility

> **Status rule:** Check the [live GitHub Actions history](https://github.com/FaizanAKhan786/offline-enterprise-copilot/actions) for real workflow conclusions. This document does not invent benchmark scores or imply every feature was tested.

## Automated verification

Python source compilation and required-file checks; frontend TypeScript compilation. No end-to-end model or security tests are configured in CI.

- [View the CI workflow](https://github.com/FaizanAKhan786/offline-enterprise-copilot/actions/workflows/ci.yml)
- Any failing run is an unresolved result until corrected; a green syntax/unit-check workflow is not proof of deployment readiness.

## Reproduce the checks

Run these commands from the **repository root**, unless the commands change directories:

```bash
python -m compileall -q backend/app
cd frontend
npm install --no-audit --no-fund
npx tsc --noEmit
```

## How to interpret the results

**Relevant metrics:** No verified inference latency, translation accuracy, throughput or end-to-end RAG scores currently published.

**Requirements and limitations:** Full deployment validation needs the Docker stack, Postgres, Qdrant, Redis, appropriate local model weights and authenticated service tests.

Before comparing results, save the commit SHA, command, dataset and split (including seed), model revision, dependency environment, hardware/CPU/GPU, and the raw result file. Use the same evaluation set for all compared runs and distinguish **synthetic tests** from **real-world measurements**.

## Publication policy

Only publish numeric scores alongside the run configuration and raw evidence. A threshold, code assertion or example report must **not** be presented as a measured production result.

[Project README](../README.md) · [GitHub Actions](https://github.com/FaizanAKhan786/offline-enterprise-copilot/actions)

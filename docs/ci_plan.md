# CI/CD Plan & Strategy

## 1. Overview
This document outlines the Continuous Integration (CI) strategy for the Crossborder project. The goal is to ensure code quality, functional correctness, and regulatory compliance through automated pipelines.

## 2. Current Workflows

### 2.1. Main CI (`.github/workflows/ci.yml`)
**Trigger:** Push to `main`/`master`, Feature branches (`feat/**`), Pull Requests.
**Scope:**
- **Build:** Docker Compose build for backend.
- **Lint:** `ruff` (Fast linting), `black` (Formatting).
- **Test:** `pytest` (Unit & Integration tests).
- **E2E:** `playwright` (API Smoke tests via Docker).

### 2.2. Knowledge Guard (`.github/workflows/knowledge-guard.yml`)
**Trigger:** Schedule (Nightly at 01:00 UTC), Manual Dispatch.
**Scope:**
- **Regulation Check:** Runs `pytest -m ultracite` to fetch and compare regulatory data.
- **Reporting:** Generates diff reports (currently local/mounted, needs artifact upload if running in CI).

## 3. Gap Analysis & Proposed Improvements

### 3.1. Performance Optimization (High Priority)
- **Docker Caching:** Currently, images are rebuilt on every run.
    - *Action:* Implement `docker/build-push-action` with `type=gha` cache exporter/importer to speed up builds.
- **Dependency Caching:** Python packages are re-installed on every build.
    - *Action:* Cache `pip` directories or use a multi-stage Docker build with cached base layers.

### 3.2. Quality Gates (Medium Priority)
- **Type Checking:** No static type checking is currently performed.
    - *Action:* Add `mypy` step to `ci.yml`.
- **Security Scanning:** No vulnerability scanning.
    - *Action:* Add `bandit` or `trivy` for container scanning.

### 3.3. Observability & Artifacts (Medium Priority)
- **Test Reports:** JUnit XML reports are not generated/uploaded.
    - *Action:* Configure `pytest` to generate XML and upload via `actions/upload-artifact`.
- **Playwright Traces:** On failure, Playwright traces/screenshots are lost.
    - *Action:* Upload `test-results/` as artifacts on failure.
- **Watchdog Reports:** `knowledge-guard` generates reports inside the container but doesn't persist them.
    - *Action:* Upload `docs/regulations/reports` as a workflow artifact.

## 4. Implementation Roadmap

### Phase 1: Stabilization (Immediate)
- [ ] Document existing workflows (This file).
- [ ] Add `workflow_dispatch` to `ci.yml` for easier debugging.
- [ ] Ensure `knowledge-guard` uploads generated reports as artifacts.

### Phase 2: Optimization
- [ ] Implement Docker Layer Caching.
- [ ] Add `mypy` to the linting stage.

### Phase 3: Advanced
- [ ] Add CD (Continuous Deployment) steps (e.g., to staging environment).
- [ ] Integrate Slack/Discord notifications for build failures.

## 5. Configuration Reference

### Pytest Markers
- `integration`: Database-dependent tests.
- `ultracite`: External API/Regulation watchdog tests.
- (Unmarked): Fast unit tests.

### Docker Services
- `backend`: Flask API & Workers.
- `db`: PostgreSQL (Port 54320 on host).
- `playwright`: E2E Test runner.

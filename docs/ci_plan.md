# CI/CD Plan & Strategy

## 1. Overview
This document outlines the Continuous Integration (CI) strategy for the Crossborder project. The goal is to ensure code quality, functional correctness, and regulatory compliance through automated pipelines.

## 2. Current Workflows

### 2.1. Main CI (`.github/workflows/ci.yml`)
**Trigger:** Push to `main`/`master`, Feature branches (`feat/**`), Pull Requests.
**Scope:**
- **Build:** Docker Compose build for backend.
- **Lint (静的解析):**
    - `ruff check app tests` (ロジック・規約チェック、自動修正対応)
    - `black --check app` (コードフォーマットチェック)
- **Type Check (型定義チェック):**
    - `mypy app` (型安全性の確保)
- **Test:** `pytest` (Unit & Integration tests).
    - **Target Coverage:** 80% (Fail if under 80%).
    - **最新のローカル実行結果 (2026-01-03):** 23 passed, 81 deselected (3.58s)

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
    - **最新のローカル実行結果 (2026-01-03):** 5 passed (2.3s)
- **Watchdog Reports:** `knowledge-guard` generates reports inside the container but doesn't persist them.
    - *Action:* Upload `docs/regulations/reports` as a workflow artifact.

### 3.4. Release Engineering & Safety (Negative Check Findings)
- **Deployment Strategy:** No clear strategy for zero-downtime deployment or rollback.
    - *Action:* Define Blue/Green or Rolling update strategy. Define automated rollback criteria.
- **Database Migrations:** Risk of breaking schema changes during CD.
    - *Action:* Separate migration jobs from application deployment. Use tools like `alembic` with downgrade verification.
- **Dependency Management:** No automated vulnerability checking for dependencies.
    - *Action:* Configure Dependabot or Renovate for weekly updates.
- **Secret Management:** Secrets are used but no leak detection mechanism exists.
    - *Action:* Add `git-secrets` or `trufflehog` check in the pipeline.

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
- `backend`: Flask API & Workers (Port 65001 on host).
- `db`: PostgreSQL (Port 65432 on host).
- `playwright`: E2E Test runner.

## 2026-01-06T13:30:39+09:00 [backend] task=phaseA hs review/rules/compliance API

context:
  branch: feature/hs-api-impl
  files:
    - backend/app/api/v1_hs_review.py
    - backend/app/api/v1_hs_rules.py
    - backend/app/api/v1_compliance.py
    - backend/app/models.py
    - backend/app/api/v1_classify.py
    - backend/app/factory.py
    - backend/openapi.yaml
    - backend/migrations/versions/20260106130000_add_hs_review_fields.py

summary:
  - Added HS review, HS rules, and compliance API endpoints (Phase A) and registered blueprints.
  - Extended HSClassification model with review fields and added migration.
  - Restored and updated OpenAPI with new paths/schemas, duty models, and Error400/RuleDslError alignment.

next:
  - Add tests for HS review/rules/compliance endpoints and align OpenAPI/implementation details.
  - Confirm Phase A rule DSL format expectations for /hs-rules:test.

refs:
  - Issue: https://github.com/mazatada/crossborder/issues/8
  - Issue: https://github.com/mazatada/crossborder/issues/9

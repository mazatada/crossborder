## 2026-01-06T12:25:24+09:00 [backend] task=openapi extend for HS review/rules/compliance

context:
  branch: feature/hs-api-impl
  files:
    - backend/openapi.yaml

summary:
  - Added HS Review, HS Rules, and Compliance paths with request/response schemas.
  - Added HSRule/HSClassification/DutyRateOverride/ComplianceView schemas plus Error409.
  - Integrated RuleDslError into Error400 and aligned rate deprecation descriptions.

next:
  - Validate the new OpenAPI paths against implementation status and adjust if any fields differ.
  - Address tariff API error_class naming in backend/app/api/v1_tariffs.py.

refs:
  - Issue: https://github.com/mazatada/crossborder/issues/8

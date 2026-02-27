## 2026-01-06T11:58:48+09:00 [backend] task=review responses for if_spec_extended

context:
  branch: feature/hs-api-impl
  files:
    - docs/if_spec_extended.md

summary:
  - Reviewed docs/rbrb.txt and updated if_spec_extended spec with audit targets, paging policy, date/time rules, and OpenAPI mapping guidance.
  - Clarified duty_rate compatibility (tolerance, 422 example, v2 removal date) and phased rollout timeline/rollback.
  - Standardized models (DutyRateDetailed, DutySummary, DutyComponent, ProductSample, RuleDslError) and clarified override/ordering/CRUD/DSL rules.

next:
  - Reflect the spec changes into backend/openapi.yaml (schemas, paths, error mappings).
  - Fix tariff API error_class naming in backend/app/api/v1_tariffs.py to distinguish invalid_format vs missing_required.

refs:
  - Review source: docs/rbrb.txt
  - Spec updated: docs/if_spec_extended.md

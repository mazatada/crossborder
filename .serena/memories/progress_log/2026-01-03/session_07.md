## 2026-01-04T00:10:00+09:00 [chief] task=tariff-json-hardening

context:
  branch: feature/hs-api-impl
  files:
    - backend/app/api/v1_tariffs.py
    - backend/openapi.yaml
    - docs/if_spec_extended.md

summary:
  - Tariff JSONの必須項目にtariff_schedule_version/last_updated_atを追加
  - 404エラーの専用スキーマ(Error404)をOpenAPIに追加
  - TTL遅延の運用影響を仕様に明記
  - commit/push を完了

next:
  - 改ざん検知（hash/署名）方針の明文化、またはPhase B(DB化)設計に着手

refs:
  - commit: 1b55cee1

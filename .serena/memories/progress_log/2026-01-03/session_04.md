## 2026-01-03T23:10:00+09:00 [chief] task=openapi-diff-alignment

context:
  branch: feature/hs-api-impl
  files:
    - docs/if_spec_extended.md
    - docs/openapi_diff_extended.yaml

summary:
  - 互換性ポリシー（ad_valorem_rate/pct）を仕様本文に明記し、次期メジャー削除方針を追加
  - OpenAPI差分にoneOf/required/descriptionを追加し相互制約と優先順位を明文化
  - コミット＆プッシュを完了

next:
  - M3: backend/openapi.yaml と frontend/src/types.ts の整合方針を決める

refs:
  - commit: 46c501dd
  - issue: #7

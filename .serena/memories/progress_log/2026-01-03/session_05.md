## 2026-01-03T23:45:00+09:00 [chief] task=openapi-contract-tighten

context:
  branch: feature/hs-api-impl
  files:
    - backend/openapi.yaml
    - frontend/src/types.ts

summary:
  - OpenAPI本体にad_valorem_rate/ pctの相互制約・移行方針を明文化
  - duty_rateの必須要件を明記し、additionalの移行説明を追加
  - フロント型のad_valorem_rateを任意に戻し、実装未対応とのズレを緩和
  - commit/push を完了

next:
  - M3残作業: 実装側(v1_classify)のad_valorem_rate返却対応と互換テスト追加

refs:
  - commit: 93e86698

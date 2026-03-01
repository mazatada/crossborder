## 2026-01-03T23:55:00+09:00 [chief] task=duty-rate-rollout-plan

context:
  branch: feature/hs-api-impl
  files:
    - docs/if_spec_extended.md

summary:
  - DutyRateの段階導入方針（null許容→算出→FTA考慮→Compliance反映）を仕様に追記
  - Issue #7 に進捗コメントを追加
  - commit/push を完了

next:
  - ad_valorem_rate の実値算出ロジックの設計・実装方針を決める

refs:
  - commit: 198d06c0
  - issue: #7

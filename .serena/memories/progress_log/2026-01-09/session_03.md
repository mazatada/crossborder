## 2026-01-09T18:16:34+09:00 [backend] task=HS rules audit + HS review 409

context:
  branch: feature/hs-api-impl
  files:
    - backend/app/api/v1_hs_rules.py
    - backend/app/api/v1_hs_review.py
    - backend/app/api/v1_compliance.py
    - backend/tests/test_api_hs_rules.py
    - backend/tests/test_api_hs_review.py

summary:
  - HSルールCRUDに監査イベントを追加し、Error404フォーマットを統一
  - HSレビュー更新で locked 状態の409競合を追加しテストで検証
  - Dockerで pytest -k hs_rules / hs_review を実行し全てパス

next:
  - Issue #9 の残項目を確認し、Issue #8 のOpenAPI整合を進める
  - 監査の trace_id/target_id 設計は Issue #10 で検討

refs:
  - Issue: https://github.com/mazatada/crossborder/issues/9
  - Issue: https://github.com/mazatada/crossborder/issues/10
  - Tests: docker compose run --rm pytest -k hs_rules; docker compose run --rm pytest -k hs_review

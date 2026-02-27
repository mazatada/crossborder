## 2026-01-09T09:30:00+09:00 [backend] task=negative review Phase A HS endpoints

context:
  branch: feature/hs-api-impl
  files:
    - backend/app/api/v1_hs_rules.py
    - backend/app/api/v1_hs_review.py
    - backend/app/api/v1_compliance.py

summary:
  - HSルールの condition_dsl が作成/更新時に検証されず無効DSLが保存可能な点を指摘
  - /hs-rules:test が RuleEngine の private API 依存で壊れやすい点を指摘
  - compliance の prior_notice_required の意味が仕様とズレる可能性を指摘
  - HSレビュー更新の reviewed_at 条件が甘くなる可能性を指摘

next:
  - condition_dsl のバリデーション方針を決定し、必要なら作成/更新時に検証を追加
  - prior_notice_required の仕様意図を確認し、必要ならレスポンス設計を修正
  - /hs-rules:test の評価APIを public 経由に置き換えるか、保守方針を明確化

refs:
  - Serena progress_log/2026-01-06/session_01.md
  - Serena progress_log/2026-01-06/session_02.md
  - Serena progress_log/2026-01-06/session_03.md

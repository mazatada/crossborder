## 2026-01-03T20:15:00+09:00 [chief] task=local-windows-deploy-docs

context:
  branch: feature/hs-api-impl
  files:
    - docs/deployment_strategy.md
    - docs/deployment.md
    - docs/runbook.md
    - docs/rbrb.txt
    - scripts/local_deploy.ps1
    - .gitignore

summary:
  - ソース運用(ローカルWindows)に方針統一し、ロールバックをgit commit単位へ修正
  - ヘルスチェックURLを http://localhost:65001/v1/health に統一
  - ローカル運用スクリプトを追加し、ロールバック/排他/last_good_commit保存を実装
  - 進行中の前提( origin固定、Git認証、作業ツリーclean )を明文化

next:
  - .github/workflows/cd.yml のレビュー対応に着手
  - docs/ci_plan.md と docs/spec/* のレビュー対応を整理

refs:
  - none

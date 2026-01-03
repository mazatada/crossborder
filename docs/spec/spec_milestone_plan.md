# Spec Milestone Plan (v1)

## 0. 目的
仕様の粒度を「実装前提でブレない」水準まで引き上げ、実装/CIに安全に接続する。

## 1. 参照ハブ
- `docs/越境EC成分表翻訳アプリ仕様書_v1_0.md`
- `docs/spec/backend_completion_spec_v1.md`（実装完了/リリース判定）

## 2. マイルストーン

### M1: 仕様精緻化（IF/モデル）
- [ ] `docs/if_spec_extended.md` の以下を確定
  - duty_rate の型・数値形式（ad_valorem_rate の統一）
  - review_required の更新可否
  - Compliance の鮮度/更新主体
  - HSRule effect/DSL の仕様（weightの意味、DSL簡易文法）
- [ ] 仕様内の一貫性（日時/数値/ページング/エラー）を整合

### M2: OpenAPI差分の確定
- [ ] `docs/openapi_diff_extended.yaml` を `if_spec_extended.md` に合わせて更新
- [ ] モデル定義（DutyRateDetailed/HSClassificationReview/ComplianceView 等）を反映

### M3: 契約整合（既存実装との互換）
- [ ] `backend/openapi.yaml` への反映方針を確定（追加のみ）
- [ ] `frontend/src/types.ts` の型整合方針を確定
- [ ] `ad_valorem_pct` → `ad_valorem_rate` の移行戦略を明文化

### M4: 実装・検証への接続
- [ ] `docs/spec/backend_completion_spec_v1.md` の残作業にリンク
- [ ] 実装タスクへの分解（API/DB/Jobs/Docs）

## 3. 完了条件
- M1〜M4 がすべて完了し、仕様→OpenAPI→実装の道筋が明文化されている。

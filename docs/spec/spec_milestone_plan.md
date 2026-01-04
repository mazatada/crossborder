# Spec Milestone Plan (v1)

## 0. 目的

仕様の粒度を「実装前提でブレない」水準まで引き上げ、実装/CIに安全に接続する。

## 1. 参照ハブ

- `docs/越境EC成分表翻訳アプリ仕様書_v1_0.md`
- `docs/spec/backend_completion_spec_v1.md`（実装完了/リリース判定）

## 2. マイルストーン

### M1: 仕様精緻化（IF/モデル）

- [x] `docs/if_spec_extended.md` の以下を確定
  - duty_rate の型・数値形式（ad_valorem_rate の統一）
  - review_required の更新可否
  - Compliance の鮮度/更新主体
  - HSRule effect/DSL の仕様（weightの意味、DSL簡易文法）
- [x] 仕様内の一貫性（日時/数値/ページング/エラー）を整合
- 完了根拠:
  - 仕様本文に「互換性・移行ポリシー」「相互制約」「override優先」「更新トリガー」等を明記
  - 変更要約: duty_rate互換/更新/DSL/Compliance鮮度の契約を明文化
  - 検証レベル: ドキュメント更新のみ（実装/検証は未着手）
  - 参照コミット: `25daa374`, `46c501dd`
  - 影響ファイル: `docs/if_spec_extended.md`

### M2: OpenAPI差分の確定

- [x] `docs/openapi_diff_extended.yaml` を `if_spec_extended.md` に合わせて更新
- [x] モデル定義（DutyRateDetailed/HSClassificationReview/ComplianceView 等）を反映
- 完了根拠:
  - `ad_valorem_rate` 追加 + `ad_valorem_pct` deprecated 設定
  - `AdditionalDuty` / `DutyRateOverride` / `oneOf` / `required` を反映
  - 変更要約: OpenAPI差分がIF仕様と整合
  - 検証レベル: ドキュメント更新のみ（実装/検証は未着手）
  - 参照コミット: `46c501dd`
  - 影響ファイル: `docs/openapi_diff_extended.yaml`

### M3: 契約整合（既存実装との互換）

- [x] `backend/openapi.yaml` への反映方針を確定（追加のみ）
- [x] `frontend/src/types.ts` の型整合方針を確定
- [x] `ad_valorem_pct` → `ad_valorem_rate` の移行戦略を明文化
- 次の具体作業:
  - 依存順序: OpenAPI本体 → フロント型 → 実装
  - OpenAPI本体へ `ad_valorem_rate` を追加し `ad_valorem_pct` をdeprecatedにする
  - 既存 `HSResponse.duty_rate` の互換維持方針を追記
  - フロント型で `ad_valorem_rate` を必須、`ad_valorem_pct` を任意にする
 - 完了根拠:
   - OpenAPI本体に `ad_valorem_rate`/`ad_valorem_pct` を反映し移行説明を追記
   - フロント型で `ad_valorem_rate`/`ad_valorem_pct` を任意に調整
   - 移行戦略を `docs/if_spec_extended.md` に明記
   - 参照コミット: `900d1ec4`, `93e86698`, `2397ba47`, `198d06c0`
   - 影響ファイル: `backend/openapi.yaml`, `frontend/src/types.ts`, `docs/if_spec_extended.md`
   - 検証レベル: ドキュメント/契約更新のみ（実装算出は未着手）

### M4: 実装・検証への接続

- [ ] `docs/spec/backend_completion_spec_v1.md` の残作業にリンク
- [ ] 実装タスクへの分解（API/DB/Jobs/Docs）
- 次の具体作業:
  - 分解基準: API / DB / Jobs / Docs / QA の5軸で切り分け
  - M3確定後に実装タスクを分割し、担当を割当
  - 仕様→OpenAPI→実装の追跡リンクを追加

## 3. 完了条件

- M1〜M4 がすべて完了し、仕様→OpenAPI→実装の道筋が明文化されている。

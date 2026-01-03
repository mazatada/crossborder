# Backend Completion Implementation Plan

目的: 仕様書/機能一覧に照らしたバックエンドの残タスクを整理し、実装完了に向けたマイルストーンを提示する。

## Inputs
- docs/spec/backend_completion_spec_v1.md
- docs/越境EC成分表翻訳アプリ仕様書_v1_0.md
- docs/機能一覧.md

## Milestones

### M1: 仕様整合とイベント定義
目的: 連携仕様とイベント定義の抜けを埋め、実装の前提を固める。

Deliverables:
- イベントカタログ（最低: HS_CLASSIFIED, DOCS_PACKAGED, PN_SUBMITTED/ACCEPTED/REJECTED, AUDIT_APPENDED）
  - payload必須項目・型・互換ポリシー（追加のみ）
  - trace_id の必須化と生成規約
- Webhook送信/受信I/FのOpenAPI反映方針（draft->正式への差分確認）
  - 反映対象のエンドポイント/スキーマ一覧
  - 既存OpenAPIとの差分表（破壊的変更なし）
- Inbound `ORDER_PAID` / `ORDER_CANCELED` の必須項目とバリデーション定義
  - 最小入力・422エラー形式・監査イベントの内容
- データ保持/非保持ポリシー
  - PII非保持の範囲
  - 監査/書類/ジョブの保存期間と削除条件

Acceptance:
- 仕様書にイベント一覧/ペイロードが明記される
- Inboundバリデーションの要件が明文化される
- PII非保持と監査保存期間が明文化される

### M2: API/機能ギャップの埋め
目的: 仕様書と機能一覧で未確定のAPI/機能を実装レベルに落とす。

Deliverables:
- `/v1/products/:id/compliance` の返却項目を仕様と整合（HS/UoM/アレルゲン等の不確定項目整理）
- Export API (`/v1/export/entry`, `/v1/export/isf`) の入力検証/出力仕様の明文化
- OpenAPIの更新（上記API/ペイロードの整合）

Acceptance:
- 仕様書/実装/テストの一致がレビュー可能

### M3: 品質ゲートと運用仕上げ
目的: CI/運用の最終確認を行い、リリース可能状態を作る。

Deliverables:
- GitHub Actions main CI green 確認
- テスト根拠の記録（ローカルDocker実行の結果/条件）
- Runbook/CHANGELOG/OpenAPI検証の再確認

Acceptance:
- `backend_completion_spec_v1.md` の残作業が完了扱いになる

## Task Breakdown (Short)

1) イベントカタログ整理
- 仕様: docs/越境EC成分表翻訳アプリ仕様書_v1_0.md
- 参照: docs/機能一覧.md (Webhook 送信/Inbound)
- 追加: payload必須項目・型・互換ポリシーの明文化

2) Inboundバリデーション
- `ORDER_PAID`/`ORDER_CANCELED` の必須フィールド定義
- 422ルール/エラーフォーマット整合

3) データ保持ポリシー
- PII非保持と監査保存期間の明文化
- 保持期間/削除条件の記述

4) OpenAPI反映
- Webhook I/F draft -> openapi.yaml 反映可否の決定
- 反映する場合の差分PR作成

5) CI green 確認
- GitHub Actions main CI
 - 実行条件（環境/secret/compose）を明記

## Test Strategy
- Unit: キャッシュ/バリデーション/監査関連
- Integration: Inbound/Webhook/ジョブ状態遷移
- E2E: translate -> classify -> docs -> PN

## Risks
- OpenAPI draft未整合による仕様齟齬
- Inboundイベントの必須項目定義が曖昧なまま実装される
- CI green 未確認でのマージ判断

# 越境EC AI自動化アプリ — 開発仕様書（v1 完成版）
最終更新: 2025-10-12 07:15:42 UTC

本仕様は、越境EC業務（US食品MVP）における **翻訳→HS分類→通関書類→PN最小連携→監査** を担うバックエンドの**完成版**開発仕様書です。ダウンロード可能な付属ファイル（OpenAPI, DDL, JSON Schema, ルールYAML, Postman）を同梱します。

---

## 0. 目次
1. 目的と設計原則
2. システム境界・役割分担
3. アーキテクチャ（論理/物理）
4. API 仕様（OpenAPI 概要）
5. データモデル（ERD/データ辞書）
6. ルールエンジン（DSL/サンプル）
7. 非同期ジョブ/状態遷移
8. エラー設計/エラーカタログ
9. セキュリティ/ガバナンス/監査
10. 非機能要件（性能/可用/可観測性）
11. 環境変数/設定項目
12. デプロイ/運用（Docker/K8s）
13. テスト計画/受入基準
14. 変更管理/バージョニング方針
付録: OpenAPI, DDL, JSON Schema, ルール, Postman

---

## 1. 目的と設計原則
- 目的: 規制・分類・通関・監査の**説明可能な自動化**を提供。
- 原則: 最小保持 / 監査可能 / 疎結合（マーケは別） / 後方互換 / セキュア既定 / 観測可能。

## 2. システム境界・役割分担
- 本アプリが持つ: 成分抽出/翻訳、法規DB、HS分類、書類生成、PN最小連携、監査・証跡、UoM整合、ジョブ管理、Webhook。
- 本アプリが持たない: 顧客/売上/在庫/決済/分析/KPI。マーケは別アプリが担当。
- 連携は **Inbound最小API**（注文状態）と **Outbound Webhook**（イベント通知）のみ。

## 3. アーキテクチャ
### 論理
- API層(Flask) — JSON REST, CORS, APIキー/HMAC
- ルール・分類層 — 翻訳(用語>辞書>LLM)、HSルール+スコア
- ジョブ・連携層 — PN/書類を非同期、Webhook通知/再送/DLQ
- データ層(PostgreSQL) — 正規化/監査、JSONB活用
- メディア — 証憑/ラベル画像（local/S3置換可能）
### 物理（Docker Compose想定）
- services: backend, db(postgres), (frontendは別開発)
- ボリューム: db_data, media

## 4. API 仕様（OpenAPI 概要）
- バージョン: v1 / JSON / UTF-8
- 認証: Inbound=APIキー, Webhook=HMAC-SHA256署名
- 主要エンドポイント（詳細は `openapi.yaml` 参照）
  - `GET /v1/health`, `GET /v1/version`
  - `POST /v1/translate/ingredients`
  - `POST /v1/classify/hs`
  - `POST /v1/docs/clearance-pack`, `GET /v1/jobs/{id}`
  - `POST /v1/fda/prior-notice`
  - `GET /v1/audit/trace/{traceId}`
  - `POST /v1/integrations/orders/{id}/status`
  - `POST /v1/integrations/webhooks`, `POST /v1/integrations/webhooks/test`

## 5. データモデル（ERD/辞書）
### ERD（テキスト）
```
products( product_id PK, name, category, process[], origin_country, label_media_id )
hs_classifications( id PK, product_id FK→products, hs_candidates JSONB, required_uom, final_hs_code, review_required, created_at )
document_packages( job_id PK, status, artifacts JSONB, uom_check JSONB, created_at )
pn_submissions( job_id PK, status, payload JSONB, receipt_media_id, errors JSONB, created_at )
tag_def( tag_id PK, namespace, key, value_type, enum_values[], description )
tag_assignment( assign_id PK, entity_type, entity_id, tag_id FK→tag_def, value_json, scope, effective_from, expires_at, source, confidence, created_by, created_at, updated_by, updated_at )
audit_event( id PK, trace_id, event, actor JSONB, at, target JSONB, diff JSONB, reason )
jobs( id PK, type, payload_json, status, attempts, next_run_at, result_json, error_json, created_at, updated_at )
```
### データ辞書（抜粋・型/制約）
- `products.origin_country`: ISO-3166-1 alpha-2（正規表現 `^[A-Z]{2}$`）
- `hs_classifications.hs_candidates`: `[{code:"^\d{4}(\.\d{2}){0,2}$", confidence:0..1, rationale[]}]`
- `document_packages.uom_check.valid`: boolean ハードブロック条件に使用
- `tag_assignment.scope`: JSONB（例: { "locale":"US", "channel":"web" }）
- 監査保持: 7年（WORM相当運用）

## 6. ルールエンジン（DSL）
Phase A は **JSON条件文字列** を採用し、述語の単一ソースは `backend/app/rules/predicates.py` とする。  
YAMLサンプルは `rules/hs_food.yml` を参照。

述語（Phase A）:
- `contains_any_ids`（values: string[]）
- `not_contains_ids`（values: string[]）
- `process_any`（values: string[]）
- `origin_in`（values: string[]）
- `category_is`（value: string）
- `ingredient_pct_threshold`（ingredient_id: string, min_pct: number, max_pct?: number）
- `always`（params: {}）

## 7. 非同期ジョブ/状態遷移
- 共通: `queued → running → (done|error)` / `error→retry(backoff)→done|dlq`
- PN: `submitted → (accepted|rejected)`（外部応答を受け取って更新）
- Webhook: 最大5回再試行、指数バックオフ、72h DLQ、手動リプレイ

## 8. エラー設計/エラーカタログ
共通フォーマット: `{ "error": {"class","message","code","fields"} }`  
主コード: 400(必須不足/UoM不整合), 401, 403, 404, 409(PNロック), 422(ルール評価不能), 429, 500, 503  
詳細は「付録: エラーカタログ」および `openapi.yaml` 参照。

## 9. セキュリティ/ガバナンス/監査
- 認証: `Authorization: Bearer <token>`（Inbound）/ `X-Signature: sha256=...`（Webhook）
- RBAC: operator/customs/law（hs/*編集はcustomsのみ）
- PII最小化: 顧客情報は持たない。注文ID等の参照キーのみ。
- 監査: 重要操作は `audit_event` へ記録、trace_id必須、保持7年。
- 暗号化: TLS必須、機微データは保存しない。SecretsはENV+KMS。

## 10. 非機能要件
- HS分類: P95 ≤ 300ms（キャッシュ/ルールのみ時）
- Webhook遅延: P95 ≤ 5s、再試行5回、DLQ:72h
- スループット: API 100rps、ジョブワーカーN並列（横スケール前提）
- 可観測性: 構造化ログ/メトリクス/トレースID相関

## 11. 環境変数
- `DB_URL`, `SECRET_KEY`, `CORS_ORIGINS`, `STORAGE_BACKEND`, `STORAGE_PATH`
- `PN_SANDBOX`, `WEBHOOK_SIGN_ALG`, `RATE_LIMIT`, `API_KEYS`（カンマ区切り）

## 12. デプロイ/運用
- Docker Compose（dev）/ K8s（prod想定）
- 健康監視 `/v1/health`、ログはJSONでstdout
- バックアップ: DBスナップショット、メディアはオブジェクトストレージ推奨

## 13. テスト計画/受入基準
- ユニット: 述語評価、Schema検証、署名検証、UoM整合
- 結合: PNモック、書類パック生成、Webhook再試行/DLQ
- E2E: 代表50品目で一次候補リコール≥80%、審査後100%
- 異常系: 400/404/409/422/503 を網羅、再試行/リトライ確認

## 14. 変更管理/バージョニング
- 追加のみ後方互換。削除/意味変更は禁止（deprecated→置換）。
- DBマイグレーション: Alembicで管理（Up/Down必須）。

---

## 付録ファイル一覧
- `openapi.yaml` — API完全仕様
- `ddl.sql` — DDL定義（PostgreSQL）
- `schemas/product.json` / `schemas/hs_classification.json` — JSON Schema
- `rules/hs_food.yml` — ルールサンプル
- `postman/Crossborder_Automation.postman_collection.json` — 動作確認用

以上。

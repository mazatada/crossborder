# 越境EC AI自動化アプリ
## バックエンド仕様書（v1 Draft）

最終更新: 2025-10-12 / 対象: US食品MVP（翻訳・HS分類・通関書類・PN最小連携・監査）

---

## 1. 目的と設計原則

**目的**: 規制・分類・通関・監査の自動化を担う中核APIを提供し、販売・マーケ系は別アプリに疎結合連携する。  
**原則**: 説明可能性 / 監査可能性 / 最小保持 / 疎結合 / 互換性維持 / 可観測性。

---

## 2. システム構成（論理）

- **API層（Flask, Python 3.11）**
  - REST + JSON。CORS対応。
  - 認証: APIキー（Inbound） / HMAC署名検証（Webhook）。
- **ルール・分類層**
  - 成分翻訳: 用語ベース＋辞書＋LLM補助のパイプライン。
  - HS分類: 述語ルール＋スコアリングで候補提示、レビュー可。
- **ジョブ・連携層**
  - PN申請・書類生成などを非同期ジョブで処理（テーブル型キュー）。
  - Webhook通知（再試行・DLQ・手動リプレイ）。
- **データ層（PostgreSQL/SQLite dev）**
  - 正規化スキーマ + 監査イベント（WORM相当運用）。
- **ストレージ**
  - 証憑・ラベル画像（ローカル/オブジェクトストレージ抽象化）。

---

## 3. エンドポイント一覧（v1）

### 3.1 ヘルス・バージョン
- `GET /v1/health` → 200: {status:"ok"}  
- `GET /v1/version` → 200: {version:"1.0.0", commit:"..."}

### 3.2 翻訳・正規化
- `POST /v1/translate/ingredients`
  - 入力: {text_ja: string, image_media_id?: string, product_context?: {...}}
  - 出力: {terms: [{ja, en, canonical_id, confidence}], glossary_hits: [...]}
  - 役割: OCR/正規化/訳語適用（用語ベース優先）。

### 3.3 HS分類
- `POST /v1/classify/hs`
  - 入力: {product:{name, category, process[], origin_country?, ingredients[{id, pct?}]}}  
  - 出力: {hs_candidates:[{code, confidence, rationale[]}], required_uom, review_required, duty_rate?, risk_flags, quota_applicability}
  - 役割: 述語ルールとヒューリスティックの合成。

### 3.4 書類生成
- `POST /v1/docs/clearance-pack`
  - 入力: {traceId, hs_code, required_uom, invoice_uom, invoice_payload?}
  - 出力: {job_id, status:"queued"} → 完了時 Webhook `DOCS_PACKAGED`
  - 生成物: 商業インボイス, パッキングリスト（PDF/ZIP）。

### 3.5 PN（Prior Notice）
- `POST /v1/fda/prior-notice`
  - 入力: {traceId, product{...}, logistics{...}, importer{...}, consignee{...}, label_media_id?}
  - 出力: 202 {job_id}
  - 応答: `PN_SUBMITTED` → (`PN_ACCEPTED` | `PN_REJECTED`)

### 3.6 ジョブ・監査
- `GET /v1/jobs/{id}` → {status, result?, error?}
- `GET /v1/audit/trace/{traceId}` → 監査イベント時系列

### 3.7 連携（境界）
- **Inbound**: `POST /v1/integrations/orders/{id}/status`
  - 受信: {order_id, status: PAID|CANCELED, ts, customer_region?, sku_list?}
  - 目的: PNロック/取消トリガのみ。詳細は保持しない。
- **Webhook登録/テスト**
  - `POST /v1/integrations/webhooks`（登録）
  - `POST /v1/integrations/webhooks/test`（接続・署名検証）

---

## 4. データモデル（概要）

### 4.1 プロダクト関連
- **Product**(product_id, name, category, process[], origin_country?, label_media_id?)
- **IngredientRef**(id, display_ja?, display_en?, pct?)  ※用語ベースキー使用

### 4.2 分類・書類・PN
- **HSClassification**(product_id, hs_candidates[], required_uom, final_hs_code?, review_required)
- **DocumentPackage**(job_id, status, artifacts[{type, media_id}], uom_check{required, invoice, valid})
- **PNSubmission**(job_id, status, payload, receipt_media_id?, errors[])

### 4.3 タグ（横断メタ）
- **tag_def**(namespace, key, value_type, enum_values?, description)
- **tag_assignment**(entity_type, entity_id, tag_id, value_json, scope, effective_from, expires_at?, source, confidence, created_by/at, updated_by/at)

### 4.4 監査
- **audit_event**(trace_id, event, actor, at, target, diff, reason)

---

## 5. ルールエンジン（述語DSL, v1）

### 5.1 述語
- `contains_any(ingredient_ids, [...])`
- `process_any([...])`
- `origin_in([...])`
- `threshold(field, op, value)` 例: `threshold("sugar_pct", ">=", 5)`
- `always`

### 5.2 ルール定義（YAML例）
```yaml
- id: hs19_bakery_wheat_baked
  when:
    all:
      - contains_any:
          ingredient_ids: ["ing_wheat_flour"]
      - process_any: ["baked", "roasted"]
  then:
    heading_hints: ["1905.90"]
    rationale: ["wheat flour present", "baked product"]
```

### 5.3 評価
- 先頭から順に `when` を評価、`then.heading_hints` を候補集合へ追加。
- コンフリクト時は信頼度スコア（ヒューリスティック）でランク付け。
- `review_required` 判定規則: 信頼度 < 閾値 / ルール衝突 / 特定品目。

---

## 6. エラー設計

### 6.1 共通フォーマット
```json
{
  "error": { "class": "invalid_argument", "message": "..." , "code": "E400_001", "fields": {"path.to.field":"reason"} }
}
```

### 6.2 主なエラーコード
| code         | http | 説明 |
|--------------|------|------|
| E400_001     | 400  | 必須項目不足 |
| E400_002     | 400  | UoM不整合 |
| E401_001     | 401  | 認証失敗 |
| E403_001     | 403  | 権限不足 |
| E404_001     | 404  | リソース未検出 |
| E409_001     | 409  | 状態不整合（PNロック等） |
| E422_001     | 422  | ルール評価不能 |
| E429_001     | 429  | レート超過 |
| E500_001     | 500  | 内部エラー |
| E503_001     | 503  | 連携先エラー |

---

## 7. セキュリティ・ガバナンス

- **認証**: InboundはAPIキー（`Authorization: Bearer <token>`）。WebhookはHMAC署名（`X-Signature`）。
- **権限**: RBAC（operator/customs/law）。`hs/*` 編集は通関士ロールのみ。
- **PII最小化**: 顧客情報は保持しない。注文IDは参照キーのみ。
- **暗号化**: TLS前提。保管時は秘密情報をKMS/OS暗号化。
- **監査**: すべての重要操作は `audit_event` に送出（trace_id必須）。保持7年。

---

## 8. 非機能要件

- **可用性**: 単一AZ障害に耐える（DBは定期バックアップ）。
- **性能**: HS分類 API P95 ≤ 300ms（キャッシュ有）/ 書類生成・PNは非同期。
- **スケーラビリティ**: APIは水平スケール、ジョブはワーカー数で調整。
- **可観測性**: 構造化ログ(JSON)、メトリクス（req/sec, p95, err率）, トレースID連結。

---

## 9. 設定・環境変数

| KEY | 例 | 説明 |
|-----|----|------|
| `DB_URL` | `postgresql+psycopg://cb:cbpass@db:5432/cbdb` | DB接続 |
| `SECRET_KEY` | `devsecret` | 署名/CSRF 用 |
| `CORS_ORIGINS` | `*` | CORS制御 |
| `STORAGE_BACKEND` | `local`/`s3` | 証憑ストレージ |
| `STORAGE_PATH` | `/data/media` | local時 |
| `PN_SANDBOX` | `true` | PN連携先切替 |
| `WEBHOOK_SIGN_ALG` | `HMAC-SHA256` | 署名 |
| `RATE_LIMIT` | `100rps` | レート制御 |

---

## 10. ジョブ・再試行・DLQ

- **ジョブ表**: `job(id, type, payload_json, status, attempts, next_run_at, result_json, error_json)`  
- **状態遷移**: `queued → running → (done | error)` / `error → retry/backoff` / `dlq`  
- **再試行**: 5回、指数バックオフ（初期3s, 上限2m）。  
- **Webhook**: 同仕様でリプレイUI提供。

---

## 11. DBスキーマ（要点）

- 正規化: `products`, `hs_classifications`, `pn_submissions`, `document_packages`, `tag_def`, `tag_assignment`, `audit_event`, `job`。
- 主要インデックス: `idx_*_trace`, `idx_job_status_next`, `gin` on JSONB（検索用）。
- マイグレーション: Alembic（バージョン管理 / rollback手順）。

---

## 12. バリデーション・JSON Schema

- `schemas/product.json`, `schemas/hs_classification.json`（要件定義の定義を踏襲）。
- API受信はSchema検証 → 400/422 を厳格返却。

---

## 13. エンドツーエンド・フロー（例）

1. 画像アップロード → 翻訳/正規化（`INGREDIENTS_TRANSLATED`）。  
2. HS分類（`HS_CLASSIFIED`）→ UoM確定。  
3. 書類生成ジョブ（`DOCS_PACKAGED`）。  
4. PN申請（`PN_SUBMITTED` → `PN_ACCEPTED|REJECTED`）。  
5. すべてのステップで `audit_event` を追記、Webhook送信。

---

## 14. テスト・受入基準

- **ユニット**: 述語・ルール評価、UoM整合、署名検証、Schema検証。
- **結合**: 書類パック生成、PNモック連携、Webhook再試行。
- **受入**: テストコーパス（≥50品目）で一次候補リコール≥80%、審査後100%。404/400/409 異常系カバレッジ。

---

## 15. デプロイ・運用

- **Docker Compose**（dev）, **Kubernetes**（prod想定）。
- 健康監視: `/v1/health` + メトリクスエンドポイント（将来）。
- バックアップ: DBスナップショット / 媒体暗号化。

---

## 16. バージョニング・互換性

- **ポリシー**: 追加はマイナー互換 / 既存フィールドの削除・意味変更禁止。  
- **廃止**: 非推奨 → 猶予期間 → 切替ガイド提供。

---

## 付録 A: 用語集
- **PN**: Prior Notice（FDAへの事前通知）
- **UoM**: Unit of Measure（計量単位）
- **DLQ**: Dead Letter Queue（再送不能行き）

---



````markdown
# 越境EC AI自動化アプリ  
## 要件定義書（連携・境界仕様）

---

## 1. 目的
このアプリは越境EC業務における「**規制・分類・通関・監査**」の自動化を目的とする。  
販売・マーケティング領域は別アプリで実装し、本アプリは**規制判断の中核**と**連携の入口**のみを担う。

---

## 2. 機能スコープ

| 領域                     | 本アプリで実装                       | 他アプリ（マーケ・EC） |
|--------------------------|--------------------------------------|---------------------------|
| 成分抽出/OCR             | ✔ 自動翻訳＋構造化                   | ✖                         |
| HSコード分類             | ✔ AI＋ルールベース                   | ✖                         |
| PN（Prior Notice）生成   | ✔ 自動化＋ステータス管理             | ✖                         |
| 書類生成・監査           | ✔ 署名・トレーサビリティ              | ✖                         |
| マーケ分析               | ✖                                    | ✔                         |
| 顧客・注文管理           | ✖                                    | ✔                         |
| 在庫・販売・決済         | ✖                                    | ✔                         |

---

## 3. 連携ポリシー（システム境界）

本アプリは以下の3系統で外部と接続する。

### 3.1 Outbound Webhook（イベント送信）
- **目的**：分類・翻訳・書類生成・PN処理など、主要イベントを他システムに通知
- **例**：
  - `PRODUCT_NORMALIZED`
  - `INGREDIENTS_TRANSLATED`
  - `HS_CLASSIFIED`
  - `DOCS_PACKAGED`
  - `PN_SUBMITTED` / `PN_ACCEPTED` / `PN_REJECTED`
  - `AUDIT_APPENDED`
- **形式**：
  - `POST` JSON
  - HMAC署名（`X-Signature` ヘッダ）
  - 再試行（指数バックオフ、72h DLQ）
- **設定**：
  - Webhook URL複数登録可能
  - 有効・無効切替／手動リプレイ対応

---

### 3.2 Inbound API（イベント受信）
- **目的**：最低限の販売状態を受信して規制処理をトリガ
- **対象イベント**：
  - `ORDER_PAID`（課税・PNロック）
  - `ORDER_CANCELED`（PN取消判断）
- **仕様**：
  - `POST /v1/integrations/orders/:id/status`
  - 最小項目：
    ```json
    {
      "order_id": "ORD-123",
      "status": "PAID",
      "ts": "2025-10-12T03:30:00Z",
      "customer_region": "US"
    }
    ```
  - 本アプリは注文詳細を保持しない

---

### 3.3 Pull API（データ共有）
マーケアプリ側が必要な時のみ参照。

| API                                    | 内容                             |
|-----------------------------------------|------------------------------------|
| `GET /v1/products/:id/compliance`       | HS分類結果、UoM、アレルゲン等     |
| `GET /v1/jobs/:id`                      | PN・書類処理状況                  |
| `GET /v1/audit/trace/:traceId`         | 監査ログ・根拠の参照              |

---

## 4. イベントペイロード（例）

### 4.1 `HS_CLASSIFIED`
```json
{
  "event_id": "evt_20251012_0001",
  "event_type": "HS_CLASSIFIED",
  "occurred_at": "2025-10-12T03:30:00Z",
  "product": {
    "product_id": "prod_xxx",
    "category": "confectionery",
    "origin_country": "JP"
  },
  "hs": {
    "candidates": [{"code":"1905.90","confidence":0.82}],
    "final_code": "1905.90",
    "required_uom": "kg",
    "review_required": false
  },
  "trace_id": "LAW-2025-10-10-XYZ"
}
````

### 4.2 `DOCS_PACKAGED`

```json
{
  "event_type": "DOCS_PACKAGED",
  "occurred_at": "2025-10-12T03:40:00Z",
  "job_id": "JOB-123",
  "artifacts": [
    {"type":"commercial_invoice","media_id":"sha256:..."},
    {"type":"packing_list","media_id":"sha256:..."}
  ],
  "uom_check": {"required":"kg","invoice":"kg","valid":true},
  "trace_id":"LAW-2025-10-10-XYZ"
}
```

---

## 5. データ保持ポリシー

| 区分            | 保持 | 理由            |
| ------------- | -- | ------------- |
| 成分・HS・翻訳      | ✔  | 規制判断に必要       |
| PN申請情報        | ✔  | 法令上の記録保持義務    |
| 顧客情報（PII）     | ✖  | マーケアプリ側で保持    |
| 売上・CVR・マーケKPI | ✖  | 本アプリの責任範囲外    |
| 書類・証憑         | ✔  | トレーサビリティ、税関対応 |
| ログ・監査         | ✔  | 説明可能性、訴訟・監査対応 |

---

## 6. ID・フォーマット規約

* `product_id`, `sku_id`, `job_id`, `trace_id`：UUIDまたは英数固定
* 国コード：ISO 3166-1 alpha-2
* HSコード：6/8/10桁対応
* UoM（単位）：国際単位（kg, l, No.）
* 日時：UTC ISO8601（`occurred_at`）
* Webhook署名：HMAC-SHA256（`X-Signature`）

---


## 6.1 互換性と表現ルール（上流規範）

- 互換性は追加のみ。破壊的変更は不可。
- 関税率表現は小数（例: 0.05 = 5%）に統一。
- Complianceの鮮度は"最新"または"最終計算時点のスナップショット"として定義する。
- 詳細仕様は `docs/if_spec_extended.md` を正とする。
## 7. 運用設計

* Webhook リプレイ／一時停止／再送機能をUIに実装
* Webhook マッピング（コード体系変換）の設定
* PN却下時のマーケ連携はイベント通知のみ（制御はしない）
* ログ・トレースIDで全処理を遡れるように設計

---

## 8. 今後の開発タスク（ToDo）
### 8.1 仕様リンク（該当Issue/関連ソース）

- Issue: #7（duty_rate移行、Compliance鮮度、DSL定義の整合）
- 関連セクション: 2. 機能スコープ / 3.3 Pull API / 6. ID・フォーマット規約 / 9. 非機能要件
- 関連仕様/実装ファイル:
  - docs/if_spec_extended.md
  - docs/openapi_diff_extended.yaml
  - backend/openapi.yaml
  - backend/app/api/v1_classify.py
  - frontend/src/types.ts
  - docs/api_design_hs_classification.md
  - docs/spec/backend_spec_v1_draft.md
  - docs/spec/SPEC.md


- デプロイ戦略（Composeベース）: docs/deployment_strategy.md
- 仕様マイルストーン: docs/spec/spec_milestone_plan.md


| 項目                          | 内容                    | 期日 | 担当      |
| --------------------------- | --------------------- | -- | ------- |
| OpenAPIドラフト                 | Webhook送信・受信I/F仕様     | -  | dev     |
| イベントカタログ定義                  | HS/PN/Doc等の最低イベント7種   | -  | dev     |
| Webhook設定UI                 | URL・Secret・有効/無効・フィルタ | -  | dev     |
| `ORDER_PAID/CANCELED` API仕様 | 必須項目とバリデーション          | -  | dev     |
| データ保持・非保持一覧                 | セキュリティレビュー用明文化        | -  | PM      |
| 責任分界図＋障害時対応フロー              | 本番リリース前合意             | -  | dev/ops |

---

## 9. 非機能要件

* Webhook遅延：P95 ≤ 5s
* 再送上限：72時間
* イベント互換性：**追加のみ許可**（削除・意味変更は禁止）
* 監査保全期間：7年

---

## 10. 今後の拡張余地

* マーケアプリとのKPI連携（BI/DWH）
* 成分変更に伴う自動再分類・再申請
* 外部ラベル翻訳・規制DBとのAPI連携
* ロット・原材料トレーサビリティ拡張

---

## 付録：責任分界（図解イメージ）

```
 ┌────────────────────┐         ┌────────────────────────────┐
 │ 越境EC AI自動化     │──────▶ │ マーケ・ECアプリ            │
 │（本システム）       │◀────── │ （販売・分析・在庫）        │
 └────────────────────┘         └────────────────────────────┘
       │                                   │
       ▼                                   ▼
   HS分類・PN申請                  KPI分析・広告・顧客管理
   証憑生成・審査                  注文・在庫・支払い
```

---
# 越境EC AI自動化アプリ  
## OpenAPIドラフト仕様書（Webhook送信・受信API）

---

## 1. 概要
本ドキュメントは、越境EC業務AI自動化アプリが外部システムと連携するための**Webhook（送信）**および**受信API（Inbound）**の通信仕様を定義する。  
目的は、**イベント駆動型の非同期連携**を可能にしつつ、**販売系システムとの責任分界**を明確にすること。

---

## 2. バージョン情報
- **APIバージョン**：v1  
- **フォーマット**：JSON（UTF-8）  
- **認証**：HMAC-SHA256署名（Webhook）またはAPIキー（Inbound）  
- **共通ヘッダー**：
  | Key | Value | 説明 |
  |-----|--------|------|
  | `Content-Type` | `application/json` | 常にJSON |
  | `X-Event-Type` | `HS_CLASSIFIED` 等 | イベント種別 |
  | `X-Signature` | `sha256=xxxx` | 署名（送信時） |
  | `X-Trace-ID` | 任意UUID | 処理トレース |

---

## 3. Webhook（Outbound Event）

### 3.1 エンドポイント登録
外部システムは `/v1/integrations/webhooks` にURLを登録し、受信イベントを指定する。

#### `POST /v1/integrations/webhooks`
```json
{
  "url": "https://partner-app.example.com/hooks/compliance",
  "secret": "abc123xyz",
  "events": ["HS_CLASSIFIED", "DOCS_PACKAGED", "PN_SUBMITTED"],
  "enabled": true
}

```
```

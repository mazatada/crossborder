# IF Specification: Extended Backend APIs

対象: Duty Calculation / HS Code Master / HS Classification Review / HS Rule Management / Product Compliance  
前提: 既存 `openapi.yaml` / `SPEC.md` に準拠し、後方互換を維持した上での追加APIである。
参照: `backend/openapi.yaml` / `docs/spec/SPEC.md`

---

## 0. 共通前提

### 0.1 認証・バージョニング・エラー

- 認証: `Authorization: Bearer <api_key>`（既存仕様と同一）
- バージョン: `/v1/` プレフィックスを維持
- エラー形式: 既存の `Error400` / `Violation422` スキーマを再利用  
  - 400: 必須欠落・型不正  
  - 404: リソース未存在  
  - 409: 競合（レビュー済みレコードの更新試行など）  
  - 422: ビジネスバリデーション違反（ルール評価不能など）

### 0.2 トレース・監査

- 可能な限り `X-Trace-ID` ヘッダと `trace_id` プロパティを利用
- 重要な変更操作（HS分類レビュー更新、ルールCRUD）は `audit_event` に記録  
  - event: `"hs.review.update"`, `"hs.rule.create"` など
  - actor: APIキー起点（operator/customs/law などのRBACは将来拡張）

### 0.3 日付・日時フォーマット

- 日付: `YYYY-MM-DD`  
- 日時: ISO 8601（UTC, `Z` サフィックス）


---
### 0.4 互換性・移行ポリシー

- `ad_valorem_rate` を正とする（小数表現）
- 互換のため `ad_valorem_pct` は移行期間のみ返却可
  - 返却時は `ad_valorem_rate` を必須、`ad_valorem_pct` は任意
- 相互制約: `ad_valorem_pct` は `ad_valorem_rate * 100` と一致必須
  - 受信時に両方が指定された場合は一致必須（例: 0.05 と 5.0）
- 移行期間の終了後は `ad_valorem_pct` を廃止予定（次期メジャーで削除予定）
- UI表示: `ad_valorem_rate` が null の場合は「未算出」と表示する


---

## 1. Duty Calculation API
### 1.0 DutyRate算出方針（段階導入）

- 初期: `ad_valorem_rate` は null を許容（互換期間）
- 段階1: TariffRateResponse の `duty_rate.ad_valorem_rate` を `hs_code`/`destination_country` から算出
- 段階2: `origin_country`/FTA を考慮した最終税率に更新
- 段階3: `duty_rate_override` 更新時に `Compliance` 側へ反映


関税率の参照および関税額の計算を提供するAPI群。

### 1.1 `GET /v1/tariffs/{destination_country}/{hs_code}`

#### 目的

- 指定した仕向国・HSコードについて、現時点または指定日付時点の基本税率および追加関税（AD/CVD等）を返す。

#### パスパラメータ

- `destination_country` (string, ISO 3166-1 alpha-2, 必須)  
- `hs_code` (string, 必須)  
  - 形式: `"^\d{4}(\.\d{2}){0,2}$"` または `^\d{6,10}$` を許容（正規化済み or ドット付き）

#### クエリパラメータ

- `origin_country` (string, 任意)  
  - 原産国。FTA/特恵税率の判定に利用。
- `as_of` (string, date, 任意)  
  - `YYYY-MM-DD`。省略時は当日。

#### 成功レスポンス 200

```json
{
  "destination_country": "US",
  "hs_code": "1905.90",
  "origin_country": "JP",
  "as_of": "2025-12-06",
  "duty_rate": {
    "type": "ad_valorem",
    "ad_valorem_rate": 0.05,
    "specific": null,
    "currency": "USD",
    "basis_uom": null
  },
  "additional_duties": [
    {
      "type": "section301",
      "rate_type": "ad_valorem",
      "rate": 0.075,
      "amount": null,
      "basis": "customs_value"
    }
  ],
  "metadata": {
    "tariff_schedule_version": "HTSUS_2025_v3",
    "source": "internal_master",
    "last_updated_at": "2025-11-20T00:00:00Z"
  }
}
```

#### 主なフィールド仕様

- `duty_rate.type`: "ad_valorem" | "specific" | "mixed"  
- `duty_rate.ad_valorem_rate`: 関税率（小数、0.05 は 5%）  
- **移行**: `ad_valorem_pct` は互換期間のみ（5.0は5%）  
- `duty_rate.specific`: 従量税額（1単位あたり）  
- `additional_duties[]`:
  - `type`: `"section301"`, `"safeguard"`, `"anti_dumping"`, `"countervailing"` など
  - `rate_type`: `"ad_valorem"` or `"specific"`

#### エラー

- 400: フォーマット不正（国コード/日付）  
- 404: 指定HS/国/日付で税率未定義  
- 422: 内部ルール評価不能

---

### 1.2 `POST /v1/tariffs/calculate`

#### 目的

- HSコード・原産国・仕向国・申告価額などを入力し、関税額の計算結果と内訳を返す。

#### リクエストボディ

```json
{
  "hs_code": "1905.90",
  "origin_country": "JP",
  "destination_country": "US",
  "customs_value": {
    "amount": 1000.0,
    "currency": "USD"
  },
  "quantity": 200.0,
  "uom": "kg",
  "valuation_method": "CIF",
  "declaration_date": "2025-12-06",
  "options": {
    "apply_preferential_if_available": true,
    "rounding_mode": "standard"
  }
}
```

- 必須:
  - `hs_code`, `origin_country`, `destination_country`, `customs_value`
- 任意:
  - `quantity`/`uom`: 従量税用
  - `valuation_method`: `"FOB" | "CIF" | "EXW"` 等
  - `declaration_date`: 関税改定前後での比較などに利用
  - `options.rounding_mode`: `"standard" | "floor" | "ceil"`

#### 成功レスポンス 200

```json
{
  "hs_code": "1905.90",
  "origin_country": "JP",
  "destination_country": "US",
  "customs_value": {
    "amount": 1000.0,
    "currency": "USD"
  },
  "duty": {
    "total_amount": 125.0,
    "currency": "USD",
    "components": [
      {
        "type": "basic",
        "rate_type": "ad_valorem",
        "rate": 0.05,
        "amount": 50.0,
        "basis": "customs_value"
      },
      {
        "type": "section301",
        "rate_type": "ad_valorem",
        "rate": 0.075,
        "amount": 75.0,
        "basis": "customs_value"
      }
    ]
  },
  "applied_rates": {
    "tariff_schedule_version": "HTSUS_2025_v3",
    "rules": [
      {
        "code": "basic",
        "description": "MFN rate",
        "legal_reference": "HTSUS 1905.90"
      },
      {
        "code": "section301",
        "description": "Section 301 duties",
        "legal_reference": "FR Doc 2019-xxxx"
      }
    ]
  }
}
```

#### エラー

- 400: 必須欠落・型不正  
- 404: 税率情報が見つからない  
- 422: ロジック上不整合（例: valuation_methodとcustoms_valueの整合性が取れない）

---

## 2. HS Code Master API

HSコード定義（説明・デフォルトUoMなど）の参照と検索API。

### 2.1 `GET /v1/hs-codes/{code}`

#### 目的

- 指定したHSコードの正式な説明・チャプター情報・デフォルトUoM等を返す。

#### パスパラメータ

- `code` (string, 必須)  
  - `"1905.90"` や `"190590"` など

#### クエリパラメータ

- `country` (string, 任意)  
  - `"US"` 等。ローカルHS（HTSUSなど）を扱う場合。

#### 成功レスポンス 200

```json
{
  "code": "1905.90",
  "normalized_code": "190590",
  "chapter": "19",
  "heading": "1905",
  "description_en": "Bread, pastry, cakes, biscuits and other bakers' wares",
  "description_local": "パン、菓子、ビスケットその他のベーカリー製品",
  "default_required_uom": "kg",
  "notes": {
    "chapter_note": "Chapter 19 notes ...",
    "exclusions": [
      "Prepared foods of heading 2106"
    ]
  },
  "valid_from": "2022-01-01",
  "valid_to": null,
  "metadata": {
    "source": "WCO_HS_2022",
    "last_updated_at": "2025-10-01T00:00:00Z"
  }
}
```

---

### 2.2 `GET /v1/hs-codes`

#### 目的

- テキストやチャプターを用いた検索用API。

#### クエリパラメータ

- `q` (string, 任意): 説明文検索キーワード  
- `chapter` (string, 任意): 章番号（例: `"19"`）  
- `country` (string, 任意): ローカルHS用  
- `limit` (integer, 任意, default=20, max=100)  
- `cursor` (string, 任意): ページング用トークン  

#### 成功レスポンス 200

```json
{
  "items": [
    {
      "code": "1905.31",
      "description_en": "Sweet biscuits",
      "description_local": "ビスケット（甘味）",
      "default_required_uom": "kg"
    },
    {
      "code": "1905.90",
      "description_en": "Other",
      "description_local": "その他",
      "default_required_uom": "kg"
    }
  ],
  "next_cursor": "eyJvZmZzZXQiOjJ9"
}
```

---

## 3. HS Classification Review API

`hs_classifications` テーブルの読み出し・人手レビュー確定のためのAPI。

### 3.1 `GET /v1/hs-classifications/{id}`

#### 目的

- 自動分類結果を含む1件のHS分類レコードを取得し、通関士レビュー画面に表示する。

#### パスパラメータ

- `id` (string, UUID想定, 必須)

#### 成功レスポンス 200

```json
{
  "id": "2c38f4f4-1f9c-4c3d-9d7b-8c1b3e6e1234",
  "trace_id": "trace-20251206-001",
  "product_id": "prod_12345",
  "status": "classified",
  "hs_candidates": [
    {
      "code": "1905.90",
      "description": "Bread, pastry, cakes etc.",
      "confidence": 0.87,
      "rationale": [
        "Contains wheat flour 60%",
        "Category: bread / bakery"
      ],
      "required_uom": "kg"
    }
  ],
  "final_hs_code": "1905.90",
  "final_source": "system",
  "duty_rate": {
    "type": "ad_valorem",
    "ad_valorem_rate": 0.05,
    "specific": null,
    "currency": "USD",
    "basis_uom": null
  },
  "risk_flags": [
    {
      "code": "contains_allergen",
      "severity": "medium",
      "description": "Contains wheat and milk"
    }
  ],
  "review_required": true,
  "reviewed_by": null,
  "reviewed_at": null,
  "review_comment": null,
  "created_at": "2025-12-06T01:23:45Z",
  "updated_at": "2025-12-06T01:23:45Z"
}
```

---

### 3.2 `PUT /v1/hs-classifications/{id}`

#### 目的

- 通関士がHSコード・関税情報・リスクなどを確認し、最終確定する。

#### リクエストボディ

```json
{
  "final_hs_code": "1905.90",
  "final_source": "manual",
  "duty_rate_override": {
    "ad_valorem_rate": 0.05,
    "additional": [
      {
        "type": "section301",
        "rate_type": "ad_valorem",
        "rate": 0.075
      }
    ]
  },
  "review_required": false,
  "review_comment": "No issue. Applied basic + Section 301 duty.",
  "reviewed_by": "tsukan-shi_001"
}
```

- `final_hs_code`: 変更があれば上書き、未指定なら現状維持  
- `final_source`: `"system" | "manual" | "rule" | "llm"` など  
- `duty_rate_override`: Duty Calculation APIの結果からの人手上書き用
  - `DutyRateDetailed` + `additional_duties` を許容
- `review_required`: 指定時に更新可。未指定なら現状維持。
- override優先: duty_rate_override が指定された場合、`duty_rate` より優先される。

#### 成功レスポンス 200

- `GET /v1/hs-classifications/{id}` と同一形式で最新状態を返す。

#### エラー

- 404: id不明  
- 409: 既にロック済み（通関完了など）で更新不可  

---

## 4. HS Rule Management API

YAMLファイルで管理していたHS分類ルールをDB管理へ移し、API経由でCRUDとテストを行う。

### 4.1 モデル概要: HSRule

- `id`: string/UUID  
- `name`: string  
- `description`: string  
- `priority`: integer（小さいほど優先）  
- `scope`: string（例: `"food"`, `"cosmetic"`）  
- `condition_dsl`: string（既存DSL/YAML本体）  
- `effect`: object（`{ "hs_code": "1905.90", "weight": 0.8, "tags": ["baked_goods"] }` 等）  
  - `weight`: 0.0〜1.0 の優先度係数（高いほど優先）
  - 複数マッチ時は `weight` > `priority` > `version` の順で決定
  - 同値の場合は `created_at` が早いものを優先
- `status`: `"draft" | "active" | "inactive"`  
- `version`: integer  
- `created_by`, `updated_by`: string  
- `created_at`, `updated_at`: datetime  

#### condition_dsl 仕様（簡易）
- 比較: `==`, `!=`, `>`, `>=`, `<`, `<=`
- 論理: `and`, `or`, `not`
- 代表的な関数: `ingredient.contains("wheat")`, `pct("wheat") >= 30`
- 例: `ingredient.contains("wheat flour") and wheat_pct >= 30 and is_baked == true`


#### condition_dsl 仕様（利用可能なフィールド）
- `product.name`: string
- `product.category`: string
- `product.origin_country`: string (ISO 3166-1 alpha-2)
- `ingredients[].name`: string
- `ingredients[].pct`: number
- `process[].name`: string
- `is_baked`: boolean（プロセス推定フラグ）


---

### 4.2 `GET /v1/hs-rules`

#### 目的

- ルール一覧を取得し、管理画面で一覧表示する。

#### クエリパラメータ

- `status`: `"draft" | "active" | "inactive"`  
- `scope`: string  
- `limit` / `cursor`: ページング

#### 成功レスポンス 200

```json
{
  "items": [
    {
      "id": "rule_hs_food_001",
      "name": "Wheat-based baked goods",
      "description": "Products with wheat flour > 30% are likely 1905.x",
      "priority": 100,
      "scope": "food",
      "status": "active",
      "version": 3,
      "updated_at": "2025-12-05T10:00:00Z"
    }
  ],
  "next_cursor": null
}
```

---

### 4.3 `POST /v1/hs-rules`

#### 目的

- 新規ルールを作成する（初期状態は `draft` 推奨）。

#### リクエストボディ

```json
{
  "name": "Wheat-based baked goods",
  "description": "Wheat flour ≥ 30% and baked.",
  "priority": 100,
  "scope": "food",
  "condition_dsl": "if ingredient.contains('wheat flour') and wheat_pct >= 30 and is_baked: ...",
  "effect": {
    "hs_code": "1905.90",
    "weight": 0.8,
    "tags": ["baked_goods"]
  },
  "status": "draft"
}
```

#### 成功レスポンス 201

- 作成されたHSRule全体を返す（`id`, `version=1`, `created_at` 等含む）

---

### 4.4 `GET /v1/hs-rules/{id}` / `PUT /v1/hs-rules/{id}` / `DELETE /v1/hs-rules/{id}`

- `GET`: 単一ルール詳細取得  
- `PUT`: ルールの更新（`condition_dsl` / `effect` 変更時は `version` 自動増加）  
- `DELETE`: 論理削除 or status=`inactive` への遷移（物理削除は避ける）

---

### 4.5 `POST /v1/hs-rules:test`

#### 目的

- 本番有効化前に、ルールの動作をサンプル商品に対してシミュレーションする。

#### リクエストボディ

```json
{
  "rule": {
    "name": "Wheat-based baked goods",
    "priority": 100,
    "scope": "food",
    "condition_dsl": "if ingredient.contains('wheat flour') and wheat_pct >= 30 and is_baked: ...",
    "effect": {
      "hs_code": "1905.90",
      "weight": 0.8
    }
  },
  "product_sample": {
    "name": "Chocolate chip cookie",
    "ingredients": [
      { "name": "wheat flour", "pct": 40.0 },
      { "name": "sugar", "pct": 30.0 },
      { "name": "cocoa mass", "pct": 10.0 }
    ],
    "category": "cookie"
  }
}
```

#### 成功レスポンス 200

```json
{
  "matched": true,
  "reason": [
    "ingredient 'wheat flour' found with pct 40.0 >= 30.0",
    "is_baked == true"
  ],
  "effect_preview": {
    "hs_code": "1905.90",
    "weight": 0.8
  }
}
```

#### エラー

- 400: DSL構文エラー（`error.class="rule_dsl_error"` など）

---

## 5. Product Compliance API

商品ごとの最新コンプライアンス状態（HS/関税/PN/書類）をまとめて返す集約ビュー。

### 5.1 `GET /v1/products/{product_id}/compliance`

#### 目的

- EC担当画面・社内ツールから、「この商品は今どこまでOKか？」を一発で参照する。

#### パスパラメータ

- `product_id` (string, 必須)

#### 成功レスポンス 200

```json
{
  "product_id": "prod_12345",
  "trace_id": "trace-20251206-001",
  "hs_classification": {
    "final_hs_code": "1905.90",
    "final_source": "manual",
    "review_required": false,
    "status": "classified",
    "reviewed_by": "tsukan-shi_001",
    "reviewed_at": "2025-12-06T02:00:00Z",
    "risk_flags": [
      {
        "code": "contains_allergen",
        "severity": "medium",
        "description": "Contains wheat and milk"
      }
    ]
  },
  "duty": {
    "destination_country": "US",
    "origin_country": "JP",
    "last_calculated_at": "2025-12-06T02:05:00Z",
    "customs_value": {
      "amount": 1000.0,
      "currency": "USD"
    },
    "duty": {
      "total_amount": 125.0,
      "currency": "USD"
    }
  },
  "docs": {
    "clearance_pack_job_id": "job_abc123",
    "clearance_pack_status": "completed",
    "prior_notice_required": true,
    "prior_notice_status": "submitted"
  },
  "audit": {
    "last_updated_by": "tsukan-shi_001",
    "last_updated_at": "2025-12-06T02:00:00Z"
  }
}
```

#### エラー

- 404: product_id不明  
- 200 + `hs_classification.status = "pending"`: まだ分類前

#### 鮮度・設定主体
- `hs_classification`: 最新の `hs_classifications` レコード由来
- `duty`: 直近計算結果（または最終計算時点のスナップショット）
- `docs`: `/v1/docs/clearance-pack` と `/v1/fda/prior-notice` のジョブ結果由来


#### docs フィールドの扱い
- `docs.*` はシステム管理の読み取り専用。クライアントからの更新不可。


#### 更新トリガー
- `hs_classification`: `/v1/classify/hs` 完了時、またはレビュー更新（PUT）時
- `duty`: `/v1/tariffs/calculate` 実行時、または `duty_rate_override` 更新時
- `docs`: clearance-pack / prior-notice のジョブ完了時


---

## 6. モデル定義（再利用前提）

### DutyRateDetailed
- `type`: "ad_valorem" | "specific" | "mixed"
- `ad_valorem_rate`: number（小数、0.05 = 5%）
- `specific`: number | null（従量税額）
- `currency`: string | null
- `basis_uom`: string | null

### AdditionalDuty
- `type`: "section301" | "safeguard" | "anti_dumping" | "countervailing"
- `rate_type`: "ad_valorem" | "specific"
- `rate`: number（小数、0.075 = 7.5%）
- `amount`: number | null
- `basis`: "customs_value" | "quantity"

### DutyRateOverride
- `duty_rate`: `DutyRateDetailed`
- `additional_duties`: `AdditionalDuty[]`

### HSClassificationReview
- `duty_rate`: `DutyRateDetailed` を参照
- `review_required`: boolean

### ComplianceView
- `hs_classification.status`: "pending" | "classified" | "reviewed"
- `docs.*`: ジョブ結果由来（変更主体はシステム）

## 7. OpenAPIへの反映方針

- 本IF仕様の各エンドポイント・モデルは、`openapi.yaml` に以下のように反映する:
  - `paths` に新規パスを追加
  - `components.schemas` に新規スキーマ（DutyRateDetailed, DutyComponent, HSCode, HSRule, HSClassificationReview, ComplianceView など）を追加
- 既存スキーマ（特に `HSResponse.duty_rate`）は互換性維持のため変更しない  
  - Duty Calculation APIは新しい詳細スキーマを使用する
- エラー仕様は既存の `Error400` / `Violation422` を参照する

以上。

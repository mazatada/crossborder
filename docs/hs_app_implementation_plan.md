# HSコード自動化アプリ 追加機能 実装計画書（MVP→多段展開）
作成日: 2026-03-03  
対象: 越境EC（季節限定・限定ドロップ中心）向け HSコード/通関業務の自動化バックエンド

---

## 0. 目的と成功条件
本計画は、HSコード推定バックエンドに「通関で詰まる面倒」を吸収する機能を追加し、限定ドロップ運用を回せる状態を最短で作る。

成功条件は次の3つを同時に満たすこととする。

- **出荷前に止める**: 必須情報欠落・国別追加要件・禁止/高リスクの検知を出荷前にブロックまたはレビューに送る。
- **書類が出る**: EAD/税関告知/商業インボイスに必要な行データ（CSV/JSON）を確定し、再現可能に出力できる。
- **二重入力を消す**: Shopify（または販売チャネル）へ確定情報を戻し、注文起点でジョブが自動生成される。

---

## 1. 前提と必要な仮定
現時点で「外部から受け取るJSON契約が未定」なので、本計画では **バックエンドが主導して契約を定義**する。

仮定（必要最小）:
- 初期の発送は **日本発・郵便（EAD前提）中心**、対象国は絞る。
- 取扱は **加工済み常温食品が主**（一部非食品も将来あり得る）。
- 入口は **DDU/DAP寄り**、上位で **DDP（関税込み）や補償**を検討。
- 現在のバックエンドには「HS候補生成・スコアリング・ジョブ基盤・監査ログ」がある前提で、欠けている周辺を足す。

---

## 2. スコープ
### 2.1 今回のMVPでやること（面倒の8割を取る）
1. **商品マスタ（通関属性の正規化）**
2. **国別ルールエンジン（要件差分/禁止/追加コード/インコターム）**
3. **レビューキュー（割当・ロック・監査）**
4. **書類データ層（EAD/InvoiceのCSV/JSON）＋バリデーション**
5. **Shopify同期（商品メタ更新＋注文取り込み）**
6. **テストと運用KPI（回帰・EAD欠落検知・ドロップ模擬）**

### 2.2 今回はやらないこと（後段）
- HS分類のML高度化（まずはデータと運用を固める）
- 完全自動のDDP関税見積り（暫定はルール＋対象国絞り）
- すべての国の食品規制の網羅（初期は対象国セットのみ）

---

## 3. 追加機能の全体アーキテクチャ
### 3.1 追加後の処理フロー（イベント駆動）
1. **商品登録/更新**（Shopify or 管理UI）  
2. Productマスタに保存 → **必須属性バリデーション**  
3. HS推定ジョブ（任意/自動） → **候補＋確信度＋理由**  
4. 宛先国/配送モードを指定 → **国別ルール評価**（追加コード要否/禁止/要レビュー）  
5. 注文確定イベント → **出荷パック生成ジョブ**（EAD/Invoice行データ）  
6. 出力（CSV/JSON）→（後段でPDFやラベルへ接続）  
7. 監査ログに全イベントを記録（trace_id一貫）

### 3.2 設計原則
- **「分類できない」より「出荷できない/レビューへ」**に倒す。
- **HSは6桁を核**とし、国別追加コード（CN/TARIC等）は「必要なら要求する」。
- 書類は **まず行データ（CSV/JSON）**、PDFは後段。

---

## 4. データモデル（DB）設計
> 既存テーブルは維持しつつ、結合点として Product / Shipment / Document を追加する。

### 4.1 Product（新規）
- `id`（内部ID）
- `external_ref`（例: shopify_product_id / variant_id）
- `title`
- `description_en`（通関用短文: 例 “Japanese snack (processed confectionery)”）
- `origin_country`（ISO2）
- `is_food`（bool）
- `processing_state`（processed/fresh/frozen/unknown）
- `physical_form`（solid/powder/liquid/mixed）
- `unit_weight_g`
- `dimensions_mm`（任意）
- `shelf_life_days`（任意）
- `packaging`（JSON: individual_wrap等）
- `animal_derived_flags`（JSON: meat/dairy/egg/seafood）
- `hs_base6`（確定値。未確定ならNULL）
- `country_specific_codes`（JSON: { "FR": {type,digits,value}, ... }）
- `status`（draft/ready/review_required/locked）

**必須（出荷ブロッカー）**  
`description_en`, `origin_country`, `is_food`, `processing_state`, `physical_form`, `unit_weight_g`

**準必須（欠けたらレビュー）**  
`animal_derived_flags`, `shelf_life_days`（食品の場合は強推奨）

### 4.2 HSClassification（既存を拡張）
- `product_id`（FK追加）
- `destination_country`（任意: ルール評価と紐付け用）
- `candidates[]`（既存）
- `final_hs_base6`（既存 or 追加）
- `review_required` / `review_reasons[]`
- `locked_at`, `locked_by`（ロック）

### 4.3 Shipment（新規）
- `id`
- `order_ref`（shopify_order_id等）
- `destination_country`
- `shipping_mode`（postal/courier）
- `incoterm`（DAP/DDP）
- `currency`
- `total_value`
- `total_weight_g`
- `status`（draft/review_required/ready/exported）
- `validation_errors[]`

### 4.4 ShipmentLine（新規）
- `shipment_id`
- `product_id`
- `qty`
- `unit_price`
- `line_value`
- `line_weight_g`
- `hs_base6`
- `country_specific_code`（必要なら）
- `origin_country`
- `description_en`

### 4.5 DocumentExport（新規）
- `shipment_id`
- `type`（ead/invoice/customs_cn22/customs_cn23）
- `format`（csv/json/pdf）
- `storage_url`（S3等）
- `schema_version`
- `created_at`

---

## 5. API設計（JSON契約をここから作る）
> 「まだ何も受け取っていない」前提で、バックエンド中心に最小契約を定義する。

### 5.1 Product API（管理）
- `POST /v1/products`（作成）
- `PUT /v1/products/{id}`（更新）
- `GET /v1/products?status=...`（検索）
- `POST /v1/products/{id}/validate`（必須属性チェック）

### 5.2 HS分類 API
- `POST /v1/hs/classify`  
入力: `product_id`, `destination_country?`, `shipping_mode?`  
出力: `hs_base6 candidates`, `confidence`, `review_required`, `review_reasons`, `country_specific_requirements`

### 5.3 国別ルール評価 API
- `POST /v1/compliance/evaluate`  
入力: `product_id`, `destination_country`, `shipping_mode`, `incoterm`  
出力: `allowed`, `block_reasons`, `required_codes`, `required_fields`, `notes`

### 5.4 レビューキュー API（運用）
- `GET /v1/reviews/hs?status=pending`
- `POST /v1/reviews/hs/{classification_id}/assign`
- `POST /v1/reviews/hs/{classification_id}/lock`
- `POST /v1/reviews/hs/{classification_id}/finalize`（確定値をProductへ反映可能）

### 5.5 出荷パック生成 API
- `POST /v1/shipments/from-order`（注文参照でShipment生成）
- `POST /v1/shipments/{id}/generate-docs`（EAD/Invoice行データ生成）
- `GET /v1/shipments/{id}/exports`（出力一覧）

---

## 6. ルールエンジン（国別差分の吸収）
### 6.1 ルールの責務
- 追加コード要否（例: CN 8桁、TARIC 10桁など）
- 禁止・要許可・高リスク（初期は「ブロックorレビュー」）
- EAD必須項目の差分（郵便/クーリエ）
- インコタームによる表示・書類反映（DAP/DDP）

### 6.2 ルール定義形式
- YAML/JSON（既存のHSルール方式と同居できる形）
- ルールに **version** を付け、監査ログへ記録
- ルールの出力は「決定」ではなく **要求（required）** を返す  
例: `required_code: { type: "CN", digits: 8, required: true }`

### 6.3 初期対応国セット（例）
- Phase 0: SG / HK / AU（比較的運用しやすい想定）
- Phase 1: EU主要国（EAD/追加コード差分）
- Phase 2: US（食品はPrior Notice含む）

---

## 7. 書類データ層（CSV/JSON）とバリデーション
### 7.1 出力物（MVP）
- `commercial_invoice_header.csv`
- `commercial_invoice_lines.csv`
- `ead.json`（郵便向け内容品データ＋validation）

### 7.2 バリデーション（出荷ブロックの根拠）
- ルールエンジンが要求した `required_fields` と `required_codes` を検証
- 欠落があれば `shipment.status = review_required` にし、exports生成を止める
- validationは **スキーマ（JSON Schema等）** と **業務ルール** を分離

---

## 8. Shopify連携（最小実装）
### 8.1 方向性
- **商品→マスタ**: Shopify商品/バリアントをProductに同期
- **マスタ→商品**: `hs_base6`, `origin_country`, `unit_weight_g` 等をメタフィールドで戻す
- **注文→Shipment**: 注文作成/支払/フルフィルメントイベントでShipment生成ジョブを起動

### 8.2 必要機能
- Webhook署名検証
- 再送（retry）/DLQ（既存基盤があれば流用）
- idempotency（同じイベントが複数来ても二重生成しない）

---

## 9. レビュー運用設計（詰まらないキュー）
### 9.1 キューの種類
- HSレビュー（分類の曖昧さ、2106帯など）
- 国別追加コードレビュー（CN/TARIC等）
- 属性欠落レビュー（重量、説明文など）

### 9.2 ロックと監査
- 先にロックを取り、確定後は変更不可（例外は管理者のみ）
- 変更は必ず `audit_event` に残す（誰が・いつ・何を・なぜ）

---

## 10. セキュリティ/コンプライアンス
- PII（住所、氏名、電話）を監査ログに入れない（allowlist方式）
- 署名検証（Shopify webhook）
- 秘密情報（APIキー等）はVault/環境変数で管理
- エクスポートファイルは署名付きURL・期限付き

---

## 11. テスト計画とKPI
### 11.1 テスト種別
- ルール回帰テスト: 代表SKU100件で `final_hs_base6` と `review_required` を毎回比較
- スキーマテスト: EAD/Invoice出力が必須項目欠落ならCIで落とす
- 統合テスト: Shopifyイベント→Shipment→docs生成→exports取得のE2E
- ドロップ模擬: 100件Shipmentを投入し、処理時間/失敗率/レビュー滞留を計測

### 11.2 KPI（最初に追う3本）
- `review_rate`（レビュー比率）
- `time_to_decision`（レビューの意思決定時間）
- `export_success_rate`（EAD/Invoiceの生成成功率）
（後段で通関遅延率・返送率へ接続）

---

## 12. 実装ロードマップ（優先順）
### Phase 0: 結合点を作る（最優先）
- Productマスタ追加（DB + API + validate）
- 既存HSClassificationに product_id を紐付け
- trace_id の一貫付与（API→jobs→exports）

### Phase 1: 止める仕組み
- 国別ルールエンジン（最小: 追加コード要否、禁止フラグ、required_fields）
- レビューキュー（一覧・割当・ロック・確定）

### Phase 2: 書類が出る
- Shipment/ShipmentLineの生成（注文or手動）
- EAD/InvoiceのCSV/JSON出力＋バリデーション

### Phase 3: Shopify同期
- 商品同期（取り込み→Product作成）
- メタフィールド更新（hs/origin/weight）
- 注文Webhook→Shipmentジョブ生成

---

## 13. 受け入れ基準（Definition of Done）
- Product作成時に必須属性欠落は **保存不可** または **review_required** で明確に分岐
- 宛先国を指定すると、必要な追加コードや欠落項目が **機械的に列挙**される
- Shipmentを生成すると、EAD/Invoiceが **バリデーション付きで出力**できる
- Shopifyからの注文イベントで **重複なく** Shipmentが作られ、失敗時はDLQに残る
- 監査ログで「誰が何を確定したか」を追跡できる

---

## 14. 付録: JSONスキーマ雛形（最小）
> まだ何も受け取っていない前提の「契約のたたき台」。

```json
{
  "product": {
    "external_ref": {"platform": "shopify", "product_id": "123", "variant_id": "456"},
    "title": "Sakura Dorayaki",
    "description_en": "Processed Japanese confectionery snack",
    "origin_country": "JP",
    "is_food": true,
    "processing_state": "processed",
    "physical_form": "solid",
    "unit_weight_g": 85,
    "animal_derived_flags": {"meat": false, "dairy": false, "egg": true, "seafood": false}
  }
}
```

---

## 15. 次アクション（実装に着手する順）
1. Productスキーマ（必須/準必須）を確定し、DB migrationを作る  
2. `POST /v1/products` と `POST /v1/products/{id}/validate` を実装  
3. HSClassificationを `product_id` 結合に切り替え、レビュー理由を統一  
4. 国別ルールの最小セット（対象国3〜5）をYAMLで定義して評価APIを作る  
5. Shipment + docs export（CSV/JSON）を先に完成させ、PDFは後段に回す  

---

# 実装計画書 — 4. コア業務API群

対象: 翻訳API、HS分類、通関書類、PN申請。

---
## 1. 目的
- 成分→翻訳→分類→書類→PN申請を一貫APIで自動化。
- バリデーション強化と説明可能性確保。

---
## 2. 成果物
- `v1_translate_ingredients.py`
- `v1_classify_hs.py`
- `v1_docs_clearance_pack.py`
- `v1_fda_prior_notice.py`
- JSON Schema: `schemas/`

---
## 3. 各API要点
### /v1/translate/ingredients
- 入力: {text_ja, image_media_id?, product_context?}
- 出力: {terms:[{ja,en,canonical_id,confidence}]}
- 検証: text_ja or image_media_id 必須

### /v1/classify/hs
- 入力: {product:{name,category,process[],origin_country,ingredients[]}}
- 出力: {hs_candidates:[{code,confidence,rationale}], required_uom}
- 内部: DSLルール評価 + スコアリング

### /v1/docs/clearance-pack
- 入力: {traceId,hs_code,required_uom,invoice_uom}
- 出力: {job_id,status:"queued"}
- 動作: ジョブ起票 + PDF生成

### /v1/fda/prior-notice
- 入力: {traceId,product,logistics,importer,consignee}
- 出力: 202 + job_id
- ジョブ完了で Webhook `PN_SUBMITTED`

---
## 4. テスト計画
- 400/401/422 の異常系網羅
- 正常系で成果物(PDF/JSON)を確認
- `trace_id` 連携を検証

---
## 5. Definition of Done
- 4 API が OpenAPI仕様どおりに応答
- バリデーション/エラーが統一形式
- 全処理で監査イベント発行

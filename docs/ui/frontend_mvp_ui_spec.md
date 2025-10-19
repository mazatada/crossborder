# フロントエンド最小仕様（MVP/US食品）
最終更新: 2025-10-12 07:43:38 UTC

本書は、越境EC自動化MVPにおける**5画面**のUI最小仕様（項目・バリデーション・エラー表示・APIマッピング）を定義します。  
バックエンドは先行策で配布済みの `openapi.yaml` に準拠します。

---

## 0. 画面一覧（ナビゲーション）
1. **成分取り込み**（画像/OCR・手入力・辞書ヒット確認）  
2. **翻訳レビュー**（用語マージ・信頼度・採否）  
3. **HS分類レビュー**（候補・根拠表示・確定/UoM確認）  
4. **通関書類パック**（生成実行・UoM整合・成果物DL）  
5. **PN申請モニタ**（submitted/accepted/rejected・Webhookログ）

上記に加え、**ジョブ一覧**と**監査ログ**は各画面から遷移する補助ビューとして提供します（MVPはテーブルのみ）。

---

## 1) 成分取り込み画面
**目的**: 日本語ラベル（画像/テキスト）から成分を構造化し、辞書化IDへ正規化する。

### フォーム項目
| 項目 | 型 | 必須 | 入力規則 | 例 |
|---|---|---|---|---|
| ラベル画像 | file(image/*) | 任意 | 10MB以下 / png,jpg | label.jpg |
| 成分テキスト(JA) | textarea | 任意 | 10,000文字以内 | 小麦粉、砂糖、卵… |
| 製品名 | text | 必須 | 2..100文字 | どら焼き |
| カテゴリ | select | 必須 | confectionery / processed_food | confectionery |
| 加工プロセス | multiselect | 任意 | baked, roasted, mix, powder, canned, bottled | baked |
| 原産国 | select | 任意 | ISO-3166-1 alpha-2 | JP |

### 動作
- 画像アップロード→OCR（将来拡張）。MVPは**テキスト入力優先**。
- 「正規化を実行」クリック → POST /v1/translate/ingredients (JSON)。

### バリデーション/エラー
- **前提**: 製品名/カテゴリは必須。画像 or テキストの**少なくとも1つ**が必要。  
- 失敗例: 400 missing_required → トースト「必須項目を確認してください」＋フィールド別エラー。  
- CORS/ネットワーク: トースト「接続に失敗しました（再試行）」 + リトライ。

---

## 2) 翻訳レビュー画面
**目的**: 自動翻訳結果を**人手で最終確定**、用語辞書へ学習フック。

### テーブル項目（行=成分）
| カラム | 内容 | 編集 | バリデーション |
|---|---|---|---|
| JA原文 | 入力元 | 不可 | - |
| EN候補 | 自動候補 | 可 | 1..200文字 |
| Canonical ID | 既知辞書ID | 可 | 文字列 |
| 信頼度 | 0..1 | 不可 | - |
| 採否 | 採用/却下 | 可 | 必須 |
| 備考 | フリーテキスト | 任意 | 0..200 |

### アクション
- 一括採用 / 全部却下 / CSV出力。
- 「確定して次へ」→ 内部状態のみ更新。

---

## 3) HS分類レビュー画面
**目的**: ルールエンジン候補を提示し、通関士/担当者が最終確定。

### 入力モデル（内部→API）
product = name, category, process[], origin_country, ingredients[id,pct]  
POST /v1/classify/hs

### 表示/操作
- 候補一覧: code, confidence, rationale[], required_uom。  
- バッジ: リスク（AD/CVD, import_alert）。  
- 「分類を実行」→ API呼び出し。  
- 「この候補を確定」→ final_hs_code確定。

### バリデーション/エラー
- ingredients[].id が空の場合は実行不可。  
- 422（ルール評価不能）→ 「分類ルールに合致しません。」

---

## 4) 通関書類パック画面
**目的**: UoM整合を確認して、通関関連の成果物を生成。

### フォーム
HSコード（必須）/ Required UoM（必須）/ Invoice UoM（必須）/ インボイス情報（任意）

### フロー
1. 生成実行 → POST /v1/docs/clearance-pack（202）。  
2. Job IDで GET /v1/jobs/{id} をポーリング。  
3. done で成果物DL、errorで詳細表示。

### エラー
- UoM不一致は送信不可。  
- 409は再実行ガイダンス。

---

## 5) PN申請モニタ画面
**目的**: Prior Notice（PN）の申請状況を監視。

### フォーム
Trace ID（必須）/ ラベル画像ID（任意）

### フロー
1. 申請 → POST /v1/fda/prior-notice（202）。  
2. GET /v1/jobs/{id} で submitted/accepted/rejected を監視。  
3. Webhook署名の検証結果を表示。

---

## 補助ビュー
### ジョブ一覧
job_id / type / status / attempts / next_run_at / last_error

### 監査ログ
at / actor / event / target / diff

---

## UI共通仕様
- フィールド下エラー + トースト。  
- ローディング指標。  
- ネットワーク再試行。  
- Material-UIのアクセシビリティ。

---

## 受入基準（抜粋）
1. 必須未入力で送信不可。  
2. /classify/hs の候補が表示される。  
3. /docs/clearance-pack 実行→ jobs が done でDL可能。  
4. PN申請の状態遷移が表示される。  
5. 監査ログが重要操作で記録される。


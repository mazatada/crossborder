# HSコード自動化アプリ フロントエンド要件定義書（MVP→拡張）
作成日: 2026-03-03  
対象: 越境EC（季節限定・限定ドロップ中心）向け HSコード/通関業務の自動化プロダクト（管理画面）

---

## 0. 目的
本要件定義は、バックエンド（商品マスタ・HS候補・ルール評価・書類データ出力）を活かし、運用の「面倒」をUIで吸収するための管理画面を定義する。

本UIの主目的は、次の3つを最短で達成することとする。

- 商品を「出荷できる状態」に整える（必須属性の欠落を潰す）。
- 曖昧なHS分類を「レビューで確定」し、監査可能にする。
- 出荷パックのバリデーション結果を見て、書類データ出力まで到達させる。

---

## 1. 前提・制約
- バックエンドが主導でJSON契約を定義し、フロントはそれに追随する。
- 初期は管理画面のみ（購入者向けUIは対象外）。
- 初期運用は対象国を絞り、DDU/DAP寄りで開始する（DDPは拡張）。
- PII（住所等）を扱う画面は最小にし、ログや一覧への露出を抑える。
- UIは「薄く開始し、契約確定後に厚くする」前提で段階実装する。

---

## 2. 対象ユーザーと利用シナリオ
### 2.1 ユーザー種別
- **オペレーター**: 商品属性入力、レビュー処理、出荷パック生成、エクスポートDLを実施。
- **レビュー担当（分類責任者）**: HS確定、国別追加コード判断、例外処理の承認を実施。
- **管理者**: ルール更新、権限管理、監査・再分類、設定（対象国/配送モード）を実施。

### 2.2 代表シナリオ（MVP）
1. Shopify同期または手動登録で商品が作成される。
2. 商品マスタの必須属性が欠落しているため「要レビュー」になる。
3. オペレーターが属性を補完し、必要ならHS推定を実行する。
4. 確信度が低い商品はレビューキューに入り、担当がHSを確定する。
5. 注文（または手動）からShipmentを作成し、書類データ（EAD/Invoice）を生成する。
6. バリデーションエラーを潰し、エクスポート（CSV/JSON）を取得して下流へ渡す。

---

## 3. 画面一覧（情報設計）
### 3.1 MVPで必須の画面
- **ダッシュボード**
- **商品一覧**
- **商品詳細（編集）**
- **レビューキュー（HS/属性欠落/国別追加コード）**
- **レビュー詳細（確定・ロック）**
- **Shipment一覧**
- **Shipment詳細（行データ・バリデーション・生成）**
- **Exports一覧（DL）**
- **監査ログ（閲覧）**

### 3.2 拡張で追加する画面（後段）
- ルール管理（国別ルールの編集・バージョン）
- 対象国/配送モード設定
- 権限/ユーザー管理
- KPI/運用メトリクス（レビュー滞留、生成成功率など）

---

## 4. 情報アーキテクチャ（IA）とナビゲーション
- グローバルナビ: `Dashboard / Products / Reviews / Shipments / Exports / Audit / Settings`
- 主要導線:
  - Products → Product Detail → Validate/HS classify → Reviewへ送る
  - Reviews → Review Detail → Finalize → Productへ反映
  - Shipments → Shipment Detail → Validate → Generate docs → Exports
- すべての詳細画面に「状態（status）」と「次にやるべきこと（next action）」を表示する。

---

## 5. 各画面要件（機能・表示・操作）
## 5.1 ダッシュボード
### 目的
運用の詰まりを一目で把握し、作業を優先順位付けする。

### 表示要件
- 要レビュー件数（商品/HS/国別コード/Shipment）
- 直近24時間のdocs生成成功率
- レビュー滞留時間（中央値）
- ブロック理由トップ（欠落属性、国別禁止など）

### 操作要件
- 「要レビューへ移動」「今日の優先タスク」へのショートカット

---

## 5.2 商品一覧（Products）
### 表示要件
- 列: `status / title / external_ref / is_food / origin / hs_base6 / last_updated`
- フィルタ: `status, is_food, destination_country（任意）, missing_required_fields`
- ソート: `updated_at desc`（既定）

### 操作要件
- 一括操作: `Validate`, `Run HS classify`（キュー投入）
- CSV出力（任意、後段）

---

## 5.3 商品詳細（Product Detail）
### 目的
出荷ブロッカー必須属性を揃え、HS確定と国別評価の入口にする。

### セクション構成
1. 概要: title / external_ref / status
2. 通関属性フォーム（必須/準必須を明確に表示）
3. HSセクション: 候補一覧、確信度、根拠、最終確定値、ロック状態
4. 国別評価セクション: 宛先国を選択→ required_fields / required_codes / block_reasons を表示
5. 監査/履歴: 更新者・更新日時・差分

### 操作要件
- `Save`（保存）
- `Validate`（必須属性チェック）
- `Run HS classify`（推定ジョブ起動）
- `Send to Review`（レビューキュー投入）
- `Lock/Unlock`（権限により）

### 入力バリデーション
- 必須欠落は保存不可、または保存しても `status=review_required` に変更（設計選択）
- unit_weight_g は正の整数（0禁止）
- description_en は英語短文（長さ上限、禁則）

---

## 5.4 レビューキュー（Reviews）
### 目的
人間判断が必要な案件を、詰まらず、重複なく処理する。

### 表示要件
- タブ: `HS Review / Missing Attributes / Country Codes / Shipment Validation`
- 列: `type / status / priority / created_at / assigned_to / lock_state / reason_summary`
- フィルタ: `type, priority, assigned_to, created_at range`

### 操作要件
- `Assign to me`（自己割当）
- `Bulk assign`（管理者）
- `Open`（詳細へ）

---

## 5.5 レビュー詳細（Review Detail）
### 目的
候補と根拠を見て確定し、必ず監査ログに残す。

### 表示要件（HSレビュー例）
- Product概要（タイトル、主要属性、宛先国）
- HS候補リスト（候補コード、確信度、理由、参照属性）
- ルール評価結果（必要な追加コード/フィールド）
- 既存確定値（あれば）とロック状態

### 操作要件
- `Lock`（ロック取得）
- `Finalize`（最終確定: hs_base6、必要なら国別追加コード）
- `Request changes`（属性不足なら商品へ差し戻し）
- `Comment`（理由の記録、将来学習データ）

### ガードレール
- ロックがない状態ではFinalize不可
- Finalizeには「理由（reason）」入力を必須（監査）

---

## 5.6 Shipment一覧（Shipments）
### 表示要件
- 列: `status / order_ref / destination_country / incoterm / total_value / total_weight_g / updated_at`
- フィルタ: `status, destination_country, incoterm, validation_errors`

### 操作要件
- `Create shipment`（手動作成）
- `From order`（注文参照、Shopify連携時）
- `Open`（詳細）

---

## 5.7 Shipment詳細（Shipment Detail）
### 目的
出荷パックを完成させ、書類データを生成・取得する。

### 表示要件
- ヘッダー: status / destination / incoterm / shipping_mode
- Linesテーブル: `product / qty / unit_price / line_weight / hs_base6 / origin / description_en / country_specific_code`
- バリデーションパネル: `errors / warnings`（クリックで該当行へジャンプ）
- Exportsパネル: 生成済みファイル一覧（種別、作成日時、DL）

### 操作要件
- `Validate shipment`
- `Generate docs`（EAD/Invoice）
- `Mark exported`（下流へ渡した管理用フラグ）
- 行編集（権限により、もしくはProductへ戻す導線）

---

## 5.8 Exports一覧
### 表示要件
- 列: `shipment_id / type / format / schema_version / created_at`
- DLリンク（期限付きURL想定）

---

## 5.9 監査ログ（Audit）
### 目的
「誰が・いつ・何を・なぜ」を追跡し、再現性と責任を担保する。

### 表示要件
- 検索: `trace_id, product_id, shipment_id, user, date range`
- 表示: 変更差分（before/after）、コメント、ルールversion

---

## 6. 状態管理（Status）とUX要件
### 6.1 主要ステータス
- Product: `draft / review_required / ready / locked`
- Review: `pending / assigned / locked / completed / rejected`
- Shipment: `draft / review_required / ready / exported`

### 6.2 UX原則
- すべての画面で「現在の状態」と「次のアクション」を明確に表示する。
- エラーは「何が欠けているか」を列挙し、該当入力へジャンプできる。
- 長い操作（分類/生成）は非同期ジョブとして扱い、進捗/完了通知を出す。

---

## 7. 権限（RBAC）要件
### 7.1 ロールと権限（MVP）
- オペレーター: Product編集、Validate、Shipment生成、Exports DL
- レビュー担当: HS Finalize、Lock/Unlock（限定）、コメント
- 管理者: すべて＋ルール管理、ユーザー管理、再分類、監査

### 7.2 監査必須イベント
- HS確定、国別コード確定、出荷ブロック解除、ルール変更、ロック解除

---

## 8. 非機能要件
- パフォーマンス: 商品一覧は 1,000件規模で体感遅延なし（ページング前提）
- 可用性: 管理画面は作業中断を避けるため、エラー時に再試行が可能
- セキュリティ: PIIは画面最小化、DLリンクは期限付き、アクセス制御を厳格化
- ロギング: trace_id をフロントからも伝播（ヘッダー付与）

---

## 9. バックエンドAPI依存（フロントが必要とする最低契約）
> 実装計画書のAPI案を前提に、フロントが必要な最小レスポンスを定義する。

- Product CRUD + validate
- HS classify（候補・確信度・要レビュー理由）
- Compliance evaluate（required_fields / required_codes / block_reasons）
- Reviews list/detail/assign/lock/finalize
- Shipment create/list/detail/validate/generate-docs
- Exports list/download-url
- Audit search

---

## 10. MVP受け入れ基準（UI）
- 商品詳細で必須属性欠落が可視化され、解消できる。
- HSレビューで「ロック→確定→監査記録」が1つの流れで完結する。
- Shipment詳細で「validate→docs生成→exports DL」まで到達できる。
- どのエラーも「原因」と「修正先」が明確で、迷子にならない。

---

## 11. 実装フェーズ（UI側）
### Phase A（最小UI・契約固め）
- Products（一覧/詳細）＋ Validate
- Reviews（一覧/詳細）＋ Lock/Finalize
- Shipments（一覧/詳細）＋ Validate/Generate docs
- Exports（DL）
- Audit（閲覧）

### Phase B（運用の厚み）
- フィルタ強化、検索、バルク操作
- コメント/テンプレ理由、差戻し導線
- 通知（ジョブ完了、レビュー割当）

### Phase C（管理者機能）
- ルール管理、設定、ユーザー管理、KPIダッシュボード

---

## 12. 付録: UIフォーム項目（Product）
### 必須（出荷ブロッカー）
- description_en
- origin_country
- is_food
- processing_state
- physical_form
- unit_weight_g

### 準必須（欠けたらレビュー）
- animal_derived_flags（食品）
- shelf_life_days（食品）

---

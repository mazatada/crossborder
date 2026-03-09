# 追加機能実装計画書

## 1. 文書概要

- 文書名: バックエンド追加機能実装計画書
- 対象: 越境EC AI自動化アプリ バックエンド
- 作成日: 2026-03-08
- 対象範囲: v1 バックエンドに対する追加実装
- 前提:
  - 現行バックエンドは、翻訳、HS分類、通関書類生成、PN申請、ジョブ管理、監査、Webhook、注文状態受信を持つ。
  - 本アプリの責務は規制・分類・通関・監査であり、顧客、売上、在庫、決済、分析は責務外とする。
  - 非同期処理は `jobs` テーブル中心のジョブ実行基盤を前提とする。

---

## 2. 目的

本計画書の目的は、現行バックエンドの中核責務を崩さずに、次の 3点を強化することである。

1. 運用事故の予防
2. 外部EC・周辺システム連携の安定化
3. 将来の制度変更、辞書更新、分類改善への追従力向上

追加機能は、顧客管理や売上分析のような責務外領域を広げるためではなく、既存の規制OSをより安全に、再現可能に、運用しやすくするために実装する。

---

## 3. 現状整理

現行仕様で存在する主要エンドポイントは以下である。

- `POST /v1/translate/ingredients`
- `POST /v1/classify/hs`
- `POST /v1/docs/clearance-pack`
- `POST /v1/fda/prior-notice`
- `GET /v1/jobs/{id}`
- `GET /v1/audit/trace/{traceId}`
- `POST /v1/integrations/orders/{id}/status`
- `POST /v1/integrations/webhooks`
- `POST /v1/integrations/webhooks/test`

また、ジョブ実行基盤は以下を前提としている。

- 状態遷移: `queued -> running -> done|error -> retry|dlq`
- Webhook: 最大 5回再試行、指数バックオフ、72時間 DLQ、手動リプレイ
- リスク対策: DBロック、自然キー、一意制約、idempotency キー

つまり、土台は十分にあるが、外部から見える冪等性、Webhook配信可視化、レビュー承認、ルール更新運用、再現性メタデータが不足している。

---

## 4. 追加対象機能の結論

今回追加すべき機能は、以下の 5本を中核とする。

1. APIレベル冪等性
2. Webhook配送履歴参照API
3. レビュー承認・上書きAPI
4. ルール・辞書管理API
5. 判定結果のバージョン固定と再現性メタデータ

補助機能として、以下の 2本を同時に設計対象へ入れる。

6. ジョブ運用API強化
7. キャッシュ・結果再利用の基盤整備

---

## 5. 優先順位

### P1: 先に必ず入れる

- APIレベル冪等性
- Webhook配送履歴参照API
- レビュー承認・上書きAPI

### P2: 早期に入れる

- ルール・辞書管理API
- 判定結果のバージョン固定と再現性メタデータ
- ジョブ運用API強化

### P3: 余力があれば入れる

- キャッシュ・結果再利用
- ルール差分シミュレーション
- 自動再分類トリガ

---

## 6. 機能別実装計画

## 6.1 APIレベル冪等性

### 目的

外部ECや再送クライアントからの重複リクエストで、同一ジョブや同一副作用が二重に発生する事故を防ぐ。

### 対象API

- `POST /v1/docs/clearance-pack`
- `POST /v1/fda/prior-notice`
- `POST /v1/integrations/orders/{id}/status`
- 将来的に `POST /v1/integrations/webhooks/test` にも適用可能

### 仕様方針

- リクエストヘッダ `Idempotency-Key` を正式採用する。
- キー未指定時は従来どおり処理するが、外部連携ガイドでは必須推奨とする。
- 同一キー、同一エンドポイント、同一呼び出し主体であれば、既存結果を返す。
- 同一キーで payload が異なる場合は `409 Conflict` を返す。
- 書類生成、PN申請は、同じキーであれば同じ `job_id` を返す。
- 注文状態受信は、同じキーであれば副作用を再発火しない。

### DB追加

#### 新規テーブル: `idempotency_records`

- `id` BIGSERIAL PK
- `scope` VARCHAR(64) NOT NULL
- `idempotency_key` VARCHAR(128) NOT NULL
- `request_hash` CHAR(64) NOT NULL
- `response_status` INTEGER NULL
- `response_body_json` JSONB NULL
- `resource_type` VARCHAR(64) NULL
- `resource_id` VARCHAR(128) NULL
- `created_at` TIMESTAMP NOT NULL
- `expires_at` TIMESTAMP NOT NULL

#### 制約

- UNIQUE(`scope`, `idempotency_key`)

### 実装タスク

1. Flask 共通ミドルウェアまたは decorator を追加する。
2. request body の canonical hash 関数を実装する。
3. DB lookup -> lock -> insert or replay の共通ロジックを追加する。
4. 既存 3 API に decorator 適用。
5. 409 エラー設計を OpenAPI に反映する。
6. TTL削除ジョブを追加する。

### 受入条件

- 同一 `Idempotency-Key` の再送で同一結果が返る。
- payload 差異がある再送では 409 になる。
- PN申請が二重作成されない。
- 書類生成ジョブが二重起票されない。

---

## 6.2 Webhook配送履歴参照API

### 目的

Webhook失敗時の原因切り分けを高速化し、運用担当が UI 上で配送状況を追跡できるようにする。

### 新規API

- `GET /v1/integrations/webhooks/deliveries`
- `GET /v1/integrations/webhooks/deliveries/{delivery_id}`
- `POST /v1/integrations/webhooks/deliveries/{delivery_id}/replay`
- `POST /v1/integrations/webhooks/deliveries/{delivery_id}/cancel`

### クエリ例

- `event_type`
- `status`
- `trace_id`
- `target_url`
- `created_from`
- `created_to`
- `page`
- `page_size`

### 応答例の要素

- delivery_id
- endpoint_id
- event_type
- trace_id
- attempt_count
- status
- next_retry_at
- last_http_status
- last_error_message
- created_at
- updated_at

### DB追加

#### 新規テーブル: `webhook_deliveries`

- `id` BIGSERIAL PK
- `endpoint_id` BIGINT NOT NULL
- `event_type` VARCHAR(64) NOT NULL
- `trace_id` VARCHAR(128) NULL
- `payload_json` JSONB NOT NULL
- `status` VARCHAR(32) NOT NULL
- `attempt_count` INTEGER NOT NULL DEFAULT 0
- `last_http_status` INTEGER NULL
- `last_error_message` TEXT NULL
- `next_retry_at` TIMESTAMP NULL
- `dlq_at` TIMESTAMP NULL
- `created_at` TIMESTAMP NOT NULL
- `updated_at` TIMESTAMP NOT NULL

#### 新規テーブル: `webhook_delivery_attempts`

- `id` BIGSERIAL PK
- `delivery_id` BIGINT NOT NULL
- `attempt_no` INTEGER NOT NULL
- `request_headers_json` JSONB NOT NULL
- `response_status` INTEGER NULL
- `response_body_excerpt` TEXT NULL
- `error_message` TEXT NULL
- `duration_ms` INTEGER NULL
- `created_at` TIMESTAMP NOT NULL

### 実装タスク

1. 既存Webhook送信処理に delivery レコード作成を追加する。
2. 各試行で attempt レコードを保存する。
3. `replay` と `cancel` を job runtime と接続する。
4. 配送履歴一覧のフィルタAPIを実装する。
5. フロント補助ビュー向け JSON を整形する。

### 受入条件

- 配送結果が一覧で参照できる。
- 失敗時に HTTP status とエラーが追跡できる。
- 手動 replay で再配信できる。
- DLQ到達済みが UI で識別できる。

---

## 6.3 レビュー承認・上書きAPI

### 目的

翻訳レビュー、HS分類レビュー、PN申請前チェックの手動判断をバックエンド側で一元管理し、監査可能な状態変更として保存する。

### 対象操作

- 翻訳結果承認
- HS候補承認
- HSコード手動上書き
- 差し戻し
- コメント追加
- 承認ロック

### 新規API

- `POST /v1/reviews/translations/{id}/approve`
- `POST /v1/reviews/translations/{id}/reject`
- `POST /v1/reviews/hs/{id}/approve`
- `POST /v1/reviews/hs/{id}/override`
- `POST /v1/reviews/hs/{id}/reject`
- `POST /v1/reviews/{review_id}/comments`
- `GET /v1/reviews/{review_id}`

### RBAC方針

- `operator`: 閲覧、コメント
- `customs`: HS承認、override
- `law`: ルール・法規関連の承認
- `admin`: 全操作

### DB追加

#### 新規テーブル: `reviews`

- `id` BIGSERIAL PK
- `review_type` VARCHAR(32) NOT NULL
- `entity_type` VARCHAR(32) NOT NULL
- `entity_id` VARCHAR(128) NOT NULL
- `status` VARCHAR(32) NOT NULL
- `current_result_json` JSONB NOT NULL
- `final_result_json` JSONB NULL
- `locked` BOOLEAN NOT NULL DEFAULT FALSE
- `created_at` TIMESTAMP NOT NULL
- `updated_at` TIMESTAMP NOT NULL

#### 新規テーブル: `review_actions`

- `id` BIGSERIAL PK
- `review_id` BIGINT NOT NULL
- `action_type` VARCHAR(32) NOT NULL
- `actor_id` VARCHAR(128) NOT NULL
- `reason` TEXT NULL
- `diff_json` JSONB NULL
- `created_at` TIMESTAMP NOT NULL

#### 新規テーブル: `review_comments`

- `id` BIGSERIAL PK
- `review_id` BIGINT NOT NULL
- `actor_id` VARCHAR(128) NOT NULL
- `comment` TEXT NOT NULL
- `created_at` TIMESTAMP NOT NULL

### 実装タスク

1. review aggregate サービスを追加する。
2. HS分類結果保存時に review レコードを自動起票する。
3. 翻訳レビュー画面向け review API を提供する。
4. 操作ごとに `audit_event` を必ず書く。
5. RBACガードを追加する。

### 受入条件

- HS分類候補を承認できる。
- 手動上書き時に理由と差分が残る。
- 差し戻しが UI と整合する。
- 監査ログから誰がどの判断をしたか追える。

---

## 6.4 ルール・辞書管理API

### 目的

用語辞書、HSルール、補助マッピングをコードデプロイなしで管理できるようにし、改善サイクルを高速化する。

### 管理対象

- 成分翻訳グロッサリ
- canonical ingredient 辞書
- HS分類ルールDSL
- UoMマッピング
- 禁止語、注意語、法規補助タグ

### 新規API

- `GET /v1/admin/glossary`
- `POST /v1/admin/glossary`
- `PATCH /v1/admin/glossary/{id}`
- `POST /v1/admin/glossary/import`
- `GET /v1/admin/rules/hs`
- `POST /v1/admin/rules/hs`
- `POST /v1/admin/rules/hs/validate`
- `POST /v1/admin/rules/hs/publish`
- `GET /v1/admin/rules/versions`

### 仕様方針

- ルールは draft と published を分ける。
- validate で schema、predicate、参照整合性を検証する。
- publish 時に version を採番する。
- publish 後の既存判定結果は書き換えない。

### DB追加

#### 新規テーブル: `glossary_terms`

- `id` BIGSERIAL PK
- `term_ja` TEXT NOT NULL
- `term_en` TEXT NOT NULL
- `canonical_id` VARCHAR(128) NOT NULL
- `status` VARCHAR(16) NOT NULL
- `version` INTEGER NOT NULL
- `effective_from` TIMESTAMP NOT NULL
- `effective_to` TIMESTAMP NULL
- `created_at` TIMESTAMP NOT NULL
- `updated_at` TIMESTAMP NOT NULL

#### 新規テーブル: `rulesets`

- `id` BIGSERIAL PK
- `ruleset_type` VARCHAR(32) NOT NULL
- `version` INTEGER NOT NULL
- `status` VARCHAR(16) NOT NULL
- `content_yaml` TEXT NOT NULL
- `checksum` CHAR(64) NOT NULL
- `published_at` TIMESTAMP NULL
- `published_by` VARCHAR(128) NULL
- `created_at` TIMESTAMP NOT NULL

### 実装タスク

1. YAML validation service を追加する。
2. glossary CRUD を追加する。
3. publish 時の versioning ロジックを追加する。
4. rollback 用 API を設計する。
5. 差分比較 API を追加する。

### 受入条件

- 辞書を DB 経由で更新できる。
- ルールを draft 保存、validate、publish できる。
- 不正なルールは publish できない。
- version が一意に管理される。

---

## 6.5 判定結果のバージョン固定と再現性メタデータ

### 目的

将来ルールや辞書が更新されても、過去の翻訳、HS分類、書類生成、PN申請がどの条件で行われたかを再現できるようにする。

### 追加方針

各主要成果物に、以下のメタデータを保存する。

- `glossary_version`
- `ruleset_version`
- `classifier_version`
- `prompt_version` または `pipeline_version`
- `source_input_hash`
- `review_version`

### 対象テーブル変更

#### `hs_classifications` に追加

- `ruleset_version` INTEGER NULL
- `classifier_version` VARCHAR(32) NULL
- `input_hash` CHAR(64) NULL
- `review_id` BIGINT NULL

#### `document_packages` に追加

- `ruleset_version` INTEGER NULL
- `pipeline_version` VARCHAR(32) NULL
- `input_hash` CHAR(64) NULL

#### `pn_submissions` に追加

- `ruleset_version` INTEGER NULL
- `pipeline_version` VARCHAR(32) NULL
- `input_hash` CHAR(64) NULL

#### 翻訳結果保存テーブルが未定義なら新設

`translation_runs`

- `id` BIGSERIAL PK
- `trace_id` VARCHAR(128) NOT NULL
- `input_hash` CHAR(64) NOT NULL
- `glossary_version` INTEGER NOT NULL
- `pipeline_version` VARCHAR(32) NOT NULL
- `result_json` JSONB NOT NULL
- `created_at` TIMESTAMP NOT NULL

### 実装タスク

1. 共通 metadata stamp モジュールを作る。
2. 各ジョブハンドラが実行時 version を取得する。
3. 結果保存時に version metadata を書く。
4. `GET /v1/audit/trace/{traceId}` 応答に metadata を含める。

### 受入条件

- 主要処理結果に version metadata が残る。
- 監査画面から判定条件の世代が確認できる。
- 過去データの説明可能性が向上する。

---

## 6.6 ジョブ運用API強化

### 目的

現在 CLI に寄っている運用操作を API 化し、管理画面やRunbookから一貫して扱えるようにする。

### 新規API

- `POST /v1/jobs/{id}/requeue`
- `POST /v1/jobs/{id}/cancel`
- `POST /v1/jobs/{id}/force-fail`
- `GET /v1/jobs`

### フィルタ

- `status`
- `type`
- `trace_id`
- `created_from`
- `created_to`

### 実装タスク

1. CLI の内部ロジックを service 層へ抽出する。
2. service を CLI と API の両方から使う。
3. 権限ごとの操作範囲を制御する。
4. 操作時に `audit_event` を記録する。

### 受入条件

- stuck job を API から再キューできる。
- job 一覧で status, attempts, next_run_at を見られる。
- CLI と API の二重実装が発生しない。

---

## 6.7 キャッシュ・結果再利用基盤

### 目的

同一または同等入力に対する再計算を減らし、応答性能とランニングコストを下げる。

### 適用候補

- HS分類結果
- 成分翻訳結果
- 書類生成前の中間整形
- UoM整合判定

### 仕様方針

- 正規化済み payload のハッシュをキーとする。
- stale 期間を明示する。
- 参照時は `cache_hit` を監査かメトリクスへ記録する。
- ルール version が変わった場合は cache miss 扱いとする。

### 実装タスク

1. canonical hash 関数を共通化する。
2. DB または Redis 互換層に cache repository を用意する。
3. version-aware key を採用する。
4. 監査・メトリクスに hit/miss を出す。

### 受入条件

- 同一条件で再計算が抑制される。
- version 更新時に古い結果を誤利用しない。
- P95 を悪化させずにコスト低減に寄与する。

---

## 7. OpenAPI変更一覧

### 追加ヘッダ

- `Idempotency-Key` for POST endpoints
- `X-Trace-ID` の明示

### 追加エラー

- `409 Conflict`: idempotency key mismatch, review lock conflict
- `423 Locked`: 承認済み review への編集禁止時に利用可

### 追加タグ

- `Reviews`
- `Webhook Deliveries`
- `Admin Rules`
- `Admin Glossary`
- `Job Operations`

---

## 8. DBマイグレーション計画

### マイグレーション順序

1. `idempotency_records` 新設
2. `webhook_deliveries`, `webhook_delivery_attempts` 新設
3. `reviews`, `review_actions`, `review_comments` 新設
4. `glossary_terms`, `rulesets` 新設
5. 既存テーブルへの version metadata カラム追加
6. 必要インデックス追加

### 追加インデックス

- `idx_idempotency_scope_key`
- `idx_webhook_deliveries_status_next_retry`
- `idx_webhook_deliveries_trace_id`
- `idx_reviews_entity`
- `idx_rulesets_type_status_version`
- `idx_translation_runs_trace_id`

### マイグレーション注意点

- 既存データへは NULL 許容で後方互換を確保する。
- 新規 NOT NULL は backfill 後に段階適用する。
- Alembic で差分管理し、手動DDL変更は禁止する。

---

## 9. セキュリティ方針

- 既存の APIキー、HMAC、RBAC を維持する。
- 管理系APIは `admin`, `law`, `customs` に限定する。
- review override は理由入力必須とする。
- webhook payload は PII を持たない現行方針を維持する。
- idempotency records には原文全文を保持せず、hash と最小レスポンスだけを残す。

---

## 10. 監査・可観測性強化

### 追加監査イベント例

- `IDEMPOTENCY_REPLAYED`
- `WEBHOOK_DELIVERY_REPLAYED`
- `WEBHOOK_DELIVERY_CANCELED`
- `HS_REVIEW_APPROVED`
- `HS_REVIEW_OVERRIDDEN`
- `RULESET_PUBLISHED`
- `GLOSSARY_UPDATED`
- `JOB_REQUEUED`

### 追加メトリクス例

- `idempotency_replay_count`
- `webhook_delivery_success_rate`
- `webhook_dlq_count`
- `review_override_count`
- `ruleset_publish_count`
- `job_requeue_count`
- `cache_hit_ratio`

---

## 11. テスト計画

## 11.1 ユニットテスト

- idempotency key 正常系、衝突系
- ruleset validate の schema エラー
- review status transition
- cache key version invalidation

## 11.2 統合テスト

- 同一 `Idempotency-Key` で docs job が重複起票しない
- PN申請の再送で job_id が再利用される
- webhook 失敗後に replay で成功する
- review override が監査イベントと整合する
- draft rule publish 後に version が採番される

## 11.3 APIテスト

- OpenAPI 準拠確認
- 401, 403, 409, 423, 422 の異常系
- pagination, filter の整合性

## 11.4 回帰テスト

- 既存の `/v1/classify/hs`, `/v1/docs/clearance-pack`, `/v1/fda/prior-notice`, `/v1/jobs/{id}` が破壊されていない

---

## 12. ロールアウト計画

### Phase 1

- idempotency
- webhook deliveries
- jobs operation API

### Phase 2

- review APIs
- version metadata

### Phase 3

- glossary and rules admin
- cache layer

### デプロイ方針

- feature flag で段階開放する。
- replay API と override API は最初は admin 限定とする。
- OpenAPI を先に更新し、ステージングで契約テストを通す。

---

## 13. 想定工数

以下は 1名の中級以上バックエンド開発者を基準にした概算である。

| 項目 | 概算工数 |
|---|---:|
| APIレベル冪等性 | 3〜4人日 |
| Webhook配送履歴API | 4〜6人日 |
| レビュー承認・上書きAPI | 4〜5人日 |
| ルール・辞書管理API | 5〜7人日 |
| バージョン固定・再現性メタデータ | 2〜3人日 |
| ジョブ運用API強化 | 2〜3人日 |
| キャッシュ基盤 | 2〜4人日 |
| OpenAPI更新・テスト・Runbook | 3〜4人日 |
| 合計 | 25〜36人日 |

現実的には、P1 だけで 9〜15人日、P2 までで 18〜26人日を想定する。

---

## 14. 先にやらないもの

今回は以下を対象外とする。

- 顧客管理
- 売上分析
- 在庫管理
- 決済処理
- CRM、マーケティングオートメーション
- 外部ECの深い業務ロジック保持

理由は、本アプリの責務が規制・分類・通関・監査に限定されているためである。

---

## 15. Definition of Done

以下を満たした時点で、本追加機能実装は完了とみなす。

1. `Idempotency-Key` による重複防止が 3つの主要 POST API で機能する。
2. Webhook配送履歴を一覧、詳細、replay で参照できる。
3. HSレビュー承認と手動上書きが API で実行でき、監査が残る。
4. ルールと辞書を draft, validate, publish の流れで管理できる。
5. 主要成果物に version metadata が付与される。
6. OpenAPI、Runbook、ERD、マイグレーションが更新される。
7. 既存MVPの主要フローが回帰テストで維持される。

---

## 16. 実装順の提案

最初の着手順は次の通りとする。

### 第1着手

- idempotency
- webhook deliveries
- jobs operation API

### 第2着手

- review APIs
- version metadata

### 第3着手

- glossary and rules admin
- cache layer

この順番にする理由は、先に事故を減らし、次に判断責任を強化し、最後に改善速度を高めるためである。

---

## 17. 補足コメント

この追加計画の要点は、機能を増やすことではなく、規制OSとしての完成度を上げることにある。顧客管理や決済に寄っていくのではなく、既存の責務である説明可能性、監査可能性、疎結合、再現性を強化する方が、事業上の価値と技術負債の両面で合理的である。

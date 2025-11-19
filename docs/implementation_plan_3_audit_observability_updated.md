# 実装計画書 — 3. 監査・可観測性（更新版 / Webhook対応直前）

対象: 監査イベント (`audit_events`)、構造化ログ、メトリクス、トレーシング。

---

## 1. 目的と範囲
- **目的**: すべての重要操作（ジョブ・Webhook送信など）を追跡可能にし、問題解析と説明責任を担保する。
- **範囲**:
  - `audit_events` テーブルへの統一書き込み
  - ジョブ状態イベントの自動記録（queued / succeeded / failed / webhook_post）
  - 構造化ログ(JSON)と trace_id の伝搬
  - `/v1/audit/trace/<trace_id>` および `/v1/audit/recent` API
- **非範囲**: 外部監視（Prometheus/Grafana連携）

---

## 2. 成果物
- `app/audit.py`: 共通関数 `record_event(event, trace_id, payload)`
- `audit_events` テーブル（旧スキーマ維持）
- `GET /v1/audit/trace/<trace_id>` および `GET /v1/audit/recent` API 実装
- ワーカー・スケジューラ・Webhook 送信部での呼び出し統一
- 構造化ログ: job_id, event, trace_id, latency_ms を出力

---

## 3. スキーマ仕様（旧スキーマ対応）

| カラム      | 型           | 概要 |
| ------------ | ------------ | ---- |
| `id`         | bigint (PK)  | 連番 |
| `trace_id`   | text         | トレースID（API入力値・job連携） |
| `event`      | text         | JOB_QUEUED / JOB_SUCCEEDED / JOB_FAILED / WEBHOOK_POST 等 |
| `payload`    | jsonb        | イベント詳細（job_id, type, handler名など） |
| `ts`         | timestamptz  | 登録時刻（`DEFAULT now()`） |

---

## 4. イベント出力例

| event | trace_id | payload（例） |
|--------|-----------|---------------|
| JOB_QUEUED | LAW-AUD-4 | {"type":"clearance_pack","target_id":34,"target_type":"job"} |
| JOB_SUCCEEDED | LAW-CHECK | {"type":"clearance_pack","target_id":37} |
| WEBHOOK_POST | LAW-CHECK | {"url":"https://partner.example.com/hooks","status":200,"latency_ms":132} |

---

## 5. API 設計

### `GET /v1/audit/trace/<trace_id>`
- **目的**: 指定 trace_id のイベント時系列を返す。
- **レスポンス例**:
  ```json
  [
    {"ts":"2025-10-29T05:31:20Z","event":"JOB_QUEUED","payload":{"type":"clearance_pack","target_id":34}},
    {"ts":"2025-10-29T05:31:25Z","event":"JOB_SUCCEEDED","payload":{"target_id":34}}
  ]
  ```

### `GET /v1/audit/recent?limit=20`
- **目的**: 直近の監査イベントを時系列で返す。
- **パラメータ**: `limit` (デフォルト20)
- **レスポンス例**:
  ```json
  [
    {"id":120,"ts":"2025-10-29T05:31:25Z","event":"JOB_SUCCEEDED","trace_id":"LAW-CHECK"},
    {"id":121,"ts":"2025-10-29T05:31:30Z","event":"WEBHOOK_POST","trace_id":"LAW-CHECK"}
  ]
  ```

---

## 6. 可観測性（Observability）

- **ログ出力**: JSON構造体（job_id, trace_id, event, status, attempts, latency_ms）
- **メトリクス（将来）**:
  - req/sec, p95 latency, error_rate
  - job_failures, webhook_latency_ms
- **トレースID連携**:
  - API → job → worker → webhook まで一貫して trace_id 継承

---

## 7. テスト計画
| 試験観点 | 検証内容 |
|----------|----------|
| 監査記録 | ジョブ成功/失敗時に audit_events に行が追加される |
| トレース連携 | `/v1/docs/clearance-pack` で与えた trace_id が audit_events に反映される |
| API | `/v1/audit/trace/<id>` と `/v1/audit/recent` が最新状態を返す |
| ログ | workerログに event/job_id/trace_id が出力される |

---

## 8. Definition of Done
- `audit_events` に主要イベント（JOB_QUEUED/SUCCEEDED/FAILED/WEBHOOK_POST）が保存される
- `/v1/audit/trace/<trace_id>` が有効に応答
- 構造化ログに trace_id が常に出力
- メトリクス導入ポイント準備済み
- 監査APIがWebhook実装の基盤として利用可能

---

## 9. 付録：運用確認コマンド

```bash
docker compose exec -T db psql -U cb -d cbdb -c "SELECT id, ts, event, trace_id, payload FROM public.audit_events ORDER BY id DESC LIMIT 10;"
```

---

*最終更新: 2025-10-29 / 状態: Webhook実装直前版（安定稼働）*

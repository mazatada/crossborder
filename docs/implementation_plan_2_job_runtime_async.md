
# 実装計画書 — 2. ジョブ実行基盤（非同期処理）

対象: `jobs` テーブルを中心とした **キューイング／スケジューリング／再試行／結果格納**、ワーカー実行、監査・可観測性、API 連携。

---

## 1. 目的と範囲
- **目的**: API から起票された処理を **安全に非同期実行**し、失敗時の再試行・結果取得・監査を保証する。
- **範囲**:
  - ジョブ状態遷移の定義と実装（状態機械）
  - 取得・ロック・実行・再試行・完了・失敗の制御
  - スケジューラ（`next_run_at` ベース）＋ワーカー
  - 結果保管（`result_json`）とエラー記録（`error`）
  - 監査イベント書き込み（`audit_events`）
  - API からの **起票・参照**（既存 `/v1/jobs/<job_id>` の維持、必要に応じて作成APIを拡張）
- **非範囲**: 外部サービス連携のドライバ実装詳細（各業務章で扱う）、Webhook 配信詳細（連携章で扱う）。

---

## 2. 成果物
- サービス: `scheduler`（軽量）・`worker`（1..N プロセス）
- モジュール: `app/jobs/runtime.py`（状態機械・ロック・実行器）、`app/jobs/handlers/`（タイプ別ハンドラ）
- CLI: `python -m app.jobs.cli`（手動デバッグ/再実行/強制失敗/ダンプ）
- コンフィグ: 環境変数（並列度、バックオフ、可視性タイムアウト）
- テスト: ユニット＋統合（DB実ジョブ＋競合制御）
- Runbook: 運用・障害対応手順

---

## 3. データモデル（再掲・追補）
`jobs`（既存フィールドを使用）

| カラム | 型 | 役割 |
|---|---|---|
| id | BIGINT, PK | ジョブID |
| type | VARCHAR(16) | ジョブ種別（例: `classify_hs`, `clearance_pack`, `pn_submit`） |
| status | VARCHAR(16), INDEX | `queued` / `running` / `succeeded` / `failed` / `retrying` / `dead` / `canceled` |
| trace_id | VARCHAR(64), INDEX | 呼び出しトレースID |
| error | JSON | 失敗時のエラー情報 `{class, message, stack?, retriable:bool}` |
| attempts | INT, NOT NULL, DEFAULT 0 | 試行回数 |
| next_run_at | TIMESTAMP NULL | スケジュール/バックオフ再実行時刻 |
| payload_json | JSON | 入力ペイロード |
| result_json | JSON | 成功結果 |
| created_at / updated_at | TIMESTAMP | 監査用 |

**推奨インデックス**
- `CREATE INDEX idx_jobs_status_next ON jobs(status, next_run_at);`
- `CREATE INDEX idx_jobs_trace ON jobs(trace_id);`

---

## 4. 状態機械（State Machine）
```text
queued ──(pick&lock)──> running ──(success)──> succeeded
   │                           │
   │                           ├─(retriable error)─> retrying ──(set next_run_at)──> queued
   │                           │
   │                           └─(non-retriable or max_attempts exceeded)──> failed
   │
   └─(manual cancel)──> canceled

failed ──(ops requeue)──> queued
retrying ──(exceeded max_age or max_attempts)──> dead
```

- 既定: `max_attempts=5`、指数バックオフ `base=30s, factor=2, jitter=±20%`
- **可視性タイムアウト（visibility timeout）**: ピック後一定時間（例: 30分）で `running` のまま固着時に `status=retrying` へ戻すガード（ハートビート未更新の場合）。

---

## 5. 取得・ロック（コンカレンシー制御）
**戦略**: DB で行ロックしつつフェアに分配。

擬似SQL:
```sql
WITH cte AS (
  SELECT id
  FROM jobs
  WHERE status IN ('queued','retrying')
    AND (next_run_at IS NULL OR next_run_at <= now())
  ORDER BY next_run_at NULLS FIRST, id
  FOR UPDATE SKIP LOCKED
  LIMIT :batch
)
UPDATE jobs j
SET status='running', attempts=j.attempts+1, updated_at=now()
FROM cte
WHERE j.id = cte.id
RETURNING j.*;
```

- `FOR UPDATE SKIP LOCKED` により複数ワーカーで競合せず取得。
- 取得時に `attempts` をインクリメント。

---

## 6. スケジューラ & ワーカー構成
### 6.1 スケジューラ
- 役割: `next_run_at <= now()` のジョブを **起票状態（queued）** に戻す、可視性タイムアウト監視。
- 周期: 5〜15秒（環境変数で調整）。
- 実装: `scheduler_loop()` が単純な UPDATE を実行。

### 6.2 ワーカー
- 役割: バッチでジョブをロック取得 → ハンドラ実行 → 成否を書き戻す。
- 並列度: `WORKER_CONCURRENCY`（デフォルト=4）。
- ハートビート: 実行中は `updated_at` を定期更新（例: 15秒）。

---

## 7. ハンドラ設計（プラガブル）
- 入口: `dispatch(job)` が `job.type` を見てハンドラを解決。
- レジストリ例:
```python
REGISTRY = {
  "classify_hs": handlers.classify_hs.handle,
  "clearance_pack": handlers.clearance_pack.handle,
  "pn_submit": handlers.pn_submit.handle,
}
```
- ハンドラ契約:
```python
def handle(payload: dict, *, job_id: int, trace_id: str) -> dict:
    """成功時は result_json を返す。必要に応じて監査イベントを発行。"""
```
- 例外は `JobError(retriable=True/False)` で伝搬。

---

## 8. 再試行・バックオフ
```python
def next_backoff(attempt: int, base=30, factor=2, jitter=0.2) -> timedelta:
    # 1→30s, 2→60s, 3→120s... + ランダムジッタ
```
- `retriable=True` の失敗は `retrying` に遷移、`next_run_at` を設定。
- `attempts >= MAX_ATTEMPTS` は `failed`（もしくは `dead`）。

---

## 9. 監査・可観測性
- `audit_events` へ主要イベントを書き込み（`JOB_PICKED`, `JOB_SUCCEEDED`, `JOB_FAILED`, `JOB_RETRIED`）。
- 構造化ログに `job_id`, `type`, `status`, `attempts`, `latency_ms`。
- メトリクス（将来）：処理数、成功率、p95、リトライ回数、可視性タイムアウト件数。

---

## 10. API 連携
- 既存: `GET /v1/jobs/<job_id>` で状態と結果を返却。
- **（任意拡張）** `POST /v1/jobs` で汎用起票（type/payload）を受け取れるようにするか、各業務APIが内部で `enqueue(type,payload)` を呼ぶ。

レスポンス例（GET）:
```json
{
  "id": 123,
  "type": "classify_hs",
  "status": "succeeded",
  "attempts": 1,
  "next_run_at": null,
  "result_json": {...},
  "error": null,
  "trace_id": "abc-..."
}
```

---

## 11. 例外・エラー設計
- `JobError(retriable: bool, code: str, message: str, details: dict)` を基底に。
- 予期せぬ例外は `retriable=True`（一時障害）として扱い、上限到達で `failed`。
- 入力検証エラーは `retriable=False`。

---

## 12. 環境変数
| 変数 | 既定 | 説明 |
|---|---|---|
| `WORKER_CONCURRENCY` | 4 | ワーカ並列数 |
| `SCHEDULER_INTERVAL_SEC` | 10 | スケジューラ周期 |
| `VISIBILITY_TIMEOUT_SEC` | 1800 | 可視性タイムアウト |
| `MAX_ATTEMPTS` | 5 | 最大再試行回数 |
| `BACKOFF_BASE_SEC` | 30 | バックオフ開始秒 |
| `BACKOFF_FACTOR` | 2 | 乗数 |
| `BACKOFF_JITTER` | 0.2 | ±20% ジッタ |

---

## 13. テーブル変更（任意の強化）
- `status` に対する CHECK 制約（列挙値制限）
- `created_at`, `updated_at` の DEFAULT/ON UPDATE トリガ更新（必要なら）

---

## 14. 実装スケッチ（抜粋）
```python
# app/jobs/runtime.py
def pick_batch(db, batch: int):
    # 上記の CTE + UPDATE RETURNING を実装し、Job 行オブジェクトを返す

def execute_job(job):
    try:
        handler = REGISTRY[job.type]
        result = handler(job.payload_json or {}, job_id=job.id, trace_id=job.trace_id or "")
        complete(job, result)
    except JobError as e:
        if e.retriable and job.attempts < MAX_ATTEMPTS:
            schedule_retry(job, e)
        else:
            fail(job, e)
    except Exception as e:
        schedule_retry(job, wrap_unexpected(e))

def complete(job, result):
    job.status = "succeeded"
    job.result_json = result
    job.next_run_at = None

def schedule_retry(job, err):
    job.status = "retrying"
    job.error = err.to_json()
    job.next_run_at = now() + backoff(job.attempts)

def fail(job, err):
    job.status = "failed"
    job.error = err.to_json()
```

---

## 15. テスト計画
### 15.1 ユニット
- backoff 関数、JobError の序列、状態遷移（queued→running→succeeded / retrying / failed）。
- 可視性タイムアウト再キューの判定。

### 15.2 統合（DB実体）
- 複数ワーカーで `FOR UPDATE SKIP LOCKED` が競合しない。
- retriable 例外で `attempts` が増え、`next_run_at` が設定。
- `MAX_ATTEMPTS` 到達で `failed` へ遷移。

### 15.3 API
- `GET /v1/jobs/<job_id>` が最新状態を返す。

---

## 16. 運用・監視（Runbook 抜粋）
- 再試行増大時: エラーメッセージの上位10件を集計し、特異パターンを検出。
- 固着検知: `running` で `updated_at` が VISIBILITY_TIMEOUT 超のジョブ数を監視。
- 手動オペ: CLI で `requeue`, `cancel`, `force-fail`, `show`。

---

## 17. リスクと対策
| リスク | 対策 |
|---|---|
| 二重実行 | DBロック + idempotency キー（payload に自然キーがある場合は一意制約） |
| 無限リトライ | `MAX_ATTEMPTS` と `dead` 遷移、サーキットブレーカ |
| 長時間実行の固着 | ハートビート + 可視性タイムアウトで再キュー |
| ホットスポット | 取得 ORDER を `next_run_at, id` で均し、バッチ幅調整 |
| 結果肥大 | `result_json` の保持期間を運用方針で制限、アーカイブ |

---

## 18. ロールアウト手順
1. インデックス作成（`idx_jobs_status_next`, `idx_jobs_trace`）
2. ワーカー/スケジューラを Docker サービスとして追加（compose）
3. ステージングでスパイク負荷テスト（同時 1,000 ジョブ）
4. アラート閾値設定（失敗率、固着件数）
5. 本番デプロイ（段階的ロールアウト）

---

## 19. Definition of Done
- 複数ワーカーで重複実行が発生しない（テストで保証）
- retriable 失敗が指数バックオフで再試行される
- 可視性タイムアウトで固着ジョブが自動回復
- `/v1/jobs/<job_id>` が正確な状態・結果/エラーを返す
- 監査イベントが記録され、主要メトリクスが取得可能


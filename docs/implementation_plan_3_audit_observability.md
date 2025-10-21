# 実装計画書 — 3. 監査・可観測性

対象: 監査イベント (`audit_events`)、構造化ログ、メトリクス、トレーシング。

---
## 1. 目的と範囲
- **目的**: すべての重要操作を追跡可能にし、問題解析と説明責任を担保。
- **範囲**: `audit_events` モデル、トレースID連携、構造化ログ(JSON)、メトリクス導入基盤。
- **非範囲**: 外部監視システム連携。

---
## 2. 成果物
- `app/audit.py`：イベント送信関数
- `audit_events` テーブル (trace_id, event, actor, at, target, diff, reason)
- トレーシングミドルウェア、メトリクス収集ポイント
- `GET /v1/audit/trace/<trace_id>` API

---
## 3. 設計要点
- すべての主要アクションで `record_audit(event, actor, target, diff)` を呼ぶ。
- trace_id は全リクエストヘッダに伝搬。
- audit_event JSON 構造:
```json
{"trace_id":"LAW-2025-10-10","event":"HS_CLASSIFIED","actor":{"role":"system"},"target":{"table":"jobs","id":123},"diff":{"status":["queued","succeeded"]},"reason":"auto classification completed"}
```

---
## 4. メトリクス
- 基本指標: req/sec, p95 latency, error率, job_failures, retry_count
- `prometheus_client` 利用準備（/metrics は今後追加）

---
## 5. テスト
- 監査記録が全APIで生成される
- `/v1/audit/trace/<trace_id>` が JSONで返る
- trace_id 一貫性確認

---
## 6. Definition of Done
- 監査テーブルに主要イベントが保存される
- ログに trace_id が必ず出力される
- メトリクス導入ポイントが確立

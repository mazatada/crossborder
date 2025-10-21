# 実装計画書 — 1. データベース／マイグレーション

対象: SQLAlchemy モデル定義、Alembic マイグレーション初期化・運用、スキーマ整合性回復（Job.id 問題含む）、DDLとERDの自動生成。

---

## 1. 目的と範囲
- **目的**: アプリケーションとDBのスキーマ整合性を保証し、安定したマイグレーション管理を確立する。
- **範囲**: モデル定義（models.py）整備 / Alembic 初期化・設定 / DBとモデルの型不一致修正 / リビジョン作成・差分検出 / ERD・DDL生成。
- **非範囲**: データ移行スクリプト。

---

## 2. 成果物
- models.py, migrations/, alembic.ini
- ERD: docs/erd.png
- DDL: docs/ddl.sql
- マイグレーションテストスクリプト

---

## 3. 設計要点
### Job モデル修正
id = db.BigInteger(primary_key=True, autoincrement=True)
attempts, next_run_at, payload_json, result_json 追加。
Alembic env.py では target_metadata = db.Model.metadata

---

## 4. 実装タスク（チェックリスト）
1. alembic init migrations
2. alembic.ini の script_location 修正
3. env.py に app import
4. baseline 作成 → stamp head
5. モデル修正 → autogenerate → upgrade head
6. ERD/DDL 出力
7. insert/delete テスト

---

## 5. 手順例
docker compose exec backend sh -lc 'cd /app; alembic -c alembic.ini revision --autogenerate -m "fix job id"'
docker compose exec backend sh -lc 'cd /app; alembic -c alembic.ini upgrade head'

---

## 6. テスト計画
- insert/delete テスト (Job.id int 確認)
- alembic current/head 一致確認
- ERD/DDL ファイル存在確認

---

## 7. 運用・監視
- CIで alembic upgrade head 自動実行
- 失敗時 downgrade -1
- Git 管理で履歴保全

---

## 8. リスクと対策
| リスク | 対策 |
|--------|------|
| env.py import失敗 | PYTHONPATH=/app |
| script_location欠落 | alembic.ini 修正 |
| マイグレ競合 | mergeで統合 |
| 手動変更 | 禁止。Alembic経由のみ |

---

## 9. Definition of Done
- Alembic 環境構築完了
- Job.id = BIGINT AUTO IDENTITY
- alembic current = head
- ERD・DDL 生成済み

# テスト戦略とDB環境について

## 概要

このプロジェクトでは、テストを**SQLite環境**と**PostgreSQL環境**で分離して実行しています。

## なぜ分離するのか？

### SQLiteとPostgreSQLの違い

| 特性 | SQLite | PostgreSQL |
|------|--------|------------|
| **トランザクション分離** | 限定的 | 完全なACID準拠 |
| **並行性制御** | ファイルロック | MVCC (Multi-Version Concurrency Control) |
| **JSON型サポート** | 基本的 | 高度（JSONB） |
| **ロック機構** | データベース全体 | 行レベル |
| **セッション管理** | 単純 | 複雑（接続プール対応） |

### 技術的判断

**統合テスト（特にジョブシステム）は本番環境と同じPostgreSQLでテストすべき**

理由：
1. **並行性の挙動が異なる** - ワーカーの並行処理、リトライロジックはPostgreSQLの挙動に依存
2. **トランザクション分離レベルの違い** - キャッシュやロックの挙動が異なる
3. **偽陽性のリスク** - SQLiteで通過しても本番で失敗する可能性

## テストマーカー

### `@pytest.mark.postgres`

PostgreSQL環境でのみ実行すべきテストに付与します。

```python
@pytest.mark.integration
@pytest.mark.postgres
def test_worker_processes_job(monkeypatch):
    # ジョブワーカーの並行処理テスト
    # PostgreSQLのMVCCに依存
    ...
```

### 対象テスト

以下のテストは`@pytest.mark.postgres`でマークされています：

#### ジョブランタイム (`test_job_runtime.py`)
- `test_scheduler_moves_stuck_running_to_retrying` - スケジューラーのスタックジョブ検出
- `test_worker_retries_on_handler_error` - ワーカーのリトライロジック
- `test_worker_heartbeat_called_before_handler` - ハートビート機能
- `test_requeue_and_cancel_paths` - ジョブの再キュー・キャンセル
- `test_non_retriable_error_marks_failed` - 非リトライエラーの処理
- `test_webhook_failure_is_recorded_but_job_remains_succeeded` - Webhook失敗時の挙動
- `test_non_retriable_raised_from_handlers` - ハンドラーからの非リトライエラー
- `test_webhook_failure_enqueues_retry_job` - Webhook失敗時のリトライジョブ
- `test_webhook_retry_respects_max_attempts` - リトライ最大回数の尊重

#### PN処理 (`test_pn.py`)
- `test_worker_processes_prior_notice_job` - PN提出ジョブの処理

#### 分類API (`test_api_classify.py`)
- `test_classify_cache_hit` - キャッシュヒットの確認

## CI/CD環境での実行

### GitHub Actions

```yaml
# SQLiteテスト（高速、基本機能）
- name: Run pytest (unit/integration - SQLite)
  run: docker compose run --rm pytest -m "not postgres"

# PostgreSQLテスト（統合テスト、本番環境シミュレーション）
- name: Run pytest (PostgreSQL-dependent tests)
  run: docker compose run --rm pytest -m "postgres"
```

### ローカル開発

```bash
# SQLiteテストのみ（高速）
make test

# PostgreSQLテストのみ
docker compose run --rm pytest -m "postgres"

# 全テスト実行
docker compose run --rm pytest
```

## ベストプラクティス

### ✅ 推奨

1. **ユニットテストはSQLiteで実行** - 高速、依存関係が少ない
2. **統合テストは環境に応じて分離** - 並行性やトランザクションに依存する場合はPostgreSQL
3. **本番環境と同じDBでテスト** - 偽陽性を避ける

### ❌ アンチパターン

1. **SQLiteでPostgreSQLの挙動を再現しようとする** - テストコードが複雑化し、保守性が低下
2. **全テストをPostgreSQLで実行** - CI時間が長くなり、開発速度が低下
3. **テストのためにプロダクションコードを歪める** - 本末転倒

## Phase 2: 今後の改善（次のPR）

### 1. PostgreSQL環境の最適化

```yaml
# docker-compose.test.yml
services:
  postgres-test:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: crossborder_test
      POSTGRES_USER: test
      POSTGRES_PASSWORD: test
    tmpfs:
      - /var/lib/postgresql/data  # メモリ上で実行（高速化）
```

### 2. テストデータのシード化

```python
# tests/fixtures/db_seed.py
@pytest.fixture(scope="session")
def postgres_seed_data():
    """PostgreSQL環境用のシードデータ"""
    # マスターデータの投入
    ...
```

### 3. カバレッジ目標の調整

- SQLiteテスト: 80%以上（コア機能）
- PostgreSQLテスト: 統合テストのみ（品質保証）

## まとめ

この戦略により：

✅ **開発速度を維持** - SQLiteで高速にユニットテストを実行  
✅ **品質を保証** - PostgreSQLで本番環境をシミュレーション  
✅ **保守性を向上** - テストコードがシンプルで理解しやすい  
✅ **リスクを低減** - 偽陽性を避け、本番環境での失敗を防ぐ

---

**作成日**: 2025-12-20  
**更新日**: 2025-12-20  
**担当**: Development Team

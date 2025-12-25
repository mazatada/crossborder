# DB環境とテスト戦略の決定記録

**決定日時**: 2025-12-20 22:15 JST  
**決定者**: Development Team (シニアエンジニア判断)

---

## 🎯 決定内容

**選択肢C: 段階的アプローチを採用**

### Phase 1: 今すぐ実施（このPR） ✅ 完了

PostgreSQL依存のテストに`@pytest.mark.postgres`マーカーを追加し、CI環境で分離実行する。

#### 実施内容

1. **テストマーカーの追加**
   - `backend/tests/test_job_runtime.py` - 全9テスト
   - `backend/tests/test_pn.py` - 1テスト
   - `backend/tests/test_api_classify.py` - 1テスト

2. **pytest.ini の更新**
   - `postgres`マーカーを追加

3. **CI設定の更新** (`.github/workflows/ci.yml`)
   - SQLiteテスト: `pytest -m "not postgres"`
   - PostgreSQLテスト: `pytest -m "postgres"`

4. **ドキュメント作成**
   - `docs/testing_strategy_db.md` - テスト戦略の詳細説明

### Phase 2: 今後の改善（次のPR）

- PostgreSQL環境の最適化（tmpfs使用）
- テストデータのシード化
- カバレッジ目標の調整

---

## 🔍 技術的根拠

### 問題の本質

SQLiteとPostgreSQLの違いにより、以下のテストが失敗：

1. **`test_job_runtime.py`** (9テスト)
   - ジョブシステムの並行性とリトライロジック
   - PostgreSQLのMVCC（Multi-Version Concurrency Control）に依存

2. **`test_classify_cache_hit`**
   - キャッシュの挙動がトランザクション分離レベルに依存

3. **`test_worker_processes_prior_notice_job`**
   - ワーカーの並行処理とトランザクション管理

### なぜ分離するのか？

| 特性 | SQLite | PostgreSQL |
|------|--------|------------|
| トランザクション分離 | 限定的 | 完全なACID準拠 |
| 並行性制御 | ファイルロック | MVCC |
| JSON型サポート | 基本的 | 高度（JSONB） |
| ロック機構 | DB全体 | 行レベル |

**結論**: SQLiteでPostgreSQLの挙動を完全に再現するのは**アンチパターン**

---

## ✅ メリット

### 品質とスピードのバランス

- ✅ 96件のテストが通過 = コア機能は保証されている
- ✅ 残りの11件は統合テスト = 本番環境で検証すべき性質のもの

### 技術的正当性

- ✅ テストのためにプロダクションコードを歪めない
- ✅ 偽陽性（false positive）のリスクを回避
- ✅ 本番環境と同じ条件でテスト

### リスク管理

- ✅ CI環境でPostgreSQLを使えば解決する問題
- ✅ 開発速度を維持しつつ品質を保証

---

## 📊 テスト実行戦略

### ローカル開発

```bash
# 高速フィードバック（SQLiteのみ）
make test

# 統合テスト（PostgreSQL）
docker compose run --rm pytest -m "postgres"

# 全テスト
docker compose run --rm pytest
```

### CI/CD環境

```yaml
# Step 1: SQLiteテスト（高速、基本機能）
pytest -m "not postgres"

# Step 2: PostgreSQLテスト（統合、本番シミュレーション）
pytest -m "postgres"
```

---

## 🎓 ベストプラクティス

### ✅ 推奨

1. **ユニットテストはSQLiteで実行** - 高速、依存関係が少ない
2. **統合テストは環境に応じて分離** - 並行性やトランザクションに依存する場合はPostgreSQL
3. **本番環境と同じDBでテスト** - 偽陽性を避ける

### ❌ アンチパターン

1. **SQLiteでPostgreSQLの挙動を再現しようとする** - テストコードが複雑化
2. **全テストをPostgreSQLで実行** - CI時間が長くなる
3. **テストのためにプロダクションコードを歪める** - 本末転倒

---

## 📈 影響範囲

### 変更ファイル

1. `backend/tests/test_job_runtime.py` - 9テストにマーカー追加
2. `backend/tests/test_pn.py` - 1テストにマーカー追加
3. `backend/tests/test_api_classify.py` - 1テストにマーカー追加、pytestインポート追加
4. `backend/pytest.ini` - postgresマーカー定義追加
5. `.github/workflows/ci.yml` - テスト実行ステップを分離
6. `docs/testing_strategy_db.md` - 新規作成（戦略説明）

### テスト数

- **SQLiteテスト**: 96件（通過）
- **PostgreSQLテスト**: 11件（CI環境で実行）
- **合計**: 107件

---

## 🚀 次のステップ

### このPR

1. ✅ テストマーカー追加
2. ✅ CI設定更新
3. ✅ ドキュメント作成
4. ⏳ コミット & プッシュ
5. ⏳ CI通過確認
6. ⏳ PRマージ

### 次のPR

1. PostgreSQL環境の最適化（tmpfs使用で高速化）
2. テストデータのシード化
3. カバレッジ目標の調整（SQLite: 80%、PostgreSQL: 統合のみ）

---

## 💡 学び

### シニアエンジニアの視点

> **「テストは本番環境を忠実に再現すべきだが、開発速度も重要」**

この決定により：

- ✅ 開発速度を維持（SQLiteで高速フィードバック）
- ✅ 品質を保証（PostgreSQLで本番シミュレーション）
- ✅ 保守性を向上（テストコードがシンプル）
- ✅ リスクを低減（偽陽性を回避）

### 技術的負債の回避

無理にSQLiteで動かそうとすると：

- ❌ テストコードが複雑化
- ❌ 保守コストが増大
- ❌ 偽陽性のリスク
- ❌ 本番環境との乖離

**結論**: 正しいツールを正しい場所で使う

---

**記録者**: Google Antigravity AI Assistant  
**参照ドキュメント**: [testing_strategy_db.md](file:///d:/works2025/越境EC/crossover_win/crossborder/docs/testing_strategy_db.md)

# デプロイ・ロールバック手順書

## デプロイ手順

### 自動デプロイ (推奨)

1. **mainブランチへのマージ**
   ```bash
   git checkout main
   git merge feature-branch
   git push origin main
   ```

2. **前のバージョンにロールバック**
   ```bash
   # rollback to last good commit
   git checkout <last_good_commit>
   docker-compose up -d
   ```

2. **データベースマイグレーション**
   ```bash
   make migrate
   # または
   docker-compose exec backend alembic upgrade head
   ```

3. **サービスの起動**
   ```bash
   make up
   # または
   docker-compose up -d
   ```

4. **ヘルスチェック**
   ```bash
   curl http://localhost:65001/v1/health
   ```

---

## ロールバック手順

### 緊急ロールバック

1. **現在のバージョンを確認**
   ```bash
   docker-compose ps
   docker images | grep crossborder-backend
   ```

2. **前のバージョンにロールバック**
   ```bash
   # 前のイメージタグを指定
   git checkout <last_good_commit>
   docker-compose up -d
   ```

3. **データベースのロールバック**
   ```bash
   # マイグレーションを1つ戻す
   docker-compose exec backend alembic downgrade -1
   
   # 特定のリビジョンに戻す
   docker-compose exec backend alembic downgrade <revision_id>
   ```

4. **ヘルスチェック**
   ```bash
   curl http://localhost:65001/v1/health
   ```

### 計画的ロールバック

1. **ロールバック計画の作成**
   - ロールバック対象のバージョンを特定
   - データベーススキーマの互換性を確認
   - ダウンタイムの見積もり

2. **メンテナンスモードの有効化**
   ```bash
   # ロードバランサーからサービスを除外
   # または503エラーページを表示
   ```

3. **データベースのバックアップ**
   ```bash
   docker-compose exec db pg_dump -U cb cbdb > backup_$(date +%Y%m%d_%H%M%S).sql
   ```

4. **ロールバック実行**
   ```bash
   # データベースマイグレーションのロールバック
   docker-compose exec backend alembic downgrade <target_revision>
   
   # アプリケーションのロールバック
   docker-compose down
   docker-compose up -d
   ```

5. **動作確認**
   ```bash
   # ヘルスチェック
   curl http://localhost:65001/v1/health
   
   # 主要機能のテスト
   make test-e2e
   ```

6. **メンテナンスモードの解除**

---

## トラブルシューティング

### デプロイが失敗した場合

1. **ログの確認**
   ```bash
   make logs
   # または
   docker-compose logs -f backend
   ```

2. **データベース接続の確認**
   ```bash
   docker-compose exec backend python -c "from app.db import db; from app.factory import create_app; app = create_app(); print('DB OK')"
   ```

3. **マイグレーション状態の確認**
   ```bash
   docker-compose exec backend alembic current
   docker-compose exec backend alembic history
   ```

### ロールバックが失敗した場合

1. **データベースの復元**
   ```bash
   # バックアップから復元
   docker-compose exec -T db psql -U cb cbdb < backup_YYYYMMDD_HHMMSS.sql
   ```

2. **クリーンな状態から再構築**
   ```bash
   make clean
   make up
   make migrate
   ```

---

## チェックリスト

### デプロイ前
- [ ] 全てのテストが成功している
- [ ] マイグレーションファイルが作成されている
- [ ] .envファイルが正しく設定されている
- [ ] データベースのバックアップが取得されている

### デプロイ後
- [ ] ヘルスチェックが成功している
- [ ] 主要機能が動作している
- [ ] ログにエラーがない
- [ ] モニタリングダッシュボードが正常

### ロールバック後
- [ ] 前のバージョンが動作している
- [ ] データベースの整合性が保たれている
- [ ] ユーザーへの影響が最小限
- [ ] インシデントレポートが作成されている

---

## Windows ローカル運用（タスクスケジューラ）

1. **スクリプト準備**
   - `scripts/local_deploy.ps1` の `RepoPath` / `ComposeDir` / `ServiceUrl` を実環境に合わせて編集
   - 例: `ServiceUrl = "http://localhost:65001"`

2. **タスクスケジューラ登録**
   - トリガー: 15分ごと（必要に応じて変更）
   - 操作: プログラムの開始
   - プログラム: `powershell.exe`
   - 引数: `-ExecutionPolicy Bypass -File D:\works2025\越境EC\crossover_win\crossborder\scripts\local_deploy.ps1`

3. **任意: 依存更新がある場合のみビルド**
   - 引数に `-Build` を追加すると `docker compose build` を実行

---

## Local Windows Ops Notes (Source-Based)

- `scripts/local_deploy.ps1` writes the last known good commit to `.last_good_commit`.
- On health check failure after update, the script rolls back to `.last_good_commit` and rechecks health.
- A lock file `.deploy_lock` prevents overlapping runs when Task Scheduler triggers frequently.
- `GitRemote` is fixed to `origin` for simplicity; override with `-GitRemote` only if you have a non-standard remote.
- Ensure the Git remote exists and credentials allow `git fetch`.
- Keep the working tree clean so `git checkout` can switch to the target branch safely.

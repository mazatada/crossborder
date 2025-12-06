# Runbook - 運用手順書

クロスボーダーECシステムの運用手順をまとめたRunbookです。

---

## 目次

1. [起動・停止手順](#起動停止手順)
2. [障害対応](#障害対応)
3. [APIキー管理](#apiキー管理)
4. [データベースメンテナンス](#データベースメンテナンス)
5. [監視・ログ確認](#監視ログ確認)
6. [バックアップ・リストア](#バックアップリストア)

---

## 起動・停止手順

### 通常起動

```bash
# 全サービス起動
make up
# または
docker-compose up -d

# 起動確認
docker-compose ps
curl http://localhost:5000/health
```

### 停止

```bash
# 全サービス停止
make down
# または
docker-compose down
```

### 再起動

```bash
# 全サービス再起動
make restart
# または
docker-compose restart

# 特定サービスのみ再起動
docker-compose restart backend
docker-compose restart worker
```

### 初回セットアップ

```bash
# 1. 環境変数ファイルの作成
cp .env.example .env
# .envファイルを編集して本番環境の値を設定

# 2. Dockerイメージのビルド
docker-compose build

# 3. データベースマイグレーション
make migrate
# または
docker-compose exec backend alembic upgrade head

# 4. サービス起動
make up
```

---

## 障害対応

### サービスが起動しない

#### 症状
- `docker-compose up`が失敗する
- サービスがすぐに停止する

#### 対処手順

1. **ログの確認**
   ```bash
   docker-compose logs backend
   docker-compose logs db
   docker-compose logs worker
   ```

2. **ポート競合の確認**
   ```bash
   # Windowsの場合
   netstat -ano | findstr :5000
   netstat -ano | findstr :5432
   ```

3. **データベース接続の確認**
   ```bash
   docker-compose exec backend python -c "from app.db import db; from app.factory import create_app; app = create_app(); print('DB OK')"
   ```

4. **環境変数の確認**
   ```bash
   docker-compose exec backend env | grep DB
   docker-compose exec backend env | grep SQLALCHEMY
   ```

### データベース接続エラー

#### 症状
- `SQLALCHEMY_DATABASE_URI`エラー
- `Connection refused`エラー

#### 対処手順

1. **データベースの起動確認**
   ```bash
   docker-compose ps db
   docker-compose logs db
   ```

2. **接続文字列の確認**
   ```bash
   # .envファイルを確認
   cat .env | grep DB_URL
   ```

3. **データベースへの直接接続テスト**
   ```bash
   docker-compose exec db psql -U cb -d cbdb -c "SELECT 1;"
   ```

4. **データベースの再起動**
   ```bash
   docker-compose restart db
   # ヘルスチェックが通るまで待機
   docker-compose ps db
   ```

### ジョブが実行されない

#### 症状
- ジョブのステータスが`pending`のまま
- ワーカーログにエラー

#### 対処手順

1. **ワーカーの状態確認**
   ```bash
   docker-compose ps worker scheduler
   docker-compose logs worker
   docker-compose logs scheduler
   ```

2. **ジョブテーブルの確認**
   ```bash
   docker-compose exec db psql -U cb -d cbdb -c "SELECT id, type, status, created_at FROM jobs ORDER BY created_at DESC LIMIT 10;"
   ```

3. **ワーカーの再起動**
   ```bash
   docker-compose restart worker
   docker-compose restart scheduler
   ```

4. **手動ジョブ実行(デバッグ用)**
   ```bash
   docker-compose exec backend python -m app.jobs.cli --mode worker --once
   ```

### Webhook送信失敗

#### 症状
- Webhookが送信されない
- DLQにエントリが蓄積

#### 対処手順

1. **DLQの確認**
   ```bash
   curl http://localhost:5000/v1/integrations/webhooks/dlq
   ```

2. **Webhook設定の確認**
   ```bash
   curl http://localhost:5000/v1/integrations/webhooks
   ```

3. **手動リプレイ**
   ```bash
   curl -X POST http://localhost:5000/v1/integrations/webhooks/dlq/{dlq_id}/replay \
     -H "Content-Type: application/json" \
     -d '{"traceId": "MANUAL-REPLAY"}'
   ```

4. **DLQクリーンアップ**
   ```bash
   curl -X POST http://localhost:5000/v1/integrations/webhooks/dlq/cleanup \
     -H "Content-Type: application/json" \
     -d '{"traceId": "CLEANUP"}'
   ```

---

## APIキー管理

### APIキーの追加

1. **環境変数の更新**
   ```bash
   # .envファイルを編集
   API_KEYS=existing-key-1,existing-key-2,new-key-3
   ```

2. **サービスの再起動**
   ```bash
   docker-compose restart backend
   ```

3. **動作確認**
   ```bash
   curl -H "Authorization: Bearer new-key-3" http://localhost:5000/v1/health
   ```

### APIキーのローテーション

1. **新しいキーを追加**
   ```bash
   # 既存キーと新キーを両方有効化
   API_KEYS=old-key,new-key
   ```

2. **クライアントを新キーに移行**
   - 全てのクライアントが新キーを使用するまで待機

3. **古いキーを削除**
   ```bash
   # 新キーのみ有効化
   API_KEYS=new-key
   ```

4. **サービス再起動**
   ```bash
   docker-compose restart backend
   ```

### Inbound APIキーの更新

```bash
# .envファイルを編集
INBOUND_API_KEY=new-inbound-key

# サービス再起動
docker-compose restart backend
```

---

## データベースメンテナンス

### マイグレーション実行

```bash
# 最新バージョンへマイグレーション
make migrate
# または
docker-compose exec backend alembic upgrade head

# 現在のリビジョン確認
docker-compose exec backend alembic current

# マイグレーション履歴確認
docker-compose exec backend alembic history
```

### マイグレーションの作成

```bash
# 自動生成
make migrate-create NAME="add_new_table"
# または
docker-compose exec backend alembic revision --autogenerate -m "add_new_table"

# 手動作成
docker-compose exec backend alembic revision -m "custom_migration"
```

### マイグレーションのロールバック

```bash
# 1つ前に戻す
docker-compose exec backend alembic downgrade -1

# 特定のリビジョンに戻す
docker-compose exec backend alembic downgrade <revision_id>
```

### データベースのバキューム

```bash
# 定期的に実行してパフォーマンスを維持
docker-compose exec db psql -U cb -d cbdb -c "VACUUM ANALYZE;"
```

---

## 監視・ログ確認

### ログの確認

```bash
# 全サービスのログ
make logs
# または
docker-compose logs -f

# 特定サービスのログ
docker-compose logs -f backend
docker-compose logs -f worker
docker-compose logs -f db

# 最新100行のみ
docker-compose logs --tail=100 backend
```

### 監査ログの確認

```bash
# データベースから直接確認
docker-compose exec db psql -U cb -d cbdb -c "
  SELECT id, trace_id, event, ts 
  FROM audit_events 
  ORDER BY ts DESC 
  LIMIT 20;
"

# 特定のtrace_idで検索
docker-compose exec db psql -U cb -d cbdb -c "
  SELECT * FROM audit_events 
  WHERE trace_id = 'YOUR-TRACE-ID' 
  ORDER BY ts;
"
```

### ヘルスチェック

```bash
# APIヘルスチェック
curl http://localhost:5000/health

# データベースヘルスチェック
docker-compose exec db pg_isready -U cb -d cbdb

# 全サービスの状態確認
docker-compose ps
```

---

## バックアップ・リストア

### データベースバックアップ

```bash
# バックアップ作成
docker-compose exec db pg_dump -U cb cbdb > backup_$(date +%Y%m%d_%H%M%S).sql

# 圧縮バックアップ
docker-compose exec db pg_dump -U cb cbdb | gzip > backup_$(date +%Y%m%d_%H%M%S).sql.gz
```

### データベースリストア

```bash
# バックアップから復元
docker-compose exec -T db psql -U cb cbdb < backup_YYYYMMDD_HHMMSS.sql

# 圧縮バックアップから復元
gunzip -c backup_YYYYMMDD_HHMMSS.sql.gz | docker-compose exec -T db psql -U cb cbdb
```

### 自動バックアップの設定

cronジョブで定期バックアップを設定:

```bash
# crontabを編集
crontab -e

# 毎日午前2時にバックアップ
0 2 * * * cd /path/to/crossborder && docker-compose exec -T db pg_dump -U cb cbdb | gzip > /path/to/backups/backup_$(date +\%Y\%m\%d).sql.gz
```

---

## 緊急連絡先

- **システム管理者**: admin@example.com
- **データベース管理者**: dba@example.com
- **オンコール**: oncall@example.com

---

## 関連ドキュメント

- [デプロイ手順書](deployment.md)
- [API仕様書](../backend/openapi.yaml)
- [アーキテクチャ図](spec/)
- [変更履歴](../CHANGELOG.md)

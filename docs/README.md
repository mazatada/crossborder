# ドキュメント索引

クロスボーダーECシステムの全ドキュメントへのインデックスです。

---

## 📚 目次

- [概要](#概要)
- [アーキテクチャ](#アーキテクチャ)
- [API仕様](#api仕様)
- [実装計画](#実装計画)
- [運用ドキュメント](#運用ドキュメント)
- [開発ガイド](#開発ガイド)
- [変更履歴](#変更履歴)

---

## 概要

### プロジェクト概要
- [README.md](../README.md) - プロジェクトの概要と始め方
- [機能一覧.md](機能一覧.md) - 実装済み機能の一覧
- [越境EC成分表翻訳アプリ仕様書_v1_0.md](越境EC成分表翻訳アプリ仕様書_v1_0.md) - 詳細仕様書

---

## アーキテクチャ

### システム設計
- [spec/](spec/) - システム仕様書
- [ui/](ui/) - UI設計書
- [ERD](../backend/erd.md) - データベース設計 (Entity Relationship Diagram)

### インフラ
- [docker-compose.yml](../docker-compose.yml) - Docker Compose設定
- [.env.example](../.env.example) - 環境変数サンプル

---

## API仕様

### OpenAPI仕様
- [openapi.yaml](../backend/openapi.yaml) - OpenAPI 3.0仕様書
- OpenAPI 仕様は CI で検証（必要に応じて生成/更新）

### エンドポイント一覧

#### コアAPI
- POST /v1/translate/ingredients - 成分翻訳
- POST /v1/classify/hs - HS分類
- POST /v1/docs/clearance-pack - 通関書類パック生成
- POST /v1/fda/prior-notice - PN申請

#### ジョブAPI
- `POST /v1/jobs` - ジョブ作成
- `GET /v1/jobs/{job_id}` - ジョブ状態確認

#### 監査API
- `GET /v1/audit/events` - 監査ログ取得

#### Webhook API
- `POST /v1/integrations/webhooks` - Webhook登録
- `GET /v1/integrations/webhooks` - Webhook一覧
- `DELETE /v1/integrations/webhooks/{id}` - Webhook削除
- `POST /v1/integrations/webhooks/{id}/test` - Webhookテスト
- `GET /v1/integrations/webhooks/dlq` - DLQ一覧
- `POST /v1/integrations/webhooks/dlq/{id}/replay` - DLQリプレイ
- `POST /v1/integrations/webhooks/dlq/cleanup` - DLQクリーンアップ

#### Inbound API
- `POST /v1/integrations/orders/{order_id}/status` - 注文ステータス受信

---

## 実装計画

### Phase 0-8
- [implementation_plan_0_common.md](implementation_plan_0_common.md) - 共通基盤
- [implementation_plan_1_database_migration.md](implementation_plan_1_database_migration.md) - データベース・マイグレーション
- [implementation_plan_2_job_runtime_async.md](implementation_plan_2_job_runtime_async.md) - ジョブランタイム・非同期処理
- [implementation_plan_3_audit_observability.md](implementation_plan_3_audit_observability.md) - 監査・可観測性
- [implementation_plan_4_core_api.md](implementation_plan_4_core_api.md) - コアAPI
- [implementation_plan_5_integration.md](implementation_plan_5_integration.md) - 外部連携
- [implementation_plan_6_security_ops.md](implementation_plan_6_security_ops.md) - セキュリティ・運用
- [implementation_plan_7_devex_quality.md](implementation_plan_7_devex_quality.md) - 開発体験・品質保証
- [implementation_plan_8_docs_knowledge.md](implementation_plan_8_docs_knowledge.md) - ドキュメント・ナレッジ管理

---

## 運用ドキュメント

### 運用手順書
- [runbook.md](runbook.md) - Runbook (起動・障害対応・キー更新)
- [deployment.md](deployment.md) - デプロイ・ロールバック手順書
- [webhook_retry.md](webhook_retry.md) - Webhook再送仕様

### 規制・コンプライアンス
- [regulations/](regulations/) - 規制関連ドキュメント

---

## 開発ガイド

### セットアップ
```bash
# 1. リポジトリのクローン
git clone <repository-url>
cd crossborder

# 2. 環境変数の設定
cp .env.example .env
# .envファイルを編集

# 3. サービスの起動
make up

# 4. マイグレーション実行
make migrate
```

### 開発コマンド
```bash
# テスト
make test              # 全テスト
make test-unit         # ユニットテスト
make test-integration  # 統合テスト
make test-e2e          # E2Eテスト
make test-coverage     # カバレッジレポート

# コード品質
make lint        # リンター
make format      # フォーマッター
make type        # 型チェック
make ci          # 全チェック

# サービス管理
make up          # 起動
make down        # 停止
make restart     # 再起動
make logs        # ログ表示
```

### テスト戦略
- **Unit**: モデル、バリデーション、ルール、エラー
- **Integration**: API、DB、ジョブ
- **E2E**: 全フロー (翻訳→分類→書類→PN)

### CI/CD
- [.github/workflows/ci.yml](../.github/workflows/ci.yml) - CI設定
- [.github/workflows/cd.yml](../.github/workflows/cd.yml) - CD設定

---

## 変更履歴

- [CHANGELOG.md](../CHANGELOG.md) - プロジェクトの変更履歴

---

## ドキュメント更新ガイドライン

### 原則
1. **コードと同時更新**: 仕様変更時はドキュメントとコードを同時にPR
2. **生成/検証の活用**: OpenAPI仕様は生成/検証の運用を明確化
3. **バージョン管理**: リリースタグごとにドキュメントをバージョニング

### 更新手順
1. 機能追加・変更時は該当ドキュメントを更新
2. `CHANGELOG.md`に変更内容を記載
3. PRに変更内容を明記
4. レビュー時にドキュメントの整合性を確認

### ドキュメント配布
- 自動ビルドでHTML出力 (mkdocs or mdBook)
- GitHub Pagesで公開 (オプション)

---

## 関連リンク

- [GitHub Repository](https://github.com/mazatada/crossborder)
- [Issue Tracker](https://github.com/mazatada/crossborder/issues)
- [Wiki](https://github.com/mazatada/crossborder/wiki)

---

## サポート

質問や問題がある場合は、以下の方法でサポートを受けられます:

- **Issue**: GitHub Issueを作成
- **Email**: support@example.com
- **Slack**: #crossborder-support

---

最終更新: 2026-01-01

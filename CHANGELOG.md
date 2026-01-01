# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Plan8: ドキュメント・ナレッジ管理体系
  - Runbook (運用手順書)
  - CHANGELOG.md
  - ドキュメント索引 (docs/README.md)
  - ERD生成スクリプト

- Plan7: 開発体験・品質保証機能
  - Makefile (開発コマンドの簡素化)
  - E2Eテスト (完全なクロスボーダーフロー)
  - カバレッジ設定 (80%以上を目標)
  - CD設定 (自動デプロイ、マイグレーション、ロールバック)
  - デプロイ・ロールバック手順書

- Plan5: 外部連携機能
  - Webhook DLQ (Dead Letter Queue)
  - DLQ管理API (一覧、リプレイ、クリーンアップ)
  - Inbound注文受信API
  - Webhook再送機能 (最大5回、72時間保持)

### Changed
- `.env.example`: 全環境変数のサンプルを追加
- `pytest.ini`: カバレッジ設定とE2Eマーカーを追加
- `requirements.txt`: pytest-covを追加

### Fixed
- Inbound API: APIキーを動的に取得するように修正 (テスト対応)
- Webhook retry: DLQ保存処理を追加

## [0.1.0] - 2025-12-05

### Added
- 初期リリース
- 基本的なクロスボーダーEC機能
  - 翻訳API
  - HS分類API
  - 書類作成API
  - PN提出API
- ジョブシステム
  - 非同期ジョブ処理
  - ワーカー・スケジューラー
  - リトライ機能
- 監査ログ機能
- Webhook機能
  - HMAC-SHA256署名
  - イベント通知
- Docker Compose環境
- CI/CD設定 (GitHub Actions)
- 基本的なテスト

### Security
- APIキー認証
- HMAC署名検証
- CORS設定

## Release Notes Format

各リリースは以下のセクションで構成されます:

- **Added**: 新機能
- **Changed**: 既存機能の変更
- **Deprecated**: 非推奨となった機能
- **Removed**: 削除された機能
- **Fixed**: バグ修正
- **Security**: セキュリティ関連の変更

---

## Version History

- `[Unreleased]`: 次のリリースに含まれる変更
- `[0.1.0]`: 初期リリース (2025-12-05)

---

## Contributing

変更を加える際は、以下のガイドラインに従ってください:

1. **機能追加**: `Added`セクションに記載
2. **バグ修正**: `Fixed`セクションに記載
3. **破壊的変更**: `Changed`セクションに記載し、詳細を説明
4. **セキュリティ**: `Security`セクションに記載

リリース時は、`[Unreleased]`セクションを新しいバージョン番号に変更し、リリース日を追加してください。

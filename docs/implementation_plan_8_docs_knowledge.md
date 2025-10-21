# 実装計画書 — 8. ドキュメント／ナレッジ管理

---
## 1. 目的
- 開発・運用を継続可能に保つナレッジ体系を整える。

---
## 2. 成果物
- Runbook: 起動・障害対応・キー更新
- APIリファレンス (OpenAPI自動生成)
- ERD・DDL更新スクリプト
- 変更履歴管理 (CHANGELOG.md)
- docs/README.md（全仕様書索引）

---
## 3. 運用方針
- 仕様変更時は docs とコードを同時PR
- 自動ビルドでHTML出力（mkdocs or mdBook）
- リリースタグごとに docs/versioning

---
## 4. Definition of Done
- Runbookが存在し最新
- OpenAPIがCIで生成
- docs/がビルド可能で配布済み

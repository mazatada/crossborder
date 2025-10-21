# 実装計画書 — 7. 開発体験／品質保証

---
## 1. 目的
- 開発効率と品質を維持する自動化体制を整備。

---
## 2. 成果物
- Docker Compose dev環境
- `.env.example`
- `make test / make up / make down`
- pytest + coverage
- CI: lint, type, test
- CD: alembic migrate + deploy

---
## 3. テスト戦略
- Unit: モデル, バリデーション, ルール, エラー
- Integration: API, DB, ジョブ
- E2E: 全フロー(翻訳→分類→書類→PN)

---
## 4. CI/CD
- GitHub Actions or GitLab CI
- ステージング自動適用
- rollback手順付き

---
## 5. Definition of Done
- CIが全自動パス
- カバレッジ>=80%
- alembic migrate 自動化

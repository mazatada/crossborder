# 実装計画書 — 6. セキュリティ／運用

---
## 1. 目的
- 認証・CORS・Secret・PII最小化で堅牢運用を実現。

---
## 2. 成果物
- APIキー管理ロジック
- CORS設定 (`CORS_ALLOW_ORIGINS`)
- Secret管理 (.env → Docker Secret)
- PIIポリシー文書
- 監査ログのマスキング実装

---
## 3. 要点
- APIキーを複数許可・ローテーション対応
- 環境別CORS設定（dev=*, prod=固定）
- Secrets: DB, API_KEYS, TLS, PN鍵をSecret化
- ログにPII含まない (order_idのみ許可)

---
## 4. テスト
- 無許可キー→401
- 許可キー→200
- CORSヘッダ確認
- ログ出力に個人情報が含まれない

---
## 5. Definition of Done
- Secretsがenv以外の安全領域管理
- CORS適切
- APIキー失効テスト合格

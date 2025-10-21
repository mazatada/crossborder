# 実装計画書 — 5. 外部連携（Webhook・Inbound）

対象: Webhook送信・署名検証、Inbound注文受信API。

---
## 1. 目的
- イベント駆動で他アプリと接続。確実な再送・署名検証を実装。

---
## 2. 成果物
- `/v1/integrations/webhooks` 登録/テストAPI
- `/v1/integrations/orders/<id>/status` 受信API
- `app/integrations/webhook_dispatcher.py`
- HMAC署名検証ユーティリティ

---
## 3. Webhook仕様
- HMAC-SHA256 (`X-Signature`)
- 再送 5回 / DLQ72h / 手動リプレイ
- イベント例: HS_CLASSIFIED, DOCS_PACKAGED, PN_SUBMITTED

---
## 4. Inbound仕様
- 入力: {order_id,status:"PAID"|"CANCELED",ts,customer_region}
- 認証: APIキー
- 出力: 202 Accepted

---
## 5. テスト計画
- 署名が正しい場合のみ200
- 再送間隔/回数確認
- Inboundでstatusが正しく反映

---
## 6. Definition of Done
- Webhook登録・送信・再送が動作
- Inbound注文イベントがDBに反映
- 署名・認証が完全一致

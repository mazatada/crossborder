- 「4.」がすべて 実装済み になれば **実装完了**

## 1. 目的
バックエンド実装の完了定義を明確化し、**仕様充足（機能）**と**リリース準備（品質・運用）**を統合したチェックリストを提供する。

## 2. 対象範囲
- API（翻訳 / HS分類 / 通関書類 / FDA PN / Webhook / Inbound / 監査 / Jobs）
- 非同期ジョブ基盤（scheduler / worker / retry / DLQ）
- 監査・可観測性
- セキュリティ運用（APIキー / CORS / Secrets / PII）
- CI/テスト（lint / unit / integration / E2E）
- ドキュメントと運用準備

## 3. 完了判定の基本方針
- **仕様充足**: 仕様書に記載されたAPI・イベント・データモデルが存在し、期待される挙動を満たす。
- **リリース準備**: CIが安定し、運用上の再現性・手順が整っている。

## 4. 総合チェックリスト（完了条件）
### 4.1 コアAPI（Plan 4）
- [x] `/v1/translate/ingredients` が正常系/異常系で仕様通り応答（実装済み）
- [x] `/v1/classify/hs` が仕様通り応答（422/400/200）（実装済み）
- [x] `/v1/docs/clearance-pack` がジョブを起票し `job_id` を返す（実装済み）
- [x] `/v1/fda/prior-notice` が202+job起票で応答（実装済み）

### 4.2 ジョブ基盤（Plan 2）
- [x] jobsスキーマ（attempts/next_run_at/payload_json/result_json）整合（実装済み）
- [x] schedulerが可視性タイムアウトを処理（実装済み）
- [x] workerがretry/fail/success遷移を実施（実装済み）
- [x] webhook_retryが失敗時に起票される（実装済み）

### 4.3 監査・可観測性（Plan 3）
- [x] audit_eventsに主要イベントが記録される（実装済み）
- [x] `/v1/audit/trace/<trace_id>` と `/v1/audit/recent` が応答（実装済み）
- [x] ログに trace_id / job_id / event が含まれる（実装済み）

### 4.4 外部連携（Plan 5）
- [x] Webhook登録・送信・再送が動作（実装済み）
- [x] HMAC-SHA256署名検証が正しく機能（実装済み）
- [x] Inbound注文イベントがDBに反映（実装済み）

### 4.5 セキュリティ運用（Plan 6）
- [x] APIキーの許可/失効テストがある（実装済み）
- [x] CORS が環境別に制御される（実装済み）
- [x] Secrets の安全管理が明文化される（方針確定）
- [x] PII をログに含めない方針が実装/確認される（実装済み）

### 4.6 CI/テスト（Plan 7）
- [ ] lint / type / pytest / Playwright がCIで全通過（未確認、ローカルDockerで通過済み）
- [x] テストカバレッジ 80% 以上（ローカルDocker計測で達成）
- [x] pytest マーカーが全て登録され警告がない（実装済み）

### 4.7 ドキュメント（Plan 8）
- [x] Runbook が最新（実装済み）
- [x] OpenAPI がCIで生成/検証される（検証ステップ実装済み）
- [x] docs/README で索引が整備される（実装済み）
- [x] 変更履歴が更新される（実装済み）

## 5. 残作業の洗い出し（要確認/未完了）
- [ ] GitHub Actions の main CI が green であることの確認
- [x] ローカルDockerで lint/type/pytest/Playwright 全通過（2026-01-03 再確認）
- [x] pytest の `security` マーカー登録（警告解消）
- [x] Playwright 依存の脆弱性（npm audit）対応方針の決定
- [x] OpenAPI 生成/検証ステップの実運用化
- [x] Secrets の安全管理ポリシー確定（env以外の管理方法）
- [x] CORS 設定の環境別検証
- [x] PII マスキングの実装/監査（ログ出力検証）
- [ ] イベントカタログの定義と、Webhook送信イベントの一覧・ペイロードの確定
- [ ] Inbound `ORDER_PAID` / `ORDER_CANCELED` の必須項目・バリデーション定義（仕様書整合）
- [ ] データ保持/非保持ポリシーの明文化（PIIを含む保持期間）
- [ ] OpenAPIドラフト仕様の未反映分（Webhook送信/受信I/F）の反映方針決定

## 6. 判定ルール
- 「4.」がすべて 実装済み になれば **実装完了**
- 「5.」がすべて完了になれば **リリース可能**

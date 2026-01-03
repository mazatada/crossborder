# デプロイ戦略（Composeベース / 完全実装ガイド）

> 仕様書ハブ: docs/越境EC成分表翻訳アプリ仕様書_v1_0.md

## 1. 目的
Docker Compose 環境で、実運用に耐えるデプロイ手順・ロールバック手順・
マイグレーション方針・ヘルスチェックを一貫して定義する。

## 2. 前提
- デプロイ方式: Docker Compose
- 実行基盤: ローカルWindows上で `docker compose` を実行（SSH 経由のリモート運用は将来拡張）
- DB は単一（PostgreSQL）で共有
- 互換性ポリシー: 既存APIの意味変更・削除は禁止（追加のみ）
- 監査/PII: 監査ログは保持、PII は最小保持（マスキング前提）

## 3. 運用方式（現状: ソース運用）
- 現行の compose は `build: ./backend` + bind mount 前提のため、ソース運用とする
- ロールバックは **git commit** を単位に実施（後述）
- 画像タグ運用は将来の拡張（イメージ運用へ移行する場合に適用）

## 4. デプロイ手順（Compose / ローカル）

### 4.1 更新手順（ソース運用）
1) リポジトリ更新（`git pull`）
2) 必要に応じて依存更新（例: `docker compose build`）
3) `docker compose up -d` で反映

### 4.2 更新の順序（安全順）
```bash
# 依存サービス起動順を担保
docker compose up -d db redis
# DBがhealthyになるまで待機
# 例: docker compose ps / logsで確認

# backend -> worker -> scheduler の順
docker compose up -d backend
docker compose up -d worker
docker compose up -d scheduler
```

## 5. マイグレーション方針（前方互換）
- 破壊的変更は禁止
- 変更は2段階
  1) expand: 新カラム/新テーブル追加
  2) contract: 旧カラム削除は次リリース以降
- downgrade は原則禁止（必要時は手動・限定条件）

### 実行タイミング
- **デプロイ後**に実行（対象コンテナが存在する前提）

```bash
# 例: backend コンテナ内で実行
docker compose exec backend alembic upgrade head
```

### 失敗時の復旧（具体手順）
- まずアプリのみロールバック（DBは前方互換前提）

```bash
# 直前の安定コミットへ戻す
git checkout <last_good_commit>
docker compose up -d backend
```

- それでも復旧しない場合は、**追加修正マイグレーション**で対応
  - 例: `alembic revision -m "hotfix"` を作成し、必要最小限の修正を forward 適用

## 6. ヘルスチェック（必須）

### 6.1 深いヘルス
- `/v1/health` は DB/Redis 接続 + 簡易クエリ（SELECT 1 など）を実行
- 成功条件: HTTP 200 + DB/Redis が正常

### 6.2 自動ヘルスチェック例
```bash
for i in {1..30}; do
  if curl -f $SERVICE_URL/v1/health > /dev/null 2>&1; then
    echo "Service is healthy"
    exit 0
  fi
  echo "Attempt $i: not ready"
  sleep 10
done
exit 1
```

## 7. API スモーク（必須）
- translate → classify → docs → PN の最小フローを確認
- 成功条件: 202 + job queued
- 追加検証: 監査イベントの存在（`HS_CLASSIFIED`, `DOCS_PACKAGED`, `PN_SUBMITTED`）
- 例: Playwright API スモーク（`frontend/playwright/tests/api.spec.ts`）

### 具体入力例
- translate: `{ "text_ja": "砂糖, 小麦粉", "trace_id": "deploy-smoke" }`
- classify: translate結果のproductを使用
- docs: classify結果のhs_code/required_uom/invoice_payloadを使用
- PN: docs結果のtrace_idでリクエスト

## 8. 互換性検証（必須）
- 旧APIレスポンスが維持されていることを確認
- 旧DBスキーマとの前方互換を確認（expand後も旧コードが動く）
- 具体例: 旧APIのスモーク + 旧カラムがまだ利用可能であること

## 9. ロールバック方針（ソース運用）
- 条件: デプロイ成功 + ヘルスチェック成功 + API スモーク成功
- 失敗時: 直前の安定コミットへ戻す
- 例: `git checkout <last_good_commit>` → `docker compose up -d`

## 10. ロールバック手順
- 直前の安定コミットへ戻す
- ロールバック後に再度ヘルスチェック + API スモークを実行

```bash
git checkout <last_good_commit>
docker compose up -d backend
```

## 11. 監視と障害対応
- 監視指標: エラー率、レスポンスタイム、ジョブ失敗率
- 目安: エラー率 > 1% / p95 レイテンシ > 1500ms でアラート
- 障害時: 直ちに last_good_tag へロールバック
- 監査: trace_id で全フロー追跡可能であること

## 12. Secrets / 環境変数
- APIキー / DB URL / Webhookシークレットは .env で注入
- 本番は Docker Secret 等へ移行を推奨
- GitHub Actions で使用する Secrets は最小権限にする

## 13. ログとメトリクス
- ログは構造化（trace_id / event / job_id）を維持
- 監視基盤（例: Prometheus/Grafana）導入を検討

## 14. チェックリスト（運用前）
- [ ] CI パイプラインが green
- [ ] Trivy スキャンが pass
- [ ] マイグレーション前方互換が確認済み
- [ ] ヘルスチェック定義が最新
- [ ] last_good_tag の更新条件が明文化
- [ ] Secrets の運用が確認済み

## 15. 将来的な拡張
- カナリア / Blue-Green への移行
- K8s/ECS への移行（真のゼロダウンを実現）

## 16. 将来: イメージ運用への移行計画
- compose を `image` + `IMAGE_TAG` 前提に変更し、`build`/bind mount を削除
- CI で `{env}-{sha}` タグ付きイメージをビルド/スキャン/Push
- デプロイは `docker compose pull` → `docker compose up -d` に統一
- `LAST_GOOD_TAG_<ENV>` を更新し、ロールバックはタグで実施
- すべての運用ドキュメントをタグ運用前提に統一

## 17. Local Source Ops Notes
- Store the last known good commit in `.last_good_commit` (repo root).
- Update `.last_good_commit` only after health check + API smoke succeed.
- Use a lock file `.deploy_lock` to avoid overlapping scheduled runs.

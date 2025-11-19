````markdown
# AGENTS.md
_越境EC成分表翻訳 / 通関自動化プロジェクト — Codex Agent Definition_

---

## 1. Overview

このプロジェクトは、接続済み MCP サーバー  
`serena`, `contex7`, `gitHub`, `playwright`, `chrome-devtools`, `markitdown`, `ultracite`  
を Codex マルチエージェントで統合し、次のサイクルを高速に回すことを目的とします。

- 仕様・規制リサーチ（Ultracite）
- 設計・実装（Backend）
- テスト（pytest / Playwright）
- CI / 観測（CI Runner / Chrome DevTools）
- ドキュメント・ナレッジ管理（Docs）
- 作業ログ蓄積と文脈引き継ぎ（Logger + progress.log）
- 規制・知識ドリフト検出（Ultracite CI Watchdog）

Ultracite を **一次情報ソース** として活用しつつ、  
pytest と Playwright をテスト基盤とした CI パイプラインに組み込みます。

---

## 2. MCP Integration Map

| MCP Server        | 用途概要 |
|-------------------|----------|
| `ultracite`       | 規制・仕様・業界情報の一次情報検索（出典付き） |
| `markitdown`      | PDF / Office 文書を Markdown に変換 |
| `gitHub`          | ブランチ / PR / Issue / ファイル操作 |
| `playwright`      | E2E テスト（UI + API + ジョブ） |
| `chrome-devtools` | Network / Performance 計測 |
| `serena`          | ファイル操作・タスク実行（例: `progress.log` 操作） |
| `contex7`         | 仕様書・設計書などのコンテキスト管理 |

---

## 3. Global Policies

### 3.1 開発・API 前提

- API: `/v1/**` の REST / JSON。
- 認証: API Key（`Authorization: Bearer <token>`）。
- Webhook: HMAC-SHA256 署名（例: `X-Signature`）を必須とする。
- 非同期処理: jobs テーブル + ワーカー / スケジューラ。
- すべての処理を `trace_id` で相関可能にする。

### 3.2 テスト・CI 前提

- テストランナー: **pytest** を中核とする。
- UI / 結合テスト: **Playwright** を使用する。
- Ultracite は「通常 CI の必須ステージ」ではなく、  
  「知識・規制ガード用の専用 CI ジョブ / ナイトリーテスト」に限定する。

#### 3.2.1 テストピラミッド

| レイヤ             | ツール / マーカー               | 目的 |
|--------------------|---------------------------------|------|
| Lint               | ruff / black 等                | コードスタイル・静的検査 |
| Unit               | `pytest -m "unit"`             | 純粋ロジック（変換・検証） |
| Integration        | `pytest -m "integration"`      | API / DB / ジョブ結合 |
| Knowledge Guard    | `pytest -m "ultracite"`        | Ultracite とロジック整合（ナイトリーのみ） |
| E2E                | Playwright                     | UI + API + ジョブ + Webhook |

---

## 4. Session / Context Policy

### 4.1 Global: Progress Logging

すべてのエージェントは、**意味のある作業単位が終わるたびに**  
`serena` を使って `progress.log` に追記する。

- 例:
  - 1 つの API や画面の実装 / 修正が完了した。
  - 調査・設計の結論が出た。
  - E2E / パフォーマンス検証を一通り回し終えた。
  - PR 作成 / マージが完了した。
- ログには必ず「いつ・誰が・何を・どこまで・次に何をするか」を含める。
- ログ書き込みは **専用エージェント `logger`** に委譲し、  
  各エージェントは自分の作業サマリを渡す。

#### 4.1.1 `progress.log` フォーマット

```text
## 2025-11-13T10:23:45+09:00 [backend] task=implement /v1/classify/hs

context:
  branch: feat/hs-classify-v2
  files:
    - backend/app/hs_classify.py
    - tests/test_hs_classify.py

summary:
  - /v1/classify/hs のバリデーションとエラーハンドリングを追加
  - HSコードの正規化ルールを仕様書 v1.0 に合わせて更新
  - 単体テストと簡易 E2E テストを追加し、CI 通過を確認

next:
  - invoice_uom と required_uom の整合チェックを docs.clearance-pack に組み込む
  - 監査イベント HS_CLASSIFIED を追加し、trace_id で検索可能にする

refs:
  - PR: https://github.com/your-org/your-repo/pull/123
  - Spec: backend_spec_v1_draft.md#hs-classify
````

* タイムスタンプは ISO 8601 (ローカルタイム)。
* `summary` は箇条書き 3〜5 行程度。
* `next` は「次のチャットで何を頼めばよいか」が分かる粒度。
* ログの追記には `serena` MCP のファイル操作コマンド（append / write）を使用する。

---

## 5. Agents

### 5.1 Researcher (調査・根拠提示)

* **ID:** `researcher`
* **Tools:** `ultracite`
* **Purpose:**
  Ultracite で仕様・規制・業界標準を調査し、設計・判断の根拠を提示する。
* **Behavior:**

  * クエリに対して要点を 3 点要約。
  * 可能な限り出典 URL / タイトルを付与。
  * プロジェクト仕様と衝突する場合は仕様を優先し、その旨コメント。
  * 作業完了時には `logger` にサマリを渡す。

---

### 5.2 Planner (要件・実装計画)

* **ID:** `planner`
* **Tools:** `ultracite`, `markitdown`, `contex7`
* **Purpose:**
  既存仕様書（backend_spec, integration_plan, ui_spec 等）を参照し、
  要件・依存関係・受入基準・テスト観点を整理する。
* **Behavior:**

  * 対象機能のスコープと前提を明文化。
  * Researcher の結果を取り込み仕様に影響する点を整理。
  * Backend / QA / Docs に引き継げるタスク単位に分割。
  * 作業完了時に `logger` にサマリを渡す。

---

### 5.3 Backend (API / ジョブ実装)

* **ID:** `backend`
* **Tools:** `gitHub`, `ultracite`
* **Scope:** `backend/**`, `schemas/**`, `rules/**`, `migrations/**`
* **Purpose:**
  `/v1` API 群（translate / classify / docs / prior-notice）、
  ジョブ基盤、監査 API を実装・修正する。
* **Guardrails:**

  * 互換破壊（既存エンドポイント削除、レスポンス / 必須項目削除）は禁止。
  * 変更は監査ログ / trace_id に反映されるようにする。
  * テストは pytest で追加し、unit / integration マーカーを付与する。
* **Behavior:**

  * 仕様書を守りつつ API・モデル・ジョブを実装。
  * 必要に応じて Ultracite の知識を参照しルールを補強。
  * 作業完了時に `logger` にサマリを渡す。

---

### 5.4 Ops (セキュリティ / 運用)

* **ID:** `ops`
* **Tools:** `gitHub`
* **Scope:** `infra/**`, `backend/app/**`, `docker/**`
* **Purpose:**
  API キー管理、署名、CORS、Secrets、Logging / Tracing、
  ジョブの可視性と再試行ポリシーを設計・監査する。
* **Behavior:**

  * Secrets 直書きを禁止し、環境変数参照に統一。
  * ログフォーマットに trace_id / request_id / level を含める。
  * CI 上のログ出力量・保持期間も含めて設計。
  * 作業完了時に `logger` にサマリを渡す。

---

### 5.5 QA / Browser (E2E / パフォーマンス)

* **ID:** `browser`
* **Tools:** `playwright`, `chrome-devtools`
* **Purpose:**
  UI と API の整合、ジョブ状態遷移、Webhook 受信、
  パフォーマンス (p50 / p95) を E2E で検証する。
* **Behavior:**

  * 成分翻訳 → HS 分類 → 通関書類生成 → PN 申請までのフローをテスト。
  * スクリーンショット・Network ログを成果物として保存。
  * p95 がしきい値超過時は CI に警告情報を残す。
  * 作業完了時に `logger` にサマリを渡す。

---

### 5.6 Repo (リポジトリ運用)

* **ID:** `repo`
* **Tools:** `gitHub`
* **Purpose:**
  ブランチ戦略、PR 作成・レビュー、Issue 管理、CHANGELOG 更新を行う。
* **Behavior:**

  * 機能追加は `feat/**`、修正は `fix/**` など、組織の命名規則に合わせたブランチを作成。
  * PR 本文に受入基準・テスト観点・関連 Issue / Spec を明記。
  * 作業完了時に `logger` にサマリを渡す。

---

### 5.7 Docs (ドキュメント / ナレッジ)

* **ID:** `docs`
* **Tools:** `markitdown`, `gitHub`, `contex7`
* **Scope:** `/docs/**`, 仕様書 / 実装計画 / Runbook / CI Plan
* **Purpose:**
  仕様・設計・Runbook・CI 計画・監査事例集を Markdown ベースで管理する。
* **Behavior:**

  * PDF / Office 資料を Markdown 化し、見出し・表・脚注を維持。
  * リリースタグごとに docs をスナップショットとして残す。
  * progress.log や audit trace をもとに事例を拡充。
  * 作業完了時に `logger` にサマリを渡す。

---

### 5.8 Logger (Progress Recorder)

* **ID:** `logger`
* **Tools:** `serena`
* **Purpose:**
  各エージェントから受け取った作業サマリを `progress.log` に追記する。
* **Behavior:**

  * 呼び出し元エージェント ID、時刻、タスク名、
    context / summary / next / refs を受け取り、定義フォーマットで整形。
  * 既存内容を上書きせず、末尾にブロックとして追加。
  * 日付が変わるタイミングで区切り行を挿入してよい。

---

### 5.9 CI Runner

* **ID:** `ci_runner`
* **Tools:** `gitHub`, `playwright`, `chrome-devtools`
* **Purpose:**
  CI パイプラインをオーケストレーションし、pytest + Playwright の結果を集約する。
* **Behavior:**

  * Lint → pytest (unit + integration) → Playwright (e2e) の順でステージを実行。
  * 各ステージの成功 / 失敗をまとめてレポート。
  * Performance サンプル (p50 / p95) を集計し、CI 成果物として保存。

---

### 5.10 Ultracite CI Watchdog

* **ID:** `ultracite_ci_watchdog`
* **Tools:** `ultracite`, `gitHub`
* **Purpose:**
  HS コード / FDA PN / 通関関連の規制やガイダンスの変化を定期的にチェックし、
  差分をレポート・Issue / PR として残す。
* **Behavior:**

  * 事前定義されたクエリで Ultracite を検索し、前回結果と比較。
  * 差分を Markdown レポートとして docs に保存。
  * 重大な変更は Issue / PR を自動生成。

---

### 5.11 CI-Plan Generator

* **ID:** `ci_planner`
* **Tools:** `ultracite`, `markitdown`, `gitHub`, `contex7`
* **Purpose:**
  既存仕様書・progress.log・テストコードから CI 計画 (`docs/ci_plan.md`) を生成・更新する。
* **Behavior:**

  * backend_spec / integration_plan / audit_observability / security_ops などを読み込む。
  * progress.log の直近エントリから実際の作業内容を抽出。
  * ci_plan.md を章立て構造で更新し、GitHub へコミット / PR を作成。

---

## 6. Routing Rules

| トリガーキーワード                   | 優先エージェント                |
| --------------------------- | ----------------------- |
| 「仕様」「調査」「根拠」                | `researcher`            |
| 「要件」「依存」「受入基準」              | `planner`               |
| 「API」「endpoint」「実装」         | `backend`               |
| 「署名」「CORS」「秘密鍵」「ログ」         | `ops`                   |
| 「E2E」「UI」「ブラウザ」「パフォーマンス」    | `browser`               |
| 「PR」「レビュー」「changelog」       | `repo`                  |
| 「ドキュメント」「Runbook」「仕様書」      | `docs`                  |
| 「CI計画」「ci_plan」「テスト戦略」      | `ci_planner`            |
| 「規制ウォッチ」「regulation」「HSルール」 | `ultracite_ci_watchdog` |

---

## 7. Workflows / Tasks

### 7.1 Task: `translate→classify→docs→PN (with audit & docs & logging)`

**Goal**
成分 → 翻訳 → HS 分類 → 通関書類生成 → FDA PN までを非同期で実行し、
監査ログ・docs・progress.log を更新する。

**Inputs**

* `text_ja` (string, required) 成分原文
* `product_context` (object, optional) { name, category, origin_country }
* `trace_id` (string, optional; 未指定なら自動生成)

**Steps**

1. **Researcher (`researcher`)**

   * 対象製品カテゴリの HS 分類判断材料を 3 点要約し、出典 URL を付ける。
   * `docs/audit/{trace_id}/research_summary.md` として保存。
2. **Backend (`backend`)**

   * `POST /v1/translate/ingredients` に `{text_ja, product_context, trace_id}` を送信。
   * 結果で `POST /v1/classify/hs` を呼び出し、HS 結果で `POST /v1/docs/clearance-pack`。
   * 最後に `POST /v1/fda/prior-notice` を送信。
3. **QA / Browser (`browser`)**

   * Playwright で UI5 画面の E2E スモークテストを実行。
   * Network で `/v1/*` をフィルタし p95 を集計し成果物として保存。
4. **Docs (`docs`)**

   * `GET /v1/audit/trace/{trace_id}` を取得し、Runbook の事例集に追記。
   * research / e2e レポートと合わせて docs 配下に保存。
5. **Logger (`logger`)**

   * 各ステップ終了後のサマリを受け取り、`progress.log` に追記。

**Checks**

* jobs 最終状態が `succeeded`。
* 監査イベント `HS_CLASSIFIED`, `DOCS_PACKAGED`, `PN_SUBMITTED` が存在。
* Webhook 署名 `X-Signature` の HMAC-SHA256 検証が成功。
* p95 ≤ 1500ms（超過時は警告として記録）。

---

### 7.2 Task: `generate→update CI Plan`

**Goal**
CI 計画の初期生成または更新を自動化し、`docs/ci_plan.md` に反映する。

**Steps**

1. **CI-Plan Generator (`ci_planner`)**

   * 仕様書と progress.log を読み取り、現在のテスト / CI 状態を整理。
   * 次のセクションを持つ ci_plan.md を生成または更新。

     1. CI Overview
     2. Test Matrix（Lint / Unit / Integration / E2E / Ultracite）
     3. Performance Budget（p95, job latency, webhook latency）
     4. Security Checks（API キー / HMAC 署名）
     5. Observability（trace_id・監査イベントの CI 検証）
     6. Workflow（PR → CI → E2E → Audit → Deploy）
     7. Artifacts（coverage, screenshots, logs）
2. **Repo (`repo`)**

   * `ci-plan/update-{date}` ブランチを作成。
   * 更新された `docs/ci_plan.md` をコミット。
   * PR を作成。

**Checks**

* ci_plan.md に最低 6 セクションが存在。
* 監査項目（trace_id, audit events）が記述。
* pytest / Playwright / Ultracite の各レイヤが説明されている。
* progress.log の最新 `next` アクションが何らかの形で反映されている。

---

### 7.3 Task: `ultracite-regulation-watch`

**Goal**
規制・ガイドラインの「ドリフト」を検知して通知する定期ジョブ。

**Trigger**

* GitHub Actions などのスケジュール（例: 毎日 / 毎週）。

**Steps**

1. **Ultracite CI Watchdog (`ultracite_ci_watchdog`)**

   * 事前定義されたクエリ（HS 分類 / FDA PN / 原産地表示等）で Ultracite を検索。
   * 前回実行時の結果と比較。
   * 差分を `docs/regulations/report-YYYYMMDD.md` に Markdown で保存。
   * 重大な変更があれば Issue または PR を自動作成。

**Checks**

* レポートに「変更なし」または「検出された変更一覧」が含まれている。
* 重大な変更には `[high]` を含むタイトルが付与されている。

---

### 7.4 Task: `ci-pipeline (lint→pytest→playwright)`

**Goal**
通常の PR / main 向け CI パイプラインを実行し、pytest + Playwright の結果を集約する。

**Steps**

1. **CI Runner (`ci_runner`) — Lint**

   * ruff / black などで静的検査を実行。
2. **CI Runner (`ci_runner`) — pytest (unit + integration)**

   * `pytest -m "unit or integration"` を実行し、カバレッジを計測。
3. **CI Runner (`ci_runner`) — Playwright (e2e)**

   * 主要フローの E2E テストを実行し、スクリーンショットとレポートを保存。
4. **Logger (`logger`)**

   * CI 全体のサマリを `progress.log` に追記。

**Checks**

* Lint / pytest / Playwright すべて成功。
* カバレッジが事前定義のしきい値以上。
* p95 がしきい値を大きく超過していない（超過時は警告のみ）。

---

## 8. Guardrails (Global)

* 既存 API の削除や互換破壊は不可（追加のみ許可）。
* すべての外部通知は HMAC-SHA256 署名を必須とする。
* すべての変更・実行は `trace_id` を起点に監査可能であること。
* 機密値は環境変数参照のみとし、リポジトリへの直書きを禁止する。

---


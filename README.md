# CrossBorder

このリポジトリは成分翻訳→HS分類→通関書類生成→PN申請を含む越境ECワークフローを実装しています。バックエンドは Docker 上の Flask アプリとして動作し、PostgreSQL に接続します。

## Docker Compose 環境

`docker compose up --build` で `db` / `backend` / `worker` / `scheduler` を立ち上げることができます。API を叩く際は `backend` サービスの 5000 番ポート（ホストの 5001 番）を利用します。

## pytest を Docker 内で動かす

CI 向けに `docker-compose.yml` には `pytest` サービスも追加され、`unit` および `integration` マーカー付きテストを実行します。事前に `db` が起動している必要があるので、`docker compose up -d db` を実行してから、以下のコマンドで pytest を走らせてください：

```
docker compose run --rm pytest
```

このコマンドは `crossborder-backend:latest` イメージを使ってテストコンテナを起動し、環境変数 `.env` を読み込むので、CI 環境でも同様に `pytest` サービスをステージとして追加すれば一貫した検証ができます。

## Lint を Docker 内で実行する

`ruff` / `black` は backend 依存に含まれているため、Docker 上で lint を走らせるには以下のコマンドを使います（`E501` は設定で無視）：

```
docker compose run --rm --entrypoint ruff backend check app tests
docker compose run --rm --entrypoint black backend --check app tests
```

CI 上でも同じ `docker compose run` をステージに追加すれば、Python のスタイル・静的検知が本番環境と同じ依存で動きます。

## Playwright で API スモークを走らせる

Playwright テストは `frontend` 内にあり、API リクエスト経由で `/v1/health` や `/v1/translate/ingredients`、`/v1/classify/hs` を叩きます。CI で Playwright を動かすには、まずバックエンドを起動してから Node の依存をインストールします。

```
docker compose up -d db backend
cd frontend
npm install
npx playwright install
npm run test:e2e
docker compose down
```

Playwright の結果は `frontend/playwright/tests` 以下の `api.spec.ts` で定義されており、CI 環境では後述の workflow で `npm run test:e2e` を実行します。ジョブ終了後は `docker compose down` してリソースを解放してください。

## Knowledge Guard（Ultracite）ジョブ

Ultracite による知識・規制チェックは通常の CI ステージではなくナイトリー／条件付きの知識ガードジョブとして実行する方針なので、`.github/workflows/knowledge-guard.yml` を用意して `docker compose run --rm pytest -m ultracite` が nightly/手動で走る仕組みにしています。CI で状況を確認したいときは `workflow_dispatch` を使ってジョブを再実行してください。

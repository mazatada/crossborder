# Developer Knowledge Base

このドキュメントは、プロジェクト開発における技術的な知見、トラブルシューティング、および再発防止策をまとめたものです。
CI/CDやGit操作で繰り返しやすいミスを防ぐための指針として機能します。

## 1. CI/Lint/Formatter (Python)

### 概要
本プロジェクトでは `ruff` (Lint), `black` (Format), `mypy` (Type Check) を使用しています。
これらは競合する可能性があるため、以下の順序と設定順守が重要です。

### ベストプラクティス
1. **実行順序**: `ruff --fix` → `black` → `mypy` の順で実行する。
   - Ruffで自動修正した後、Blackで整形し、最後に型チェックを行う。
   - Black実行後にもう一度Ruffを実行すると、整形スタイルの違反（E501など）が出る場合があるため、CI設定での制御が必要。

2. **設定ファイル**:
   - `mypy.ini` は必須。特にサードパーティライブラリ（Flask-SQLAlchemy等）のエラーを制御するために必要。
   - `types-requests` などのスタブパッケージは漏らさず `requirements.txt` に入れる。

3. **E501 (Line too long) 方針**:
   - Blackを唯一の整形ルールとし、Ruffの `E501` は **無視する**。
   - ただし可読性が著しく落ちる行はレビューで指摘して手動で折り返す。
   - 重点レビュー対象: `app/api/*`, `app/jobs/*`, `app/classify/*`
   - 個別例外は `# noqa: E501` で明示。

### Flask-SQLAlchemy と Mypy
- **問題**: `db.Column(...)` の戻り値は `Column` 型だが、Pythonのフィールド型宣言（`id: int`）と型が合わないため、代入エラー(`assignment`)が発生する。また、`db.Model` が動的生成されるため、継承元の解決に失敗する場合がある。

- **根本対策（SQLAlchemy 2.0+ & 最新プラグイン）**:
  `Mapped[int] = mapped_column(...)` を使用する。これが今後の標準。

- **現状の対策（SQLAlchemy 1.x Style）**:
  1. 親クラスには `db.Model` ではなく、宣言的ベースクラス `Base` (`from .db import Base`) を使用する。
  2. フィールド定義には明示的な型ヒントをつけ、行末に `# type: ignore` を付与して代入エラーを回避する。
     ```python
     # app/models.py
     from .db import Base
     
     class User(Base):
         id: int = db.Column(db.Integer, primary_key=True)  # type: ignore
         name: str = db.Column(db.String(64))  # type: ignore
     ```
  これにより、利用側コード（`user.id`）では `int` として推論され、定義側の整合性エラーは無視できる。

### 設定ファイル (`mypy.ini`)
- 厳格にしすぎるとサードパーティ由来の `return Any` エラーなどが大量に出るため、プロジェクトの成熟度に合わせて調整する。
- 現状の推奨設定:
  ```ini
  warn_return_any = False
  no_implicit_optional = False
  ```

## 2. Git操作

### 注意点
1. **`node_modules` の混入**:
   - `frontend/node_modules` などが過去の履歴に含まれている場合、`git add .` で再混入したり、エラーを引き起こす場合がある。
   - **対策**: ステージング時は `git add .` を避け、`git add backend .github` のように対象ディレクトリを明示する。

2. **履歴の修正**:
   - 不要ファイルが含まれてしまった場合は、`git filter-repo` 等で履歴から完全に削除するか、クリーンな状態でForce Pushを行う（チーム合意の上で）。

## 3. Pull Request 前のチェックリスト

PRを作成する前に、以下の手順をローカルで必ず実施すること。

- [ ] **Dockerコンテナ起動確認**: `docker compose ps` で `Up` 状態であること。
- [ ] **Lint & Format**:
  ```bash
  docker compose run --rm --entrypoint ruff backend check --fix app tests
  docker compose run --rm --entrypoint black backend app tests
  ```
- [ ] **Type Check**:
  ```bash
  docker compose run --rm --entrypoint mypy backend app tests
  ```
- [ ] **Test**:
  ```bash
  docker compose run --rm --entrypoint pytest backend
  ```

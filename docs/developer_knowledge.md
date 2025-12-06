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

3. **E501 (Line too long) 対策**:
   - Blackを使用している場合、Ruff/Flake8の `E501` エラーは **無視する** のが推奨設定。
   - CI (`.github/workflows/ci.yml`) では `ruff ... --ignore E501` を付与する。

### Flask-SQLAlchemy と Mypy
- `db.Model` を継承するモデルクラスでは、Mypyが動的なカラム定義を理解できない場合がある。
- **対策**: 全フィールドにPythonの型ヒントを明示する。
  ```python
  # Bad
  name = db.Column(db.String(64))

  # Good
  name: str = db.Column(db.String(64))
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
  docker compose run --rm --entrypoint mypy backend app
  ```
- [ ] **Test**:
  ```bash
  docker compose run --rm --entrypoint pytest backend
  ```

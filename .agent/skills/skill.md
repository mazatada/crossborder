pawn-4-git/antigravity_skill_test/.agent/skills/pr_review/SKILL.md
in main

---
name: PR Review (Main Branch)
description: Skill for parsing, organizing, and implementing fixes based on GitHub Pull Request review comments for PRs merging into the main branch.
---

# PR Review Skill (Main Branch) / PRレビュー修正スキル（mainブランチ向け）

This skill provides a structured workflow for addressing review comments from a GitHub Pull Request that aims to merge the current feature branch into the `main` branch.
このスキルは、現在の機能ブランチを `main` ブランチにマージすることを目的としたGitHubプルリクエストのレビュー指摘事項に対応するための構造化されたワークフローを提供します。
このスキルは、GitHubのプルリクエストにおけるレビュー指摘事項に対応するための構造化されたワークフローを提供します。

## Workflow / ワークフロー

### 1. Information Gathering / 情報収集
- Accept a PR URL or PR Number as input. / PRのURLまたはPR番号を入力として受け取ります。
- Verify the Pull Request using GitHub CLI: / GitHub CLIを使用してプルリクエストの検証を行います：
  - **Check Target Branch**: `gh pr view <number> --json baseRefName --template '{{.baseRefName}}'`
    マージ先ブランチが `main` であることを確認します。
  - **Check Source Branch**: `gh pr view <number> --json headRefName --template '{{.headRefName}}'`
    PRのマージ元ブランチ（headブランチ）が現在のローカルブランチと一致することを確認します。
- Fetch Review Comments: / レビュー指摘事項を取得します：
  - Use GitHub CLI to get all comments:
    GitHub CLIを使用してすべてのコメントを取得します：
    ```bash
    gh pr view <number> --json reviews,comments
    ```
  - Review messages might also be provided via:
    指摘事項は以下の形式で提供される場合もあります：
    - Pasted as text by the user. / ユーザーによるテキストの貼り付け。
    - Provided in a file (e.g., `reviews.md` or `comments.json`). / ファイル（例：`reviews.md` や `comments.json`）での提供。
- Identify the target files and specific line ranges mentioned in the comments.
  指摘されている対象ファイルと特定の行範囲を特定します。

### 2. Analysis and Categorization / 分析と分類
- Group comments by file. / 指摘をファイルごとにグループ化します。
- Categorize comments into: / 指摘を以下のように分類します：
  - **Critical**: Bug fixes or logic errors that must be fixed. / **重要**: 修正必須のバグや論理エラー。
  - **Stylistic**: Formatting, naming, or linting suggestions. / **スタイル**: フォーマット、命名、リンターの提案。
  - **Design/Architectural**: Suggestions for refactoring or better patterns. / **設計/構成**: リファクタリングやより良いパターンの提案。
  - **Clarification**: Questions from the reviewer that need answering or code documentation. / **確認事項**: レビュワーからの質問、回答やコードのドキュメント化が必要なもの。

### 3. Implementation Process / 実装プロセス
- For each file/group of comments: / 各ファイルまたは指摘グループについて：
  - Read the current file content to understand the context. / 文脈を理解するために現在のファイル内容を読み取ります。
  - **Incremental Fixes**: Apply the requested changes one comment at a time.
    **段階的な修正**: 1つの指摘事項ごとに変更を適用します。
  - **Commit after each fix**: Perform a `git commit` after each logical fix is applied and verified.
    **各修正後のコミット**: 論理的な修正を適用し検証した後に、その都度 `git commit` を実行します。
  - **Descriptive Commit Messages**: Include the details of the fix and reference the original comment.
    **詳細なコミットメッセージ**: 修正内容の詳細を記述し、元の指摘事項を引用または参照します。
    - *Example*: `fix: rename data variable to eventList in ConnpassService.java (PR review fix)`
  - Ensure that the changes do not break other parts of the code. / 変更がコードの他の部分を壊さないことを確認します。
  - Maintain the original coding style and project conventions. / 元のコーディングスタイルやプロジェクトの規約を維持します。

### 4. Self-Verification / 自己検証
- Verify each fix against the original comment. / 各修正が元の指摘事項を満たしているか検証します。
- Run available tests to ensure no regressions. / デグレード（先祖返り）がないことを確認するためにテストを実行します。
- If a comment suggests a change that is technically incorrect or suboptimal, prepare a brief explanation to discuss with the user.
  指摘内容が技術的に誤っている、または最適でない場合は、ユーザーと議論するための簡潔な説明を準備します。

### 5. Reporting / 報告
- Summarize the changes made. / 実施した変更の概要をまとめます。
- Note any comments that were not addressed (and why). / 対応しなかった指摘事項があれば、その理由を記録します。
- Provide a clear message that can be used as a commit message or a PR comment update.
  コミットメッセージやPRコメントの更新に使用できる明確なメッセージを提供します。

## Best Practices / ベストプラクティス
- **Atomic Commits**: If requested, group fixes into logical commits rather than one giant update.
  **原子的なコミット**: 要求に応じて、修正を一つの巨大な更新ではなく論理的なコミット単位に分割します。
- **Context is Key**: Don't just apply the suggestion blindly. Understand *why* it was suggested.
  **文脈の理解**: 提案を鵜呑みにせず、「なぜ」その提案がなされたのかを理解します。
- **Explain Decisions**: If you deviate from a reviewer's suggestion, explain the rationale clearly.
  **意思決定の説明**: レビュワーの提案とは異なる対応をする場合は、その根拠を明確に説明します。
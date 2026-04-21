# python-devcontainer-template

Python 開発用の devcontainer テンプレートです。VS Code の Dev Containers 拡張で開くと、Python 3.14 / uv / ruff / ty が揃った再現可能な開発環境がすぐに立ち上がります。

## 含まれるもの

- **ベースイメージ**: `mcr.microsoft.com/devcontainers/base:ubuntu`
- **パッケージマネージャ**: [uv](https://docs.astral.sh/uv/) (Dockerfile でプリインストール)
- **Python**: `>=3.14` (`pyproject.toml` / `.python-version` で指定)
- **リンタ / フォーマッタ**: [ruff](https://docs.astral.sh/ruff/) (`ANN` ルールで型注釈を強制)
- **型チェッカ**: [ty](https://docs.astral.sh/ty/)
- **テスト**: pytest (設定済み、依存は任意追加)
- **追加機能**: git / GitHub CLI / AWS CLI / Docker-in-Docker
- **VS Code 拡張**: `ms-python.python`, `charliermarsh.ruff`, `astral-sh.ty` ほか

## 使い方

1. このリポジトリをテンプレートとして clone する
2. VS Code で開き、コマンドパレットから **Dev Containers: Reopen in Container** を実行
3. コンテナ起動後、依存をインストール:
   ```bash
   uv sync
   ```
4. エントリポイントを実行:
   ```bash
   uv run python main.py
   ```

## 開発ワークフロー

- **保存時**: ruff が自動フォーマット + import 整列 + lint 自動修正
- **編集後フック** (`.claude/post-edit-hook.sh`): Claude Code がファイルを編集するたびに `ruff format` → `ruff check --fix` → `ty check` が走り、違反があれば差し戻される
- **手動実行**:
  ```bash
  uv run ruff format .
  uv run ruff check .
  uv run ty check
  uv run pytest
  ```

## 設定ファイル

| ファイル                | 役割                                                       |
| ----------------------- | ---------------------------------------------------------- |
| `.devcontainer/`        | devcontainer 定義 (Dockerfile, features, VS Code 拡張一覧) |
| `pyproject.toml`        | プロジェクトメタデータ / 依存 / ruff / ty の設定           |
| `.vscode/settings.json` | エディタ設定 (ruff / ty / pytest)                          |
| `.claude/`              | Claude Code のフック・権限設定                             |

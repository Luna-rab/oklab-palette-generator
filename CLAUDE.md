# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

ロジック・アルゴリズム・アーキテクチャの詳細は `README.md` を参照。本ファイルは **コーディングルール** のみを扱う。

## コミュニケーション

- ユーザーとのやり取りは **必ず日本語** で行う。
- コード内のコメント・docstring・ドキュメントも日本語で記述する。

## 主要コマンド

| 目的 | コマンド |
| --- | --- |
| 依存インストール | `uv sync` |
| エントリポイント実行 | `uv run python main.py` |
| フォーマット | `uv run ruff format .` |
| Lint (自動修正) | `uv run ruff check --fix .` |
| 型チェック | `uv run ty check` |
| 単一ファイルの型チェック | `uv run ty check <path>` |
| テスト（pytest は未導入） | `uv run pytest` |

Python バージョンは `pyproject.toml` と `.python-version` で **3.14 固定**。古い Python を使うと `uv sync` が失敗する。

## PostToolUse フック (重要)

`.claude/settings.json` で `Write|Edit|MultiEdit` に `.claude/post-edit-hook.sh` が紐付いている。Python ファイルを編集するたびに以下が順に走り、**どれか 1 つでも失敗すると編集は差し戻される**:

1. `ruff format <file>`
2. `ruff check --fix <file>`
3. `ty check <file>`

- 「フックが通らないので後で直す」はできない — 編集時点でフォーマット・lint・型エラーゼロが必須。
- フック失敗時は根本原因を直す。`# type: ignore` や `# noqa` で黙らせるのは最終手段。

## コード規約

### 型注釈 (ruff ANN)

`ANN` ルールが有効。**関数・メソッドの引数と戻り値には必ず型注釈を付ける**。`*args` / `**kwargs` も含む。

### ty

- `unused-ignore-comment` / `unused-type-ignore-comment` が `error` 扱い（`pyproject.toml` の `[tool.ty.rules]`）。不要な `# type: ignore` は削除する。

### コメントの方針

- **Why を書き、What は書かない**。識別子で読み取れる内容（何をしているか）はコメントにしない。
- WHY が非自明な箇所にだけコメントを置く: 隠れた制約・暗黙の不変条件・ワークアラウンド・驚きを生む挙動。
- 完結した日本語で書く（セッションや PR 文脈に依存しない）。

### 行長

ruff の `line-length = 99`、`E501` は無視設定。つまり長い行を自分で折り返す必要はないが、読みやすさが落ちるなら適宜改行する。

## ディレクトリ構成

- `src/palette.py` — コア実装
- `main.py` — デモ用エントリポイント
- `.claude/` — Claude Code の設定・フック・スラッシュコマンド
  - `INSTRUCTION.md` — 元の実装仕様
  - `post-edit-hook.sh` — ruff/ty ゲート
- `.devcontainer/` — Dev Container 定義
- `README.md` — プロジェクトの目的・アルゴリズム・使い方
